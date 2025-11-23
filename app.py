import tkinter as tk
from tkinter import ttk, scrolledtext, Menu
import sys
import numpy
import os

# Assuming these exist in your environment
from sharp import process_blocks
from utils import minimize_block, reconstruct_block

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
        self.decoding_enabled = tk.BooleanVar(value=False)

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
            text="Execute All Templates",
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

        def load_templates():
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
            load_templates()

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
                load_templates()
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
        load_templates()

    def execute_sharp(self):
        """
        1. Minimizes A directly to get baseline 'cube_before'.
           (Note: Since 0 is Black/Ink, we invert A before sending to minimizer)
        2. For each template B:
           - Computes X = A ^ B
           - Minimizes X directly (since 1s represent differences/changes)
        3. Displays comparison: {cube_before} >> {cube_after}
        """
        execute_window = tk.Toplevel(self.root)
        execute_window.title("Execution Results")
        execute_window.geometry("1200x750")

        # --- Top Summary Frame ---
        summary_frame = tk.Frame(execute_window, bg="#e6f3ff", pady=10)
        summary_frame.pack(side="top", fill="x")

        lbl_status = tk.Label(
            summary_frame, text="Processing...", bg="#e6f3ff", font=("Arial", 12)
        )
        lbl_status.pack()

        # --- Scrollable Area Setup ---
        canvas = tk.Canvas(execute_window)
        scrollbar = tk.Scrollbar(
            execute_window, orient="vertical", command=canvas.yview
        )
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ==========================================
        # 1. Get User Input A & Calculate Baseline
        # ==========================================
        # 0 = Black (Ink), 1 = White (Empty)
        grid_a_state = self.creator_grid_A.get_grid_state().astype(int)

        cube_before = 0
        # To count blocks, we need to count the Black pixels (0).
        # The minimizer expects 1 as "Active". So we invert A for this calculation.
        # (1 - 0 = 1, 1 - 1 = 0)
        inverted_a_for_counting = 1 - grid_a_state

        if numpy.any(inverted_a_for_counting):
            baseline_block = minimize_block(inverted_a_for_counting)
            if baseline_block and "cubes" in baseline_block:
                cube_before = len(baseline_block["cubes"])
            else:
                cube_before = 999

        print(f"Baseline (A) Cubes: {cube_before}")

        # ==========================================
        # 2. Read Templates
        # ==========================================
        templates = []
        try:
            with open("config/templates.txt", "r") as f:
                for line in f:
                    line = line.strip()
                    if len(line) == GRID_SIZE * GRID_SIZE:
                        templates.append(line)
        except FileNotFoundError:
            lbl_status.config(text="Error: config/templates.txt not found")
            return

        if not templates:
            lbl_status.config(text="Error: No templates available")
            return

        # --- Tracking Best Result ---
        best_after_size = float("inf")
        best_template_idx = -1

        # ==========================================
        # 3. Loop through templates
        # ==========================================
        for idx, tmpl_str in enumerate(templates):
            try:
                grid_b_state = numpy.array(list(tmpl_str), dtype=int).reshape(
                    (GRID_SIZE, GRID_SIZE)
                )
            except Exception:
                continue

            # ---------------------------------------------------------
            # CORE LOGIC: XOR (A ^ B)
            # ---------------------------------------------------------
            # 0^0=0 (Match), 1^1=0 (Match)
            # 0^1=1 (Diff),  1^0=1 (Diff)
            # The result X contains 1s wherever A and B disagree.
            diff_pixels_X = grid_a_state ^ grid_b_state

            # Minimize X
            # Since 1 represents a "Difference" (a necessary change),
            # the minimizer naturally counts these 1s. No inversion needed here.
            minimized_block = None
            cube_after = 0

            if numpy.any(diff_pixels_X):
                minimized_block = minimize_block(diff_pixels_X)
                if minimized_block and "cubes" in minimized_block:
                    cube_after = len(minimized_block["cubes"])
                else:
                    cube_after = 999

            # Track Best
            if cube_after < best_after_size:
                best_after_size = cube_after
                best_template_idx = idx

            # --- UI Generation for Row ---
            row_frame = tk.Frame(scrollable_frame, relief="groove", borderwidth=2)
            row_frame.pack(pady=10, padx=10, fill="x")

            # Determine Color
            size_color = "#000000"
            if cube_after < cube_before:
                size_color = "#008800"  # Green (Good)
            elif cube_after > cube_before:
                size_color = "#cc0000"  # Red (Bad)

            # Row Header
            header_color = "#d1e7dd" if cube_after == 0 else "#f0f0f0"
            header_frame = tk.Frame(row_frame, bg=header_color)
            header_frame.pack(fill="x")

            tk.Label(
                header_frame,
                text=f"Template #{idx + 1}",
                font=("Arial", 10, "bold"),
                bg=header_color,
            ).pack(side="left", padx=10, pady=5)

            comparison_text = f"Cubes: {cube_before} >> {cube_after}"
            tk.Label(
                header_frame,
                text=comparison_text,
                font=("Arial", 11, "bold"),
                fg=size_color,
                bg=header_color,
            ).pack(side="right", padx=10)

            grids_frame = tk.Frame(row_frame)
            grids_frame.pack(pady=5)

            # Helper to draw grid
            def draw_grid(parent, title, matrix):
                f = tk.Frame(parent)
                f.pack(side="left", padx=10)
                tk.Label(f, text=title, font=("Arial", 9)).pack()
                g = InteractiveGrid(
                    f, execute_window, self.pixel_image, show_reset_button=False
                )
                for r in range(GRID_SIZE):
                    for c in range(GRID_SIZE):
                        g._update_cell(r, c, int(matrix[r, c]))
                return g

            # 1. User Input
            draw_grid(grids_frame, "User (A)", grid_a_state)

            # 2. Template
            draw_grid(grids_frame, "Template (B)", grid_b_state)

            # 3. XOR Difference
            draw_grid(grids_frame, "XOR Diff (A ^ B)", diff_pixels_X)

            # 4. Final Result (Visual Decoding)
            final_display = diff_pixels_X
            result_title = "Raw Result (X)"

            if self.decoding_enabled.get():
                if minimized_block:
                    try:
                        # Reconstruct X from the compressed block
                        reconstructed_X = reconstruct_block(
                            minimized_block, GRID_SIZE, GRID_SIZE
                        )
                        # Decoding: Recover A = X ^ B
                        # This verifies if the compression is lossless
                        final_display = reconstructed_X ^ grid_b_state
                        result_title = "Recovered A (X ^ B)"
                    except Exception:
                        result_title = "Error Reconstructing"
                else:
                    # If X is empty (Perfect Match), A = B
                    final_display = grid_b_state
                    result_title = "Recovered (Perfect)"

            draw_grid(grids_frame, result_title, final_display)
            self.root.update_idletasks()

        # ==========================================
        # 4. Final Summary Update
        # ==========================================
        if best_template_idx != -1:
            saving = ""
            if cube_before > 0:
                pct = ((cube_before - best_after_size) / cube_before) * 100
                saving = f"(Saved {pct:.1f}%)"

            summary_text = f"Best: Template #{best_template_idx + 1} | {cube_before} >> {best_after_size}"
            lbl_status.config(text=summary_text, fg="green", font=("Arial", 14, "bold"))
        else:
            lbl_status.config(text="No valid templates processed.")

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
