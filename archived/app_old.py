import tkinter as tk
from tkinter import ttk, scrolledtext, Menu
import sys
import numpy

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
            button_frame,
            text="Clear Output",
            command=self.clear_output
        )
        clear_btn.pack(side="left", padx=5)

        self.text_widget = scrolledtext.ScrolledText(
            self.window,
            wrap=tk.WORD,
            width=70,
            height=20,
            font=("Courier", 9),
            state="disabled"
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

        self.grid_state = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
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
                    bg=COLOR_WHITE,
                    relief="solid",
                    borderwidth=1,
                    bd=1,
                    highlightbackground=COLOR_GRID_LINE,
                    highlightthickness=0.5
                )

                cell.grid(row=r, column=c, sticky="nsew")

                cell.bind("<Button-1>", self.handle_mouse_down)
                cell.bind("<B1-Motion>", self.handle_mouse_drag)
                self.root_window.bind("<ButtonRelease-1>", self.handle_mouse_up, add="+")

                self.grid_cells[r][c] = cell
                cell.grid_coords = (r, c)

        if show_reset_button:
            self.reset_button = tk.Button(
                self.parent_frame,
                text="Reset Grid",
                command=self.reset_grid
            )
            self.reset_button.pack(pady=5, fill="x")

    def handle_mouse_down(self, event):
        self.is_drawing = True

        cell = event.widget
        r, c = cell.grid_coords

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

        new_color = COLOR_BLACK if new_state == 1 else COLOR_WHITE
        self.grid_cells[r][c].config(bg=new_color)

    def reset_grid(self):
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                self._update_cell(r, c, 0)

    def print_grid_state(self):
        print("\n--- Grid State ---")
        for row in self.grid_state:
            print(" ".join(map(str, row)))

    def get_grid_state(self):
        return numpy.array(self.grid_state)


class GridApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tkinter 8x8 Grid")
        self.root.resizable(False, False)

        self.pixel_image = tk.PhotoImage(width=1, height=1)

        self.output_window = OutputWindow(self.root)

        self.create_menu_bar()

        self.notebook = ttk.Notebook(root)

        self.creator_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.creator_tab, text='Creator')

        self.compare_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.compare_tab, text='Compare')

        self.notebook.pack(expand=True, fill="both")

        self.creator_grid = InteractiveGrid(
            self.creator_tab,
            self.root,
            self.pixel_image,
            show_reset_button=True
        )

        self.execute_button = tk.Button(
            self.creator_tab,
            text="Execute",
            command=self.execute_sharp
        )
        self.execute_button.pack(pady=5, fill="x")

        grids_frame = tk.Frame(self.compare_tab)
        grids_frame.pack(pady=10, expand=True)

        frame_grid_1 = tk.Frame(grids_frame)
        frame_grid_1.pack(side="left", padx=(0, 5))
        self.compare_grid_1 = InteractiveGrid(
            frame_grid_1,
            self.root,
            self.pixel_image,
            show_reset_button=False
        )
        frame_grid_2 = tk.Frame(grids_frame)
        frame_grid_2.pack(side="left", padx=(5, 0))
        self.compare_grid_2 = InteractiveGrid(
            frame_grid_2,
            self.root,
            self.pixel_image,
            show_reset_button=False
        )
        self.sharp_button = tk.Button(
            self.compare_tab,
            text="Apply Sharp",
            command=self.apply_sharp
        )
        self.sharp_button.pack(pady=5, fill="x")

        self.reset_button = tk.Button(
            self.compare_tab,
            text="Reset Grid",
            command=self.reset_grids
        )
        self.reset_button.pack(pady=5, fill="x")

        self.setup_output_redirection()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_menu_bar(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        edit_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Add Template", command=self.add_template)

        tools_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Outputs", command=self.show_outputs)

    def add_template(self):
        template_window = tk.Toplevel(self.root)
        template_window.title("Add Template")
        template_window.geometry("400x400")

        left_frame = tk.Frame(template_window)
        left_frame.pack(side="left", padx=10, pady=10)

        right_frame = tk.Frame(template_window)
        right_frame.pack(side="right", padx=10, pady=10)

        template_grid = InteractiveGrid(
            left_frame,
            template_window,
            self.pixel_image,
            show_reset_button=True
        )

        templates_list = tk.Listbox(right_frame)
        templates_list.pack(pady=5)

        def load_templates():
            templates_list.delete(0, tk.END)
            try:
                with open("config/templates.txt", "r") as f:
                    for line in f:
                        templates_list.insert(tk.END, line.strip())
            except FileNotFoundError:
                pass

        def save_template():
            grid_state = template_grid.get_grid_state()
            template_str = "".join(map(str, grid_state.flatten()))
            with open("config/templates.txt", "a") as f:
                f.write(template_str + "\n")
            load_templates()

        def delete_template():
            selected_index = templates_list.curselection()
            if not selected_index:
                return
            
            selected_template = templates_list.get(selected_index)
            
            with open("config/templates.txt", "r") as f:
                lines = f.readlines()
            
            with open("config/templates.txt", "w") as f:
                for line in lines:
                    if line.strip() != selected_template:
                        f.write(line)
            
            load_templates()

        templates_list.bind("<<ListboxSelect>>", load_template_grid)

        save_button = tk.Button(left_frame, text="Save Template", command=save_template)
        save_button.pack(pady=5, fill="x")

        delete_button = tk.Button(right_frame, text="Delete Template", command=delete_template)
        delete_button.pack(pady=5, fill="x")

        load_templates()

    def execute_sharp(self):
        execute_window = tk.Toplevel(self.root)
        execute_window.title("Execute Sharp")
        execute_window.geometry("800x600")

        canvas = tk.Canvas(execute_window)
        scrollbar = tk.Scrollbar(execute_window, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        creator_grid_state = self.creator_grid.get_grid_state()
        
        try:
            with open("config/templates.txt", "r") as f:
                for i, line in enumerate(f):
                    template_str = line.strip()
                    template_grid_state = numpy.array(list(template_str), dtype=int).reshape((GRID_SIZE, GRID_SIZE))
                    
                    result_cubes = []
                    if numpy.any(creator_grid_state):
                        block1 = minimize_block(creator_grid_state)
                        block2 = minimize_block(template_grid_state)
                        result_cubes = process_blocks(block1, block2)

                    result_frame = tk.Frame(scrollable_frame, relief="solid", borderwidth=1)
                    result_frame.pack(pady=10, padx=10, fill="x")

                    label = tk.Label(result_frame, text=f"Result with Template {i+1}")
                    label.pack()

                    grids_frame = tk.Frame(result_frame)
                    grids_frame.pack(pady=10)

                    # Creator grid
                    creator_frame = tk.Frame(grids_frame)
                    creator_frame.pack(side="left", padx=5)
                    creator_label = tk.Label(creator_frame, text="Creator")
                    creator_label.pack()
                    creator_grid_display = InteractiveGrid(creator_frame, execute_window, self.pixel_image, show_reset_button=False)
                    for r in range(GRID_SIZE):
                        for c in range(GRID_SIZE):
                            creator_grid_display._update_cell(r, c, int(creator_grid_state[r, c]))
                    
                    # Template grid
                    template_frame = tk.Frame(grids_frame)
                    template_frame.pack(side="left", padx=5)
                    template_label = tk.Label(template_frame, text=f"Template {i+1}")
                    template_label.pack()
                    template_grid_display = InteractiveGrid(template_frame, execute_window, self.pixel_image, show_reset_button=False)
                    for r in range(GRID_SIZE):
                        for c in range(GRID_SIZE):
                            template_grid_display._update_cell(r, c, int(template_grid_state[r, c]))

                    # Result grid
                    result_grid_frame = tk.Frame(grids_frame)
                    result_grid_frame.pack(side="left", padx=5)
                    result_label = tk.Label(result_grid_frame, text="Result")
                    result_label.pack()
                    result_grid_display = InteractiveGrid(result_grid_frame, execute_window, self.pixel_image, show_reset_button=False)

                    if result_cubes:
                        block1 = minimize_block(creator_grid_state)
                        result_block = {
                            "code": "00",
                            "cubes": [(cube, "1") for cube in result_cubes],
                            "n_bits": block1['n_bits'],
                            "encoding_map": block1['encoding_map'],
                            "map_value": block1['map_value'],
                        }
                        reconstructed_grid = reconstruct_block(result_block, GRID_SIZE, GRID_SIZE)
                        for r in range(GRID_SIZE):
                            for c in range(GRID_SIZE):
                                result_grid_display._update_cell(r, c, int(reconstructed_grid[r, c]))

        except FileNotFoundError:
            label = tk.Label(scrollable_frame, text="No templates found.")
            label.pack(pady=20)



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
        print("Apply Sharp clicked!")

        block1 = minimize_block(self.compare_grid_1.get_grid_state())
        block2 = minimize_block(self.compare_grid_2.get_grid_state())

        print("Block1:", block1)
        print("Block2:", block2)

        result_cubes = process_blocks(block1, block2)

        print(f"Result: {len(result_cubes)} cubes")
        print(result_cubes)

        self.compare_grid_2.reset_grid()

        if result_cubes:
            result_block = {
                "code": "00",
                "cubes": [(cube, "1") for cube in result_cubes],
                "n_bits": block1['n_bits'],
                "encoding_map": block1['encoding_map'],
                "map_value": block1['map_value'],
            }

            reconstructed_grid = reconstruct_block(result_block, GRID_SIZE, GRID_SIZE)

            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE):
                    self.compare_grid_2._update_cell(r, c, int(reconstructed_grid[r, c]))

            print(f"Reconstructed result grid with {len(result_cubes)} cubes")
        else:
            print("Empty result (A # A = ∅ or A ⊆ B)")

    def on_closing(self):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        self.output_window.destroy()

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = GridApp(root)
    root.mainloop()
