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
                },
                "code_counts": {
                    "64x64": {"00": 0, "01": 0, "10": 0, "11": 0},
                    "32x32": {"00": 0, "01": 0, "10": 0, "11": 0},
                    "16x16": {"00": 0, "01": 0, "10": 0, "11": 0},
                    "8x8": {"00": 0, "01": 0, "10": 0, "11": 0},
                    "4x4": {"00": 0, "01": 0, "10": 0, "11": 0},
                    "2x2": {"00": 0, "01": 0, "10": 0, "11": 0},
                },
                "level_leaf_counts": {
                    "8x8": {"espresso": 0, "raw": 0, "homo_0": 0, "homo_1": 0},
                    "4x4": {"espresso": 0, "raw": 0, "homo_0": 0, "homo_1": 0},
                    "2x2": {"espresso": 0, "raw": 0, "homo_0": 0, "homo_1": 0},
                },
                "xor_usage": {
                    "4x4": {"xor_applied": 0, "no_xor": 0},
                    "2x2": {"xor_applied": 0, "no_xor": 0},
                },
                "overflow_stats": {
                    "leaf_node_counts": {
                        "compressible_homo_0": 0,
                        "compressible_homo_1": 0,
                        "compressible_espresso": 0,
                        "incompressible_raw": 0,
                    }
                },
                "xor_comparison_stats": {
                    "originally_compressible": 0,
                    "originally_incompressible": 0,
                    "xor_converted_to_compressible": 0,
                    "xor_failed_to_convert": 0,
                },
            }

    def dump_to_file(
        self,
        filepath,
        compression_time,
        decompression_time,
        initial_size_bits,
        padded_size_bits,
        baseline_stats=None,
    ):
        try:
            with open(filepath, "w") as f:
                f.write("=" * 50 + "\n")
                f.write("      Compression Statistics Report\n")
                f.write("=" * 50 + "\n\n")

                def to_percent(numerator, denominator):
                    return (numerator / denominator) * 100 if denominator > 0 else 0.0

                for bit, stats in sorted(self.plane_stats.items()):
                    f.write("-" * 40 + "\n")
                    f.write(f"  Bitplane {bit}\n")
                    if 'compressed_bits' in stats:
                        compressed_bits = stats['compressed_bits']
                        f.write(f"  Compressed Bits: {compressed_bits}\n")
                        if baseline_stats and bit in baseline_stats:
                            baseline_bits = baseline_stats[bit]
                            diff = baseline_bits - compressed_bits
                            perc = (diff / baseline_bits) * 100 if baseline_bits > 0 else 0
                            f.write(f"  Improvement vs 8x4 ({baseline_bits} bits): {diff} bits ({perc:.2f}%)\n")
                    f.write("-" * 40 + "\n")

                    f.write("--- Analysis of Used Quadtrees ---\n")
                    total_64_blocks = (
                        stats["quadtree_64_blocks"] + stats["raw_64_blocks"]
                    )
                    f.write(f"Total 64x64 blocks processed: {total_64_blocks}\n")
                    if total_64_blocks > 0:
                        f.write(
                            f"  - Compressed with Quadtree: {stats['quadtree_64_blocks']} ({to_percent(stats['quadtree_64_blocks'], total_64_blocks):.2f}%)\n"
                        )
                        f.write(
                            f"  - Stored as Raw (64x64 Overflow): {stats['raw_64_blocks']} ({to_percent(stats['raw_64_blocks'], total_64_blocks):.2f}%)\n\n"
                        )

                    f.write(
                        "Code Appearances per Level (00: Homo-0, 01: Homo-1, 10: Internal, 11: Hetero-Leaf):\n"
                    )
                    for level in ["64x64", "32x32", "16x16", "8x8", "4x4", "2x2"]:
                        counts = stats["code_counts"][level]
                        total_level_nodes = sum(counts.values())
                        f.write(
                            f"  Level {level} (Total Nodes: {total_level_nodes}):\n"
                        )
                        if total_level_nodes > 0:
                            code_map = {
                                "00": "Homo-0",
                                "01": "Homo-1",
                                "10": "Internal",
                                "11": "Hetero-Leaf",
                            }
                            for code, desc in code_map.items():
                                if code == "11" and level not in ["8x8", "4x4", "2x2"]:
                                    continue
                                count = counts.get(code, 0)
                                perc = to_percent(count, total_level_nodes)
                                f.write(
                                    f"    - {code} ({desc}):".ljust(30)
                                    + f"{count} ({perc:.2f}%)\n"
                                )
                        else:
                            f.write("    - No nodes at this level.\n")
                    f.write("\n")

                    f.write("Leaf Node Type Distribution (Per Level):\n")
                    for level in ["8x8", "4x4", "2x2"]:
                        level_counts = stats["level_leaf_counts"][level]
                        total_level_leaves = sum(level_counts.values())
                        f.write(
                            f"  Level {level} (Total Leaves: {total_level_leaves}):\n"
                        )
                        if total_level_leaves > 0:
                            for leaf_type in ["espresso", "raw", "homo_0", "homo_1"]:
                                count = level_counts[leaf_type]
                                perc = to_percent(count, total_level_leaves)
                                type_name = {
                                    "espresso": "Espresso",
                                    "raw": "Raw",
                                    "homo_0": "Homogeneous-0",
                                    "homo_1": "Homogeneous-1",
                                }[leaf_type]
                                f.write(
                                    f"    - {type_name}:".ljust(25)
                                    + f"{count} ({perc:.2f}%)\n"
                                )
                        else:
                            f.write("    - No leaves at this level.\n")
                    f.write("\n")

                    f.write("XOR Usage Statistics (Predictive XOR for Small Blocks):\n")
                    for level in ["4x4", "2x2"]:
                        xor_counts = stats["xor_usage"][level]
                        total_xor_blocks = (
                            xor_counts["xor_applied"] + xor_counts["no_xor"]
                        )
                        f.write(
                            f"  Level {level} (Total Blocks: {total_xor_blocks}):\n"
                        )
                        if total_xor_blocks > 0:
                            f.write(
                                f"    - XOR Applied:".ljust(25)
                                + f"{xor_counts['xor_applied']} ({to_percent(xor_counts['xor_applied'], total_xor_blocks):.2f}%)\n"
                            )
                            f.write(
                                f"    - No XOR:".ljust(25)
                                + f"{xor_counts['no_xor']} ({to_percent(xor_counts['no_xor'], total_xor_blocks):.2f}%)\n"
                            )
                        else:
                            f.write("    - No blocks at this level.\n")
                    f.write("\n")

                    if "xor_comparison_stats" in stats:
                         xor_s = stats["xor_comparison_stats"]
                         orig_comp = xor_s["originally_compressible"]
                         orig_incomp = xor_s["originally_incompressible"]
                         total_blocks = orig_comp + orig_incomp
                         
                         converted = xor_s["xor_converted_to_compressible"]
                         failed = xor_s["xor_failed_to_convert"]
                         
                         f.write("Predictive XOR 8x8 Effectiveness (Targeted Analysis):\n")
                         f.write(f"  Total 8x8 Blocks Evaluated: {total_blocks}\n")
                         
                         if total_blocks > 0:
                             f.write(f"    Originally Compressible:   {orig_comp} ({to_percent(orig_comp, total_blocks):.2f}%)\n")
                             f.write(f"    Originally Incompressible: {orig_incomp} ({to_percent(orig_incomp, total_blocks):.2f}%)\n")
                             
                             if orig_incomp > 0:
                                 f.write(f"      -> Converted to Compressible via XOR: {converted} ({to_percent(converted, orig_incomp):.2f}% success rate)\n")
                                 f.write(f"      -> Remained Incompressible:           {failed} ({to_percent(failed, orig_incomp):.2f}%)\n")
                             else:
                                 f.write("      (No incompressible blocks to test XOR on)\n")
                         else:
                             f.write("    No 8x8 blocks evaluated.\n")
                    f.write("\n")

                    f.write("Overall Leaf Node Type Distribution:\n")
                    leaf_counts = stats["leaf_node_counts"]
                    total_leaf_nodes = sum(leaf_counts.values())
                    f.write(f"  Total Leaf Nodes: {total_leaf_nodes}\n")
                    if total_leaf_nodes > 0:
                        f.write(
                            f"  - Homogeneous-0:".ljust(30)
                            + f"{leaf_counts['compressible_homo_0']} ({to_percent(leaf_counts['compressible_homo_0'], total_leaf_nodes):.2f}%)\n"
                        )
                        f.write(
                            f"  - Homogeneous-1:".ljust(30)
                            + f"{leaf_counts['compressible_homo_1']} ({to_percent(leaf_counts['compressible_homo_1'], total_leaf_nodes):.2f}%)\n"
                        )
                        f.write(
                            f"  - Espresso:".ljust(30)
                            + f"{leaf_counts['compressible_espresso']} ({to_percent(leaf_counts['compressible_espresso'], total_leaf_nodes):.2f}%)\n"
                        )
                        f.write(
                            f"  - Raw:".ljust(30)
                            + f"{leaf_counts['incompressible_raw']} ({to_percent(leaf_counts['incompressible_raw'], total_leaf_nodes):.2f}%)\n\n"
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
                        f.write(f"    Total Leaf Nodes: {total_leaf_nodes_ovf}\n")
                        if total_leaf_nodes_ovf > 0:
                            f.write(
                                f"    - Homogeneous-0:".ljust(30)
                                + f"{leaf_counts_ovf['compressible_homo_0']} ({to_percent(leaf_counts_ovf['compressible_homo_0'], total_leaf_nodes_ovf):.2f}%)\n"
                            )
                            f.write(
                                f"    - Homogeneous-1:".ljust(30)
                                + f"{leaf_counts_ovf['compressible_homo_1']} ({to_percent(leaf_counts_ovf['compressible_homo_1'], total_leaf_nodes_ovf):.2f}%)\n"
                            )
                            f.write(
                                f"    - Espresso:".ljust(30)
                                + f"{leaf_counts_ovf['compressible_espresso']} ({to_percent(leaf_counts_ovf['compressible_espresso'], total_leaf_nodes_ovf):.2f}%)\n"
                            )
                            f.write(
                                f"    - Raw:".ljust(30)
                                + f"{leaf_counts_ovf['incompressible_raw']} ({to_percent(leaf_counts_ovf['incompressible_raw'], total_leaf_nodes_ovf):.2f}%)\n\n"
                            )
                    else:
                        f.write("  No 64x64 blocks overflowed.\n\n")

                # Accumulate totals for XOR stats
                total_orig_comp = 0
                total_orig_incomp = 0
                total_converted = 0
                total_failed = 0
                
                for bit, stats in self.plane_stats.items():
                    if "xor_comparison_stats" in stats:
                        xor_s = stats["xor_comparison_stats"]
                        total_orig_comp += xor_s["originally_compressible"]
                        total_orig_incomp += xor_s["originally_incompressible"]
                        total_converted += xor_s["xor_converted_to_compressible"]
                        total_failed += xor_s["xor_failed_to_convert"]
                
                total_eval = total_orig_comp + total_orig_incomp

                if total_eval > 0:
                    f.write("=" * 50 + "\n")
                    f.write("      Total Predictive XOR 8x8 Effectiveness\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(f"Total 8x8 Blocks Evaluated (All Planes): {total_eval}\n")
                    f.write(f"  Originally Compressible:   {total_orig_comp} ({to_percent(total_orig_comp, total_eval):.2f}%)\n")
                    f.write(f"  Originally Incompressible: {total_orig_incomp} ({to_percent(total_orig_incomp, total_eval):.2f}%)\n")
                    
                    if total_orig_incomp > 0:
                        f.write(f"    -> Converted to Compressible via XOR: {total_converted} ({to_percent(total_converted, total_orig_incomp):.2f}% success rate)\n")
                        f.write(f"    -> Remained Incompressible:           {total_failed} ({to_percent(total_failed, total_orig_incomp):.2f}%)\n")
                    f.write("\n")

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
                    f"Initial Size (before padding): {initial_size_bits / 8:.0f} bytes ({initial_size_bits} bits)\n"
                )
                f.write(
                    f"Size After Padding:            {padded_size_bits / 8:.0f} bytes ({padded_size_bits} bits)\n"
                )
                f.write(
                    f"Compressed Size:               {self.compressed_bits / 8:.2f} bytes ({self.compressed_bits} bits)\n"
                )
                if baseline_stats and 'total' in baseline_stats:
                    baseline_total = baseline_stats['total']
                    diff_total = baseline_total - self.compressed_bits
                    perc_total = (diff_total / baseline_total) * 100 if baseline_total > 0 else 0
                    f.write(f"Improvement vs 8x4 (Total, {baseline_total} bits):    {diff_total} bits ({perc_total:.2f}%)\n")
                f.write("\n")
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

    w, h = node.get("w", 0), node.get("h", 0)
    level_key = f"{w}x{h}"
    code_counts = stat_root["code_counts"]

    if level_key in code_counts:
        if node["type"] == "leaf":
            subtype = node.get("subtype")
            if subtype in ["espresso", "raw"]:
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

        if subtype == "espresso":
            target_leaf_counter["compressible_espresso"] += 1
            if not is_overflow and level_key in stat_root["level_leaf_counts"]:
                stat_root["level_leaf_counts"][level_key]["espresso"] += 1
                if level_key in stat_root["xor_usage"]:
                    if node.get("xor_applied", False):
                        stat_root["xor_usage"][level_key]["xor_applied"] += 1
                    else:
                        stat_root["xor_usage"][level_key]["no_xor"] += 1

        elif subtype == "raw":
            target_leaf_counter["incompressible_raw"] += 1
            if not is_overflow and level_key in stat_root["level_leaf_counts"]:
                stat_root["level_leaf_counts"][level_key]["raw"] += 1
                if level_key in stat_root["xor_usage"]:
                    if node.get("xor_applied", False):
                        stat_root["xor_usage"][level_key]["xor_applied"] += 1
                    else:
                        stat_root["xor_usage"][level_key]["no_xor"] += 1

        elif "code" in node:
            if node["code"] == "10":
                target_leaf_counter["compressible_homo_0"] += 1
                if not is_overflow and level_key in stat_root["level_leaf_counts"]:
                    stat_root["level_leaf_counts"][level_key]["homo_0"] += 1
            elif node["code"] == "11":
                target_leaf_counter["compressible_homo_1"] += 1
                if not is_overflow and level_key in stat_root["level_leaf_counts"]:
                    stat_root["level_leaf_counts"][level_key]["homo_1"] += 1

    if "children" in node:
        for child in node["children"]:
            _collect_stats_from_node(child, stats, bit, is_overflow)
