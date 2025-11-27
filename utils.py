import subprocess
from collections import Counter
from math import ceil, log2
import numpy as np
import os


def get_espresso_cost(min_data, use_3_bit_cube_count=False):
    cubes = min_data.get("cubes", [])
    num_cubes = len(cubes)
    map_value = min_data.get("map_value", 0)
    input_pattern_cost = 0
    if cubes:
        encoding_map, _ = decode_char_code_mapping(map_value)
        for inp, _ in cubes:
            for char in inp:
                input_pattern_cost += len(encoding_map.get(char, "10"))
    header_cost = 1 + 3
    cube_count_cost = 3 if use_3_bit_cube_count else 7
    data_cost = input_pattern_cost + num_cubes * 1
    return header_cost + cube_count_cost + data_cost


def load_templates(grid_size=8):
    """Loads templates from config/templates.txt"""
    templates = []
    try:
        path = os.path.join("config", "templates.txt")
        if os.path.exists(path):
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if len(line) == grid_size * grid_size:
                        try:
                            arr = np.array(list(line), dtype=int).reshape(
                                (grid_size, grid_size)
                            )
                            templates.append(arr)
                        except ValueError:
                            continue
    except Exception:
        pass
    return templates


def zigzag_indices(width, height):
    idxs = []
    for r in range(height):
        row = list(range(r * width, r * width + width))
        idxs.extend(row if r % 2 == 0 else reversed(row))
    return idxs


def bin_to_gray(bin_str):
    b = list(map(int, bin_str))
    g = [b[0]]
    for i in range(1, len(b)):
        g.append(b[i] ^ b[i - 1])
    return "".join(map(str, g))


def run_espresso(terms, n_bits):
    try:
        pla_content = [f".i {n_bits}", ".o 1"]
        for inp, out in terms:
            pla_content.append(f"{inp} {out}")
        pla_content.append(".e")
        pla_input_str = "\n".join(pla_content)
        res = subprocess.run(
            [".\\bin\\espresso"],
            input=pla_input_str,
            capture_output=True,
            text=True,
            check=True,
        )
        cubes = []
        for line in res.stdout.splitlines():
            parts = line.split()
            if len(parts) == 2 and all(c in "01-" for c in parts[0]):
                cubes.append((parts[0], parts[1]))
        return cubes
    except FileNotFoundError:
        print("Error: 'espresso' command not found.")
        print(
            "Please ensure Espresso is installed and accessible in your system's PATH."
        )
        return []
    except subprocess.CalledProcessError as e:
        print(f"Error running Espresso (exit code {e.returncode}): {e}")
        print(f"Stderr: {e.stderr}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred during Espresso execution: {e}")
        return []


def get_char_frequencies(cubes):
    char_counts = Counter()
    for inp, _ in cubes:
        char_counts.update(inp)
    return char_counts


def get_char_code_mapping(char_counts):
    codes = ["0", "10", "11"]
    sorted_chars = [char for char, count in char_counts.most_common()]
    mapping = {}
    assigned_codes = set()
    for char in sorted_chars:
        if char in ["0", "1", "-"]:
            for code in codes:
                if code not in assigned_codes:
                    is_prefix = False
                    for assigned in assigned_codes:
                        if code.startswith(assigned) or assigned.startswith(code):
                            is_prefix = True
                            break
                    if not is_prefix:
                        mapping[char] = code
                        assigned_codes.add(code)
                        break
    remaining_codes = sorted(list(set(codes) - assigned_codes))
    remaining_chars = sorted([char for char in ["0", "1", "-"] if char not in mapping])
    for i, char in enumerate(remaining_chars):
        if i < len(remaining_codes):
            mapping[char] = remaining_codes[i]
        else:
            pass
    return mapping


def encode_char_code_mapping(mapping):
    char_order = ["-", "0", "1"]
    code_map = {code: char for char, code in mapping.items()}
    map_bits = []
    char_at_code_0 = code_map.get("0")
    if char_at_code_0 == "0":
        map_bits.extend([0, 0])
    elif char_at_code_0 == "1":
        map_bits.extend([0, 1])
    elif char_at_code_0 == "-":
        map_bits.extend([1, 0])
    else:
        raise ValueError(
            f"Invalid char_at_code_0: {char_at_code_0}. Mapping: {mapping}"
        )
    remaining_chars_order = [char for char in char_order if char != char_at_code_0]
    char_at_code_10 = code_map.get("10")
    if char_at_code_10 == remaining_chars_order[0]:
        map_bits.append(0)
    elif char_at_code_10 == remaining_chars_order[1]:
        map_bits.append(1)
    else:
        raise ValueError(
            f"Invalid char_at_code_10: {char_at_code_10}. Mapping: {mapping}"
        )
    map_value = int("".join(map(str, map_bits)), 2)
    return map_value


def decode_char_code_mapping(map_value):
    if map_value < 0 or map_value > 7:
        raise ValueError(f"Map value out of range (0-7): {map_value}")
    map_bits = [(map_value >> 2) & 1, (map_value >> 1) & 1, map_value & 1]
    char_order = ["-", "0", "1"]
    char_at_code_0 = None
    if map_bits[0] == 0 and map_bits[1] == 0:
        char_at_code_0 = "0"
    elif map_bits[0] == 0 and map_bits[1] == 1:
        char_at_code_0 = "1"
    elif map_bits[0] == 1 and map_bits[1] == 0:
        char_at_code_0 = "-"
    remaining_chars_order = [char for char in char_order if char != char_at_code_0]
    char_at_code_10 = remaining_chars_order[map_bits[2]]
    char_at_code_11 = [
        char for char in remaining_chars_order if char != char_at_code_10
    ][0]
    decoding_map = {"0": char_at_code_0, "10": char_at_code_10, "11": char_at_code_11}
    encoding_map = {v: k for k, v in decoding_map.items()}
    return encoding_map, decoding_map


def minimize_block(block):
    h, w = block.shape
    size = h * w

    if size == 0:
        return {
            "code": "10",
            "cubes": [],
            "n_bits": 1,
            "encoding_map": {},
            "map_value": 0,
        }

    n_bits = max(1, ceil(log2(size))) if size > 1 else 1
    idxs = zigzag_indices(w, h)
    flat = block.flatten()

    onset = []
    for pos in idxs:
        gray_code = bin_to_gray(format(pos, f"0{n_bits}b"))
        onset.append((gray_code, str(int(flat[pos]))))

    offset = [(inp, "1" if out == "0" else "0") for inp, out in onset]
    o_cubes = run_espresso(onset, n_bits)
    f_cubes = run_espresso(offset, n_bits)

    # Store both on-set and off-set information
    on_set_cubes = len(o_cubes) if o_cubes else 0
    off_set_cubes = len(f_cubes) if f_cubes else 0

    if not o_cubes and not f_cubes:
        if np.all(flat == 0):
            code = "10"
            selected_cubes = []
        elif np.all(flat == 1):
            code = "11"
            selected_cubes = []
        else:
            print(
                f"Warning: Espresso failed and block size {h}x{w} is heterogeneous. Encoding as all 0s (empty ON-set)."
            )
            code = "00"
            selected_cubes = []
    elif not o_cubes:
        code = "01"
        selected_cubes = f_cubes
    elif not f_cubes:
        code = "00"
        selected_cubes = o_cubes
    elif len(o_cubes) <= len(f_cubes):
        code = "00"
        selected_cubes = o_cubes
    else:
        code = "01"
        selected_cubes = f_cubes

    char_counts = get_char_frequencies(selected_cubes)
    encoding_map = get_char_code_mapping(char_counts)
    map_value = encode_char_code_mapping(encoding_map)

    return {
        "code": code,
        "cubes": selected_cubes,
        "n_bits": n_bits,
        "encoding_map": encoding_map,
        "map_value": map_value,
        "on_set_cubes": on_set_cubes,  # NEW: track on-set cubes
        "off_set_cubes": off_set_cubes,  # NEW: track off-set cubes
    }


def reconstruct_block(info, w, h):
    size = w * h
    if size == 0:
        return np.zeros((h, w), dtype=np.uint8)
    n_bits = info.get("n_bits", 1)
    if size > 0 and n_bits == 0:
        print(f"Warning: n_bits is 0 for block size {w}x{h}. Assuming homogeneous.")
        color = 1 if info.get("code") == "11" else 0
        return np.full((h, w), color, dtype=np.uint8)
    if size == 1 and n_bits == 1 and "cubes" not in info:
        color = 1 if info.get("code") == "11" else 0
        return np.full((h, w), color, dtype=np.uint8)
    idxs = zigzag_indices(w, h)
    flat = [0] * size
    invert = info.get("code") == "01"
    cubes = info.get("cubes", [])
    for pos in idxs:
        gray = bin_to_gray(format(pos, f"0{n_bits}b"))
        val = 0
        for inp, o in cubes:
            match = True
            if len(inp) != len(gray):
                print(
                    f"Warning: Input pattern length mismatch in cube for block size {w}x{h} at pos {pos}. Expected {len(gray)}, Got {len(inp)}"
                )
                match = False
            else:
                for p, g in zip(inp, gray):
                    if p != "-" and p != g:
                        match = False
                        break
            if match:
                try:
                    val = int(o)
                    break
                except ValueError:
                    print(
                        f"Warning: Invalid output '{o}' in cube for block size {w}x{h}"
                    )
                    val = 0
                    break
        flat[pos] = val ^ invert
    blk = np.zeros((h, w), dtype=np.uint8)
    for pos, val in enumerate(flat):
        r, c = divmod(pos, w)
        blk[r, c] = val
    return blk


class BitStreamWriter:
    def __init__(self, byte_stream):
        self._byte_stream = byte_stream
        self._current_byte = 0
        self._bits_in_byte = 0

    def write_bit(self, bit):
        if bit not in (0, 1):
            raise ValueError("Bit must be 0 or 1")
        self._current_byte |= bit << (7 - self._bits_in_byte)
        self._bits_in_byte += 1
        if self._bits_in_byte == 8:
            self._byte_stream.write(bytes([self._current_byte]))
            self._current_byte = 0
            self._bits_in_byte = 0

    def write_bits(self, value, num_bits):
        if num_bits < 0:
            raise ValueError("Number of bits must be non-negative")
        if num_bits > 0 and (value < 0 or value >= (1 << num_bits)):
            raise ValueError(f"Value {value} out of range for {num_bits} bits")
        for i in range(num_bits):
            bit = (value >> (num_bits - 1 - i)) & 1
            self.write_bit(bit)

    def flush(self):
        if self._bits_in_byte > 0:
            self._byte_stream.write(bytes([self._current_byte]))
            self._current_byte = 0
            self._bits_in_byte = 0


class BitStreamReader:
    def __init__(self, byte_stream):
        self._byte_stream = byte_stream
        self._current_byte = 0
        self._bits_in_byte = 0
        self._byte_buffer = b""
        self._eof = False

    def _read_next_byte(self):
        if self._eof:
            return False
        byte = self._byte_stream.read(1)
        if not byte:
            self._eof = True
            return False
        self._byte_buffer += byte
        return True

    def read_bit(self):
        if self._bits_in_byte == 0:
            if not self._read_next_byte():
                return None
            self._current_byte = self._byte_buffer[0]
            self._byte_buffer = self._byte_buffer[1:]
            self._bits_in_byte = 8
        bit = (self._current_byte >> (self._bits_in_byte - 1)) & 1
        self._bits_in_byte -= 1
        return bit

    def read_bits(self, num_bits):
        if num_bits < 0:
            raise ValueError("Number of bits must be non-negative")
        if num_bits == 0:
            return 0
        value = 0
        for _ in range(num_bits):
            bit = self.read_bit()
            if bit is None:
                return None
            value = (value << 1) | bit
        return value

    def read_variable_code(self, decoding_map):
        buffer = []
        max_code_len = 2
        while len(buffer) < max_code_len:
            bit = self.read_bit()
            if bit is None:
                return None
            buffer.append(str(bit))
            current_code = "".join(buffer)
            if current_code in decoding_map:
                return decoding_map[current_code]
        return None
