import cv2
import numpy as np
import time
import argparse
from utils import read_image_png
from pla import generate_pla_for_image, generate_offset_pla_for_image, minimize_offset_with_espresso, minimize_with_espresso, write_pla_files, write_offset_pla_files
from codec import compress_image, decompress, json_to_arr, reconstruct_image

def main():
    parser = argparse.ArgumentParser(description='Image Compression CLI')

    parser.add_argument('-i', '--input', required=True, help='Path to the input image file')
    parser.add_argument('-o', '--output', required=True, help='Path to the output file')
    parser.add_argument('-b', '--block', required=True, help='Block shape in the format heightxwidth')
    parser.add_argument('-s','--shape', required=True, help='Shape of the image in the format heightxwidth')

    args = parser.parse_args()

    input_path = args.input
    output_path = args.output
    block_height = int(args.block.split('x')[0])
    block_width = int(args.block.split('x')[1])
    image_height = int(args.shape.split('x')[0])
    image_width = int(args.shape.split('x')[1])
    num_blocks_x = image_width // block_width
    num_blocks_y = image_height // block_height
    num_bit_planes = 8

    print("Block Shape = ", args.block)
    print("Image Shape = ", args.shape)

    print('-------------------------------------------------------')
    print('Reading image....')
    image = read_image_png(input_path, image_height, image_width)
    print('-------------------------------------------------------')

    compression_start_time = time.time()

    print('Generating ON-Set PLA....')
    pla_files = generate_pla_for_image(image, block_height, block_width)
    input_filenames = write_pla_files(pla_files)

    print('Generate OFF-Set PLA....')
    offset_pla_files = generate_offset_pla_for_image(image, block_height, block_width)
    offset_input_filenames = write_offset_pla_files(offset_pla_files)


    print('Minimizing ON-Set PLA....')
    # offset_output_filenames = minimize_offset_with_espresso(offset_input_filenames)
    minimize_offset_with_espresso(offset_input_filenames)

    print('Minimizing OFF-Set PLA....')
    # output_filenames = minimize_with_espresso(input_filenames)
    minimize_with_espresso(input_filenames)


    print('Compressing....')
    compressed_data = compress_image(image, block_height, block_width)
    print('Compressed')
    print(f'Total compression time - {time.time() - compression_start_time:.2f} seconds')
    print('-------------------------------------------------------')

    decompression_start_time = time.time()
    print('Json to array...')
    compressed_bit_stream = json_to_arr(compressed_data)

    reconstructed_image = reconstruct_image(data = decompress(compressed_bit_stream, block_height = block_height, block_width = block_width), num_bit_planes=num_bit_planes, num_blocks_y=num_blocks_y, num_blocks_x=num_blocks_x, block_height=block_height, block_width=block_width, image_height=image_height, image_width=image_width)
    print('Decompressed')
    print(f'Total decompression time - {time.time() - decompression_start_time:.2f} seconds')
    print('-------------------------------------------------------')

    cv2.imwrite(output_path, reconstructed_image)
    numpy_array = np.concatenate(compressed_bit_stream, axis=0)
    compressed_len = len(numpy_array)
    original_len = len(image.flatten()) * 8

    print(f"Bits Lost: {original_len - compressed_len} bits")
    print(f"Compression Ratio: {original_len/ compressed_len:.2f}", )
    print(f"Percentage Reduction: {((original_len - compressed_len) / original_len * 100):.2f}%")
    print(f'Image saved to {output_path}')
    print('-------------------------------------------------------')

if __name__ == "__main__":
    main()
