import customtkinter as ctk
import json
import os
from tkinter import filedialog, simpledialog, messagebox
from PIL import Image, ImageTk
from modules.helpers.template_loader import load_template
from modules.generic.entity_selection_dialog import EntitySelectionDialog
from modules.generic.generic_model_wrapper import GenericModelWrapper

PORTRAIT_FOLDER = "assets/portraits"
MAX_PORTRAIT_SIZE = (64, 64)
PLACEHOLDER_IMAGE = os.path.join(PORTRAIT_FOLDER, "default_portrait.png")


class NPCGraphEditor(ctk.CTkToplevel):
    def __init__(self, master, npc_wrapper: GenericModelWrapper, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.transient(master)
        self.grab_set()
        self.focus_force()
        self.title("NPC Relationship Graph")
        self.geometry("1280x720")

        self.npc_wrapper = npc_wrapper
        self.npcs = {npc["Name"]: npc for npc in self.npc_wrapper.load_items()}

        self.graph = {"nodes": [], "links": [], "shapes": []}
        self.node_positions = {}
        self.node_images = {}

        self.selected_node = None
        self.link_start = None
        self.pending_npc = None

        self.canvas = ctk.CTkCanvas(self, bg="white", width=1000, height=600)
        self.canvas.pack(fill="both", expand=True)

        self.init_toolbar()

        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_click)

    def init_toolbar(self):
        toolbar = ctk.CTkFrame(self)
        toolbar.pack(fill="x")

        ctk.CTkButton(toolbar, text="Add NPC", command=self.add_npc).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Create Link", command=self.start_link_creation).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Add Shape", command=self.add_shape).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Generate Faction Graph", command=self.generate_faction_graph).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Save Graph", command=self.save_graph).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Load Graph", command=self.load_graph).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Export PNG", command=self.export_to_png).pack(side="left", padx=5)

    def add_npc(self):
        def on_npc_selected(npc):
            self.pending_npc = npc
            messagebox.showinfo("Placement", "Click on the canvas to place the NPC.")
            self.canvas.bind("<Button-1>", self.place_pending_npc)

        npc_template = load_template("npcs")
        dialog = EntitySelectionDialog(self, "NPCs", self.npc_wrapper, npc_template, on_npc_selected)
        dialog.wait_window()

    def place_pending_npc(self, event):
        if not self.pending_npc:
            return

        npc_name = self.pending_npc.get("Name")
        self.graph["nodes"].append({"npc_name": npc_name, "x": event.x, "y": event.y})
        self.node_positions[npc_name] = (event.x, event.y)

        self.pending_npc = None
        self.canvas.unbind("<Button-1>")
        self.draw_graph()

    def start_link_creation(self):
        self.link_start = self.get_node_at(*self.canvas.winfo_pointerxy())

    def add_shape(self):
        shape_type = simpledialog.askstring("Add Shape", "Shape type (circle/rect):")
        if shape_type == "circle":
            self.graph["shapes"].append({"type": "circle", "x": 300, "y": 300, "radius": 50})
        elif shape_type == "rect":
            self.graph["shapes"].append({"type": "rect", "x": 300, "y": 300, "width": 150, "height": 100})
        self.draw_graph()

    def on_canvas_click(self, event):
        if self.link_start:
            link_end = self.get_node_at(event.x, event.y)
            if link_end and link_end != self.link_start:
                desc = simpledialog.askstring("Link Description", f"Describe relationship between {self.link_start} and {link_end}:")
                if desc:
                    self.graph["links"].append({"from": self.link_start, "to": link_end, "description": desc})
            self.link_start = None
            self.draw_graph()

    def get_node_at(self, x, y):
        for node in self.graph["nodes"]:
            nx, ny = self.node_positions.get(node["npc_name"], (node["x"], node["y"]))
            if abs(nx - x) < 50 and abs(ny - y) < 50:
                return node["npc_name"]
        return None

    def draw_graph(self):
        self.canvas.delete("all")
        self.node_images.clear()

        NODE_WIDTH = 80
        NODE_HEIGHT = 100
        PORTRAIT_SIZE = 64

        for node in self.graph["nodes"]:
            npc_name = node["npc_name"]
            npc = self.npcs[npc_name]
            x, y = self.node_positions.get(npc_name, (node["x"], node["y"]))

            portrait_path = npc.get("Portrait", "")
            has_portrait = portrait_path and os.path.exists(portrait_path)

            # Draw background rectangle (entire node)
            self.canvas.create_rectangle(
                x - NODE_WIDTH // 2, y - NODE_HEIGHT // 2,
                x + NODE_WIDTH // 2, y + NODE_HEIGHT // 2,
                fill="lightblue", tags=npc_name
            )

            # Draw portrait (if exists)
            if has_portrait:
                img = Image.open(portrait_path)
                img.thumbnail((PORTRAIT_SIZE, PORTRAIT_SIZE))
                tk_img = ImageTk.PhotoImage(img)
                self.node_images[npc_name] = tk_img

                self.canvas.create_image(
                    x, y - NODE_HEIGHT // 2 + PORTRAIT_SIZE // 2,
                    image=tk_img, tags=npc_name
                )
                text_y = y - NODE_HEIGHT // 2 + PORTRAIT_SIZE + 5
            else:
                text_y = y  # Center name if no portrait

            # Draw name (first + last name)
            first_name = npc.get("First Name", npc_name).strip()
            last_name = npc.get("Last Name", "").strip()
            full_name = f"{first_name}\n{last_name}" if last_name else first_name

            self.canvas.create_text(
                x, text_y, text=full_name, font=("Arial", 10),
                justify="center", tags=npc_name
            )

            # Ensure all parts (rect, image, text) share the same tag
            self.canvas.tag_bind(npc_name, "<Button-1>", lambda e, n=npc_name: self.start_drag(e, n))
            self.canvas.tag_bind(npc_name, "<B1-Motion>", lambda e, n=npc_name: self.on_drag(e, n))


    def start_drag(self, event, npc_name):
        self.selected_node = npc_name
        self.drag_offset_x = event.x - self.node_positions[npc_name][0]
        self.drag_offset_y = event.y - self.node_positions[npc_name][1]

    def on_drag(self, event, npc_name):
        if self.selected_node != npc_name:
            return

        x = event.x - self.drag_offset_x
        y = event.y - self.drag_offset_y

        self.node_positions[npc_name] = (x, y)

        for node in self.graph["nodes"]:
            if node["npc_name"] == npc_name:
                node["x"], node["y"] = x, y
                break

        self.draw_graph()


    def save_graph(self):
        with filedialog.asksaveasfile(defaultextension=".json") as file:
            json.dump(self.graph, file)

    def load_graph(self):
        with filedialog.askopenfile() as file:
            self.graph = json.load(file)
        self.draw_graph()

    def export_to_png(self):
        messagebox.showinfo("Export", "PNG export can be implemented if required.")

    def generate_faction_graph(self):
        faction = simpledialog.askstring("Faction", "Enter Faction Name:")
        if not faction:
            return

        self.graph["nodes"].clear()
        self.graph["links"].clear()

        x, y = 100, 100
        spacing_x = 150
        spacing_y = 150
        column_count = 5

        for npc_name, npc in self.npcs.items():
            if npc.get("Faction") == faction:
                self.graph["nodes"].append({"npc_name": npc_name, "x": x, "y": y})
                self.node_positions[npc_name] = (x, y)

                x += spacing_x
                if x > (spacing_x * column_count):
                    x = 100
                    y += spacing_y

        self.draw_graph()

