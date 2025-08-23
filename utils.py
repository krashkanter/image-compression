import numpy as np
import matplotlib.pyplot as plt
import cv2

def read_image(path, height, width):
    fd = open(path, "rb")
    rows = height
    cols = width
    f = np.fromfile(fd, dtype=np.uint8, count=rows * cols)
    image = f.reshape((rows, cols))
    fd.close()

    return image

def read_image_png(path, height, width):
    image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    image = cv2.resize(image, (width, height))
    return image

def show_image(image):
    plt.imshow(image, cmap="gray")
    plt.axis("off")
    plt.show()

def get_bit_planes(image):
    height, width = image.shape[:2]
    bit_planes = [np.zeros((height, width), dtype=np.uint8) for _ in range(8)]

    for i in range(8):
        bit_planes[i] = (image >> i) & 1

    return bit_planes

def split_bit_plane_into_blocks(bit_plane, block_height, block_width):
    height, width = bit_plane.shape
    blocks = [
        bit_plane[y : y + block_height, x : x + block_width]
        for y in range(0, height, block_height)
        for x in range(0, width, block_width)
    ]
    return blocks

def generate_gray_code(n):
    if n == 0:
        return [""]
    first_half = generate_gray_code(n - 1)
    second_half = list(reversed(first_half))
    return ["0" + code for code in first_half] + ["1" + code for code in second_half]

def generate_zigzag_indices(cols, rows):
    indices = []
    for row in range(rows):
        if row % 2 == 0:
            # Ascending order for even rows
            indices.extend([row * cols + col for col in range(cols)])
        else:
            # Descending order for odd rows
            indices.extend([row * cols + col for col in range(cols - 1, -1, -1)])
    return indices

def revert_zigzag(arr, cols, rows):
    zigzag_indices = generate_zigzag_indices(cols, rows)
    original_order = [None] * len(arr)
    for original_pos, zigzag_pos in enumerate(zigzag_indices):
        original_order[original_pos] = arr[zigzag_pos]
    
    return original_order

def is_uniform_block(block):
    return np.all(block == 0) or np.all(block == 1)

def calculate_code_allotment(cubes):
    freq = {"0": 0, "1": 0, "-": 0}
    for inputs, _ in cubes:
        for char in inputs:
            if char in freq:
                freq[char] += 1

    sorted_freq = sorted(freq.items(), key=lambda x: -x[1])
    code_allotment = {"0": None, "1": None, "-": None}
    symbol = "0"

    if sorted_freq[0][0] == "0":
        code_allotment = {"0": "0", "1": "10", "-": "11"}
        symbol = "0"
    elif sorted_freq[0][0] == "1":
        code_allotment = {"1": "0", "0": "10", "-": "11"}
        symbol = "10"
    elif sorted_freq[0][0] == "-":
        code_allotment = {"-": "0", "0": "10", "1": "11"}
        symbol = "11"

    return code_allotment, symbol

def encode_cubes(cubes, code_allotment):
    encoded_bits = []

    for inputs, output in cubes:
        encoded_inputs = "".join(code_allotment[char] for char in inputs)
        encoded_bits.append(encoded_inputs)

    return "".join(encoded_bits), len(cubes)

# def json_to_arr(compressed_data):
#     bit_planes = compressed_data["bit_planes"]
#     compressed_bit_stream = []
#     for plane in bit_planes:
#         for block in plane["blocks"]:
#             bit_stream = []
#             block_type = block["type"]
#             if block_type == "uniform":
#                 if block["data"] == [1]:
#                     bit_stream += [0, 1]
#                 else:
#                     bit_stream += [0, 0]
#                 compressed_bit_stream.append(bit_stream)
#                 continue
#             elif block_type == "incompressible":
#                 bit_stream += [1, 1]
#                 bit_stream += block["data"]
#                 compressed_bit_stream.append(bit_stream)
#                 continue
#             else:
#                 bit_stream += [1, 0, 0]
#                 data = block["data"]
#                 bit_stream += [int(i) for i in data["code_allotment_bits"]]
#                 bit_stream += [int(i) for i in data["number_of_cubes_bin"]]
#                 bit_stream += [int(i) for i in data["encoded_bits"]]
#                 compressed_bit_stream.append(bit_stream)
#                 continue
#     return compressed_bit_stream

def calculate_decode_allotment(symbol):
    if symbol == "0":
        return {"0": "0", "10": "1", "11": "-"}
    elif symbol == "10":
        return {"0": "1", "10": "0", "11": "-"}
    elif symbol == "11":
        return {"0": "-", "10": "0", "11": "1"}

def generate_combinations(s):
    if "-" not in s:
        return [s]

    combinations = []
    for i, char in enumerate(s):
        if char == "-":
            for replacement in ["0", "1"]:
                new_s = s[:i] + replacement + s[i + 1 :]
                combinations.extend(generate_combinations(new_s))
            break
    return combinations

def deminimize_cubes(cubes):
    graycode_list = generate_gray_code(5)
    graycode_dict = {}
    block_bits = []
    for i in graycode_list:
        graycode_dict[i] = 0
    for i in cubes:
        combinations = generate_combinations(i)
        for i in combinations:
            graycode_dict[i] = 1

    for i in graycode_dict:
        block_bits.append(graycode_dict[i])

    # print(block_bits,'\n', 'Block Bits Length: ', len(block_bits))
    return block_bits

def decode_cubes(bits, allotment):
    decoded = []
    index = 0
    temp = ""
    while index < len(bits):
        if bits[index] == "0":
            temp += allotment["0"]
            index += 1
        elif bits[index] == "1" and bits[index + 1] == "0":
            temp += allotment["10"]
            index += 2
        else:
            temp += allotment["11"]
            index += 2
        if len(temp) == 5:
            decoded.append(temp)
            temp = ""

    return decoded

