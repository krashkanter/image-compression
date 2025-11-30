import os
import sys
import time
import argparse
import cv2
import numpy as np
from bitstream import compress_image_to_bitstream, decompress_image_from_bitstream
import flags as config


def main():
    parser = argparse.ArgumentParser(
        description="Quadtree-based image compression utility."
    )
    parser.add_argument("input_image", help="Path to the input image file.")
    parser.add_argument(
        "output_image", nargs="?", help="Path to save the reconstructed image file."
    )
    parser.add_argument(
        "--dump-bin",
        action="store_true",
        help="Save the compressed binary bitstream to a .bin file.",
    )
    parser.add_argument(
        "--dump-stats",
        action="store_true",
        help="Save compression statistics to a .txt file.",
    )
    parser.add_argument(
        "--pure-quadtree",
        action="store_true",
        help="Use pure quadtree compression without minimization.",
    )
    parser.add_argument(
        "--predictive-xor",
        action="store_true",
        help="Use predictive XOR technique.",
    )
    parser.add_argument(
        "--predictive-xor-8x8",
        action="store_true",
        help="Use predictive XOR technique on 8x8 blocks.",
    )
    parser.add_argument(
        "--gray-pixels",
        action="store_true",
        help="Use Gray coding for pixel values to improve bitplane correlation.",
    )
    parser.add_argument(
        "--rle",
        action="store_true",
        help="Use Run-Length Encoding on the final bitstream.",
    )
    args = parser.parse_args()

    if args.pure_quadtree:
        config.PURE_QUADTREE_MODE = True
    if args.predictive_xor:
        config.PREDICTIVE_XOR_MODE = True
    if args.predictive_xor_8x8:
        config.PREDICTIVE_XOR_8X8_MODE = True
    if args.gray_pixels:
        config.GRAY_PIXELS_MODE = True
    if args.rle:
        config.RLE_MODE = True

    base_name = os.path.splitext(os.path.basename(args.input_image))[0]
    output_path = (
        args.output_image
        if args.output_image
        else f"./output/{base_name}_reconstructed.png"
    )
    compressed_bitstream_path = f"./output/{base_name}_compressed{'_pure_quadtree' if config.PURE_QUADTREE_MODE else ''}.bin"
    stats_output_path = f"./output/{base_name}_stats{'_pure_quadtree' if config.PURE_QUADTREE_MODE else ''}.txt"

    print(f"Compressing '{args.input_image}'...")
    compression_start_time = time.time()
    compressed_result = compress_image_to_bitstream(args.input_image)
    compression_end_time = time.time()
    compression_time_taken = compression_end_time - compression_start_time
    print(f"Compression finished in {compression_time_taken:.4f} seconds.")

    if not compressed_result:
        print("Compression failed.")
        sys.exit(1)

    bitstream = compressed_result["bitstream"]
    stats_obj = compressed_result["stats"]
    initial_size_bits = (
        compressed_result["original_width"] * compressed_result["original_height"] * 8
    )
    padded_width = compressed_result["width"]
    padded_height = compressed_result["height"]
    padded_size_bits = padded_width * padded_height * 8
    compressed_size_bits = stats_obj.compressed_bits

    print("\n--- Compression Summary ---")
    print(f"Original Size (pre-padding): {initial_size_bits / 8:.0f} bytes")
    print(f"Padded Size:                 {padded_size_bits / 8:.0f} bytes")
    print(f"Compressed Size:             {compressed_size_bits / 8:.2f} bytes")

    ratio = initial_size_bits / compressed_size_bits if compressed_size_bits > 0 else 0
    savings = (
        (1 - (compressed_size_bits / padded_size_bits)) * 100
        if padded_size_bits > 0
        else 0
    )
    print(f"Compression Ratio (Initial/New): {ratio:.4f}")
    print(f"Space Savings (vs Padded):       {savings:.2f}%")

    if args.dump_bin:
        try:
            with open(compressed_bitstream_path, "wb") as f:
                f.write(bitstream)
            print(f"\nCompressed bitstream saved to '{compressed_bitstream_path}'")
        except Exception as e:
            print(f"Error saving compressed bitstream file: {e}")

    print("\nDecompressing from in-memory bitstream...")
    decompression_start_time = time.time()
    reconstructed_arr = decompress_image_from_bitstream(
        bitstream, padded_width, padded_height
    )
    decompression_end_time = time.time()
    decompression_time_taken = decompression_end_time - decompression_start_time

    if reconstructed_arr is not None:
        print(f"Decompression finished in {decompression_time_taken:.4f} seconds.")
    else:
        print("Decompression failed.")
        decompression_time_taken = 0.0

    if args.dump_stats:
        print(f"Dumping statistics to '{stats_output_path}'...")
        stats_obj.dump_to_file(
            stats_output_path,
            compression_time_taken,
            decompression_time_taken,
            initial_size_bits,
            padded_size_bits,
        )

    if reconstructed_arr is not None:
        try:
            original_h = compressed_result["original_height"]
            original_w = compressed_result["original_width"]
            cropped_reconstructed_arr = reconstructed_arr[0:original_h, 0:original_w]
            cv2.imwrite(output_path, cropped_reconstructed_arr)
            print(f"Reconstructed image saved to '{output_path}'")
            original_arr = cv2.imread(args.input_image, cv2.IMREAD_GRAYSCALE)
            if np.array_equal(original_arr, cropped_reconstructed_arr):
                print("Verification successful: Reconstructed image matches original.")
            else:
                print(
                    "Verification FAILED: Reconstructed image does NOT perfectly match original."
                )
        except Exception as e:
            print(f"Error saving or verifying reconstructed image: {e}")


if __name__ == "__main__":
    main()
