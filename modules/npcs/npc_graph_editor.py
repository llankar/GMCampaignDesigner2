import json
import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from modules.helpers.template_loader import load_template
from modules.generic.entity_selection_dialog import EntitySelectionDialog
from modules.generic.generic_model_wrapper import GenericModelWrapper

PORTRAIT_FOLDER = "assets/portraits"
MAX_PORTRAIT_SIZE = (64, 64)

class NPCGraphEditor(ctk.CTkToplevel):
    def __init__(self, master, npc_wrapper: GenericModelWrapper, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.title("NPC Relationship Graph")
        self.geometry("1280x720")
        self.transient(master)
        self.grab_set()
        self.focus_force()

        self.npc_wrapper = npc_wrapper
        self.npcs = {npc["Name"]: npc for npc in self.npc_wrapper.load_items()}
        print(f"Loaded {len(self.npcs)} NPCs")

        self.graph = {"nodes": [], "links": []}
        self.node_positions = {}
        self.node_images = {}

        self.selected_node = None
        self.selected_items = []
        self.drag_start = None

        self.canvas = ctk.CTkCanvas(self, bg="#ffffff", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.init_toolbar()

        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.on_drag)

    def init_toolbar(self):
        toolbar = ctk.CTkFrame(self)
        toolbar.pack(fill="x", padx=5, pady=5)

        ctk.CTkButton(toolbar, text="Add NPC", command=self.add_npc).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Save Graph", command=self.save_graph).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Load Graph", command=self.load_graph).pack(side="left", padx=5)

    def add_npc(self):
        def on_npc_selected(npc):
            self.pending_npc = npc
            messagebox.showinfo("Placement", "Click on the canvas to place the NPC.")
            self.canvas.bind("<Button-1>", self.place_pending_npc)

        npc_template = load_template("npcs")
        dialog = EntitySelectionDialog(self, "NPCs", self.npc_wrapper, npc_template, on_npc_selected)
        dialog.wait_window()

    def place_pending_npc(self, event):
        npc_name = self.pending_npc["Name"]
        tag = f"npc_{npc_name.replace(' ', '_')}"
        self.graph["nodes"].append({"npc_name": npc_name, "x": event.x, "y": event.y})
        self.node_positions[tag] = (event.x, event.y)
        self.pending_npc = None
        self.canvas.unbind("<Button-1>")
        self.canvas.bind("<Button-1>", self.start_drag)
        self.draw_graph()

    def start_drag(self, event):
        item = self.canvas.find_closest(event.x, event.y)
        if not item:
            return
        item_id = item[0]
        tags = self.canvas.gettags(item_id)
        self.selected_node = next((t for t in tags if t.startswith("npc_")), None)
        if self.selected_node:
            self.selected_items = self.canvas.find_withtag(self.selected_node)
            self.drag_start = (event.x, event.y)

    def on_drag(self, event):
        if not self.selected_node or not self.drag_start:
            return

        dx = event.x - self.drag_start[0]
        dy = event.y - self.drag_start[1]

        for item in self.selected_items:
            self.canvas.move(item, dx, dy)

        x, y = self.node_positions[self.selected_node]
        self.node_positions[self.selected_node] = (x + dx, y + dy)

        self.drag_start = (event.x, event.y)

    def draw_graph(self):
        self.canvas.delete("all")
        self.node_images.clear()

        NODE_WIDTH = 100
        TEXT_LINE_HEIGHT = 14
        TEXT_TOTAL_HEIGHT = 2 * TEXT_LINE_HEIGHT + 4
        TEXT_PADDING = 5

        for node in self.graph["nodes"]:
            npc_name = node["npc_name"]
            tag = f"npc_{npc_name.replace(' ', '_')}"
            x, y = self.node_positions.get(tag, (node["x"], node["y"]))

            portrait_path = self.npcs.get(npc_name, {}).get("Portrait", "")
            has_portrait = portrait_path and os.path.exists(portrait_path)

            portrait_height = 0
            portrait_width = 0

            if has_portrait:
                img = Image.open(portrait_path)
                original_width, original_height = img.size

                max_portrait_width = NODE_WIDTH - 4
                max_portrait_height = 80

                ratio = min(max_portrait_width / original_width, max_portrait_height / original_height)
                portrait_width = int(original_width * ratio)
                portrait_height = int(original_height * ratio)

                img = img.resize((portrait_width, portrait_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)

                self.node_images[npc_name] = photo

            node_height = portrait_height + TEXT_TOTAL_HEIGHT + (TEXT_PADDING if has_portrait else 0)

            self.canvas.create_rectangle(
                x - NODE_WIDTH // 2, y - node_height // 2,
                x + NODE_WIDTH // 2, y + node_height // 2,
                fill="lightblue", tags=(tag,)
            )

            if has_portrait:
                self.canvas.create_image(
                    x, y - node_height // 2 + portrait_height // 2,
                    image=self.node_images[npc_name], tags=(tag,)
                )

            words = npc_name.split()
            if len(words) >= 2:
                wrapped_name = f"{words[0]}\n{' '.join(words[1:])}"
            else:
                wrapped_name = npc_name

            if has_portrait:
                text_y = y - node_height // 2 + portrait_height + TEXT_PADDING + TEXT_LINE_HEIGHT // 2 + 2
            else:
                text_y = y

            self.canvas.create_text(
                x, text_y,
                text=wrapped_name,
                fill="black",
                font=("Arial", 9, "bold"),
                width=NODE_WIDTH - 4,
                justify="center",
                tags=(tag,)
            )

    def save_graph(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json")
        if file_path:
            for node in self.graph["nodes"]:
                tag = f"npc_{node['npc_name'].replace(' ', '_')}"
                x, y = self.node_positions.get(tag, (node["x"], node["y"]))
                node["x"] = x
                node["y"] = y

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.graph, f, indent=2)

    def load_graph(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                self.graph = json.load(f)

            self.node_positions = {
                f"npc_{n['npc_name'].replace(' ', '_')}": (n["x"], n["y"])
                for n in self.graph["nodes"]
            }

            self.draw_graph()
