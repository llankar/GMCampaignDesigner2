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
import requests  # make sure to import requests at the top


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

        self.node_images = {}  # Store PhotoImage objects here to prevent garbage collection

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

        # Create the scenario node in the center.
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

        # --------------------
        # 1) NPC nodes on the top half (arc: 30° to 150°)
        # --------------------
        npcs_list = scenario.get("NPCs", [])
        npcs_count = len(npcs_list)
        if npcs_count > 0:
            arc_start_npcs = 30    # starting angle in degrees (directly upper right-ish)
            arc_end_npcs   = 150   # ending angle in degrees (upper left-ish)
            offset_npcs    = 350   # distance from the scenario node

            for i, npc_name in enumerate(npcs_list):
                if npc_name not in self.npcs:
                    continue
                if npcs_count == 1:
                    angle_deg = (arc_start_npcs + arc_end_npcs) / 2
                else:
                    angle_deg = arc_start_npcs + i * (arc_end_npcs - arc_start_npcs) / (npcs_count - 1)
                angle_rad = math.radians(angle_deg)
                x = center_x + offset_npcs * math.cos(angle_rad)
                y = center_y + offset_npcs * math.sin(angle_rad)
                npc_data = self.npcs[npc_name]
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
                self.graph["links"].append({
                    "from": scenario_tag,
                    "to": npc_tag,
                    "text": ""
                })

        # --------------------
        # 2) Place nodes on the bottom half (arc: 210° to 330°)
        # --------------------
        places_list = scenario.get("Places", [])
        places_count = len(places_list)
        if places_count > 0:
            arc_start_places = 210  # starting angle in degrees (lower left)
            arc_end_places   = 330  # ending angle in degrees (lower right)
            offset_places    = 350  # distance from the scenario node

            for j, place_name in enumerate(places_list):
                if place_name not in self.places:
                    continue
                if places_count == 1:
                    angle_deg = (arc_start_places + arc_end_places) / 2
                else:
                    angle_deg = arc_start_places + j * (arc_end_places - arc_start_places) / (places_count - 1)
                angle_rad = math.radians(angle_deg)
                x = center_x + offset_places * math.cos(angle_rad)
                y = center_y + offset_places * math.sin(angle_rad)
                place_data = self.places[place_name]
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
                self.graph["links"].append({
                    "from": scenario_tag,
                    "to": place_tag,
                    "text": ""
                })

        self.draw_graph()

    def display_portrait_on_fire_tv(self, portrait_path):
        """
        Sends a JSON-RPC command to Kodi running on your Fire TV to display the image.
        This example uses the 'Player.Open' method, which may work if Kodi is configured to display images.
        Adjust the command as needed.
        """
        FIRE_TV_IP = "192.168.1.100"  # <-- Set your Fire TV's IP address here
        KODI_PORT = 8080              # <-- Set the Kodi JSON-RPC port (usually 8080)
        url = f"http://{FIRE_TV_IP}:{KODI_PORT}/jsonrpc"
        
        payload = {
            "jsonrpc": "2.0",
            "method": "Player.Open",
            "params": {
                "item": {"file": portrait_path}
            },
            "id": 1
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
        except Exception as e:
            messagebox.showerror("Error", f"Error displaying portrait on Fire TV: {e}")

    def display_on_fire_tv(self):
        """
        Called when the user selects "Display on Fire TV" from the node context menu.
        It finds the portrait path from the selected NPC node and calls display_portrait_on_fire_tv.
        """
        if not self.selected_node or not self.selected_node.startswith("npc_"):
            return
        portrait_path = None
        # Find the NPC node in our graph
        for node in self.graph["nodes"]:
            node_tag = f"{node['type']}_{node['name'].replace(' ', '_')}"
            if node_tag == self.selected_node:
                portrait_path = node["data"].get("Portrait", "")
                break
        if portrait_path and os.path.exists(portrait_path):
            self.display_portrait_on_fire_tv(portrait_path)
        else:
            messagebox.showerror("Error", "No valid portrait found for this NPC.")


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
    def load_portrait(self, portrait_path, node_tag):
        """
        Loads a portrait from portrait_path using the new Pillow resampling method.
        Returns a tuple (portrait_image, (width, height)). If loading fails, returns (None, (0,0)).
        """
        if not portrait_path or not os.path.exists(portrait_path):
            return None, (0, 0)
        try:
            img = Image.open(portrait_path)
            # Use the new Pillow constant; fallback if needed.
            resample_method = getattr(Image, "Resampling", Image).LANCZOS
            img.thumbnail(MAX_PORTRAIT_SIZE, resample_method)
            portrait_image = ImageTk.PhotoImage(img, master=self.canvas)
            self.node_images[node_tag] = portrait_image  # persist the image
            return portrait_image, img.size
        except Exception as e:
            print(f"Error loading portrait for {node_tag}: {e}")
            return None, (0, 0)

    def draw_nodes(self):
        """
        Draw nodes with dynamic sizing based on text content.
        For NPC nodes, if a portrait is available, it is shown on the left,
        with the text wrapped to the right.
        """
        MAX_TEXT_WIDTH = 200            # Maximum width for text area (in pixels)
        PAD_X = 10                      # Horizontal padding inside the rectangle
        PAD_Y = 10                      # Vertical padding inside the rectangle
        GAP = 5                         # Gap between portrait and text
        portrait_image = None

        # Helper to measure wrapped text size.
        def measure_wrapped_text(text, font_obj, wrap_width):
            temp_id = self.canvas.create_text(
                0, 0,
                text=text,
                font=font_obj,
                width=wrap_width,
                anchor="nw",
                justify="center",
                tags=("temp_measure",)
            )
            bbox = self.canvas.bbox(temp_id)
            self.canvas.delete(temp_id)
            if bbox is None:
                return (0, 0)
            x1, y1, x2, y2 = bbox
            return (x2 - x1, y2 - y1)

        for node in self.graph["nodes"]:
            node_type = node["type"]
            node_name = node["name"]
            x, y = node["x"], node["y"]
            color = node.get("color", "lightgray")
            node_tag = f"{node_type}_{node_name.replace(' ', '_')}"

            # For scenario nodes, use Summary; for others, use Description.
            if node_type == "scenario":
                raw_text = node["data"].get("Summary", "")
            else:
                raw_text = node["data"].get("Description", "")

            # Prepare a font; if raw_text is a dict, extract formatting.
            if isinstance(raw_text, dict):
                display_text = raw_text.get("text", "")
                formatting = raw_text.get("formatting", {})
                weight = "bold" if formatting.get("bold") else "normal"
                slant = "italic" if formatting.get("italic") else "roman"
                underline = 1 if formatting.get("underline") else 0
                text_font = tkFont.Font(family="Arial", size=9, weight=weight, slant=slant, underline=underline)
            else:
                display_text = str(raw_text)
                text_font = tkFont.Font(family="Arial", size=9)

            combined_text = f"{node_name}\n{display_text}"

            if node_type == "npc":
                # For NPCs, check for a portrait.
                portrait_path = node["data"].get("Portrait", "")
                # Reuse a loaded image if available.
                if node_tag in self.node_images:
                    portrait_image = self.node_images[node_tag]
                    portrait_width = portrait_image.width()
                    portrait_height = portrait_image.height()
                else:
                    portrait_image, (portrait_width, portrait_height) = self.load_portrait(portrait_path, node_tag)
                if portrait_width > 0:
                    wrap_width = MAX_TEXT_WIDTH - portrait_width - GAP - 2 * PAD_X
                else:
                    wrap_width = MAX_TEXT_WIDTH - 2 * PAD_X
                text_width, text_height = measure_wrapped_text(combined_text, text_font, wrap_width)
                node_width = (portrait_width + GAP if portrait_width > 0 else 0) + text_width + 2 * PAD_X
                node_height = max(portrait_height, text_height) + 2 * PAD_Y
            else:
                wrap_width = MAX_TEXT_WIDTH - 2 * PAD_X
                text_width, text_height = measure_wrapped_text(combined_text, text_font, wrap_width)
                node_width = text_width + 2 * PAD_X
                node_height = text_height + 2 * PAD_Y

            left = x - (node_width / 2)
            top = y - (node_height / 2)
            right = x + (node_width / 2)
            bottom = y + (node_height / 2)

            rect_id = self.canvas.create_rectangle(
                left, top, right, bottom,
                fill=color, outline="black", width=2,
                tags=("node", node_tag)
            )
            self.node_rectangles[node_tag] = rect_id

            if node_type == "npc" and portrait_width > 0:
                # Draw portrait on the left.
                image_x = left + PAD_X + (portrait_width / 2)
                image_y = top + PAD_Y + (portrait_height / 2)
                self.canvas.create_image(
                    image_x, image_y,
                    image=portrait_image,
                    anchor="center",
                    tags=("node", node_tag)
                )
                # Draw text to the right.
                text_x = left + PAD_X + portrait_width + GAP
                text_y = top + PAD_Y
                self.canvas.create_text(
                    text_x, text_y,
                    text=combined_text,
                    font=text_font,
                    width=wrap_width,
                    anchor="nw",
                    justify="center",
                    tags=("node", node_tag)
                )
            else:
                text_x = left + PAD_X
                text_y = top + PAD_Y
                self.canvas.create_text(
                    text_x, text_y,
                    text=combined_text,
                    font=text_font,
                    width=wrap_width,
                    anchor="nw",
                    justify="center",
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
    # Then, update your show_node_menu method to include the new command for NPC nodes:
    def show_node_menu(self, x, y):
        node_menu = Menu(self.canvas, tearoff=0)
        node_menu.add_command(label="Delete Node", command=self.delete_node)
        node_menu.add_separator()
        node_menu.add_command(label="Change Color", command=lambda: self.show_color_menu(x, y))
        # If the selected node is an NPC, add a command to display its portrait on Fire TV.
        if self.selected_node and self.selected_node.startswith("npc_"):
            node_menu.add_command(label="Display Portrait", command=self.display_on_fire_tv)
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
    def get_state(self):
        # Capture both the graph structure and the node positions.
        return {
            "graph": self.graph,
            "node_positions": self.node_positions,
            # You might also want to preserve other runtime state if needed.
        }

    def set_state(self, state):
        self.graph = state.get("graph", {})
        self.node_positions = state.get("node_positions", {})
        # Redraw the graph with the restored state.
        self.draw_graph()