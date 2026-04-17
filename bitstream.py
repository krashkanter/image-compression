from math import ceil
import cv2
import numpy as np
import io
import flags
from utils import (
    reconstruct_block,
    decode_char_code_mapping,
    minimize_block,
    get_espresso_cost,
    load_templates,
    numpy_binary_to_gray,
    numpy_gray_to_binary,
)
from stats import SimpleStats, _collect_stats_from_node

ENCODING_HOMOGENEOUS_0 = 0b00
ENCODING_HOMOGENEOUS_1 = 0b01
ENCODING_INTERNAL = 0b10
ENCODING_HETEROGENEOUS = 0b11

# New Subtype Encodings (2 bits appended to 11)
SUBTYPE_ESPRESSO = 0b00  # 1100
SUBTYPE_TEMPLATE = 0b01  # 1101
SUBTYPE_RAW      = 0b11  # 1111
# 1110 is unused

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
        self.best_candidate = None # (id, cube_count)

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
                # Add 4 bits for Subtype Header (1100)
                espresso_cost = get_espresso_cost(min_data, use_3_bit_cube_count=True) + 4

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

                        # Ensure diff doesn't exceed encoding limits
                        if len(diff_min.get("cubes", [])) >= 8:
                            continue

                        # Cost: Espresso Cost + 3 bits (Header)
                        # Note: Espresso Cost includes its own header overhead in get_espresso_cost?
                        # get_espresso_cost adds 1+3 (header) + 3 (count).
                        # For template, we have 1101 (4) + ID (3) + diff_min body.
                        # diff_min body is what get_espresso_cost returns minus the header?
                        # Actually get_espresso_cost returns full cost.
                        # Let's approximate: 
                        # Template Total = 4 (Prefix) + 3 (ID) + (Espresso Cost of Diff - 4 (Espresso Header 1100))
                        # Wait, Espresso header is 1100 (4 bits).
                        # get_espresso_cost assumes standard espresso.
                        # Let's just check if the resulting bitstream length > 64.
                        
                        # We can't easily get exact bitstream length without encoding, 
                        # but we can estimate or just use the cost function.
                        
                        # Let's use the raw cost comparison first to pick the best template.
                        # Add 4 bits for Subtype Header (1101)
                        diff_cost = get_espresso_cost(diff_min, use_3_bit_cube_count=True) + 4
                        
                        if diff_cost < best_template_cost:
                            best_template_cost = diff_cost
                            best_template_id = i + 1
                            best_template_min = diff_min

                if best_template_id > 0 and best_template_min:
                    cube_count = len(best_template_min.get("cubes", []))
                    self.best_candidate = (best_template_id, cube_count)

                # Now decide between Raw, Espresso, and Template
                
                # 1. Template vs Raw
                # Header: 1101 (4 bits) + ID (3 bits) = 7 bits overhead
                # Payload: best_template_min encoded size
                # If Total > 64, force Raw.
                
                # We need to know the exact size of the template encoding to be sure.
                # get_espresso_cost returns: header(4) + count(3) + data.
                # Our template encoding is: 1101(4) + ID(3) + [code(1) + map(3) + count(3) + data]
                # So Template Size = 7 + (Espresso Cost - 4 (old header?))
                # Actually get_espresso_cost in utils.py: header_cost = 1 + 3 = 4.
                # So Template Size = 7 + (Espresso Cost - 4) = Espresso Cost + 3.
                
                template_total_bits = best_template_cost + 3 if best_template_id > 0 else 9999
                
                # 2. Espresso vs Raw
                # Header: 1100 (4 bits)
                # Espresso Cost in utils includes 4 bits header.
                # So Espresso Total = Espresso Cost.
                
                if raw_cost <= espresso_cost and raw_cost <= template_total_bits:
                     self.subtype = "raw"
                     self.raw_block_data = blk
                     self.discarded_minimized_data = min_data
                elif template_total_bits < espresso_cost and template_total_bits < raw_cost:
                    self.subtype = "template_match"
                    self.template_id = best_template_id
                    self.minimized = best_template_min
                    self.bits_saved = raw_cost - template_total_bits
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
            
            if self.best_candidate:
                node["best_candidate"] = self.best_candidate
                
            return node
        return {
            "type": "node",
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "children": [c.to_dict() for c in self.children],
        }


# Helper functions for direct list manipulation
def write_bits(bitstream, value, num_bits):
    for i in range(num_bits):
        bit = (value >> (num_bits - 1 - i)) & 1
        bitstream.append(bit)

def read_bits(bitstream, num_bits):
    value = 0
    for _ in range(num_bits):
        if not bitstream:
            return None
        bit = bitstream.pop(0)
        value = (value << 1) | bit
    return value

def read_bit(bitstream):
    if not bitstream:
        return None
    return bitstream.pop(0)

def read_variable_code(bitstream, decoding_map):
    buffer = []
    max_code_len = 2
    while len(buffer) < max_code_len:
        bit = read_bit(bitstream)
        if bit is None:
            return None
        buffer.append(str(bit))
        current_code = "".join(buffer)
        if current_code in decoding_map:
            return decoding_map[current_code]
    return None


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
    
    if flags.GRAY_PIXELS_MODE:
        padded_arr = numpy_binary_to_gray(padded_arr)

    # The bitstream is just a simple list of 0s and 1s
    bitstream = []
    
    stats = SimpleStats()
    stats.original_bits = h_original * w_original * 8

    # Load templates ONCE to avoid Disk I/O bottleneck
    templates = load_templates()

    # Sequential processing
    # Sequential processing
    for bit in range(8):
        plane_arr = ((padded_arr >> bit) & 1).astype(np.uint8)

        for y0 in range(0, h, 64):
            for x0 in range(0, w, 64):
                tile = plane_arr[y0 : y0 + 64, x0 : x0 + 64].copy()
                
                root = QuadTree(0, 0, 64, 64)
                root.subdivide(tile, templates)
                node_dict = root.to_dict()

                # Check if quadtree is better than raw
                temp_bitstream = []
                encode_quadtree_node_bitstream(node_dict, temp_bitstream)
                
                if len(temp_bitstream) >= tile.size:
                    # Overflow: store as raw
                    bitstream.append(1)
                    for pixel in tile.flat:
                        bitstream.append(int(pixel))
                    
                    # Record stats for RAW overflow
                    raw_stats = stats._create_empty_plane_stats()
                    raw_stats["total_blocks"] = 1
                    raw_stats["block_counts"]["raw"] = 1
                    stats.update_plane_stats(bit, raw_stats)

                else:
                    # Quadtree is better
                    bitstream.append(0)
                    bitstream.extend(temp_bitstream)
                    
                    # Collect stats for Quadtree
                    node_stats = stats._create_empty_plane_stats()
                    _collect_stats_from_node(node_dict, node_stats)
                    stats.update_plane_stats(bit, node_stats)

    # Convert to numpy array for final storage
    compressed_data = np.array(bitstream, dtype=np.uint8)
    stats.compressed_bits = len(compressed_data)
    
    return {
        "bitstream": compressed_data,
        "width": w,
        "height": h,
        "original_width": w_original,
        "original_height": h_original,
        "stats": stats,
    }


def decompress_image_from_bitstream(bitstream_arr, padded_width, padded_height):
    # Convert numpy array to list for popping
    # Note: This might be slow for very large images, but it's simple as requested.
    bitstream = bitstream_arr.tolist()
    
    final_arr = np.zeros((padded_height, padded_width), dtype=np.uint8)

    templates = load_templates()

    for bit in range(8):
        plane_arr = np.zeros((padded_height, padded_width), dtype=np.uint8)
        for y0 in range(0, padded_height, 64):
            for x0 in range(0, padded_width, 64):
                if read_bit(bitstream) == 1:
                    # Raw
                    for r_offset in range(64):
                        for c_offset in range(64):
                            pixel = read_bit(bitstream)
                            if pixel is None:
                                return None
                            if (y0 + r_offset < padded_height) and (
                                x0 + c_offset < padded_width
                            ):
                                plane_arr[y0 + r_offset, x0 + c_offset] = pixel
                else:
                    # Quadtree
                    root_node_dict = decode_quadtree_node_bitstream(
                        bitstream, 0, 0, 64, 64, templates
                    )
                    if root_node_dict is None:
                        return None
                    tile_plane = np.zeros((64, 64), dtype=np.uint8)
                    reconstruct_from_quadtree_node(
                        root_node_dict, tile_plane, templates
                    )
                    plane_arr[y0 : y0 + 64, x0 : x0 + 64] = tile_plane
        final_arr |= plane_arr << bit

    if flags.GRAY_PIXELS_MODE:
        final_arr = numpy_gray_to_binary(final_arr)

    return final_arr


def encode_quadtree_node_bitstream(node, bitstream):
    if node["type"] == "leaf":
        if node.get("subtype") == "espresso":
            write_bits(bitstream, ENCODING_HETEROGENEOUS, 2)  # 11
            write_bits(bitstream, SUBTYPE_ESPRESSO, 2)        # 00
            encode_minimized_block_bitstream(node["data"], bitstream)

        elif node.get("subtype") == "raw":
            write_bits(bitstream, ENCODING_HETEROGENEOUS, 2)  # 11
            write_bits(bitstream, SUBTYPE_RAW, 2)             # 11
            raw_block_data = np.array(node["data"])
            for pixel in raw_block_data.flat:
                bitstream.append(int(pixel))

        elif node.get("subtype") == "template_match":
            write_bits(bitstream, ENCODING_HETEROGENEOUS, 2)  # 11
            write_bits(bitstream, SUBTYPE_TEMPLATE, 2)        # 01

            # Template Data
            t_id = node.get("template_id", 0)
            write_bits(bitstream, t_id, 3)
            encode_minimized_block_bitstream(node["data"], bitstream)

        elif "code" in node:
            if node["code"] == "10":
                write_bits(bitstream, ENCODING_HOMOGENEOUS_0, 2)
            elif node["code"] == "11":
                write_bits(bitstream, ENCODING_HOMOGENEOUS_1, 2)
    elif node["type"] == "node":
        write_bits(bitstream, ENCODING_INTERNAL, 2)
        for child in node["children"]:
            encode_quadtree_node_bitstream(child, bitstream)


def encode_minimized_block_bitstream(minimized_data, bitstream):
    code = minimized_data.get("code", "00")
    cubes = minimized_data.get("cubes", [])
    encoding_map = minimized_data.get("encoding_map", {})
    map_value = minimized_data.get("map_value", 0)
    bitstream.append(0 if code == "00" else 1)
    write_bits(bitstream, map_value, 3)
    write_bits(bitstream, len(cubes), 3)
    for inp, out in cubes:
        for char in inp:
            encoded_char_code = encoding_map.get(char, "10")
            if encoded_char_code == "0":
                bitstream.append(0)
            elif encoded_char_code == "10":
                write_bits(bitstream, 0b10, 2)
            elif encoded_char_code == "11":
                write_bits(bitstream, 0b11, 2)
        bitstream.append(int(out))


def decode_quadtree_node_bitstream(bitstream, x, y, w, h, templates=None):
    node_encoding = read_bits(bitstream, 2)
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
                    bitstream, x + dx, y + dy, ww, hh, templates
                )
                if child_node:
                    node["children"].append(child_node)
    elif node_encoding == ENCODING_HETEROGENEOUS:
        node["type"] = "leaf"
        
        # Read 2 bits for subtype
        subtype_code = read_bits(bitstream, 2)
        
        if subtype_code == SUBTYPE_TEMPLATE: # 01
             # Template Match
            t_id = read_bits(bitstream, 3)
            diff_data = decode_minimized_block_bitstream(bitstream)
            node.update(
                {
                    "subtype": "template_match",
                    "template_id": t_id,
                    "data": diff_data,
                }
            )
        elif subtype_code == SUBTYPE_ESPRESSO: # 00
            # Standard Espresso
            # We need to read the espresso data.
            # decode_minimized_block_bitstream reads the standard espresso fields.
            data = decode_minimized_block_bitstream(bitstream)
            node.update({"subtype": "espresso", "data": data})
            
        elif subtype_code == SUBTYPE_RAW: # 11
             # Raw
            raw_block = [read_bit(bitstream) for _ in range(w * h)]
            node.update(
                {
                    "subtype": "raw",
                    "data": np.array(raw_block, dtype=np.uint8).reshape((h, w)),
                }
            )
        else:
            # 10 is unused, maybe error or fallback?
            # For now treat as error or ignore
            print(f"Warning: Unknown subtype code {subtype_code:02b} at {x},{y}")
            return None

    return node


def decode_minimized_block_bitstream(bitstream):
    code = "00" if read_bit(bitstream) == 0 else "01"
    map_value = read_bits(bitstream, 3)
    _, decoding_code_map = decode_char_code_mapping(map_value)
    n_bits = 6
    num_cubes = read_bits(bitstream, 3)
    cubes = []
    for _ in range(num_cubes):
        inp = "".join(
            read_variable_code(bitstream, decoding_code_map) for _ in range(n_bits)
        )
        out = str(read_bit(bitstream))
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