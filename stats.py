class CompressionStats:
    def __init__(self):
        self.raw_bits = 0
        self.compressed_bits = 0
        self.plane_stats = {}

    def _init_plane_stats(self, bit):
        """
        Initializes the statistics dictionary for a new bitplane.
        The onset_blocks and offset_blocks are now dictionaries to track counts
        for specific levels as requested.
        """
        if bit not in self.plane_stats:
            self.plane_stats[bit] = {
                'quadtree_64_blocks': 0,
                'raw_64_blocks': 0,
                'code_counts': {
                    '64x64': {'00': 0, '01': 0, '10': 0, '11': 0},
                    '32x32': {'00': 0, '01': 0, '10': 0, '11': 0},
                    '16x16': {'00': 0, '01': 0, '10': 0, '11': 0},
                    '8x8': {'00': 0, '01': 0, '10': 0, '11': 0},
                    '8x4': {'00': 0, '01': 0, '10': 0, '11': 0},
                    '4x8': {'00': 0, '01': 0, '10': 0, '11': 0}
                },
                # Changed to dictionaries to hold per-level counts
                'onset_blocks': {'8x4': 0, '4x8': 0},
                'offset_blocks': {'8x4': 0, '4x8': 0},
            }

    def dump_to_file(self, filepath, compression_time, decompression_time, initial_size_bits, padded_size_bits):
        """
        Dumps all collected statistics to a formatted text file.
        Includes a new section for on-set and off-set block counts.
        """
        try:
            with open(filepath, 'w') as f:
                f.write("=" * 50 + "\n")
                f.write("      Compression Statistics Report\n")
                f.write("=" * 50 + "\n\n")

                def to_percent(numerator, denominator):
                    return (numerator / denominator) * 100 if denominator > 0 else 0.0

                for bit, stats in sorted(self.plane_stats.items()):
                    f.write("-" * 40 + "\n")
                    f.write(f"  Bitplane {bit}\n")
                    f.write("-" * 40 + "\n")

                    total_64_blocks = stats['quadtree_64_blocks'] + stats['raw_64_blocks']
                    f.write(f"Total 64x64 blocks processed: {total_64_blocks}\n")
                    if total_64_blocks > 0:
                        quad_perc = to_percent(stats['quadtree_64_blocks'], total_64_blocks)
                        raw_perc = to_percent(stats['raw_64_blocks'], total_64_blocks)
                        f.write(f"  - Blocks under Quadtree: {quad_perc:.2f}%\n")
                        f.write(f"  - Incompressible (Raw):  {raw_perc:.2f}%\n\n")
                    else:
                        f.write(f"  - Blocks under Quadtree: 0.00%\n")
                        f.write(f"  - Incompressible (Raw):  0.00%\n\n")

                    f.write("Code Appearances per Level (00: Homo-0, 01: Homo-1, 10: Internal, 11: Hetero-Leaf):\n")
                    for level, counts in stats['code_counts'].items():
                        total_level_nodes = sum(counts.values())
                        f.write(f"  Level {level} (Total Nodes: {total_level_nodes}):\n")
                        if total_level_nodes > 0:
                            code_map = {'00': 'Homo-0', '01': 'Homo-1', '10': 'Internal', '11': 'Hetero-Leaf'}
                            for code, desc in code_map.items():
                                if code == '11' and level not in ['8x8', '8x4', '4x8']: continue
                                perc = to_percent(counts.get(code, 0), total_level_nodes)
                                f.write(f"    - {code} ({desc}):".ljust(22) + f"{perc:.2f}%\n")
                        else:
                            f.write("    - No nodes at this level.\n")
                    f.write("\n")

                    # --- NEW SECTION ---
                    # Reports the on-set and off-set counts for 8x4 and 4x8 levels.
                    f.write("On-set/Off-set Block Counts (for Espresso leaves):\n")
                    onset_8x4 = stats['onset_blocks']['8x4']
                    offset_8x4 = stats['offset_blocks']['8x4']
                    onset_4x8 = stats['onset_blocks']['4x8']
                    offset_4x8 = stats['offset_blocks']['4x8']

                    f.write(f"  Level 8x4: On-set: {onset_8x4}, Off-set: {offset_8x4}\n")
                    f.write(f"  Level 4x8: On-set: {onset_4x8}, Off-set: {offset_4x8}\n\n")

                compression_ratio = initial_size_bits / self.compressed_bits if self.compressed_bits > 0 else 0
                space_savings = (1 - (self.compressed_bits / padded_size_bits)) * 100 if padded_size_bits > 0 else 0

                f.write("=" * 50 + "\n")
                f.write("      Overall Summary\n")
                f.write("=" * 50 + "\n")
                f.write(
                    f"Initial Size (before padding): {initial_size_bits / 8:.0f} bytes ({initial_size_bits} bits)\n")
                f.write(f"Size After Padding:            {padded_size_bits / 8:.0f} bytes ({padded_size_bits} bits)\n")
                f.write(
                    f"Compressed Size:               {self.compressed_bits / 8:.2f} bytes ({self.compressed_bits} bits)\n\n")
                f.write(f"Compression Ratio (Initial/New): {compression_ratio:.4f}\n")
                f.write(f"Percentage Space Savings (vs Padded): {space_savings:.2f}%\n\n")

                f.write(f"Compression Time Taken:   {compression_time:.4f} seconds\n")
                f.write(f"Decompression Time Taken: {decompression_time:.4f} seconds\n")
                f.write("=" * 50 + "\n")

            print(f"Statistics successfully dumped to '{filepath}'")
        except IOError as e:
            print(f"Error writing statistics file: {e}")


def _collect_stats_from_node(node, stats, bit):
    """
    Recursively traverses the quadtree to collect statistics from each node.
    Now correctly increments on-set/off-set counters for 8x4 and 4x8 levels.
    """
    if not node: return
    w, h = node.get('w', 0), node.get('h', 0)
    level_key = f"{w}x{h}"
    plane_stat_dict = stats.plane_stats[bit]
    code_counts = plane_stat_dict['code_counts']
    if level_key in code_counts:
        if node['type'] == 'leaf':
            subtype = node.get('subtype')
            if subtype in ['espresso', 'raw']:
                code_counts[level_key]['11'] += 1
                if subtype == 'espresso':
                    # Check if the level is one we are tracking (8x4 or 4x8)
                    if level_key in plane_stat_dict['onset_blocks']:
                        if node['data'].get('code') == '00':
                            plane_stat_dict['onset_blocks'][level_key] += 1
                        elif node['data'].get('code') == '01':
                            plane_stat_dict['offset_blocks'][level_key] += 1
            elif 'code' in node:
                if node['code'] == '10':
                    code_counts[level_key]['00'] += 1
                elif node['code'] == '11':
                    code_counts[level_key]['01'] += 1
        elif node['type'] == 'node':
            code_counts[level_key]['10'] += 1
    if 'children' in node:
        for child in node['children']:
            _collect_stats_from_node(child, stats, bit)