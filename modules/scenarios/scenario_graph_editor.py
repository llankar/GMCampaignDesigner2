import json
import os
import math
import customtkinter as ctk
import tkinter.font as tkFont

from tkinter import filedialog, messagebox, ttk, Menu
from PIL import Image, ImageTk

from modules.generic.entity_selection_dialog import EntitySelectionDialog
from modules.helpers.template_loader import load_template
from modules.generic.generic_model_wrapper import GenericModelWrapper
from modules.generic.generic_editor_window import GenericEditorWindow
from modules.npcs import npc_opener


PORTRAIT_FOLDER = "assets/portraits"
MAX_PORTRAIT_SIZE = (64, 64)

# ─────────────────────────────────────────────────────────────────────────
# CLASS: ScenarioGraphEditor
# A custom graph editor for a single scenario, mimicking NPCGraphEditor style.
# ─────────────────────────────────────────────────────────────────────────
class ScenarioGraphEditor(ctk.CTkFrame):
    def __init__(self, master,
                 scenario_wrapper: GenericModelWrapper,
                 npc_wrapper: GenericModelWrapper,
                 place_wrapper: GenericModelWrapper,
                 *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.scenario_wrapper = scenario_wrapper
        self.npc_wrapper = npc_wrapper
        self.place_wrapper = place_wrapper

        # Preload NPC and Place data for quick lookup
        self.npcs = {npc["Name"]: npc for npc in self.npc_wrapper.load_items()}
        self.places = {pl["Name"]: pl for pl in self.place_wrapper.load_items()}

        # The single scenario chosen by the user
        self.scenario = None

        # Graph structure
        self.graph = {"nodes": [], "links": []}
        self.node_positions = {}   # Maps node_tag -> (x, y)
        self.node_rectangles = {}  # Maps node_tag -> rectangle_id
        self.selected_node = None  # Currently selected node tag
        self.selected_items = []   # All canvas items for that node
        self.drag_start = None     # (x, y) for dragging

        # Toolbar
        self.init_toolbar()

        # Create canvas with scrollbars
        self.canvas_frame = ctk.CTkFrame(self)
        self.canvas_frame.pack(fill="both", expand=True)
        self.canvas = ctk.CTkCanvas(self.canvas_frame, bg="#ffffff", highlightthickness=0)
        self.h_scrollbar = ttk.Scrollbar(self.canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.v_scrollbar = ttk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        # Global mouse events (like NPCGraphEditor)
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel_y)
        self.canvas.bind("<Shift-MouseWheel>", self._on_mousewheel_x)
        self.canvas.bind("<Button-4>", self._on_mousewheel_y)
        self.canvas.bind("<Button-5>", self._on_mousewheel_y)
        self.canvas.bind("<Shift-Button-4>", self._on_mousewheel_x)
        self.canvas.bind("<Shift-Button-5>", self._on_mousewheel_x)

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: init_toolbar
    # ─────────────────────────────────────────────────────────────────────────
    def init_toolbar(self):
        toolbar = ctk.CTkFrame(self)
        toolbar.pack(fill="x", padx=5, pady=5)
        ctk.CTkButton(toolbar, text="Select Scenario", command=self.select_scenario).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Save Graph", command=self.save_graph).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Load Graph", command=self.load_graph).pack(side="left", padx=5)

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: select_scenario
    # ─────────────────────────────────────────────────────────────────────────
    def select_scenario(self):
        scenario_template = load_template("scenarios")
        def on_scenario_selected(scenario_data):
            self.load_scenario(scenario_data)
        dialog = EntitySelectionDialog(
            self, "Scenarios", self.scenario_wrapper, scenario_template, on_scenario_selected
        )
        dialog.wait_window()

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: load_scenario
    # Build a single-scenario graph: one scenario node, plus NPC/place nodes.
    # ─────────────────────────────────────────────────────────────────────────
    def load_scenario(self, scenario):
        self.scenario = scenario
        self.graph = {"nodes": [], "links": []}
        self.node_positions.clear()

        # Create the scenario node in the center
        center_x, center_y = 400, 300
        scenario_title = scenario.get("Title", "No Title")
        summary = scenario.get("Summary", "")
        if isinstance(summary, dict):
            summary = summary.get("text", "")

        scenario_tag = f"scenario_{scenario_title.replace(' ', '_')}"
        self.graph["nodes"].append({
            "type": "scenario",
            "name": scenario_title,
            "x": center_x,
            "y": center_y,
            "color": "lightgreen",
            "data": scenario  # store entire scenario
        })
        self.node_positions[scenario_tag] = (center_x, center_y)

        # For each NPC in scenario, create a node and link to scenario
        for i, npc_name in enumerate(scenario.get("NPCs", [])):
            if npc_name in self.npcs:
                angle = math.radians(90 + i * 45)
                offset = 180
                x = center_x + offset * math.cos(angle)
                y = center_y + offset * math.sin(angle)
                npc_data = self.npcs[npc_name]
                desc = npc_data.get("Description", "")
                if isinstance(desc, dict):
                    desc = desc.get("text", "")

                npc_tag = f"npc_{npc_name.replace(' ', '_')}"
                self.graph["nodes"].append({
                    "type": "npc",
                    "name": npc_name,
                    "x": x,
                    "y": y,
                    "color": "lightblue",
                    "data": npc_data
                })
                self.node_positions[npc_tag] = (x, y)
                # link scenario -> npc
                self.graph["links"].append({
                    "from": scenario_tag,
                    "to": npc_tag,
                    "text": ""
                })

        # For each Place in scenario, create a node and link to scenario
        for j, place_name in enumerate(scenario.get("Places", [])):
            if place_name in self.places:
                angle = math.radians(270 + j * 45)
                offset = 180
                x = center_x + offset * math.cos(angle)
                y = center_y + offset * math.sin(angle)
                place_data = self.places[place_name]
                desc = place_data.get("Description", "")
                if isinstance(desc, dict):
                    desc = desc.get("text", "")

                place_tag = f"place_{place_name.replace(' ', '_')}"
                self.graph["nodes"].append({
                    "type": "place",
                    "name": place_name,
                    "x": x,
                    "y": y,
                    "color": "khaki",
                    "data": place_data
                })
                self.node_positions[place_tag] = (x, y)
                # link scenario -> place
                self.graph["links"].append({
                    "from": scenario_tag,
                    "to": place_tag,
                    "text": ""
                })

        self.draw_graph()

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: draw_graph
    # Clear the canvas and redraw nodes/links.
    # ─────────────────────────────────────────────────────────────────────────
    def draw_graph(self):
        self.canvas.delete("all")
        self.node_rectangles.clear()

        self.draw_nodes()
        self.draw_links()

        self.canvas.update_idletasks()
        bbox = self.canvas.bbox("all")
        if bbox:
            padding = 50
            self.canvas.configure(scrollregion=(
                bbox[0] - padding, bbox[1] - padding,
                bbox[2] + padding, bbox[3] + padding
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: draw_nodes
    # Draw rectangles + text for each node. No per-node tag_bind here.
    # ─────────────────────────────────────────────────────────────────────────
    def draw_nodes(self):
        # Create a font object for measuring text (should match the one used for create_text)
        font_obj = tkFont.Font(family="Arial", size=9)
        pad_x = 10  # horizontal padding
        pad_y = 10  # vertical padding

        for node in self.graph["nodes"]:
            node_type = node["type"]
            node_name = node["name"]
            x, y = node["x"], node["y"]
            color = node.get("color", "lightgray")
            
            # Determine the text to display
            if node_type == "scenario":
                short_desc = node["data"].get("Summary", "")
                if isinstance(short_desc, dict):
                    short_desc = short_desc.get("text", "")
            else:
                short_desc = node["data"].get("Description", "")
                if isinstance(short_desc, dict):
                    short_desc = short_desc.get("text", "")
            text = f"{node_name}\n{short_desc}"
            
            # Split the text into lines and measure each line's width and the total height.
            lines = text.split("\n")
            max_line_width = max(font_obj.measure(line) for line in lines) if lines else 0
            total_height = len(lines) * font_obj.metrics("linespace")
            
            # Calculate dynamic node dimensions
            node_width = max_line_width + 2 * pad_x
            node_height = total_height + 2 * pad_y
            
            # Compute rectangle boundaries based on node center (x, y)
            left = x - (node_width / 2)
            top = y - (node_height / 2)
            right = x + (node_width / 2)
            bottom = y + (node_height / 2)
            
            # Build a unique tag for this node
            node_tag = f"{node_type}_{node_name.replace(' ', '_')}"
            
            # Draw the node rectangle with the computed dimensions
            rect_id = self.canvas.create_rectangle(
                left, top, right, bottom,
                fill=color, outline="black", width=2, tags=("node", node_tag)
            )
            self.node_rectangles[node_tag] = rect_id
            
            # Draw the text centered in the node rectangle; use the same tag so that clicks on the text count.
            self.canvas.create_text(
                x, y, text=text,
                fill="black", font=("Arial", 9),
                width=node_width - 4, justify="center",
                tags=("node", node_tag)
            )

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: draw_links
    # Draw lines for each link, behind the nodes.
    # ─────────────────────────────────────────────────────────────────────────
    def draw_links(self):
        for link in self.graph["links"]:
            self.draw_one_link(link)
        self.canvas.tag_lower("link")  # keep lines behind nodes

    def draw_one_link(self, link):
        tag_from = link["from"]
        tag_to = link["to"]
        x1, y1 = self.node_positions.get(tag_from, (0, 0))
        x2, y2 = self.node_positions.get(tag_to, (0, 0))
        line_id = self.canvas.create_line(
            x1, y1, x2, y2, fill="black", width=2, tags=("link",)
        )
        self.canvas.tag_lower(line_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Mouse/Drag Events (Global Binds)
    # ─────────────────────────────────────────────────────────────────────────
    def start_drag(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        items = self.canvas.find_closest(x, y)
        if not items:
            return
        item_id = items[0]
        tags = self.canvas.gettags(item_id)
        # If clicked on a link, ignore dragging
        if "link" in tags:
            self.selected_node = None
            self.drag_start = None
            return
        node_tag = next((t for t in tags if t.startswith("scenario_")
                         or t.startswith("npc_")
                         or t.startswith("place_")), None)
        if node_tag:
            self.selected_node = node_tag
            self.selected_items = self.canvas.find_withtag(node_tag)
            self.drag_start = (x, y)
        else:
            self.selected_node = None
            self.drag_start = None

    def on_drag(self, event):
        """Updated on_drag that updates both node_positions and graph nodes."""
        if not self.selected_node or not self.drag_start:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        dx = x - self.drag_start[0]
        dy = y - self.drag_start[1]
        for item_id in self.selected_items:
            self.canvas.move(item_id, dx, dy)
        old_x, old_y = self.node_positions.get(self.selected_node, (0, 0))
        new_pos = (old_x + dx, old_y + dy)
        self.node_positions[self.selected_node] = new_pos
        self.drag_start = (x, y)
        # Update the node's x, y in the graph
        for node in self.graph["nodes"]:
            node_tag = f"{node['type']}_{node['name'].replace(' ', '_')}"
            if node_tag == self.selected_node:
                node["x"], node["y"] = new_pos
                break
        self.draw_graph()


    def on_double_click(self, event):
        """Mimics NPCGraphEditor: globally bound <Double-Button-1> on canvas."""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        items = self.canvas.find_closest(x, y)
        if not items:
            return
        item_id = items[0]
        tags = self.canvas.gettags(item_id)

        # If line, do nothing
        if "link" in tags:
            return

        node_tag = next((t for t in tags if t.startswith("scenario_")
                         or t.startswith("npc_")
                         or t.startswith("place_")), None)
        if not node_tag:
            return

        # Open the relevant editor
        if node_tag.startswith("scenario_"):
            scenario_template = load_template("scenarios")
            if self.scenario:
                GenericEditorWindow(None, self.scenario, scenario_template)
        elif node_tag.startswith("npc_"):
            npc_name = node_tag.replace("npc_", "").replace("_", " ")
            npc_opener.open_npc_editor_window(npc_name)
        elif node_tag.startswith("place_"):
            place_template = load_template("places")
            place_name = node_tag.replace("place_", "").replace("_", " ")
            place_data = self.places.get(place_name)
            if place_data:
                GenericEditorWindow(None, place_data, place_template)

    def on_right_click(self, event):
        """Mimics NPCGraphEditor: globally bound <Button-3> on canvas."""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        items = self.canvas.find_closest(x, y)
        if not items:
            return
        item_id = items[0]
        tags = self.canvas.gettags(item_id)

        if "link" in tags:
            # Could show a link context menu, or ignore
            return

        node_tag = next((t for t in tags if t.startswith("scenario_")
                         or t.startswith("npc_")
                         or t.startswith("place_")), None)
        if node_tag:
            self.selected_node = node_tag
            self.show_node_menu(x, y)

    # ─────────────────────────────────────────────────────────────────────────
    # Mouse Wheel Scrolling
    # ─────────────────────────────────────────────────────────────────────────
    def _on_mousewheel_y(self, event):
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")

    def _on_mousewheel_x(self, event):
        if event.num == 4 or event.delta > 0:
            self.canvas.xview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas.xview_scroll(1, "units")

    # ─────────────────────────────────────────────────────────────────────────
    # Context Menu for Node
    # ─────────────────────────────────────────────────────────────────────────
    def show_node_menu(self, x, y):
        node_menu = Menu(self.canvas, tearoff=0)
        node_menu.add_command(label="Delete Node", command=self.delete_node)
        node_menu.add_separator()
        node_menu.add_command(label="Change Color", command=lambda: self.show_color_menu(x, y))
        node_menu.post(int(x), int(y))

    def show_color_menu(self, x, y):
        COLORS = [
            "red", "green", "blue", "yellow", "purple",
            "orange", "pink", "cyan", "magenta", "lightgray"
        ]
        color_menu = Menu(self.canvas, tearoff=0)
        for color in COLORS:
            color_menu.add_command(label=color, command=lambda c=color: self.change_node_color(c))
        color_menu.post(int(x), int(y))

    def change_node_color(self, color):
        if not self.selected_node:
            return
        rect_id = self.node_rectangles.get(self.selected_node)
        if rect_id:
            self.canvas.itemconfig(rect_id, fill=color)
        # Update the graph data
        for node in self.graph["nodes"]:
            if node["type"] == "scenario":
                tag = f"scenario_{node['name'].replace(' ', '_')}"
            elif node["type"] == "npc":
                tag = f"npc_{node['name'].replace(' ', '_')}"
            else:
                tag = f"place_{node['name'].replace(' ', '_')}"
            if tag == self.selected_node:
                node["color"] = color
                break
        self.draw_graph()

    def delete_node(self):
        if not self.selected_node:
            return
        node_name = self.selected_node.split("_", 1)[-1].replace("_", " ")
        self.graph["nodes"] = [
            n for n in self.graph["nodes"] if n["name"] != node_name
        ]
        self.graph["links"] = [
            l for l in self.graph["links"]
            if l["from"] != self.selected_node and l["to"] != self.selected_node
        ]
        if self.selected_node in self.node_positions:
            del self.node_positions[self.selected_node]
        self.draw_graph()

    # ─────────────────────────────────────────────────────────────────────────
    # Save/Load Graph (optional)
    # ─────────────────────────────────────────────────────────────────────────
    def save_graph(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json")
        if file_path:
            # Update node positions
            for node in self.graph["nodes"]:
                node_tag = ""
                if node["type"] == "scenario":
                    node_tag = f"scenario_{node['name'].replace(' ', '_')}"
                elif node["type"] == "npc":
                    node_tag = f"npc_{node['name'].replace(' ', '_')}"
                else:
                    node_tag = f"place_{node['name'].replace(' ', '_')}"
                x, y = self.node_positions.get(node_tag, (node["x"], node["y"]))
                node["x"], node["y"] = x, y
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.graph, f, indent=2)

    def load_graph(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                self.graph = json.load(f)
            self.node_positions.clear()
            for node in self.graph["nodes"]:
                node_tag = ""
                if node["type"] == "scenario":
                    node_tag = f"scenario_{node['name'].replace(' ', '_')}"
                elif node["type"] == "npc":
                    node_tag = f"npc_{node['name'].replace(' ', '_')}"
                else:
                    node_tag = f"place_{node['name'].replace(' ', '_')}"
                self.node_positions[node_tag] = (node["x"], node["y"])
            self.draw_graph()
