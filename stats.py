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
                'raw_64_blocks': 0, # These are the 64x64 overflows
                'leaf_node_counts': {
                    'compressible_homo_0': 0, 'compressible_homo_1': 0,
                    'compressible_espresso': 0, 'incompressible_raw': 0,
                },
                'espresso_cube_counts': {
                    1: 0, 2: 0, 3: 0, 4: 0, 5: 0, '6+': 0
                },
                # NEW: Stats for leaves where Espresso was run but discarded for being too costly
                'in_tree_raw_stats': {
                    'total_blocks': 0,
                    'espresso_cube_counts': { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, '6+': 0 }
                },
                # Stats for the internal structure of discarded 64x64 trees
                'overflow_stats': {
                    'leaf_node_counts': {
                        'compressible_homo_0': 0, 'compressible_homo_1': 0,
                        'compressible_espresso': 0, 'incompressible_raw': 0,
                    },
                    'espresso_cube_counts': { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, '6+': 0 }
                }
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

                    f.write("--- Analysis of Used Quadtrees ---\n")
                    total_64_blocks = stats['quadtree_64_blocks'] + stats['raw_64_blocks']
                    f.write(f"Total 64x64 blocks processed: {total_64_blocks}\n")
                    if total_64_blocks > 0:
                        f.write(f"  - Compressed with Quadtree: {to_percent(stats['quadtree_64_blocks'], total_64_blocks):.2f}%\n")
                        f.write(f"  - Stored as Raw (64x64 Overflow): {to_percent(stats['raw_64_blocks'], total_64_blocks):.2f}%\n\n")

                    f.write("Leaf Node Type Distribution:\n")
                    leaf_counts = stats['leaf_node_counts']
                    total_leaf_nodes = sum(leaf_counts.values())
                    f.write(f"  Total Leaf Nodes: {total_leaf_nodes}\n")
                    if total_leaf_nodes > 0:
                        total_compressible = leaf_counts['compressible_homo_0'] + leaf_counts['compressible_homo_1'] + leaf_counts['compressible_espresso']
                        f.write(f"  - Compressible:".ljust(25) + f"{to_percent(total_compressible, total_leaf_nodes):.2f}% ({total_compressible} nodes)\n")
                        f.write(f"  - Incompressible (In-Tree Raw):".ljust(25) + f"{to_percent(leaf_counts['incompressible_raw'], total_leaf_nodes):.2f}% ({leaf_counts['incompressible_raw']} nodes)\n\n")

                    f.write("Espresso-Compressed Leaf Cube Distribution:\n")
                    cube_counts = stats['espresso_cube_counts']
                    total_espresso_nodes = stats['leaf_node_counts']['compressible_espresso']
                    if total_espresso_nodes > 0:
                        f.write(f"  (For the {total_espresso_nodes} leaves compressed with Espresso)\n")
                        for num_cubes, count in sorted(cube_counts.items(), key=lambda item: str(item[0])):
                            label = f"{num_cubes} Cubes" if isinstance(num_cubes, int) else "6+ Cubes"
                            f.write(f"    - {label}:".ljust(15) + f"{to_percent(count, total_espresso_nodes):.2f}% ({count} blocks)\n")
                        f.write("\n")
                    else:
                        f.write("  - No leaf nodes were compressed with Espresso.\n\n")

                    # --- NEW SECTION AS PER YOUR REQUEST ---
                    f.write("Analysis of Discarded Espresso Results (In-Tree Raw Leaves):\n")
                    in_tree_stats = stats['in_tree_raw_stats']
                    total_raw_leaves = in_tree_stats['total_blocks']
                    if total_raw_leaves > 0:
                        f.write(f"  (For the {total_raw_leaves} leaves where Espresso was costlier than raw pixels)\n")
                        cube_counts_raw = in_tree_stats['espresso_cube_counts']
                        for num_cubes, count in sorted(cube_counts_raw.items(), key=lambda item: str(item[0])):
                            label = f"{num_cubes} Cubes" if isinstance(num_cubes, int) else "6+ Cubes"
                            f.write(f"    - {label}:".ljust(15) + f"{to_percent(count, total_raw_leaves):.2f}% ({count} blocks)\n")
                        f.write("\n")
                    else:
                        f.write("  - No leaf nodes were stored as raw due to high Espresso cost.\n\n")

                    # --- Analysis of 64x64 Overflow Blocks ---
                    f.write("\n--- Analysis of Discarded 64x64 Quadtrees (Overflow) ---\n")
                    if stats['raw_64_blocks'] > 0:
                        f.write(f"  (For the {stats['raw_64_blocks']} blocks where the entire Quadtree was larger than raw)\n\n")
                        overflow_stats = stats['overflow_stats']
                        leaf_counts_ovf = overflow_stats['leaf_node_counts']
                        total_leaf_nodes_ovf = sum(leaf_counts_ovf.values())
                        f.write("  Leaf Node Type Distribution (Overflow Trees):\n")
                        f.write(f"    Total Leaf Nodes: {total_leaf_nodes_ovf}\n")
                        if total_leaf_nodes_ovf > 0:
                            total_comp_ovf = leaf_counts_ovf['compressible_homo_0'] + leaf_counts_ovf['compressible_homo_1'] + leaf_counts_ovf['compressible_espresso']
                            f.write(f"    - Compressible:".ljust(25) + f"{to_percent(total_comp_ovf, total_leaf_nodes_ovf):.2f}%\n")
                            f.write(f"    - Incompressible (In-Tree Raw):".ljust(25) + f"{to_percent(leaf_counts_ovf['incompressible_raw'], total_leaf_nodes_ovf):.2f}%\n\n")
                    else:
                        f.write("  No 64x64 blocks overflowed.\n\n")


                f.write("=" * 50 + "\n")
                f.write("      Overall Summary\n")
                f.write("=" * 50 + "\n")
                compression_ratio = initial_size_bits / self.compressed_bits if self.compressed_bits > 0 else 0
                space_savings = (1 - (self.compressed_bits / padded_size_bits)) * 100 if padded_size_bits > 0 else 0
                f.write(f"Initial Size (before padding): {initial_size_bits / 8:.0f} bytes ({initial_size_bits} bits)\n")
                f.write(f"Size After Padding:            {padded_size_bits / 8:.0f} bytes ({padded_size_bits} bits)\n")
                f.write(f"Compressed Size:               {self.compressed_bits / 8:.2f} bytes ({self.compressed_bits} bits)\n\n")
                f.write(f"Compression Ratio (Initial/New): {compression_ratio:.4f}\n")
                f.write(f"Percentage Space Savings (vs Padded): {space_savings:.2f}%\n\n")
                f.write(f"Compression Time Taken:   {compression_time:.4f} seconds\n")
                f.write(f"Decompression Time Taken: {decompression_time:.4f} seconds\n")
                f.write("=" * 50 + "\n")

            print(f"Statistics successfully dumped to '{filepath}'")
        except IOError as e:
            print(f"Error writing statistics file: {e}")

def _collect_stats_from_node(node, stats, bit, is_overflow=False):
    """
    Recursively traverses the quadtree to collect detailed statistics.
    """
    if not node: return

    stat_root = stats.plane_stats[bit]
    target_leaf_counter = stat_root['overflow_stats']['leaf_node_counts'] if is_overflow else stat_root['leaf_node_counts']
    target_cube_counter = stat_root['overflow_stats']['espresso_cube_counts'] if is_overflow else stat_root['espresso_cube_counts']
    
    if node['type'] == 'leaf':
        subtype = node.get('subtype')
        if subtype == 'espresso':
            target_leaf_counter['compressible_espresso'] += 1
            num_cubes = len(node['data'].get('cubes', []))
            if 1 <= num_cubes <= 5: target_cube_counter[num_cubes] += 1
            elif num_cubes > 5: target_cube_counter['6+'] += 1
        elif subtype == 'raw':
            target_leaf_counter['incompressible_raw'] += 1
            # MODIFIED: Check for discarded espresso data on raw leaves
            if not is_overflow and 'discarded_minimized_data' in node:
                in_tree_stats = stat_root['in_tree_raw_stats']
                in_tree_stats['total_blocks'] += 1
                discarded_data = node['discarded_minimized_data']
                num_cubes = len(discarded_data.get('cubes', []))
                if 1 <= num_cubes <= 5: in_tree_stats['espresso_cube_counts'][num_cubes] += 1
                elif num_cubes > 5: in_tree_stats['espresso_cube_counts']['6+'] += 1
        elif 'code' in node:
            if node['code'] == '10': target_leaf_counter['compressible_homo_0'] += 1
            elif node['code'] == '11': target_leaf_counter['compressible_homo_1'] += 1
    
    if 'children' in node:
        for child in node['children']:
            _collect_stats_from_node(child, stats, bit, is_overflow)