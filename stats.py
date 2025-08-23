class CompressionStats:
    def __init__(self):
        self.raw_bits = 0
        self.compressed_bits = 0
        self.plane_stats = {}

    def _init_plane_stats(self, bit):
        """
        Initializes the statistics dictionary for a new bitplane.
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
                    '4x4': {'00': 0, '01': 0, '10': 0, '11': 0}
                },
                'leaf_node_stats': {'minimized': 0, 'incompressible': 0, 'off-set': 0, 'on-set': 0},
            }

    def dump_to_file(self, filepath, compression_time, decompression_time, initial_size_bits, padded_size_bits):
        """
        Dumps all collected statistics to a formatted text file.
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
                        f.write("  - No 64x64 blocks processed.\n\n")

                    f.write("Code Appearances per Level (00: Homo-0, 01: Homo-1, 10: Internal, 11: Hetero-Leaf):\n")
                    for level, counts in stats['code_counts'].items():
                        total_level_nodes = sum(counts.values())
                        f.write(f"  Level {level} (Total Nodes: {total_level_nodes}):\n")
                        if total_level_nodes > 0:
                            code_map = {'00': 'Homo-0', '01': 'Homo-1', '10': 'Internal', '11': 'Hetero-Leaf'}
                            for code, desc in code_map.items():
                                if code == '11' and level not in ['4x4']: continue
                                perc = to_percent(counts.get(code, 0), total_level_nodes)
                                f.write(f"    - {code} ({desc}):".ljust(22) + f"{perc:.2f}%\n")
                        else:
                            f.write("    - No nodes at this level.\n")
                    f.write("\n")

                    leaf_stats = stats['leaf_node_stats']
                    total_leaves = leaf_stats['minimized'] + leaf_stats['incompressible']
                    f.write("Leaf Node Distribution (4x4 blocks):\n")
                    if total_leaves > 0:
                        min_perc = to_percent(leaf_stats['minimized'], total_leaves)
                        incomp_perc = to_percent(leaf_stats['incompressible'], total_leaves)
                        
                        f.write(f"  - Minimized (Espresso):    {min_perc:.2f}% (Total: {leaf_stats['minimized']})\n")
                        if leaf_stats['minimized'] > 0:
                            onset_perc = to_percent(leaf_stats['on-set'], leaf_stats['minimized'])
                            offset_perc = to_percent(leaf_stats['off-set'], leaf_stats['minimized'])
                            f.write(f"    - ON-set Minimizations:  {onset_perc:.2f}% (Total: {leaf_stats['on-set']})\n")
                            f.write(f"    - OFF-set Minimizations: {offset_perc:.2f}% (Total: {leaf_stats['off-set']})\n")

                        f.write(f"  - Incompressible (Raw):    {incomp_perc:.2f}% (Total: {leaf_stats['incompressible']})\n\n")
                    else:
                        f.write("  - No heterogeneous leaf nodes (4x4) were generated.\n\n")


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
    """
    if not node: return
    w, h = node.get('w', 0), node.get('h', 0)
    level_key = f"{w}x{h}"
    plane_stat_dict = stats.plane_stats[bit]
    code_counts = plane_stat_dict['code_counts']
    leaf_stats = plane_stat_dict['leaf_node_stats']

    if level_key in code_counts:
        if node['type'] == 'leaf':
            subtype = node.get('subtype')
            if subtype == 'espresso':
                code_counts[level_key]['11'] += 1
                leaf_stats['minimized'] += 1
                minimized_data = node.get('data', {})
                if minimized_data.get('code') == '00':
                    leaf_stats['on-set'] += 1
                elif minimized_data.get('code') == '01':
                    leaf_stats['off-set'] += 1
            elif subtype == 'raw':
                code_counts[level_key]['11'] += 1
                leaf_stats['incompressible'] += 1
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