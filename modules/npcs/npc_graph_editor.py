import json
import os
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import logging  # Add logging import
from modules.helpers.template_loader import load_template
from modules.generic.entity_selection_dialog import EntitySelectionDialog
from modules.generic.generic_model_wrapper import GenericModelWrapper
from .npc_graph_toolbar import NPCGraphToolbar
from .npc_graph_canvas import NPCGraphCanvas

logging.basicConfig(level=logging.DEBUG)  # Configure logging

PORTRAIT_FOLDER = "assets/portraits"
MAX_PORTRAIT_SIZE = (64, 64)

class NPCGraphEditor(ctk.CTkFrame):  # Change inheritance to CTkFrame
    def __init__(self, master, npc_wrapper: GenericModelWrapper, faction_wrapper: GenericModelWrapper, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.npc_wrapper = npc_wrapper
        self.faction_wrapper = faction_wrapper
        self.npcs = {npc["Name"]: npc for npc in self.npc_wrapper.load_items()}

        self.graph = {"nodes": [], "links": [], "objects": []}  # Ensure objects key is present
        self.node_positions = {}
        self.node_images = {}

        self.selected_node = None
        self.selected_items = []
        self.drag_start = None
        self.selected_object = None
        self.resize_handles = []

        self.toolbar = NPCGraphToolbar(self)
        self.toolbar.pack(fill="x", padx=5, pady=5)

        self.canvas_frame = ctk.CTkFrame(self)
        self.canvas_frame.pack(fill="both", expand=True)

        self.canvas = NPCGraphCanvas(self.canvas_frame, self)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.h_scrollbar = ttk.Scrollbar(self.canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.v_scrollbar = ttk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)

        self.canvas.configure(xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set)

        self.h_scrollbar.grid(row=1, column=0, sticky="ew")
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")

        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

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

            if "objects" not in self.graph:
                self.graph["objects"] = []

            self.node_positions = {
                f"npc_{n['npc_name'].replace(' ', '_')}": (n["x"], n["y"])
                for n in self.graph["nodes"]
            }

            self.canvas.draw_graph()

    def add_npc(self):
        def on_npc_selected(npc):
            self.pending_npc = npc
            self.canvas.bind("<Button-1>", self.place_pending_npc)

        npc_template = load_template("npcs")
        dialog = EntitySelectionDialog(self, "NPCs", self.npc_wrapper, npc_template, on_npc_selected)
        dialog.wait_window()

    def add_faction(self):
        class FactionSelectionDialog(ctk.CTkToplevel):
            def __init__(self, master, factions, on_faction_selected):
                super().__init__(master)
                self.title("Select Faction")
                self.geometry("400x300")
                self.transient(master)
                self.grab_set()
                self.focus_force()

                self.factions = factions
                self.filtered_factions = factions.copy()
                self.on_faction_selected = on_faction_selected

                self.search_var = ctk.StringVar()

                search_frame = ctk.CTkFrame(self)
                search_frame.pack(fill="x", padx=5, pady=5)

                ctk.CTkLabel(search_frame, text="Search Faction:").pack(side="left", padx=5)
                search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
                search_entry.pack(side="left", fill="x", expand=True, padx=5)
                search_entry.bind("<KeyRelease>", lambda event: self.filter_factions())

                self.list_frame = ctk.CTkScrollableFrame(self)
                self.list_frame.pack(fill="both", expand=True, padx=5, pady=5)

                self.refresh_list()

            def filter_factions(self):
                query = self.search_var.get().strip().lower()
                self.filtered_factions = [f for f in self.factions if query in f.lower()]
                self.refresh_list()

            def refresh_list(self):
                for widget in self.list_frame.winfo_children():
                    widget.destroy()

                for faction in self.filtered_factions:
                    btn = ctk.CTkButton(self.list_frame, text=faction, command=lambda f=faction: self.select_faction(f))
                    btn.pack(fill="x", padx=5, pady=2)

            def select_faction(self, faction):
                self.on_faction_selected(faction)
                self.destroy()

        def on_faction_selected(faction_name):
            faction_npcs = [npc for npc in self.npcs.values() if npc.get("Faction") == faction_name]
            if not faction_npcs:
                messagebox.showinfo("No NPCs", f"No NPCs found for faction '{faction_name}'.")
                return

            start_x, start_y = 100, 100
            spacing = 120
            for i, npc in enumerate(faction_npcs):
                npc_name = npc["Name"]
                tag = f"npc_{npc_name.replace(' ', '_')}"
                x = start_x + i * spacing
                y = start_y
                self.graph["nodes"].append({"npc_name": npc_name, "x": x, "y": y})
                self.node_positions[tag] = (x, y)
            self.canvas.draw_graph()

        factions = sorted(set(npc.get("Faction", "Unknown") for npc in self.npcs.values() if npc.get("Faction")))
        if not factions:
            messagebox.showerror("Error", "No factions found in NPC data.")
            return

        dialog = FactionSelectionDialog(self, factions, on_faction_selected)
        self.wait_window(dialog)

    def start_link_creation(self):
        self.canvas.bind("<Button-1>", self.select_first_node)

    def add_rectangle(self):
        logging.debug("Binding place_rectangle to Button-1")
        self.canvas.bind("<Button-1>", self.place_rectangle)

    def place_rectangle(self, event):
        x, y = event.x, event.y
        logging.debug(f"Placing rectangle at ({x}, {y})")
        rect_id = self.canvas.create_rectangle(x-20, y-20, x+20, y+20, fill="green", tags="object")
        logging.debug(f"Created rectangle ID: {rect_id}")
        self.graph["objects"].append({"type": "rectangle", "x1": x-20, "y1": y-20, "x2": x+20, "y2": y+20, "id": rect_id})
        self.canvas.unbind("<Button-1>")
        self.canvas.bind("<Button-1>", self.on_canvas_click)

    def select_object(self, item_id):
        self.selected_object = item_id
        self.canvas.itemconfig(item_id, outline="red", width=2)
        logging.debug(f"Selected object ID: {item_id}")
        
        coords = self.get_item_coords(item_id)
        if not coords or len(coords) != 4:
            logging.error(f"Failed to get valid coordinates for item ID: {item_id}, coords: {coords}")
            return

        logging.debug(f"Object coordinates: {coords}")
        self.create_resize_handles(item_id)

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

    def draw_graph(self):
        self.canvas.draw_graph()

    def place_pending_npc(self, event):
        npc_name = self.pending_npc["Name"]
        tag = f"npc_{npc_name.replace(' ', '_')}"
        self.graph["nodes"].append({"npc_name": npc_name, "x": event.x, "y": event.y})
        self.node_positions[tag] = (event.x, event.y)
        self.pending_npc = None
        self.canvas.unbind("<Button-1>")
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.draw_graph()

    def on_canvas_click(self, event):
        item = self.canvas.find_closest(event.x, event.y)
        if not item:
            return
        item_id = item[0]
        tags = self.canvas.gettags(item_id)
        logging.debug(f"Clicked item ID: {item_id}, tags: {tags}")

        if "object" in tags:
            self.select_object(item_id)
        else:
            self.start_drag(event)

    def select_first_node(self, event):
        item = self.canvas.find_closest(event.x, event.y)
        if not item:
            return
        item_id = item[0]
        tags = self.canvas.gettags(item_id)
        self.first_node = next((t for t in tags if t.startswith("npc_")), None)
        if self.first_node:
            self.canvas.bind("<Button-1>", self.select_second_node)

    def select_second_node(self, event):
        item = self.canvas.find_closest(event.x, event.y)
        if not item:
            return
        item_id = item[0]
        tags = self.canvas.gettags(item_id)
        self.second_node = next((t for t in tags if t.startswith("npc_")), None)
        if self.second_node:
            self.canvas.unbind("<Button-1>")
            self.prompt_link_text()

    def prompt_link_text(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Enter Link Text")
        dialog.geometry("400x150")
        dialog.transient(self)
        dialog.grab_set()
        dialog.focus_force()

        ctk.CTkLabel(dialog, text="Link Text:").pack(pady=5)
        link_text_var = ctk.StringVar()
        link_text_entry = ctk.CTkEntry(dialog, textvariable=link_text_var)
        link_text_entry.pack(pady=5)
        link_text_entry.bind("<Return>", lambda event: on_add_link())

        def on_add_link():
            link_text = link_text_var.get()
            self.add_link(self.first_node, self.second_node, link_text)
            dialog.destroy()
            self.canvas.bind("<Button-1>", self.on_canvas_click)

        ctk.CTkButton(dialog, text="Add Link", command=on_add_link).pack(pady=10)
        dialog.after(100, link_text_entry.focus_set)

    def add_link(self, tag1, tag2, link_text):
        if tag1 not in self.node_positions or tag2 not in self.node_positions:
            messagebox.showerror("Error", "One or both NPCs not found.")
            return

        x1, y1 = self.node_positions[tag1]
        x2, y2 = self.node_positions[tag2]

        npc_name1 = tag1.replace("npc_", "").replace("_", " ")
        npc_name2 = tag2.replace("npc_", "").replace("_", " ")

        self.graph["links"].append({"npc_name1": npc_name1, "npc_name2": npc_name2, "text": link_text})
        self.canvas.draw_graph()
        self.canvas.bind("<Button-1>", self.on_canvas_click)

    def get_item_coords(self, item_id):
        # Try to get the coordinates using coords()
        coords = self.canvas.coords(item_id)
        # Fallback: if coords() returns None or an incomplete tuple, use bbox()
        if not coords or len(coords) < 4:
            coords = self.canvas.bbox(item_id)
        return coords

    def create_resize_handles(self, item_id):
        logging.debug(f"Creating resize handles for item ID: {item_id}")
        coords = self.get_item_coords(item_id)
        logging.debug(f"Coordinates for item ID {item_id}: {coords}")
        if not coords or len(coords) != 4:
            logging.error(f"Item ID {item_id} does not have valid coordinates: {coords}")
            return

        x1, y1, x2, y2 = coords
        handle_size = 8
        self.clear_resize_handles()
        logging.debug("Cleared existing resize handles")

        self.resize_handles = [
            self.canvas.create_rectangle(x1-handle_size, y1-handle_size, x1+handle_size, y1+handle_size, fill="blue", tags="resize_handle"),  # top-left
            self.canvas.create_rectangle(x2-handle_size, y1-handle_size, x2+handle_size, y1+handle_size, fill="blue", tags="resize_handle"),  # top-right
            self.canvas.create_rectangle(x1-handle_size, y2-handle_size, x1+handle_size, y2+handle_size, fill="blue", tags="resize_handle"),  # bottom-left
            self.canvas.create_rectangle(x2-handle_size, y2-handle_size, x2+handle_size, y2+handle_size, fill="blue", tags="resize_handle"),  # bottom-right
            self.canvas.create_rectangle((x1+x2)//2-handle_size, y1-handle_size, (x1+x2)//2+handle_size, y1+handle_size, fill="blue", tags="resize_handle"),  # top-center
            self.canvas.create_rectangle((x1+x2)//2-handle_size, y2-handle_size, (x1+x2)//2+handle_size, y2+handle_size, fill="blue", tags="resize_handle"),  # bottom-center
            self.canvas.create_rectangle(x1-handle_size, (y1+y2)//2-handle_size, x1+handle_size, (y1+y2)//2-handle_size, fill="blue", tags="resize_handle"),  # left-center
            self.canvas.create_rectangle(x2-handle_size, (y1+y2)//2-handle_size, x2+handle_size, (y1+y2)//2-handle_size, fill="blue", tags="resize_handle")   # right-center
        ]

        logging.debug(f"Created resize handles: {self.resize_handles}")
        for handle in self.resize_handles:
            self.canvas.tag_bind(handle, "<B1-Motion>", self.resize_object)
            logging.debug(f"Bound resize handle {handle} to resize_object")

    def clear_resize_handles(self):
        logging.debug("Clearing resize handles")
        for handle in self.resize_handles:
            self.canvas.delete(handle)
        self.resize_handles = []

    def resize_object(self, event):
        if not self.selected_object:
            return
        x, y = event.x, event.y
        current_handle = self.canvas.find_withtag("current")
        if not current_handle:
            return
        try:
            handle_index = self.resize_handles.index(current_handle[0])
        except ValueError:
            return

        logging.debug(f"Resizing object with handle index: {handle_index}, coordinates: ({x}, {y})")
        coords = self.get_item_coords(self.selected_object)
        if not coords or len(coords) != 4:
            logging.error(f"Failed to get valid coordinates for resizing, coords: {coords}")
            return
        x1, y1, x2, y2 = coords
        if handle_index == 0:  # Top-left
            self.canvas.coords(self.selected_object, x, y, x2, y2)
        elif handle_index == 1:  # Top-right
            self.canvas.coords(self.selected_object, x1, y, x, y2)
        elif handle_index == 2:  # Bottom-left
            self.canvas.coords(self.selected_object, x, y1, x2, y)
        elif handle_index == 3:  # Bottom-right
            self.canvas.coords(self.selected_object, x1, y1, x, y)
        elif handle_index == 4:  # Top-center
            self.canvas.coords(self.selected_object, x1, y, x2, y2)
        elif handle_index == 5:  # Bottom-center
            self.canvas.coords(self.selected_object, x1, y1, x2, y)
        elif handle_index == 6:  # Left-center
            self.canvas.coords(self.selected_object, x, y1, x2, y2)
        elif handle_index == 7:  # Right-center
            self.canvas.coords(self.selected_object, x1, y1, x, y2)
        self.update_resize_handles()

    def update_resize_handles(self):
        coords = self.get_item_coords(self.selected_object)
        if not coords or len(coords) != 4:
            logging.error(f"Failed to update resize handles; invalid coordinates: {coords}")
            return
        x1, y1, x2, y2 = coords
        handle_size = 8
        self.canvas.coords(self.resize_handles[0], x1-handle_size, y1-handle_size, x1+handle_size, y1+handle_size)
        self.canvas.coords(self.resize_handles[1], x2-handle_size, y1-handle_size, x2+handle_size, y1+handle_size)
        self.canvas.coords(self.resize_handles[2], x1-handle_size, y2-handle_size, x1+handle_size, y2+handle_size)
        self.canvas.coords(self.resize_handles[3], x2-handle_size, y2-handle_size, x2+handle_size, y2+handle_size)
        self.canvas.coords(self.resize_handles[4], (x1+x2)//2-handle_size, y1-handle_size, (x1+x2)//2+handle_size, y1+handle_size)
        self.canvas.coords(self.resize_handles[5], (x1+x2)//2-handle_size, y2-handle_size, (x1+x2)//2+handle_size, y2+handle_size)
        self.canvas.coords(self.resize_handles[6], x1-handle_size, (y1+y2)//2-handle_size, x1+handle_size, (y1+y2)//2-handle_size)
        self.canvas.coords(self.resize_handles[7], x2-handle_size, (y1+y2)//2-handle_size, x2+handle_size, (y1+y2)//2-handle_size)
