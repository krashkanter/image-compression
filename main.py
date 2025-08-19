import os
import sys
import time
import argparse

import cv2
import numpy as np

from bitstream import compress_image_to_bitstream, decompress_image_from_bitstream


def main():
    parser = argparse.ArgumentParser(description="Quadtree-based image compression utility.")
    parser.add_argument("input_image", help="Path to the input image file.")
    parser.add_argument("output_image", nargs='?', help="Path to save the reconstructed image file.")
    parser.add_argument("--split", choices=['h', 'v'], required=True,
                        help="Split mode for 8x8 blocks: 'h' for 8x4 (horizontal) or 'v' for 4x8 (vertical).")
    parser.add_argument("--dump-bin", action="store_true", help="Save the compressed binary bitstream to a .bin file.")
    parser.add_argument("--dump-stats", action="store_true", help="Save compression statistics to a .txt file.")

    args = parser.parse_args()

    base_name = os.path.splitext(os.path.basename(args.input_image))[0]
    output_path = args.output_image if args.output_image else f'{base_name}_reconstructed.png'
    compressed_bitstream_path = f'{base_name}_compressed.bin'
    stats_output_path = f'{base_name}_stats_{args.split}.txt'

    # --- Compression Timing ---
    print(f"Compressing '{args.input_image}' with --split={args.split}...")
    compression_start_time = time.time()
    compressed_result = compress_image_to_bitstream(args.input_image, args.split)
    compression_end_time = time.time()
    compression_time_taken = compression_end_time - compression_start_time
    print(f"Compression finished in {compression_time_taken:.4f} seconds.")

    if not compressed_result:
        print("Compression failed.")
        sys.exit(1)

    bitstream = compressed_result['bitstream']
    stats_obj = compressed_result['stats']

    initial_size_bits = compressed_result['original_width'] * compressed_result['original_height'] * 8
    padded_width = compressed_result['width']
    padded_height = compressed_result['height']
    padded_size_bits = padded_width * padded_height * 8
    compressed_size_bits = stats_obj.compressed_bits

    print("\n--- Compression Summary ---")
    print(f"Original Size (pre-padding): {initial_size_bits / 8:.0f} bytes")
    print(f"Padded Size:                 {padded_size_bits / 8:.0f} bytes")
    print(f"Compressed Size:             {compressed_size_bits / 8:.2f} bytes")

    ratio = initial_size_bits / compressed_size_bits if compressed_size_bits > 0 else 0
    savings = (1 - (compressed_size_bits / padded_size_bits)) * 100 if padded_size_bits > 0 else 0
    print(f"Compression Ratio (Initial/New): {ratio:.4f}")
    print(f"Space Savings (vs Padded):       {savings:.2f}%")

    if args.dump_bin:
        try:
            with open(compressed_bitstream_path, "wb") as f:
                f.write(bitstream)
            print(f"\nCompressed bitstream saved to '{compressed_bitstream_path}'")
        except Exception as e:
            print(f"Error saving compressed bitstream file: {e}")

    # --- Decompression Timing ---
    print("\nDecompressing from in-memory bitstream...")
    decompression_start_time = time.time()
    reconstructed_arr = decompress_image_from_bitstream(bitstream, padded_width, padded_height, args.split)
    decompression_end_time = time.time()
    decompression_time_taken = decompression_end_time - decompression_start_time

    if reconstructed_arr is not None:
        print(f"Decompression finished in {decompression_time_taken:.4f} seconds.")
    else:
        print("Decompression failed.")
        # Set a zero time if decompression fails, for stats reporting
        decompression_time_taken = 0.0

    # --- Dump Stats ---
    if args.dump_stats:
        print(f"Dumping statistics to '{stats_output_path}'...")
        stats_obj.dump_to_file(stats_output_path, compression_time_taken, decompression_time_taken, initial_size_bits,
                               padded_size_bits)

    # --- Save and Verify ---
    if reconstructed_arr is not None:
        try:
            original_h = compressed_result['original_height']
            original_w = compressed_result['original_width']
            cropped_reconstructed_arr = reconstructed_arr[0:original_h, 0:original_w]

            cv2.imwrite(output_path, cropped_reconstructed_arr)
            print(f"Reconstructed image saved to '{output_path}'")

            original_arr = cv2.imread(args.input_image, cv2.IMREAD_GRAYSCALE)

            if np.array_equal(original_arr, cropped_reconstructed_arr):
                print("Verification successful: Reconstructed image matches original.")
            else:
                print("Verification FAILED: Reconstructed image does NOT perfectly match original.")
        except Exception as e:
            print(f"Error saving or verifying reconstructed image: {e}")


if __name__ == "__main__":
    main()