import argparse
import subprocess
import os
import re
import sys

def run_compression(command, cwd=None):
    """Runs the compression command and returns the output stats file path."""
    print(f"Running: {command} (cwd={cwd or '.'})")
    result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Error running command: {command}")
        print(result.stderr)
        return None
    
    # Extract stats file path from stdout
    match = re.search(r"Dumping statistics to '([^']+)'", result.stdout)
    
    if "Verification FAILED" in result.stdout:
        print("WARNING: Verification FAILED for this run!")
        # We might still return stats path but user should know
        
    if match:
        path = match.group(1)
        # If cwd was changed, the path reported might be relative to that cwd. 
        # But dumping usually uses f"./output/..." which is relative to cwd.
        # So if we ran in 8x4/, path is ./output/... relative to 8x4/.
        # We need to convert it to valid path from current execution dir.
        if cwd:
            path = os.path.normpath(os.path.join(cwd, path))
        return path
    return None

def parse_stats(stats_path):
    """Parses the stats file to extract compressed bits per bitplane."""
    bitplane_bits = {}
    total_compressed_bits = 0
    
    try:
        with open(stats_path, 'r') as f:
            lines = f.readlines()
            
        current_bitplane = None
        for line in lines:
            line = line.strip()
            if line.startswith("Bitplane"):
                parts = line.split()
                if len(parts) >= 2:
                    current_bitplane = int(parts[1])
            elif line.startswith("Compressed Bits:"):
                bits = int(line.split(":")[1].strip())
                if current_bitplane is not None:
                    bitplane_bits[current_bitplane] = bits
            elif line.startswith("Compressed Size:") and "bytes" in line:
                 # Extract total compressed bits from summary if needed, 
                 # but summing bitplanes should match roughly (ignoring headers if any)
                 # Actually the stats file says "Compressed Size: ... bytes (... bits)"
                 match = re.search(r"\((\d+) bits\)", line)
                 if match:
                     total_compressed_bits = int(match.group(1))

    except Exception as e:
        print(f"Error parsing stats file {stats_path}: {e}")
        return None, 0
        
    return bitplane_bits, total_compressed_bits

def main():
    parser = argparse.ArgumentParser(description="Compare image compression versions.")
    parser.add_argument("input_image", help="Path to the input image file.")
    parser.add_argument("--compare-4x4", action="store_true", help="Compare 8x4 vs 4x4 instead of 8x4 vs 8x8.")
    args = parser.parse_args()

    input_image = args.input_image
    if not os.path.exists(input_image):
        print(f"Error: Image '{input_image}' not found.")
        sys.exit(1)

    # 1. Run 8x4 version
    print("\n--- Running 8x4 Version ---")
    # Run from 8x4 directory so that ../bin/espresso path in utils.py resolves correctly
    # Input image path needs to be absolute or relative to 8x4
    input_image_abs = os.path.abspath(input_image)
    cmd_8x4 = f"../.venv/bin/python3 main.py {input_image_abs} --split h --dump-stats"
    stats_8x4_path = run_compression(cmd_8x4, cwd="8x4")
    if not stats_8x4_path:
        print("Failed to run 8x4 version.")
        sys.exit(1)
        
    bits_8x4, total_8x4 = parse_stats(stats_8x4_path)
    
    # 2. Run Second Version (Root 8x8 or 4x4)
    if args.compare_4x4:
        print("\n--- Running 4x4 Version ---")
        # Run from 4x4 directory
        cmd_4x4 = f"../.venv/bin/python3 main.py {input_image_abs} --predictive-xor-4x4 --gray-pixels --dump-stats --compare-with {stats_8x4_path}"
        stats_other_path = run_compression(cmd_4x4, cwd="4x4")
        other_label = "4x4 Bits"
    else:
        print("\n--- Running Root (8x8) Version ---")
        cmd_root = f"./.venv/bin/python3 main.py {input_image} --predictive-xor-8x8 --gray-pixels --dump-stats --compare-with {stats_8x4_path}"
        stats_other_path = run_compression(cmd_root)
        other_label = "8x8 Bits"

    if not stats_other_path:
        print(f"Failed to run {other_label.split()[0]} version.")
        sys.exit(1)

    bits_other, total_other = parse_stats(stats_other_path)

    # 3. Compare Results
    print("\n" + "="*60)
    print(f"{'Bitplane':<10} | {'8x4 Bits':<15} | {other_label:<15} | {'Improvement':<15}")
    print("-" * 60)
    
    total_savings_bits = 0
    
    for plane in range(8):
        b_8x4 = bits_8x4.get(plane, 0)
        b_other = bits_other.get(plane, 0)
        diff = b_8x4 - b_other
        perc = (diff / b_8x4 * 100) if b_8x4 > 0 else 0
        
        print(f"{plane:<10} | {b_8x4:<15} | {b_other:<15} | {diff:<6} ({perc:>5.1f}%)")
        total_savings_bits += diff
        
    print("-" * 60)
    
    total_diff = total_8x4 - total_other
    total_perc = (total_diff / total_8x4 * 100) if total_8x4 > 0 else 0
    print(f"{'Total':<10} | {total_8x4:<15} | {total_other:<15} | {total_diff:<6} ({total_perc:>5.1f}%)")
    print("="*60)
    
    print(f"\nNote: Improvement > 0 means {other_label.split()[0]} uses fewer bits (better compression).")

if __name__ == "__main__":
    main()
