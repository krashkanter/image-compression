class SimpleStats:
    def __init__(self):
        self.original_bits = 0
        self.compressed_bits = 0
        self.compression_time = 0
        self.decompression_time = 0
        # List of dicts, one for each bitplane (0-7)
        self.bitplane_stats = [self._create_empty_plane_stats() for _ in range(8)]

    def _create_empty_plane_stats(self):
        return {
            "cube_count": 0,
            "total_blocks": 0,
            "block_counts": {
                "raw": 0,
                "espresso": 0,
                "template_match": 0,
                "homogeneous": 0,
                "internal": 0 # Should be 0 for leaf counting, but good to track if needed
            },
            "template_stats": {
                "counts": {}, # ID -> count
                "total_cubes": 0,
                "min_cubes": float('inf'),
                "max_cubes": -1,
                "total_bits_saved": 0,
                "cube_counts_per_template": {} # ID -> list of cube counts
            },
            "potential_template_stats": {
                "counts": {}, # ID -> count
                "total_cubes": 0,
                "min_cubes": float('inf'),
                "max_cubes": -1,
                "total_occurrences": 0
            }
        }

    def update_plane_stats(self, plane_index, node_stats):
        """
        node_stats: dict with keys matching _create_empty_plane_stats structure
        """
        if 0 <= plane_index < 8:
            p_stats = self.bitplane_stats[plane_index]
            p_stats["cube_count"] += node_stats.get("cube_count", 0)
            p_stats["total_blocks"] += node_stats.get("total_blocks", 0)
            for k, v in node_stats.get("block_counts", {}).items():
                p_stats["block_counts"][k] = p_stats["block_counts"].get(k, 0) + v
            
            # Update template stats
            t_stats = p_stats.get("template_stats")
            n_t_stats = node_stats.get("template_stats", {})
            if t_stats and n_t_stats:
                t_stats["total_cubes"] += n_t_stats.get("total_cubes", 0)
                t_stats["total_bits_saved"] += n_t_stats.get("total_bits_saved", 0)
                
                # Update min/max
                if n_t_stats.get("min_cubes", float('inf')) < t_stats["min_cubes"]:
                    t_stats["min_cubes"] = n_t_stats["min_cubes"]
                if n_t_stats.get("max_cubes", -1) > t_stats["max_cubes"]:
                    t_stats["max_cubes"] = n_t_stats["max_cubes"]
                    
                for t_id, count in n_t_stats.get("counts", {}).items():
                    t_stats["counts"][t_id] = t_stats["counts"].get(t_id, 0) + count
                
                # Merge cube counts lists
                for t_id, counts_list in n_t_stats.get("cube_counts_per_template", {}).items():
                    if t_id not in t_stats["cube_counts_per_template"]:
                        t_stats["cube_counts_per_template"][t_id] = []
                    t_stats["cube_counts_per_template"][t_id].extend(counts_list)
            
            # Update potential template stats
            pt_stats = p_stats.get("potential_template_stats")
            n_pt_stats = node_stats.get("potential_template_stats", {})
            if pt_stats and n_pt_stats:
                pt_stats["total_cubes"] += n_pt_stats.get("total_cubes", 0)
                pt_stats["total_occurrences"] += n_pt_stats.get("total_occurrences", 0)
                
                # Update min/max
                if n_pt_stats.get("min_cubes", float('inf')) < pt_stats["min_cubes"]:
                    pt_stats["min_cubes"] = n_pt_stats["min_cubes"]
                if n_pt_stats.get("max_cubes", -1) > pt_stats["max_cubes"]:
                    pt_stats["max_cubes"] = n_pt_stats["max_cubes"]

                for t_id, count in n_pt_stats.get("counts", {}).items():
                    pt_stats["counts"][t_id] = pt_stats["counts"].get(t_id, 0) + count

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
                
                f.write("\nPer-Bitplane Details\n")
                f.write("--------------------\n")
                
                total_cubes_all = 0
                total_blocks_all = 0
                block_counts_all = {
                    "raw": 0, "espresso": 0, "template_match": 0, "homogeneous": 0
                }

                for i, p_stats in enumerate(self.bitplane_stats):
                    f.write(f"\nBitplane {i}:\n")
                    f.write(f"  Total Blocks: {p_stats['total_blocks']}\n")
                    f.write(f"  Cube Count:   {p_stats['cube_count']}\n")
                    f.write("  Block Types:\n")
                    
                    # Calculate percentages
                    total = p_stats['total_blocks']
                    if total > 0:
                        for b_type, count in p_stats['block_counts'].items():
                            if b_type in block_counts_all: # Only track main types
                                pct = (count / total) * 100
                                f.write(f"    {b_type.ljust(15)}: {count} ({pct:.2f}%)\n")
                                block_counts_all[b_type] += count
                    else:
                        f.write("    (No blocks)\n")
                    
                    # Template Analysis
                    t_stats = p_stats.get("template_stats", {})
                    t_counts = t_stats.get("counts", {})
                    t_blocks = p_stats['block_counts'].get('template_match', 0)
                    
                    if t_blocks > 0:
                        f.write("  Template Analysis:\n")
                        # Most used template
                        if t_counts:
                            most_used_id = max(t_counts, key=t_counts.get)
                            most_used_count = t_counts[most_used_id]
                            f.write(f"    Most Used ID:   {most_used_id} (used {most_used_count} times)\n")
                        
                        # Min/Max cubes
                        min_c = t_stats.get("min_cubes")
                        max_c = t_stats.get("max_cubes")
                        if min_c == float('inf'): min_c = 0
                        if max_c == -1: max_c = 0
                        f.write(f"    Best Cube Count:  {min_c}\n")
                        f.write(f"    Worst Cube Count: {max_c}\n")
                        
                        # Total Bits Saved
                        saved = t_stats.get("total_bits_saved", 0)
                        f.write(f"    Total Bits Saved: {saved}\n")

                    elif t_blocks == 0:
                         # Potential Template Analysis
                        pt_stats = p_stats.get("potential_template_stats", {})
                        pt_counts = pt_stats.get("counts", {})
                        pt_total_cubes = pt_stats.get("total_cubes", 0)
                        pt_occurrences = pt_stats.get("total_occurrences", 0)
                        
                        if pt_occurrences > 0:
                            f.write("  Potential Template Analysis:\n")
                            if pt_counts:
                                most_used_id = max(pt_counts, key=pt_counts.get)
                                most_used_count = pt_counts[most_used_id]
                                f.write(f"    Best Candidate: {most_used_id} (found {most_used_count} times)\n")
                            
                            min_c = pt_stats.get("min_cubes")
                            max_c = pt_stats.get("max_cubes")
                            if min_c == float('inf'): min_c = 0
                            if max_c == -1: max_c = 0
                            f.write(f"    Best Cube Count:  {min_c}\n")
                            f.write(f"    Worst Cube Count: {max_c}\n")
                    
                    total_cubes_all += p_stats['cube_count']
                    total_blocks_all += p_stats['total_blocks']

                f.write("\nOverall Breakdown\n")
                f.write("-----------------\n")
                f.write(f"Total Blocks: {total_blocks_all}\n")
                f.write(f"Total Cubes:  {total_cubes_all}\n")
                f.write("Block Type Distribution:\n")
                if total_blocks_all > 0:
                    for b_type, count in block_counts_all.items():
                        pct = (count / total_blocks_all) * 100
                        f.write(f"  {b_type.ljust(15)}: {count} ({pct:.2f}%)\n")

            print(f"Stats saved to {filepath}")
        except Exception as e:
            print(f"Error saving stats: {e}")

    def dump_plots(self, output_dir_base_name):
        try:
            import matplotlib.pyplot as plt
            from matplotlib.ticker import MaxNLocator
            import os
            from collections import Counter
            
            # Create output directory
            output_dir = f"output/{output_dir_base_name}_plots"
            os.makedirs(output_dir, exist_ok=True)
            
            print(f"Generating plots in {output_dir}...")
            
            for i, p_stats in enumerate(self.bitplane_stats):
                t_stats = p_stats.get("template_stats", {})
                cube_counts_map = t_stats.get("cube_counts_per_template", {})
                
                if not cube_counts_map:
                    continue
                    
                plt.figure(figsize=(10, 6))
                ax = plt.gca()
                
                # Plot scatter for each template
                for t_id, counts in cube_counts_map.items():
                    # Calculate frequency for each cube count
                    count_freq = Counter(counts)
                    x_vals = list(count_freq.keys())
                    y_vals = list(count_freq.values())
                    
                    plt.scatter(x_vals, y_vals, label=f'Template {t_id}', alpha=0.7, s=50)
                
                ax.xaxis.set_major_locator(MaxNLocator(integer=True))
                
                plt.xlabel('Cube Count')
                plt.ylabel('Frequency (Number of Blocks)')
                plt.title(f'Bitplane {i}: Template Cube Count Distribution')
                plt.legend()
                plt.grid(True, alpha=0.3)
                
                # Save plot
                plot_path = os.path.join(output_dir, f"bitplane_{i}.png")
                plt.savefig(plot_path)
                plt.close()
                
            print(f"Plots saved.")
            
        except ImportError:
            print("Error: matplotlib is not installed. Cannot generate plots.")
        except Exception as e:
            print(f"Error generating plots: {e}")

def _collect_stats_from_node(node, stats_accumulator):
    """
    Recursively collect stats from a QuadTree node dictionary.
    stats_accumulator: dict to update in-place
    """
    if node["type"] == "leaf":
        stats_accumulator["total_blocks"] += 1
        subtype = node.get("subtype")
        code = node.get("code")
        
        # Collect potential template stats if available
        if "best_candidate" in node:
            t_id, cube_count = node["best_candidate"]
            pt_stats = stats_accumulator.get("potential_template_stats", {})
            if "counts" not in pt_stats: pt_stats["counts"] = {}
            pt_stats["counts"][t_id] = pt_stats["counts"].get(t_id, 0) + 1
            pt_stats["total_cubes"] = pt_stats.get("total_cubes", 0) + cube_count
            pt_stats["total_occurrences"] = pt_stats.get("total_occurrences", 0) + 1
            
            # Update min/max
            if cube_count < pt_stats.get("min_cubes", float('inf')):
                pt_stats["min_cubes"] = cube_count
            if cube_count > pt_stats.get("max_cubes", -1):
                pt_stats["max_cubes"] = cube_count
        
        if subtype == "espresso":
            stats_accumulator["block_counts"]["espresso"] += 1
            # Count cubes in minimized data
            if "data" in node and "cubes" in node["data"]:
                stats_accumulator["cube_count"] += len(node["data"]["cubes"])
        elif subtype == "template_match":
            stats_accumulator["block_counts"]["template_match"] += 1
            # Count cubes in diff data
            cubes_in_block = 0
            if "data" in node and "cubes" in node["data"]:
                cubes_in_block = len(node["data"]["cubes"])
                stats_accumulator["cube_count"] += cubes_in_block
            
            # Template Stats
            t_id = node.get("template_id", 0)
            bits_saved = node.get("bits_saved", 0)
            t_stats = stats_accumulator.get("template_stats", {})
            if "counts" not in t_stats: t_stats["counts"] = {}
            t_stats["counts"][t_id] = t_stats["counts"].get(t_id, 0) + 1
            t_stats["total_cubes"] = t_stats.get("total_cubes", 0) + cubes_in_block
            t_stats["total_bits_saved"] = t_stats.get("total_bits_saved", 0) + bits_saved
            
            # Update min/max cubes
            if cubes_in_block < t_stats.get("min_cubes", float('inf')):
                t_stats["min_cubes"] = cubes_in_block
            if cubes_in_block > t_stats.get("max_cubes", -1):
                t_stats["max_cubes"] = cubes_in_block
            
            # Collect detailed cube counts
            if "cube_counts_per_template" not in t_stats:
                t_stats["cube_counts_per_template"] = {}
            if t_id not in t_stats["cube_counts_per_template"]:
                t_stats["cube_counts_per_template"][t_id] = []
            t_stats["cube_counts_per_template"][t_id].append(cubes_in_block)
            
        elif subtype == "raw":
            stats_accumulator["block_counts"]["raw"] += 1
        elif code in ["10", "11"]:
            stats_accumulator["block_counts"]["homogeneous"] += 1
        else:
             # Fallback for unknown leaf types
             pass

    elif node["type"] == "node":
        # Internal node
        # We don't count internal nodes as "blocks" for the final stats usually,
        # or we can count them separately. The user asked for "number of blocks",
        # usually implying leaf blocks covering the image.
        if "children" in node:
            for child in node["children"]:
                _collect_stats_from_node(child, stats_accumulator)

