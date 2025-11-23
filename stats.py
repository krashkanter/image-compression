class CompressionStats:
    def __init__(self):
        self.raw_bits = 0
        self.compressed_bits = 0
        self.plane_stats = {}

    def _init_plane_stats(self, bit):
        if bit not in self.plane_stats:
            self.plane_stats[bit] = {
                "quadtree_64_blocks": 0,
                "raw_64_blocks": 0,
                "leaf_node_counts": {
                    "compressible_homo_0": 0,
                    "compressible_homo_1": 0,
                    "compressible_espresso": 0,
                    "incompressible_raw": 0,
                    "template_match": 0,  # NEW
                },
                "espresso_cube_counts": {i: 0 for i in range(1, 33)},
                "on_set_cube_counts": {i: 0 for i in range(1, 33)},
                "off_set_cube_counts": {i: 0 for i in range(1, 33)},
                "in_tree_raw_stats": {
                    "total_blocks": 0,
                    "espresso_cube_counts": {i: 0 for i in range(1, 33)},
                    "on_set_cube_counts": {i: 0 for i in range(1, 33)},
                    "off_set_cube_counts": {i: 0 for i in range(1, 33)},
                },
                # NEW: Template Stats
                "template_stats": {
                    "blocks_resolved": 0,
                    "bits_saved": 0,
                    "template_usage": {i: 0 for i in range(1, 8)},  # IDs 1-7
                },
                "alternative_subdivision_stats": {
                    "total_espresso_blocks": 0,
                    "espresso_better": 0,
                    "subdivision_better": 0,
                    "tied": 0,
                    "total_espresso_cost": 0,
                    "total_subdivision_cost": 0,
                },
                "overflow_stats": {
                    "leaf_node_counts": {
                        "compressible_homo_0": 0,
                        "compressible_homo_1": 0,
                        "compressible_espresso": 0,
                        "incompressible_raw": 0,
                        "template_match": 0,  # FIXED: Added missing key here
                    },
                    "espresso_cube_counts": {i: 0 for i in range(1, 33)},
                },
                "code_counts": {
                    "64x64": {"00": 0, "01": 0, "10": 0, "11": 0},
                    "32x32": {"00": 0, "01": 0, "10": 0, "11": 0},
                    "16x16": {"00": 0, "01": 0, "10": 0, "11": 0},
                    "8x8": {"00": 0, "01": 0, "10": 0, "11": 0},
                    "4x4": {"00": 0, "01": 0, "10": 0, "11": 0},
                },
            }

    def dump_to_file(
        self,
        filepath,
        compression_time,
        decompression_time,
        initial_size_bits,
        padded_size_bits,
    ):
        try:
            with open(filepath, "w") as f:
                f.write("=" * 50 + "\n")
                f.write("      Compression Statistics Report\n")
                f.write("=" * 50 + "\n\n")

                def to_percent(numerator, denominator):
                    return (numerator / denominator) * 100 if denominator > 0 else 0.0

                total_template_resolved_all_planes = 0
                total_bits_saved_all_planes = 0

                for bit, stats in sorted(self.plane_stats.items()):
                    f.write("-" * 40 + "\n")
                    f.write(f"  Bitplane {bit}\n")
                    f.write("-" * 40 + "\n")

                    f.write("--- Analysis of Used Quadtrees ---\n")
                    total_64_blocks = (
                        stats["quadtree_64_blocks"] + stats["raw_64_blocks"]
                    )
                    f.write(f"Total 64x64 blocks processed: {total_64_blocks}\n")
                    if total_64_blocks > 0:
                        f.write(
                            f"  - Compressed with Quadtree: {to_percent(stats['quadtree_64_blocks'], total_64_blocks):.2f}%\n"
                        )
                        f.write(
                            f"  - Stored as Raw (64x64 Overflow): {to_percent(stats['raw_64_blocks'], total_64_blocks):.2f}%\n\n"
                        )

                    f.write("Code Appearances per Level:\n")
                    for level, counts in stats["code_counts"].items():
                        total_level_nodes = sum(counts.values())
                        if total_level_nodes > 0:
                            f.write(f"  Level {level} (Total: {total_level_nodes})\n")

                    f.write("\nLeaf Node Type Distribution:\n")
                    leaf_counts = stats["leaf_node_counts"]
                    total_leaf_nodes = sum(leaf_counts.values())

                    if total_leaf_nodes > 0:
                        total_compressible = (
                            leaf_counts["compressible_homo_0"]
                            + leaf_counts["compressible_homo_1"]
                            + leaf_counts["compressible_espresso"]
                        )
                        f.write(
                            f"  - Standard Compressible:".ljust(30)
                            + f"{to_percent(total_compressible, total_leaf_nodes):.2f}% ({total_compressible})\n"
                        )
                        f.write(
                            f"  - Template Matches (New):".ljust(30)
                            + f"{to_percent(leaf_counts['template_match'], total_leaf_nodes):.2f}% ({leaf_counts['template_match']})\n"
                        )
                        f.write(
                            f"  - Incompressible (Raw):".ljust(30)
                            + f"{to_percent(leaf_counts['incompressible_raw'], total_leaf_nodes):.2f}% ({leaf_counts['incompressible_raw']})\n\n"
                        )

                    # NEW: Template Stats Section
                    t_stats = stats["template_stats"]
                    f.write(
                        "--- Template Matching Statistics (Incompressible Fallback) ---\n"
                    )
                    if t_stats["blocks_resolved"] > 0:
                        total_template_resolved_all_planes += t_stats["blocks_resolved"]
                        total_bits_saved_all_planes += t_stats["bits_saved"]

                        f.write(
                            f"  Total Incompressible Blocks Resolved: {t_stats['blocks_resolved']}\n"
                        )
                        f.write(f"  Bits Saved vs Raw: {t_stats['bits_saved']} bits\n")
                        f.write("  Template Usage:\n")
                        for t_id, count in t_stats["template_usage"].items():
                            if count > 0:
                                f.write(
                                    f"    - Template #{t_id}: {count} times ({to_percent(count, t_stats['blocks_resolved']):.1f}%)\n"
                                )
                    else:
                        f.write("  No blocks used template matching in this plane.\n")
                    f.write("\n")

                    # Existing Espresso Stats
                    f.write("Espresso-Compressed Leaf Cube Distribution:\n")
                    cube_counts = stats["espresso_cube_counts"]
                    total_espresso_nodes = stats["leaf_node_counts"][
                        "compressible_espresso"
                    ]
                    if total_espresso_nodes > 0:
                        f.write(
                            f"  (For the {total_espresso_nodes} leaves compressed with Espresso)\n"
                        )
                        for num_cubes, count in sorted(cube_counts.items()):
                            if count > 0:
                                label = f"{num_cubes} Cubes"
                                f.write(
                                    f"    - {label}:".ljust(15)
                                    + f"{to_percent(count, total_espresso_nodes):.2f}% ({count} blocks)\n"
                                )
                        f.write("\n")

                    f.write("--- Espresso vs 4x4 Subdivision Comparison ---\n")
                    alt_stats = stats["alternative_subdivision_stats"]
                    if alt_stats["total_espresso_blocks"] > 0:
                        total = alt_stats["total_espresso_blocks"]
                        f.write(f"  Total 8x8 blocks using Espresso: {total}\n")
                        f.write(
                            f"  - Espresso was better: {to_percent(alt_stats['espresso_better'], total):.2f}%\n"
                        )
                        f.write(
                            f"  - 4x4 Subdivision was better: {to_percent(alt_stats['subdivision_better'], total):.2f}%\n"
                        )
                        f.write(
                            f"  - Tied: {to_percent(alt_stats['tied'], total):.2f}%\n\n"
                        )

                    f.write(
                        "\n--- Analysis of Discarded 64x64 Quadtrees (Overflow) ---\n"
                    )
                    if stats["raw_64_blocks"] > 0:
                        f.write(
                            f"  (For the {stats['raw_64_blocks']} blocks where the entire Quadtree was larger than raw)\n\n"
                        )
                        overflow_stats = stats["overflow_stats"]
                        leaf_counts_ovf = overflow_stats["leaf_node_counts"]
                        total_leaf_nodes_ovf = sum(leaf_counts_ovf.values())
                        f.write("  Leaf Node Type Distribution (Overflow Trees):\n")
                        if total_leaf_nodes_ovf > 0:
                            f.write(
                                f"    - Template Matches: {to_percent(leaf_counts_ovf['template_match'], total_leaf_nodes_ovf):.2f}%\n"
                            )

                f.write("=" * 50 + "\n")
                f.write("      Overall Summary\n")
                f.write("=" * 50 + "\n")

                compression_ratio = (
                    initial_size_bits / self.compressed_bits
                    if self.compressed_bits > 0
                    else 0
                )
                space_savings = (
                    (1 - (self.compressed_bits / padded_size_bits)) * 100
                    if padded_size_bits > 0
                    else 0
                )

                f.write(
                    f"Total Blocks Resolved by Templates: {total_template_resolved_all_planes}\n"
                )
                f.write(
                    f"Total Bits Saved by Templates:      {total_bits_saved_all_planes}\n\n"
                )

                f.write(
                    f"Initial Size (before padding): {initial_size_bits / 8:.0f} bytes ({initial_size_bits} bits)\n"
                )
                f.write(
                    f"Size After Padding:            {padded_size_bits / 8:.0f} bytes ({padded_size_bits} bits)\n"
                )
                f.write(
                    f"Compressed Size:               {self.compressed_bits / 8:.2f} bytes ({self.compressed_bits} bits)\n\n"
                )
                f.write(f"Compression Ratio (Initial/New): {compression_ratio:.4f}\n")
                f.write(
                    f"Percentage Space Savings (vs Padded): {space_savings:.2f}%\n\n"
                )
                f.write(f"Compression Time Taken:   {compression_time:.4f} seconds\n")
                f.write(f"Decompression Time Taken: {decompression_time:.4f} seconds\n")
                f.write("=" * 50 + "\n")

            print(f"Statistics successfully dumped to '{filepath}'")
        except IOError as e:
            print(f"Error writing statistics file: {e}")


def _collect_stats_from_node(node, stats, bit, is_overflow=False):
    if not node:
        return

    stat_root = stats.plane_stats[bit]
    target_leaf_counter = (
        stat_root["overflow_stats"]["leaf_node_counts"]
        if is_overflow
        else stat_root["leaf_node_counts"]
    )
    target_cube_counter = (
        stat_root["overflow_stats"]["espresso_cube_counts"]
        if is_overflow
        else stat_root["espresso_cube_counts"]
    )

    w, h = node.get("w", 0), node.get("h", 0)
    level_key = f"{w}x{h}"
    plane_stat_dict = stats.plane_stats[bit]
    code_counts = plane_stat_dict["code_counts"]

    if level_key in code_counts:
        if node["type"] == "leaf":
            subtype = node.get("subtype")
            if subtype in ["espresso", "raw", "template_match"]:
                code_counts[level_key]["11"] += 1
            elif "code" in node:
                if node["code"] == "10":
                    code_counts[level_key]["00"] += 1
                elif node["code"] == "11":
                    code_counts[level_key]["01"] += 1
        elif node["type"] == "node":
            code_counts[level_key]["10"] += 1

    if node["type"] == "leaf":
        subtype = node.get("subtype")

        if subtype == "template_match":
            target_leaf_counter["template_match"] += 1
            if not is_overflow:
                t_stats = stat_root["template_stats"]
                t_stats["blocks_resolved"] += 1

                # Calculate savings
                saved = node.get("bits_saved", 0)
                t_stats["bits_saved"] += saved

                t_id = node.get("template_id", 0)
                if t_id in t_stats["template_usage"]:
                    t_stats["template_usage"][t_id] += 1

        elif subtype == "espresso":
            target_leaf_counter["compressible_espresso"] += 1
            num_cubes = len(node["data"].get("cubes", []))
            if 1 <= num_cubes <= 32:
                target_cube_counter[num_cubes] += 1

            if "alternative_subdivision" in node and not is_overflow:
                alt_stats = stat_root["alternative_subdivision_stats"]
                alt_stats["total_espresso_blocks"] += 1

                alt_data = node["alternative_subdivision"]
                subdivision_cost = alt_data.get("total_cost", 0)
                espresso_cost = len(node["data"].get("cubes", [])) * 10  # Approx cost

                alt_stats["total_espresso_cost"] += espresso_cost
                alt_stats["total_subdivision_cost"] += subdivision_cost

                if espresso_cost < subdivision_cost:
                    alt_stats["espresso_better"] += 1
                elif subdivision_cost < espresso_cost:
                    alt_stats["subdivision_better"] += 1
                else:
                    alt_stats["tied"] += 1

        elif subtype == "raw":
            target_leaf_counter["incompressible_raw"] += 1
            if not is_overflow and "discarded_minimized_data" in node:
                in_tree_stats = stat_root["in_tree_raw_stats"]
                in_tree_stats["total_blocks"] += 1
                discarded_data = node["discarded_minimized_data"]
                num_cubes = len(discarded_data.get("cubes", []))
                if 1 <= num_cubes <= 32:
                    in_tree_stats["espresso_cube_counts"][num_cubes] += 1

                on_set_cubes = discarded_data.get("on_set_cubes", 0)
                if 1 <= on_set_cubes <= 32:
                    in_tree_stats["on_set_cube_counts"][on_set_cubes] += 1

        elif "code" in node:
            if node["code"] == "10":
                target_leaf_counter["compressible_homo_0"] += 1
            elif node["code"] == "11":
                target_leaf_counter["compressible_homo_1"] += 1

    if "children" in node:
        for child in node["children"]:
            _collect_stats_from_node(child, stats, bit, is_overflow)
