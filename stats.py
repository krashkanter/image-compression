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
                "espresso_cube_counts": {
                    1: 0,
                    2: 0,
                    3: 0,
                    4: 0,
                    5: 0,
                    6: 0,
                    7: 0,
                    8: 0,
                    9: 0,
                    10: 0,
                    11: 0,
                    12: 0,
                    13: 0,
                    14: 0,
                    15: 0,
                    16: 0,
                    17: 0,
                    18: 0,
                    19: 0,
                    20: 0,
                    21: 0,
                    22: 0,
                    23: 0,
                    24: 0,
                    25: 0,
                    26: 0,
                    27: 0,
                    28: 0,
                    29: 0,
                    30: 0,
                    31: 0,
                    32: 0,
                },
                "on_set_cube_counts": {
                    1: 0,
                    2: 0,
                    3: 0,
                    4: 0,
                    5: 0,
                    6: 0,
                    7: 0,
                    8: 0,
                    9: 0,
                    10: 0,
                    11: 0,
                    12: 0,
                    13: 0,
                    14: 0,
                    15: 0,
                    16: 0,
                    17: 0,
                    18: 0,
                    19: 0,
                    20: 0,
                    21: 0,
                    22: 0,
                    23: 0,
                    24: 0,
                    25: 0,
                    26: 0,
                    27: 0,
                    28: 0,
                    29: 0,
                    30: 0,
                    31: 0,
                    32: 0,
                },
                "off_set_cube_counts": {
                    1: 0,
                    2: 0,
                    3: 0,
                    4: 0,
                    5: 0,
                    6: 0,
                    7: 0,
                    8: 0,
                    9: 0,
                    10: 0,
                    11: 0,
                    12: 0,
                    13: 0,
                    14: 0,
                    15: 0,
                    16: 0,
                    17: 0,
                    18: 0,
                    19: 0,
                    20: 0,
                    21: 0,
                    22: 0,
                    23: 0,
                    24: 0,
                    25: 0,
                    26: 0,
                    27: 0,
                    28: 0,
                    29: 0,
                    30: 0,
                    31: 0,
                    32: 0,
                },
                "in_tree_raw_stats": {
                    "total_blocks": 0,
                    "espresso_cube_counts": {
                        1: 0,
                        2: 0,
                        3: 0,
                        4: 0,
                        5: 0,
                        6: 0,
                        7: 0,
                        8: 0,
                        9: 0,
                        10: 0,
                        11: 0,
                        12: 0,
                        13: 0,
                        14: 0,
                        15: 0,
                        16: 0,
                        17: 0,
                        18: 0,
                        19: 0,
                        20: 0,
                        21: 0,
                        22: 0,
                        23: 0,
                        24: 0,
                        25: 0,
                        26: 0,
                        27: 0,
                        28: 0,
                        29: 0,
                        30: 0,
                        31: 0,
                        32: 0,
                    },
                    "on_set_cube_counts": {
                        1: 0,
                        2: 0,
                        3: 0,
                        4: 0,
                        5: 0,
                        6: 0,
                        7: 0,
                        8: 0,
                        9: 0,
                        10: 0,
                        11: 0,
                        12: 0,
                        13: 0,
                        14: 0,
                        15: 0,
                        16: 0,
                        17: 0,
                        18: 0,
                        19: 0,
                        20: 0,
                        21: 0,
                        22: 0,
                        23: 0,
                        24: 0,
                        25: 0,
                        26: 0,
                        27: 0,
                        28: 0,
                        29: 0,
                        30: 0,
                        31: 0,
                        32: 0,
                    },
                    "off_set_cube_counts": {
                        1: 0,
                        2: 0,
                        3: 0,
                        4: 0,
                        5: 0,
                        6: 0,
                        7: 0,
                        8: 0,
                        9: 0,
                        10: 0,
                        11: 0,
                        12: 0,
                        13: 0,
                        14: 0,
                        15: 0,
                        16: 0,
                        17: 0,
                        18: 0,
                        19: 0,
                        20: 0,
                        21: 0,
                        22: 0,
                        23: 0,
                        24: 0,
                        25: 0,
                        26: 0,
                        27: 0,
                        28: 0,
                        29: 0,
                        30: 0,
                        31: 0,
                        32: 0,
                    },
                },
                # NEW: Alternative subdivision comparison stats
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
                    },
                    "espresso_cube_counts": {
                        1: 0,
                        2: 0,
                        3: 0,
                        4: 0,
                        5: 0,
                        6: 0,
                        7: 0,
                        8: 0,
                        9: 0,
                        10: 0,
                        11: 0,
                        12: 0,
                        13: 0,
                        14: 0,
                        15: 0,
                        16: 0,
                        17: 0,
                        18: 0,
                        19: 0,
                        20: 0,
                        21: 0,
                        22: 0,
                        23: 0,
                        24: 0,
                        25: 0,
                        26: 0,
                        27: 0,
                        28: 0,
                        29: 0,
                        30: 0,
                        31: 0,
                        32: 0,
                    },
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

                    f.write(
                        "Code Appearances per Level (00: Homo-0, 01: Homo-1, 10: Internal, 11: Hetero-Leaf):\n"
                    )
                    for level, counts in stats["code_counts"].items():
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
                                if code == "11" and level not in ["8x8", "4x4"]:
                                    continue
                                perc = to_percent(
                                    counts.get(code, 0), total_level_nodes
                                )
                                f.write(
                                    f"    - {code} ({desc}):".ljust(22)
                                    + f"{perc:.2f}%\n"
                                )
                        else:
                            f.write("    - No nodes at this level.\n")
                    f.write("\n")

                    f.write("Leaf Node Type Distribution:\n")
                    leaf_counts = stats["leaf_node_counts"]
                    total_leaf_nodes = sum(leaf_counts.values())
                    f.write(f"  Total Leaf Nodes: {total_leaf_nodes}\n")
                    if total_leaf_nodes > 0:
                        total_compressible = (
                            leaf_counts["compressible_homo_0"]
                            + leaf_counts["compressible_homo_1"]
                            + leaf_counts["compressible_espresso"]
                        )
                        f.write(
                            f"  - Compressible:".ljust(25)
                            + f"{to_percent(total_compressible, total_leaf_nodes):.2f}% ({total_compressible} nodes)\n"
                        )
                        f.write(
                            f"  - Incompressible (In-Tree Raw):".ljust(25)
                            + f"{to_percent(leaf_counts['incompressible_raw'], total_leaf_nodes):.2f}% ({leaf_counts['incompressible_raw']} nodes)\n\n"
                        )

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
                            label = f"{num_cubes} Cubes"
                            f.write(
                                f"    - {label}:".ljust(15)
                                + f"{to_percent(count, total_espresso_nodes):.2f}% ({count} blocks)\n"
                            )
                        f.write("\n")
                    else:
                        f.write("  - No leaf nodes were compressed with Espresso.\n\n")

                    # NEW: Alternative Subdivision Comparison
                    f.write("--- Espresso vs 4x4 Subdivision Comparison ---\n")
                    alt_stats = stats["alternative_subdivision_stats"]
                    if alt_stats["total_espresso_blocks"] > 0:
                        total = alt_stats["total_espresso_blocks"]
                        f.write(f"  Total 8x8 blocks using Espresso: {total}\n")
                        f.write(
                            f"  - Espresso was better: {to_percent(alt_stats['espresso_better'], total):.2f}% ({alt_stats['espresso_better']} blocks)\n"
                        )
                        f.write(
                            f"  - 4x4 Subdivision was better: {to_percent(alt_stats['subdivision_better'], total):.2f}% ({alt_stats['subdivision_better']} blocks)\n"
                        )
                        f.write(
                            f"  - Tied: {to_percent(alt_stats['tied'], total):.2f}% ({alt_stats['tied']} blocks)\n"
                        )
                        avg_espresso = alt_stats["total_espresso_cost"] / total
                        avg_subdivision = alt_stats["total_subdivision_cost"] / total
                        f.write(f"  Average Espresso cost: {avg_espresso:.2f} bits\n")
                        f.write(
                            f"  Average 4x4 Subdivision cost: {avg_subdivision:.2f} bits\n\n"
                        )
                    else:
                        f.write("  - No 8x8 blocks were compressed with Espresso.\n\n")

                    f.write(
                        "Analysis of Discarded Espresso Results (In-Tree Raw Leaves):\n"
                    )
                    in_tree_stats = stats["in_tree_raw_stats"]
                    total_raw_leaves = in_tree_stats["total_blocks"]
                    if total_raw_leaves > 0:
                        f.write(
                            f"  (For the {total_raw_leaves} leaves where Espresso was costlier than raw pixels or had >7 cubes)\n"
                        )
                        cube_counts_raw = in_tree_stats["espresso_cube_counts"]
                        for num_cubes, count in sorted(cube_counts_raw.items()):
                            label = (
                                f"{num_cubes} Cubes"
                                if isinstance(num_cubes, int)
                                else "8+ Cubes"
                            )
                            f.write(
                                f"    - {label}:".ljust(15)
                                + f"{to_percent(count, total_raw_leaves):.2f}% ({count} blocks)\n"
                            )
                        f.write("\n")
                    else:
                        f.write(
                            "  - No leaf nodes were stored as raw due to high Espresso cost or too many cubes.\n\n"
                        )

                    f.write("On-Set Cube Distribution (Before Selection):\n")
                    on_set_counts = stats["on_set_cube_counts"]
                    total_blocks_analyzed = sum(on_set_counts.values())
                    if total_blocks_analyzed > 0:
                        f.write(
                            f" (For the {total_blocks_analyzed} blocks that underwent Espresso analysis)\n"
                        )
                        for num_cubes, count in sorted(on_set_counts.items()):
                            if count > 0:
                                label = f"{num_cubes} Cubes"
                                f.write(
                                    f" - {label}:".ljust(15)
                                    + f"{to_percent(count, total_blocks_analyzed):.2f}% ({count} blocks)\n"
                                )
                        f.write("\n")
                    else:
                        f.write(" - No blocks underwent Espresso analysis.\n\n")

                    f.write("Off-Set Cube Distribution (Before Selection):\n")
                    off_set_counts = stats["off_set_cube_counts"]
                    if total_blocks_analyzed > 0:
                        f.write(
                            f" (For the {total_blocks_analyzed} blocks that underwent Espresso analysis)\n"
                        )
                        for num_cubes, count in sorted(off_set_counts.items()):
                            if count > 0:
                                label = f"{num_cubes} Cubes"
                                f.write(
                                    f" - {label}:".ljust(15)
                                    + f"{to_percent(count, total_blocks_analyzed):.2f}% ({count} blocks)\n"
                                )
                        f.write("\n")
                    else:
                        f.write(" - No blocks underwent Espresso analysis.\n\n")

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
                            total_comp_ovf = (
                                leaf_counts_ovf["compressible_homo_0"]
                                + leaf_counts_ovf["compressible_homo_1"]
                                + leaf_counts_ovf["compressible_espresso"]
                            )
                            f.write(
                                f"    - Compressible:".ljust(25)
                                + f"{to_percent(total_comp_ovf, total_leaf_nodes_ovf):.2f}%\n"
                            )
                            f.write(
                                f"    - Incompressible (In-Tree Raw):".ljust(25)
                                + f"{to_percent(leaf_counts_ovf['incompressible_raw'], total_leaf_nodes_ovf):.2f}%\n\n"
                            )
                    else:
                        f.write("  No 64x64 blocks overflowed.\n\n")

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

    target_on_set_counter = (
        stat_root.get("on_set_cube_counts", {}) if not is_overflow else {}
    )
    target_off_set_counter = (
        stat_root.get("off_set_cube_counts", {}) if not is_overflow else {}
    )

    w, h = node.get("w", 0), node.get("h", 0)
    level_key = f"{w}x{h}"
    plane_stat_dict = stats.plane_stats[bit]
    code_counts = plane_stat_dict["code_counts"]

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
            num_cubes = len(node["data"].get("cubes", []))
            if 1 <= num_cubes <= 32:
                target_cube_counter[num_cubes] += 1

            if "data" in node and not is_overflow:
                on_set_cubes = node["data"].get("on_set_cubes", 0)
                off_set_cubes = node["data"].get("off_set_cubes", 0)
                if 1 <= on_set_cubes <= 32:
                    target_on_set_counter[on_set_cubes] += 1
                if 1 <= off_set_cubes <= 32:
                    target_off_set_counter[off_set_cubes] += 1

            # NEW: Track alternative subdivision comparison
            if "alternative_subdivision" in node and not is_overflow:
                alt_stats = stat_root["alternative_subdivision_stats"]
                alt_stats["total_espresso_blocks"] += 1

                alt_data = node["alternative_subdivision"]
                subdivision_cost = alt_data.get("total_cost", 0)

                # Calculate espresso cost (assuming it's stored in the node data)
                espresso_cost = (
                    len(node["data"].get("cubes", [])) * 10
                )  # Adjust based on your cost calculation

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
                off_set_cubes = discarded_data.get("off_set_cubes", 0)
                if 1 <= on_set_cubes <= 32:
                    in_tree_stats["on_set_cube_counts"][on_set_cubes] += 1
                if 1 <= off_set_cubes <= 32:
                    in_tree_stats["off_set_cube_counts"][off_set_cubes] += 1

        elif "code" in node:
            if node["code"] == "10":
                target_leaf_counter["compressible_homo_0"] += 1
            elif node["code"] == "11":
                target_leaf_counter["compressible_homo_1"] += 1

    if "children" in node:
        for child in node["children"]:
            _collect_stats_from_node(child, stats, bit, is_overflow)
