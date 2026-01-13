from math import ceil
import cv2
import numpy as np
import io
import flags
from utils import (
    reconstruct_block,
    decode_char_code_mapping,
    minimize_block,
    BitStreamWriter,
    BitStreamReader,
    get_espresso_cost,
    apply_zigzag_xor_4x4,
    reverse_zigzag_xor_4x4,
    numpy_binary_to_gray,
    numpy_gray_to_binary,
)
from stats import CompressionStats, _collect_stats_from_node

ENCODING_HOMOGENEOUS_0 = 0b00
ENCODING_HOMOGENEOUS_1 = 0b01
ENCODING_INTERNAL = 0b10
ENCODING_HETEROGENEOUS = 0b11


class QuadTree:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.color = None
        self.minimized = None
        self.raw_block_data = None
        self.subtype = None
        self.children = []
        self.discarded_minimized_data = None
        self.xor_applied = False

    def subdivide(self, block_data):
        blk = block_data

        if np.all(blk == blk.flat[0]):
            self.color = int(blk.flat[0])
            return

        if self.w <= 8 and self.h <= 8:
            work_blk = blk.copy()

            raw_cost = self.w * self.h
            min_data = minimize_block(work_blk)
            espresso_cost = get_espresso_cost(min_data, use_3_bit_cube_count=True)

            if espresso_cost < raw_cost:
                self.subtype = "espresso"
                self.minimized = min_data
                self.xor_applied = False
                return

            if flags.PREDICTIVE_XOR_8X8_MODE:
                xor_blk = blk.copy()
                apply_zigzag_xor_4x4(xor_blk)

                min_data_xor = minimize_block(xor_blk)
                espresso_cost_xor = get_espresso_cost(
                    min_data_xor, use_3_bit_cube_count=True
                )

                if espresso_cost_xor < raw_cost:
                    self.subtype = "espresso"
                    self.minimized = min_data_xor
                    self.xor_applied = True
                else:
                    self.subtype = "raw"
                    self.raw_block_data = xor_blk
                    self.discarded_minimized_data = min_data_xor
                    self.xor_applied = True
            else:
                self.subtype = "raw"
                self.raw_block_data = work_blk
                self.discarded_minimized_data = min_data
            return

        w1, h1 = (self.w + 1) // 2, (self.h + 1) // 2
        w2, h2 = self.w - w1, self.h - h1

        child_info = [
            ((0, 0, w1, h1), blk[0:h1, 0:w1]),
            ((w1, 0, w2, h1), blk[0:h1, w1 : w1 + w2]),
            ((0, h1, w1, h2), blk[h1 : h1 + h2, 0:w1]),
            ((w1, h1, w2, h2), blk[h1 : h1 + h2, w1 : w1 + w2]),
        ]

        for (dx, dy, ww, hh), child_slice in child_info:
            if ww > 0 and hh > 0:
                child = QuadTree(self.x + dx, self.y + dy, ww, hh)
                child.subdivide(child_slice)
                self.children.append(child)

    def to_dict(self):
        if not self.children:
            node = {"type": "leaf", "x": self.x, "y": self.y, "w": self.w, "h": self.h}
            if self.color is not None:
                node["code"] = "11" if self.color == 1 else "10"
            elif self.subtype == "espresso":
                node["subtype"] = "espresso"
                node["data"] = self.minimized
                if flags.PREDICTIVE_XOR_8X8_MODE and self.w == 8 and self.h == 8:
                    node["xor_applied"] = self.xor_applied
            elif self.subtype == "raw":
                node["subtype"] = "raw"
                node["data"] = self.raw_block_data.tolist()
                if self.discarded_minimized_data:
                    node["discarded_minimized_data"] = self.discarded_minimized_data
                if flags.PREDICTIVE_XOR_8X8_MODE and self.w == 8 and self.h == 8:
                    node["xor_applied"] = self.xor_applied
            else:
                node["code"] = "10"
            return node
        return {
            "type": "node",
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "children": [c.to_dict() for c in self.children],
        }


def compress_image_to_bitstream(image_path):
    arr = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if arr is None:
        raise FileNotFoundError(f"Could not read image at {image_path}")
    h_original, w_original = arr.shape
    h_padded, w_padded = ceil(h_original / 64) * 64, ceil(w_original / 64) * 64
    padded_arr = np.pad(
        arr,
        ((0, h_padded - h_original), (0, w_padded - w_original)),
        mode="constant",
        constant_values=0,
    )
    h, w = padded_arr.shape
    byte_stream = io.BytesIO()
    writer = BitStreamWriter(byte_stream)
    stats = CompressionStats()
    stats.raw_bits = h * w * 8

    if flags.GRAY_PIXELS_MODE:
        padded_arr = numpy_binary_to_gray(padded_arr)

    for bit in range(8):
        stats._init_plane_stats(bit)
        plane_arr = ((padded_arr >> bit) & 1).astype(np.uint8)
        for y0 in range(0, h, 64):
            for x0 in range(0, w, 64):
                tile = plane_arr[y0 : y0 + 64, x0 : x0 + 64]
                root = QuadTree(0, 0, 64, 64)
                root.subdivide(tile)
                node_dict = root.to_dict()
                temp_stream = io.BytesIO()
                temp_writer = BitStreamWriter(temp_stream)
                encode_quadtree_node_bitstream(node_dict, temp_writer)
                temp_writer.flush()
                quadtree_cost_bits = len(temp_stream.getvalue()) * 8
                if quadtree_cost_bits >= tile.size:
                    stats.plane_stats[bit]["raw_64_blocks"] += 1
                    _collect_stats_from_node(node_dict, stats, bit, is_overflow=True)
                    writer.write_bit(1)
                    for pixel in tile.flat:
                        writer.write_bit(int(pixel))
                else:
                    stats.plane_stats[bit]["quadtree_64_blocks"] += 1
                    _collect_stats_from_node(node_dict, stats, bit, is_overflow=False)
                    writer.write_bit(0)
                    encode_quadtree_node_bitstream(node_dict, writer)

    writer.flush()
    compressed_data = byte_stream.getvalue()

    stats.compressed_bits = len(compressed_data) * 8
    return {
        "bitstream": compressed_data,
        "width": w,
        "height": h,
        "original_width": w_original,
        "original_height": h_original,
        "stats": stats,
    }


def decompress_image_from_bitstream(bitstream, padded_width, padded_height):
    byte_stream = io.BytesIO(bitstream)
    reader = BitStreamReader(byte_stream)
    final_arr = np.zeros((padded_height, padded_width), dtype=np.uint8)

    for bit in range(8):
        plane_arr = np.zeros((padded_height, padded_width), dtype=np.uint8)
        for y0 in range(0, padded_height, 64):
            for x0 in range(0, padded_width, 64):
                if reader.read_bit() == 1:
                    for r_offset in range(64):
                        for c_offset in range(64):
                            pixel = reader.read_bit()
                            if pixel is None:
                                return None
                            if (y0 + r_offset < padded_height) and (
                                x0 + c_offset < padded_width
                            ):
                                plane_arr[y0 + r_offset, x0 + c_offset] = pixel
                else:
                    root_node_dict = decode_quadtree_node_bitstream(
                        reader, 0, 0, 64, 64
                    )
                    if root_node_dict is None:
                        return None
                    tile_plane = np.zeros((64, 64), dtype=np.uint8)
                    reconstruct_from_quadtree_node(root_node_dict, tile_plane)
                    plane_arr[y0 : y0 + 64, x0 : x0 + 64] = tile_plane

        final_arr |= plane_arr << bit

    if flags.GRAY_PIXELS_MODE:
        final_arr = numpy_gray_to_binary(final_arr)

    return final_arr


def encode_quadtree_node_bitstream(node, writer):
    if node["type"] == "leaf":
        if node.get("subtype") in ("raw", "espresso"):
            writer.write_bits(ENCODING_HETEROGENEOUS, 2)

            if node["subtype"] == "raw":
                writer.write_bit(1)
                writer.write_bit(
                    1
                    if (node.get("xor_applied") and node["w"] == 8 and node["h"] == 8)
                    else 0
                )
                raw = np.array(node["data"])
                for b in raw.flat:
                    writer.write_bit(int(b))
            else:
                writer.write_bit(0)
                writer.write_bit(
                    1
                    if (node.get("xor_applied") and node["w"] == 8 and node["h"] == 8)
                    else 0
                )
                encode_minimized_block_bitstream(node["data"], writer)

        elif "code" in node:
            if node["code"] == "10":
                writer.write_bits(ENCODING_HOMOGENEOUS_0, 2)
            elif node["code"] == "11":
                writer.write_bits(ENCODING_HOMOGENEOUS_1, 2)

    else:
        writer.write_bits(ENCODING_INTERNAL, 2)
        for c in node["children"]:
            encode_quadtree_node_bitstream(c, writer)


def encode_minimized_block_bitstream(minimized_data, writer):
    code = minimized_data.get("code", "00")
    cubes = minimized_data.get("cubes", [])
    encoding_map = minimized_data.get("encoding_map", {})
    map_value = minimized_data.get("map_value", 0)
    writer.write_bit(0 if code == "00" else 1)
    writer.write_bits(map_value, 3)
    writer.write_bits(len(cubes), 3)
    for inp, out in cubes:
        for char in inp:
            encoded_char_code = encoding_map.get(char, "10")
            if encoded_char_code == "0":
                writer.write_bit(0)
            elif encoded_char_code == "10":
                writer.write_bits(0b10, 2)
            elif encoded_char_code == "11":
                writer.write_bits(0b11, 2)
        writer.write_bit(int(out))


def decode_quadtree_node_bitstream(reader, x, y, w, h):
    t = reader.read_bits(2)
    if t is None:
        return None

    node = {"x": x, "y": y, "w": w, "h": h}

    if t == ENCODING_HOMOGENEOUS_0:
        node.update({"type": "leaf", "code": "10"})

    elif t == ENCODING_HOMOGENEOUS_1:
        node.update({"type": "leaf", "code": "11"})

    elif t == ENCODING_INTERNAL:
        node.update({"type": "node", "children": []})
        w1, h1 = (w + 1) // 2, (h + 1) // 2
        w2, h2 = w - w1, h - h1
        for dx, dy, ww, hh in [
            (0, 0, w1, h1),
            (w1, 0, w2, h1),
            (0, h1, w1, h2),
            (w1, h1, w2, h2),
        ]:
            if ww > 0 and hh > 0:
                node["children"].append(
                    decode_quadtree_node_bitstream(reader, x + dx, y + dy, ww, hh)
                )

    elif t == ENCODING_HETEROGENEOUS:
        node["type"] = "leaf"

        raw_flag = reader.read_bit()
        xor_flag = reader.read_bit() if (w == 8 and h == 8) else 0
        node["xor_applied"] = bool(xor_flag)

        if raw_flag == 1:
            data = [reader.read_bit() for _ in range(w * h)]
            node.update(
                {
                    "subtype": "raw",
                    "data": np.array(data, dtype=np.uint8).reshape((h, w)),
                }
            )
        else:
            node.update(
                {
                    "subtype": "espresso",
                    "data": decode_minimized_block_bitstream(reader),
                }
            )

    return node


def decode_minimized_block_bitstream(reader):
    code = "00" if reader.read_bit() == 0 else "01"
    map_value = reader.read_bits(3)
    _, decoding_code_map = decode_char_code_mapping(map_value)
    n_bits = 6
    num_cubes = reader.read_bits(3)
    cubes = []
    for _ in range(num_cubes):
        inp = "".join(
            reader.read_variable_code(decoding_code_map) for _ in range(n_bits)
        )
        out = str(reader.read_bit())
        cubes.append((inp, out))
    return {"code": code, "cubes": cubes, "n_bits": n_bits}


def reconstruct_from_quadtree_node(node, plane_arr):
    x, y, w, h = node["x"], node["y"], node["w"], node["h"]
    if node["type"] == "leaf":
        if node.get("subtype") == "espresso":
            blk = reconstruct_block(node["data"], w, h)
        elif node.get("subtype") == "raw":
            blk = node["data"]
        else:
            blk = 1 if node.get("code") == "11" else 0
            blk = np.full((h, w), blk, dtype=np.uint8)

        if flags.PREDICTIVE_XOR_8X8_MODE and w == 8 and h == 8 and node.get("subtype"):
            if node.get("xor_applied"):
                reverse_zigzag_xor_4x4(blk)

        plane_arr[y : y + h, x : x + w] = blk
    elif node["type"] == "node" and "children" in node:
        for child in node["children"]:
            reconstruct_from_quadtree_node(child, plane_arr)
