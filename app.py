import tkinter as tk
from tkinter import ttk, scrolledtext, Menu
import sys
import numpy
import os

# Assuming these exist in your environment
# from sharp import process_blocks
from utils import minimize_block, reconstruct_block, load_templates, get_espresso_cost

GRID_SIZE = 8
CELL_SIZE = 30
COLOR_WHITE = "#FFFFFF"
COLOR_BLACK = "#111111"
COLOR_GRID_LINE = "#444444"


class TextRedirector:
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, string):
        self.widget.configure(state="normal")
        self.widget.insert("end", string, (self.tag,))
        self.widget.see("end")
        self.widget.configure(state="disabled")
        self.widget.update_idletasks()

    def flush(self):
        pass


class OutputWindow:
    def __init__(self, parent):
        self.parent = parent
        self.window = None
        self.text_widget = None
        self.is_visible = False

    def create_window(self):
        if self.window is not None:
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Console Output")
        self.window.geometry("600x400")

        button_frame = tk.Frame(self.window)
        button_frame.pack(side="top", fill="x", padx=5, pady=5)

        clear_btn = tk.Button(
            button_frame, text="Clear Output", command=self.clear_output
        )
        clear_btn.pack(side="left", padx=5)

        self.text_widget = scrolledtext.ScrolledText(
            self.window,
            wrap=tk.WORD,
            width=70,
            height=20,
            font=("Courier", 9),
            state="disabled",
        )
        self.text_widget.pack(expand=True, fill="both", padx=5, pady=5)

        self.text_widget.tag_configure("stdout", foreground="black")
        self.text_widget.tag_configure("stderr", foreground="red")

        self.window.protocol("WM_DELETE_WINDOW", self.hide)

    def show(self):
        if self.window is None:
            self.create_window()

        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()
        self.is_visible = True

    def hide(self):
        if self.window is not None:
            self.window.withdraw()
            self.is_visible = False

    def clear_output(self):
        if self.text_widget is not None:
            self.text_widget.configure(state="normal")
            self.text_widget.delete(1.0, tk.END)
            self.text_widget.configure(state="disabled")

    def destroy(self):
        if self.window is not None:
            self.window.destroy()
            self.window = None
            self.text_widget = None
            self.is_visible = False


class InteractiveGrid:
    def __init__(self, parent_frame, root_window, pixel_image, show_reset_button=True):
        self.parent_frame = parent_frame
        self.root_window = root_window
        self.pixel_image = pixel_image

        # CHANGE: Initialize with 1s because 1 = White (Background)
        self.grid_state = [[1 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.grid_cells = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

        self.is_drawing = False
        self.draw_mode = 0

        self.grid_frame = tk.Frame(parent_frame)
        self.grid_frame.pack(pady=5)

        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                cell = tk.Label(
                    self.grid_frame,
                    image=self.pixel_image,
                    width=CELL_SIZE,
                    height=CELL_SIZE,
                    compound="center",
                    # CHANGE: Default visual is White (which is now state 1)
                    bg=COLOR_WHITE,
                    relief="solid",
                    borderwidth=1,
                    bd=1,
                    highlightbackground=COLOR_GRID_LINE,
                    highlightthickness=0.5,
                )

                cell.grid(row=r, column=c, sticky="nsew")

                cell.bind("<Button-1>", self.handle_mouse_down)
                cell.bind("<B1-Motion>", self.handle_mouse_drag)
                self.root_window.bind(
                    "<ButtonRelease-1>", self.handle_mouse_up, add="+"
                )

                self.grid_cells[r][c] = cell
                cell.grid_coords = (r, c)

        if show_reset_button:
            self.reset_button = tk.Button(
                self.parent_frame, text="Reset Grid", command=self.reset_grid
            )
            self.reset_button.pack(pady=5, fill="x")

    def handle_mouse_down(self, event):
        self.is_drawing = True
        cell = event.widget
        r, c = cell.grid_coords
        # Toggle between 0 and 1
        new_state = 1 - self.grid_state[r][c]
        self.draw_mode = new_state
        self._update_cell(r, c, new_state)

    def handle_mouse_drag(self, event):
        if not self.is_drawing:
            return
        x, y = self.grid_frame.winfo_pointerxy()
        widget_at_cursor = self.grid_frame.winfo_containing(x, y)
        if widget_at_cursor and hasattr(widget_at_cursor, "grid_coords"):
            r, c = widget_at_cursor.grid_coords
            if self.grid_state[r][c] != self.draw_mode:
                self._update_cell(r, c, self.draw_mode)

    def handle_mouse_up(self, event):
        self.is_drawing = False

    def _update_cell(self, r, c, new_state):
        self.grid_state[r][c] = new_state
        # LOGIC MAPPING: 0 = Black, 1 = White
        new_color = COLOR_WHITE if new_state == 1 else COLOR_BLACK
        self.grid_cells[r][c].config(bg=new_color)

    def reset_grid(self):
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                # CHANGE: Reset sets cells to 1 (White/Empty)
                self._update_cell(r, c, 1)

    def print_grid_state(self):
        print("\n--- Grid State ---")
        for row in self.grid_state:
            print(" ".join(map(str, row)))

    def get_grid_state(self):
        return numpy.array(self.grid_state)


class GridApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sharp Minimizer")
        self.root.resizable(False, False)

        self.pixel_image = tk.PhotoImage(width=1, height=1)
        self.output_window = OutputWindow(self.root)

        # Toggle state for decoding
        self.decoding_enabled = tk.BooleanVar(value=True)

        self.create_menu_bar()

        self.notebook = ttk.Notebook(root)

        self.creator_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.creator_tab, text="Creator")

        self.compare_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.compare_tab, text="Compare (Legacy)")

        self.notebook.pack(expand=True, fill="both")

        self.setup_creator_tab()
        self.setup_compare_tab()
        self.setup_output_redirection()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_menu_bar(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        edit_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Manage Templates", command=self.add_template)

        tools_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Outputs Console", command=self.show_outputs)

        options_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Options", menu=options_menu)
        options_menu.add_checkbutton(
            label="Enable Decoding (Show A = X + B)", variable=self.decoding_enabled
        )

    def setup_creator_tab(self):
        # --- Input A Only ---
        frame_a = tk.Frame(self.creator_tab)
        frame_a.pack(pady=10, expand=True)
        tk.Label(frame_a, text="User Input (A)", font=("Arial", 12, "bold")).pack(
            pady=(0, 5)
        )
        self.creator_grid_A = InteractiveGrid(
            frame_a, self.root, self.pixel_image, show_reset_button=True
        )

        # Execute Button
        self.execute_button = tk.Button(
            self.creator_tab,
            text="Execute (Resolve Incompressible)",
            command=self.execute_sharp,
            bg="#dddddd",
            height=2,
        )
        self.execute_button.pack(pady=20, fill="x")

    def setup_compare_tab(self):
        grids_frame = tk.Frame(self.compare_tab)
        grids_frame.pack(pady=10, expand=True)

        frame_grid_1 = tk.Frame(grids_frame)
        frame_grid_1.pack(side="left", padx=(0, 5))
        self.compare_grid_1 = InteractiveGrid(
            frame_grid_1, self.root, self.pixel_image, show_reset_button=False
        )
        frame_grid_2 = tk.Frame(grids_frame)
        frame_grid_2.pack(side="left", padx=(5, 0))
        self.compare_grid_2 = InteractiveGrid(
            frame_grid_2, self.root, self.pixel_image, show_reset_button=False
        )
        self.sharp_button = tk.Button(
            self.compare_tab, text="Apply Sharp", command=self.apply_sharp
        )
        self.sharp_button.pack(pady=5, fill="x")

        self.reset_button = tk.Button(
            self.compare_tab, text="Reset Grid", command=self.reset_grids
        )
        self.reset_button.pack(pady=5, fill="x")

    def add_template(self):
        template_window = tk.Toplevel(self.root)
        template_window.title("Manage Templates")
        template_window.geometry("600x420")

        left_frame = tk.Frame(template_window)
        left_frame.pack(side="left", padx=10, pady=10)
        right_frame = tk.Frame(template_window)
        right_frame.pack(side="right", padx=10, pady=10, fill="y")

        template_grid = InteractiveGrid(
            left_frame, template_window, self.pixel_image, show_reset_button=True
        )
        templates_list = tk.Listbox(right_frame, width=30, height=20)
        templates_list.pack(pady=5, fill="y")

        os.makedirs("config", exist_ok=True)
        templates_path = os.path.join("config", "templates.txt")

        def load_templates_gui():
            templates_list.delete(0, tk.END)
            try:
                with open(templates_path, "r") as f:
                    for line in f:
                        templates_list.insert(tk.END, line.strip())
            except FileNotFoundError:
                pass

        def save_template():
            grid_state = template_grid.get_grid_state()
            template_str = "".join(map(str, grid_state.flatten().astype(int)))
            with open(templates_path, "a") as f:
                f.write(template_str + "\n")
            load_templates_gui()

        def delete_template():
            sel = templates_list.curselection()
            if not sel:
                return
            idx = sel[0]
            try:
                with open(templates_path, "r") as f:
                    lines = [l.rstrip("\n") for l in f]
                if 0 <= idx < len(lines):
                    del lines[idx]
                    with open(templates_path, "w") as f:
                        for line in lines:
                            f.write(line + "\n")
                load_templates_gui()
            except FileNotFoundError:
                return

        def load_template_grid(event):
            sel = templates_list.curselection()
            if not sel:
                return
            idx = sel[0]
            template_str = templates_list.get(idx)
            if not template_str or len(template_str) != GRID_SIZE * GRID_SIZE:
                return
            try:
                arr = numpy.array(list(template_str), dtype=int).reshape(
                    (GRID_SIZE, GRID_SIZE)
                )
                for r in range(GRID_SIZE):
                    for c in range(GRID_SIZE):
                        template_grid._update_cell(r, c, int(arr[r, c]))
            except Exception:
                return

        templates_list.bind("<<ListboxSelect>>", load_template_grid)
        tk.Button(left_frame, text="Save As Template", command=save_template).pack(
            pady=5, fill="x"
        )
        tk.Button(right_frame, text="Delete Selected", command=delete_template).pack(
            pady=5, fill="x"
        )
        load_templates_gui()

    def resolve_incompressible_block(self, block):
        """
        Attempts to resolve an incompressible block by XORing with templates.
        Returns the best result (template_id, minimized_data, cost).
        """
        # Load templates via utility
        templates = load_templates()
        if not templates:
            return None

        best_result = None
        min_cost = 64  # Raw cost is 64 bits

        # Try first 7 templates
        for i, tmpl in enumerate(templates[:7]):
            if tmpl.shape != block.shape:
                continue

            xor_diff = block ^ tmpl
            min_data = minimize_block(xor_diff)
            # Cost = Header (3 bits) + Espresso Cost
            cost = get_espresso_cost(min_data, use_3_bit_cube_count=True) + 3

            if cost < min_cost:
                min_cost = cost
                # template_id is 1-based index (001-111)
                best_result = (i + 1, min_data, tmpl)

        return best_result

    def execute_sharp(self):
        """
        Modified execution flow:
        1. Checks if the block is compressible via standard Espresso.
        2. If NOT (cost >= 64), it invokes resolve_incompressible_block.
        3. Displays the decision path.
        """
        execute_window = tk.Toplevel(self.root)
        execute_window.title("Execution Results")
        execute_window.geometry("1000x800")

        # --- Top Summary Frame ---
        summary_frame = tk.Frame(execute_window, bg="#e6f3ff", pady=10)
        summary_frame.pack(side="top", fill="x")

        lbl_status = tk.Label(
            summary_frame, text="Processing...", bg="#e6f3ff", font=("Arial", 12)
        )
        lbl_status.pack()

        # --- Content Area ---
        content_frame = tk.Frame(execute_window)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Helper to draw grid
        def draw_grid(parent, title, matrix, color_bg="#ffffff"):
            f = tk.Frame(parent, bg=color_bg, bd=2, relief="groove")
            f.pack(side="left", padx=10, pady=10)
            tk.Label(f, text=title, font=("Arial", 9, "bold"), bg=color_bg).pack(pady=5)
            g = InteractiveGrid(
                f, execute_window, self.pixel_image, show_reset_button=False
            )
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE):
                    g._update_cell(r, c, int(matrix[r, c]))
            return g

        # 1. Get User Input A
        grid_a_state = self.creator_grid_A.get_grid_state().astype(int)

        # 2. Evaluate Standard Compression
        # 0 = Ink, 1 = Empty. Invert for minimization logic.
        # However, minimize_block handles inputs naturally, usually expecting 1 as 'On'.
        # Since interactive grid is: 1=White/Empty, 0=Black/Ink
        # We usually minimize the Black pixels. So we send (1 - grid_a_state)
        # But if the bitstream logic uses the raw value, we should be consistent.
        # Let's assume we minimize '1's. If Ink is 0, we flip.
        # Based on previous app.py logic: inverted_a_for_counting = 1 - grid_a_state
        block_to_process = 1 - grid_a_state

        min_std = minimize_block(block_to_process)
        cost_std = get_espresso_cost(min_std, use_3_bit_cube_count=True)
        cost_raw = 64

        # Decision Phase
        if cost_std < cost_raw:
            # Case A: Standard Compression Works
            lbl_status.config(
                text=f"Block is Compressible (Standard). Cost: {cost_std} bits vs Raw: {cost_raw} bits.",
                fg="green",
            )

            row1 = tk.Frame(content_frame)
            row1.pack(fill="x")
            draw_grid(row1, "Original Input", grid_a_state)
            draw_grid(
                row1, "Standard Compressed", reconstruct_block(min_std, 8, 8) ^ 1
            )  # Invert back for display

        else:
            # Case B: Incompressible - Invoke New Function
            lbl_status.config(
                text=f"Block is Incompressible (Cost {cost_std} >= 64). Attempting Templates...",
                fg="orange",
            )

            result = self.resolve_incompressible_block(block_to_process)

            if result:
                # Resolution Successful
                t_id, min_data, tmpl = result
                # Cost is stored implicitly, recalculate for display
                cost_new = get_espresso_cost(min_data, use_3_bit_cube_count=True) + 3
                saved = cost_raw - cost_new

                lbl_status.config(
                    text=f"Incompressible Block Resolved by Template #{t_id}!\nRaw: 64 bits -> New: {cost_new} bits (Saved {saved} bits)",
                    fg="#008800",
                    font=("Arial", 14, "bold"),
                )

                # Visuals
                row1 = tk.Frame(content_frame)
                row1.pack(fill="x", pady=10)

                draw_grid(row1, "User Input (Raw)", grid_a_state)
                tk.Label(row1, text="XOR", font=("Arial", 16, "bold")).pack(
                    side="left", padx=10
                )
                draw_grid(
                    row1, f"Template #{t_id}", 1 - tmpl
                )  # Display template (inverted to match visual style)
                tk.Label(row1, text="=", font=("Arial", 16, "bold")).pack(
                    side="left", padx=10
                )

                # XOR Result (Diff)
                xor_diff = block_to_process ^ tmpl
                draw_grid(row1, "Difference (Encoded)", 1 - xor_diff)

            else:
                # Resolution Failed
                lbl_status.config(
                    text=f"Resolution Failed. No template reduced cost below 64 bits.\nFallback to Raw Pixels (Header 000).",
                    fg="red",
                )
                row1 = tk.Frame(content_frame)
                row1.pack(fill="x")
                draw_grid(row1, "Input (Stored as Raw)", grid_a_state)

    def show_outputs(self):
        self.output_window.show()

    def setup_output_redirection(self):
        self.output_window.create_window()
        self.output_window.hide()
        sys.stdout = TextRedirector(self.output_window.text_widget, "stdout")
        sys.stderr = TextRedirector(self.output_window.text_widget, "stderr")

    def reset_grids(self):
        self.compare_grid_1.reset_grid()
        self.compare_grid_2.reset_grid()

    def apply_sharp(self):
        # Legacy Mode
        print("Apply Sharp clicked!")
        a_pixels = self.compare_grid_1.get_grid_state().astype(int)
        b_pixels = self.compare_grid_2.get_grid_state().astype(int)

        # ---------------------------------------------------------
        # CORRECTED XOR IMPLEMENTATION
        # Old: diff_pixels = ((a_pixels == 1) & (b_pixels == 0)).astype(int)
        # New: True Bitwise XOR
        # ---------------------------------------------------------
        diff_pixels = a_pixels ^ b_pixels

        # Check if the result is empty (all zeros)
        if not numpy.any(diff_pixels):
            print("Grids are identical (XOR is 0).")
            self.compare_grid_2.reset_grid()
            return

        minimized = minimize_block(diff_pixels)

        # Update Grid 2 to show the result of the XOR
        try:
            reconstructed_grid = reconstruct_block(minimized, GRID_SIZE, GRID_SIZE)

            # Clear Grid 2 first (optional, but good for clarity)
            # Then draw the result
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE):
                    self.compare_grid_2._update_cell(
                        r, c, int(reconstructed_grid[r, c])
                    )
        except Exception as e:
            print("Failed to reconstruct:", e)

    def on_closing(self):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        self.output_window.destroy()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = GridApp(root)
    root.mainloop()
