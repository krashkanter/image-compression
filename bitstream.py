from math import ceil
import cv2
import numpy as np
import io
import flags
import concurrent.futures
from utils import (
    reconstruct_block,
    decode_char_code_mapping,
    minimize_block,
    BitStreamWriter,
    BitStreamReader,
    get_espresso_cost,
    load_templates,
)
from stats import CompressionStats, _collect_stats_from_node

ENCODING_HOMOGENEOUS_0 = 0b00
ENCODING_HOMOGENEOUS_1 = 0b01
ENCODING_INTERNAL = 0b10
ENCODING_HETEROGENEOUS = 0b11

# ESCAPE CODE: If cube count is 7 (111), it signals a Template Match
TEMPLATE_ESCAPE_COUNT = 7


class IntCaptureWriter:
    """Helper class to capture bits into an integer for parallel processing."""

    def __init__(self):
        self.value = 0
        self.count = 0

    def write_bit(self, bit):
        self.value = (self.value << 1) | bit
        self.count += 1

    def write_bits(self, value, num_bits):
        if num_bits > 0:
            val_masked = value & ((1 << num_bits) - 1)
            self.value = (self.value << num_bits) | val_masked
            self.count += num_bits

    def flush(self):
        pass


class QuadTree:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.color = None
        self.minimized = None
        self.raw_block_data = None
        self.subtype = None
        self.children = []
        self.discarded_minimized_data = None
        self.alternative_subdivision = None
        self.template_id = 0
        self.bits_saved = 0

    def subdivide(self, block_data, templates=None):
        blk = block_data

        if np.all(blk == blk.flat[0]):
            self.color = int(blk.flat[0])
            return

        if flags.PURE_QUADTREE_MODE:
            if self.w == 4 and self.h == 4:
                self.subtype = "raw"
                self.raw_block_data = blk
                self.discarded_minimized_data = {}
                return
        else:
            if self.w == 4 and self.h == 4:
                self.subtype = "raw"
                self.raw_block_data = blk
                self.discarded_minimized_data = {}
                return

            if self.w == 8 and self.h == 8:
                raw_cost = self.w * self.h  # 64 bits
                min_data = minimize_block(blk)
                espresso_cost = get_espresso_cost(min_data, use_3_bit_cube_count=True)

                # COMPRESSION OPTIMIZATION:
                # We reserve cube_count=7 for templates.
                # If Espresso naturally has >= 7 cubes, we force fallback to Raw/Template.
                num_cubes = len(min_data.get("cubes", []))

                if raw_cost <= espresso_cost or num_cubes >= TEMPLATE_ESCAPE_COUNT:
                    # Incompressible Block logic
                    best_template_id = 0
                    best_template_min = None
                    best_template_cost = raw_cost

                    if templates:
                        for i, tmpl in enumerate(templates[:7]):
                            if tmpl.shape != (8, 8):
                                continue

                            xor_diff = blk ^ tmpl
                            diff_min = minimize_block(xor_diff)

                            # Ensure diff doesn't exceed encoding limits (though unlikely for diff)
                            if len(diff_min.get("cubes", [])) >= 8:
                                continue

                            # Cost: Espresso Cost + 3 bits (Header)
                            diff_cost = (
                                get_espresso_cost(diff_min, use_3_bit_cube_count=True)
                                + 3
                            )

                            if diff_cost < best_template_cost:
                                best_template_cost = diff_cost
                                best_template_id = i + 1
                                best_template_min = diff_min

                    if best_template_id > 0:
                        self.subtype = "template_match"
                        self.template_id = best_template_id
                        self.minimized = best_template_min
                        self.bits_saved = raw_cost - best_template_cost
                    else:
                        self.subtype = "raw"
                        self.raw_block_data = blk
                        self.discarded_minimized_data = min_data

                else:
                    self.subtype = "espresso"
                    self.minimized = min_data
                    self.alternative_subdivision = self._create_4x4_subdivision(blk)

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
                child.subdivide(child_slice, templates)
                self.children.append(child)

    def _create_4x4_subdivision(self, blk):
        w1, h1 = (self.w + 1) // 2, (self.h + 1) // 2
        w2, h2 = self.w - w1, self.h - h1

        child_info = [
            ((0, 0, w1, h1), blk[0:h1, 0:w1]),
            ((w1, 0, w2, h1), blk[0:h1, w1 : w1 + w2]),
            ((0, h1, w1, h2), blk[h1 : h1 + h2, 0:w1]),
            ((w1, h1, w2, h2), blk[h1 : h1 + h2, w1 : w1 + w2]),
        ]

        subdivision_data = []
        for (dx, dy, ww, hh), child_slice in child_info:
            if ww > 0 and hh > 0:
                child_data = {
                    "x": self.x + dx,
                    "y": self.y + dy,
                    "w": ww,
                    "h": hh,
                }
                if np.all(child_slice == child_slice.flat[0]):
                    child_data["color"] = int(child_slice.flat[0])
                    child_data["cost"] = 1
                else:
                    child_data["data"] = child_slice.tolist()
                    child_data["cost"] = ww * hh
                subdivision_data.append(child_data)

        return {
            "children": subdivision_data,
            "total_cost": sum(c["cost"] for c in subdivision_data),
        }

    def to_dict(self):
        if not self.children:
            node = {"type": "leaf", "x": self.x, "y": self.y, "w": self.w, "h": self.h}
            if self.color is not None:
                node["code"] = "11" if self.color == 1 else "10"
            elif self.subtype == "espresso":
                node["subtype"] = "espresso"
                node["data"] = self.minimized
                if self.alternative_subdivision:
                    node["alternative_subdivision"] = self.alternative_subdivision
            elif self.subtype == "template_match":
                node["subtype"] = "template_match"
                node["template_id"] = self.template_id
                node["data"] = self.minimized
                node["bits_saved"] = self.bits_saved
            elif self.subtype == "raw":
                node["subtype"] = "raw"
                node["data"] = self.raw_block_data.tolist()
                if self.discarded_minimized_data:
                    node["discarded_minimized_data"] = self.discarded_minimized_data
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


def _worker_process_row_chunk(row_data, bit, templates):
    results = []
    for tile, x, y in row_data:
        root = QuadTree(0, 0, 64, 64)
        root.subdivide(tile, templates)
        node_dict = root.to_dict()

        temp_writer = IntCaptureWriter()
        encode_quadtree_node_bitstream(node_dict, temp_writer)
        quadtree_cost_bits = temp_writer.count

        final_writer = IntCaptureWriter()
        is_overflow = False

        if quadtree_cost_bits >= tile.size:
            is_overflow = True
            final_writer.write_bit(1)
            for pixel in tile.flat:
                final_writer.write_bit(int(pixel))
        else:
            is_overflow = False
            final_writer.write_bit(0)
            encode_quadtree_node_bitstream(node_dict, final_writer)

        results.append((is_overflow, final_writer.value, final_writer.count, node_dict))
    return results


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

    # Load templates ONCE to avoid Disk I/O bottleneck
    templates = load_templates()

    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures_map = {}

        for bit in range(8):
            stats._init_plane_stats(bit)
            plane_arr = ((padded_arr >> bit) & 1).astype(np.uint8)

            row_idx = 0
            for y0 in range(0, h, 64):
                row_tiles_data = []
                for x0 in range(0, w, 64):
                    tile = plane_arr[y0 : y0 + 64, x0 : x0 + 64].copy()
                    row_tiles_data.append((tile, x0, y0))

                f = executor.submit(
                    _worker_process_row_chunk, row_tiles_data, bit, templates
                )
                futures_map[(bit, row_idx)] = f
                row_idx += 1

        for bit in range(8):
            row_idx = 0
            for y0 in range(0, h, 64):
                f = futures_map[(bit, row_idx)]
                row_results = f.result()

                for res in row_results:
                    is_overflow, bits_val, bits_count, node_dict = res
                    if is_overflow:
                        stats.plane_stats[bit]["raw_64_blocks"] += 1
                        _collect_stats_from_node(
                            node_dict, stats, bit, is_overflow=True
                        )
                    else:
                        stats.plane_stats[bit]["quadtree_64_blocks"] += 1
                        _collect_stats_from_node(
                            node_dict, stats, bit, is_overflow=False
                        )

                    writer.write_bits(bits_val, bits_count)
                row_idx += 1

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


def xor_compress_image(image_path):
    # 1: Load grayscale image
    arr = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if arr is None:
        raise FileNotFoundError("Could not load image")

    h_org, w_org = arr.shape

    # 2: Pad to nearest multiple of 64
    H = ceil(h_org / 64) * 64
    W = ceil(w_org / 64) * 64
    padded = np.pad(
        arr, ((0, H - h_org), (0, W - w_org)), mode="constant", constant_values=0
    )

    # Storage for final XOR bitstream of all planes
    full_bitstream = []

    # 3: For each bit-plane (0 to 7)
    for bit in range(8):
        # Extract bit-plane
        plane = ((padded >> bit) & 1).astype(np.uint8)

        # List to store XOR blocks for this bit-plane
        bitstream_plane = []

        # 4: Process 8×8 blocks
        for y in range(0, H, 8):
            for x in range(0, W, 8):
                block = plane[y : y + 8, x : x + 8]

                # First block in each row → keep unchanged
                if x == 0:
                    xor_block = block
                else:
                    left_block = plane[y : y + 8, x - 8 : x]
                    xor_block = block ^ left_block

                # Convert XOR block to 64-bit bitstream
                bits = xor_block.flatten().tolist()
                bitstream_plane.extend(bits)

        full_bitstream.append(bitstream_plane)

    return {
        "padded_width": W,
        "padded_height": H,
        "original_width": w_org,
        "original_height": h_org,
        "bitstream_per_plane": full_bitstream,
    }


def decompress_image_from_bitstream(bitstream, padded_width, padded_height):
    byte_stream = io.BytesIO(bitstream)
    reader = BitStreamReader(byte_stream)
    final_arr = np.zeros((padded_height, padded_width), dtype=np.uint8)

    templates = load_templates()

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
                        reader, 0, 0, 64, 64, templates
                    )
                    if root_node_dict is None:
                        return None
                    tile_plane = np.zeros((64, 64), dtype=np.uint8)
                    reconstruct_from_quadtree_node(
                        root_node_dict, tile_plane, templates
                    )
                    plane_arr[y0 : y0 + 64, x0 : x0 + 64] = tile_plane
        final_arr |= plane_arr << bit
    return final_arr


def encode_quadtree_node_bitstream(node, writer):
    if node["type"] == "leaf":
        if node.get("subtype") == "espresso":
            writer.write_bits(ENCODING_HETEROGENEOUS, 2)  # 11
            writer.write_bit(0)  # 0 = Espresso
            encode_minimized_block_bitstream(node["data"], writer)

        elif node.get("subtype") == "raw":
            writer.write_bits(ENCODING_HETEROGENEOUS, 2)  # 11
            writer.write_bit(1)  # 1 = Raw (Standard 3-bit prefix restored)
            raw_block_data = np.array(node["data"])
            for pixel in raw_block_data.flat:
                writer.write_bit(int(pixel))

        elif node.get("subtype") == "template_match":
            # TEMPLATE ENCODING: Hijack Espresso Branch
            writer.write_bits(ENCODING_HETEROGENEOUS, 2)  # 11
            writer.write_bit(0)  # 0 = Espresso (Fake)

            # Fake Espresso Header with Escape Code
            # code=0 (1 bit), map=0 (3 bits), count=7 (3 bits) -> 111
            writer.write_bit(0)
            writer.write_bits(0, 3)
            writer.write_bits(TEMPLATE_ESCAPE_COUNT, 3)

            # Template Data
            t_id = node.get("template_id", 0)
            writer.write_bits(t_id, 3)
            encode_minimized_block_bitstream(node["data"], writer)

        elif "code" in node:
            if node["code"] == "10":
                writer.write_bits(ENCODING_HOMOGENEOUS_0, 2)
            elif node["code"] == "11":
                writer.write_bits(ENCODING_HOMOGENEOUS_1, 2)
    elif node["type"] == "node":
        writer.write_bits(ENCODING_INTERNAL, 2)
        for child in node["children"]:
            encode_quadtree_node_bitstream(child, writer)


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


def decode_quadtree_node_bitstream(reader, x, y, w, h, templates=None):
    node_encoding = reader.read_bits(2)
    if node_encoding is None:
        return None
    node = {"x": x, "y": y, "w": w, "h": h}
    if node_encoding == ENCODING_HOMOGENEOUS_0:
        node.update({"type": "leaf", "code": "10"})
    elif node_encoding == ENCODING_HOMOGENEOUS_1:
        node.update({"type": "leaf", "code": "11"})
    elif node_encoding == ENCODING_INTERNAL:
        node.update({"type": "node", "children": []})
        w1, h1 = (w + 1) // 2, (h + 1) // 2
        w2, h2 = w - w1, h - h1
        child_positions = [
            (0, 0, w1, h1),
            (w1, 0, w2, h1),
            (0, h1, w1, h2),
            (w1, h1, w2, h2),
        ]
        for dx, dy, ww, hh in child_positions:
            if ww > 0 and hh > 0:
                child_node = decode_quadtree_node_bitstream(
                    reader, x + dx, y + dy, ww, hh, templates
                )
                if child_node:
                    node["children"].append(child_node)
    elif node_encoding == ENCODING_HETEROGENEOUS:
        node["type"] = "leaf"
        if reader.read_bit() == 0:
            # Espresso or Template? Check header.
            # We must peek or just read the standard Espresso header bits first
            # encode_minimized_block_bitstream starts with 1 bit code, 3 bit map, 3 bit count

            code_bit = reader.read_bit()
            map_val = reader.read_bits(3)
            count_val = reader.read_bits(3)

            if count_val == TEMPLATE_ESCAPE_COUNT:
                # Template Match
                t_id = reader.read_bits(3)
                diff_data = decode_minimized_block_bitstream(reader)
                node.update(
                    {
                        "subtype": "template_match",
                        "template_id": t_id,
                        "data": diff_data,
                    }
                )
            else:
                # Standard Espresso - Manually reconstruct the start since we read bits
                # Re-using decode helper requires stream rewind or passing args.
                # Easier to just copy-paste the rest of decode logic here for efficiency.

                # Logic from decode_minimized_block_bitstream:
                code = "00" if code_bit == 0 else "01"
                _, decoding_code_map = decode_char_code_mapping(map_val)
                n_bits = 6
                num_cubes = count_val
                cubes = []
                for _ in range(num_cubes):
                    inp = "".join(
                        reader.read_variable_code(decoding_code_map)
                        for _ in range(n_bits)
                    )
                    out = str(reader.read_bit())
                    cubes.append((inp, out))

                data = {"code": code, "cubes": cubes, "n_bits": n_bits}
                node.update({"subtype": "espresso", "data": data})
        else:
            # Raw
            raw_block = [reader.read_bit() for _ in range(w * h)]
            node.update(
                {
                    "subtype": "raw",
                    "data": np.array(raw_block, dtype=np.uint8).reshape((h, w)),
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


def reconstruct_from_quadtree_node(node, plane_arr, templates=None):
    x, y, w, h = node["x"], node["y"], node["w"], node["h"]
    if node["type"] == "leaf":
        if node.get("subtype") == "espresso":
            blk = reconstruct_block(node["data"], w, h)
        elif node.get("subtype") == "raw":
            blk = node["data"]
        elif node.get("subtype") == "template_match":
            diff = reconstruct_block(node["data"], w, h)
            t_id = node.get("template_id", 0)
            if templates and 1 <= t_id <= len(templates):
                tmpl = templates[t_id - 1]
                if tmpl.shape == diff.shape:
                    blk = diff ^ tmpl
                else:
                    blk = diff
            else:
                blk = diff
        else:
            blk = 1 if node.get("code") == "11" else 0
        plane_arr[y : y + h, x : x + w] = blk
    elif node["type"] == "node" and "children" in node:
        for child in node["children"]:
            reconstruct_from_quadtree_node(child, plane_arr, templates)
