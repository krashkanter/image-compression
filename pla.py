from utils import (
    get_bit_planes,
    split_bit_plane_into_blocks,
    generate_gray_code,
    generate_zigzag_indices,
    run_espresso,
)
from math import ceil, log2
import numpy as np


def generate_pla_terms_for_block(block, gray_code_inputs, invert_output=False):
    """
    Returns a list of (input_str, output_str) tuples for a block.
    If invert_output=True, swaps 0 and 1 in the output (OFF-set / offset PLA).
    """
    block_height, block_width = block.shape
    flat = block.flatten()
    zigzag_indices = generate_zigzag_indices(block_width, block_height)
    reordered = np.array([flat[i] for i in zigzag_indices])

    terms = []
    for inp, out in zip(gray_code_inputs, reordered):
        out_val = str(1 - int(out)) if invert_output else str(int(out))
        terms.append((inp, out_val))
    return terms


def minimize_block_inplace(block, gray_code_inputs, n_bits):
    """
    Minimizes both ON-set and OFF-set for a single block using pyeda Espresso.
    Returns (inset_cubes, offset_cubes).
    """
    inset_terms = generate_pla_terms_for_block(block, gray_code_inputs, invert_output=False)
    offset_terms = generate_pla_terms_for_block(block, gray_code_inputs, invert_output=True)

    inset_cubes = run_espresso(inset_terms, n_bits)
    offset_cubes = run_espresso(offset_terms, n_bits)

    return inset_cubes, offset_cubes


def minimize_all_blocks(image, block_height, block_width):
    """
    Runs Espresso minimization (ON-set and OFF-set) for every block of every
    bit plane entirely in memory.

    Returns a dict structured as:
        {
            plane_index: {
                block_index: {
                    "num_bits": int,
                    "inset_cubes": [(inp, out), ...],
                    "offset_cubes": [(inp, out), ...],
                }
            }
        }
    """
    bit_planes = get_bit_planes(image)
    n_bits = ceil(log2(block_height * block_width))
    gray_code_inputs = generate_gray_code(n_bits)

    results = {}
    for plane_index, bit_plane in enumerate(bit_planes):
        results[plane_index] = {}
        blocks = split_bit_plane_into_blocks(bit_plane, block_height, block_width)
        for block_index, block in enumerate(blocks):
            inset_cubes, offset_cubes = minimize_block_inplace(
                block, gray_code_inputs, n_bits
            )
            results[plane_index][block_index] = {
                "num_bits": n_bits,
                "inset_cubes": inset_cubes,
                "offset_cubes": offset_cubes,
            }

    return results
