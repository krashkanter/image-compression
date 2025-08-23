from utils import *
from math import ceil, log2
import os
import subprocess

def generate_pla_for_block(block, gray_code_inputs):
    block_height, block_width = block.shape
    pla_lines = []
    block = block.flatten()
    zigzag_indices = generate_zigzag_indices(block_width, block_height)
    block = np.array([block[i] for i in zigzag_indices])
    for (inputs, outputs) in zip(gray_code_inputs, block):
        outputs = str(outputs)
        pla_line = f"{inputs} {outputs}"
        pla_lines.append(pla_line) 

    return pla_lines

def generate_pla_for_image(image, block_height, block_width):
    bit_planes = get_bit_planes(image)
    pla_files = []

    num_bits = ceil(log2(block_height * block_width))
    gray_code_inputs = generate_gray_code(num_bits)

    for plane_index, bit_plane in enumerate(bit_planes):
        blocks = split_bit_plane_into_blocks(bit_plane, block_height, block_width)

        for block_index, block in enumerate(blocks):
            pla_lines = generate_pla_for_block(block, gray_code_inputs)
            pla_files.append((plane_index, block_index, pla_lines, num_bits, block))

    return pla_files

def write_pla_files(pla_files, parent_dir="pla", filename_prefix="input_block"):
    filenames = []

    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    for plane_index, block_index, pla_lines, num_bits, _ in pla_files:
        plane_dir = os.path.join(parent_dir, f"plane{plane_index}")
        if not os.path.exists(plane_dir):
            os.makedirs(plane_dir)

        filename = os.path.join(plane_dir, f"{filename_prefix}_block{block_index}.pla")
        with open(filename, "w") as file:
            file.write(f".i {num_bits}\n")
            file.write(".o 1\n")
            file.write(f".p {len(pla_lines)}\n")
            for line in pla_lines:
                file.write(line + "\n")
            file.write(".e\n")
        filenames.append(filename)
    return filenames

def minimize_with_espresso(input_filenames, output_parent_dir="pla_output"):
    output_filenames = []

    if not os.path.exists(output_parent_dir):
        os.makedirs(output_parent_dir)

    for input_file in input_filenames:
        with open(input_file, "r") as f:
            lines = f.readlines()

        is_uniform = all(line.split()[-1] == "0" for line in lines[4:-1]) or all(
            line.split()[-1] == "1" for line in lines[4:-1]
        )

        relative_path = os.path.relpath(input_file, start="pla")
        output_file = os.path.join(output_parent_dir, relative_path)
        output_dir = os.path.dirname(output_file)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if is_uniform:
            with open(output_file, "w") as out_f:
                out_f.writelines(lines)
        else:
            with open(output_file, "w") as out_f:
                subprocess.run(["espresso", input_file], stdout=out_f)

        output_filenames.append(output_file)

    return output_filenames

def read_minimized_pla_files(output_parent_dir="pla_output"):
    minimized_blocks = {}

    for root, _, files in os.walk(output_parent_dir):
        for file in files:
            if file.endswith(".pla"):
                plane_index = int(root.split("plane")[-1])
                block_index = int(file.split("_block")[-1].split(".pla")[0])

                with open(os.path.join(root, file), "r") as f:
                    lines = f.readlines()

                num_bits = int(lines[0].split()[1])
                cubes = [line.strip().split() for line in lines[3:-1]]

                if plane_index not in minimized_blocks:
                    minimized_blocks[plane_index] = {}

                minimized_blocks[plane_index][block_index] = {
                    "num_bits": num_bits,
                    "cubes": cubes,
                }

    return minimized_blocks

def generate_offset_pla_for_block(block, gray_code_inputs):
    block_height, block_width = block.shape
    pla_lines = []
    block = block.flatten()
    zigzag_indices = generate_zigzag_indices(block_width, block_height)
    block = np.array([block[i] for i in zigzag_indices])
    for (inputs, outputs) in zip(gray_code_inputs, block):
        outputs = str(1 - outputs)  # Swap 0 and 1
        pla_line = f"{inputs} {outputs}"
        pla_lines.append(pla_line) 

    return pla_lines

def generate_offset_pla_for_image(image, block_height, block_width):
    bit_planes = get_bit_planes(image)
    pla_files = []

    num_bits = ceil(log2(block_height * block_width))
    gray_code_inputs = generate_gray_code(num_bits)

    for plane_index, bit_plane in enumerate(bit_planes):
        blocks = split_bit_plane_into_blocks(bit_plane, block_height, block_width)

        for block_index, block in enumerate(blocks):
            pla_lines = generate_offset_pla_for_block(block, gray_code_inputs)
            pla_files.append((plane_index, block_index, pla_lines, num_bits, block))

    return pla_files

def write_offset_pla_files(pla_files, parent_dir="pla_offset", filename_prefix="input_block"):
    filenames = []

    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    for plane_index, block_index, pla_lines, num_bits, _ in pla_files:
        plane_dir = os.path.join(parent_dir, f"plane{plane_index}")
        if not os.path.exists(plane_dir):
            os.makedirs(plane_dir)

        filename = os.path.join(plane_dir, f"{filename_prefix}_block{block_index}.pla")
        with open(filename, "w") as file:
            file.write(f".i {num_bits}\n")
            file.write(".o 1\n")
            file.write(f".p {len(pla_lines)}\n")
            for line in pla_lines:
                file.write(line + "\n")
            file.write(".e\n")
        filenames.append(filename)
    return filenames

def minimize_offset_with_espresso(input_filenames, output_parent_dir="pla_offset_output"):
    output_filenames = []

    if not os.path.exists(output_parent_dir):
        os.makedirs(output_parent_dir)

    for input_file in input_filenames:
        with open(input_file, "r") as f:
            lines = f.readlines()

        is_uniform = all(line.split()[-1] == "0" for line in lines[4:-1]) or all(
            line.split()[-1] == "1" for line in lines[4:-1]
        )

        relative_path = os.path.relpath(input_file, start="pla_offset")
        output_file = os.path.join(output_parent_dir, relative_path)
        output_dir = os.path.dirname(output_file)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if is_uniform:
            with open(output_file, "w") as out_f:
                out_f.writelines(lines)
        else:
            with open(output_file, "w") as out_f:
                subprocess.run(["espresso", input_file], stdout=out_f)

        output_filenames.append(output_file)

    return output_filenames