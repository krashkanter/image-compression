class SimpleStats:
    def __init__(self):
        self.original_bits = 0
        self.compressed_bits = 0
        self.compression_time = 0
        self.decompression_time = 0

    def dump_to_file(self, filepath):
        try:
            with open(filepath, "w") as f:
                f.write("Compression Statistics\n")
                f.write("======================\n")
                f.write(f"Original Size: {self.original_bits} bits\n")
                f.write(f"Compressed Size: {self.compressed_bits} bits\n")
                if self.compressed_bits > 0:
                    ratio = self.original_bits / self.compressed_bits
                    f.write(f"Compression Ratio: {ratio:.4f}\n")
                f.write(f"Compression Time: {self.compression_time:.4f} s\n")
                f.write(f"Decompression Time: {self.decompression_time:.4f} s\n")
            print(f"Stats saved to {filepath}")
        except Exception as e:
            print(f"Error saving stats: {e}")

def _collect_stats_from_node(node, stats, bit, is_overflow=False):
    # Simplified: No-op for now as we don't track detailed stats
    pass

