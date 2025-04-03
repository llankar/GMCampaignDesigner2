import json
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
from customtkinter import CTkImage
import logging
from screeninfo import get_monitors
import tkinter as tk  # standard tkinter
import os, logging, ctypes
from ctypes import wintypes
from modules.generic.entity_detail_factory import create_entity_detail_frame, open_entity_window
from modules.helpers.config_helper import ConfigHelper
from modules.helpers.text_helpers import format_longtext          

PORTRAIT_FOLDER = "assets/portraits"
MAX_PORTRAIT_SIZE = (64, 64)
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Helper function to get monitor information using ctypes and Windows API.
def get_monitors():
    monitors = []
    def monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
        rect = lprcMonitor.contents
        monitors.append((rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top))
        return True
    MonitorEnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL,
                                          wintypes.HMONITOR,
                                          wintypes.HDC,
                                          ctypes.POINTER(wintypes.RECT),
                                          wintypes.LPARAM)
    ctypes.windll.user32.EnumDisplayMonitors(0, 0, MonitorEnumProc(monitor_enum_proc), 0)
    return monitors
logging.basicConfig(level=logging.DEBUG)

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
        self.node_bboxes = {}
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
        self.canvas = ctk.CTkCanvas(self.canvas_frame, bg="#2B2B2B", highlightthickness=0)
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
    
    def display_portrait_window(self):
        """Display the NPC's portrait in a normal window (with decorations) that is
        sized and positioned to cover the second monitor (if available).
        Then, move the window 1920 pixels to the right.
        """
        logging.debug("Entering display_portrait_window")
        
        # Check if a valid NPC is selected.
        if not self.selected_node or not self.selected_node.startswith("npc_"):
            messagebox.showerror("Error", "No NPC selected.")
            logging.error("No NPC selected.")
            return

        # Extract NPC name from the node tag.
        npc_name = self.selected_node.replace("npc_", "").replace("_", " ")
        logging.debug(f"Extracted NPC name: {npc_name}")

        npc_data = self.npcs.get(npc_name)
        if not npc_data:
            messagebox.showerror("Error", f"NPC '{npc_name}' not found.")
            logging.error(f"NPC '{npc_name}' not found.")
            return

        portrait_path = npc_data.get("Portrait", "")
        logging.debug(f"Portrait path: {portrait_path}")
        if not portrait_path or not os.path.exists(portrait_path):
            messagebox.showerror("Error", "No valid portrait found for this NPC.")
            logging.error("No valid portrait found.")
            return

        try:
            img = Image.open(portrait_path)
            logging.debug(f"Image opened successfully, original size: {img.size}")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading portrait: {e}")
            logging.exception("Error loading portrait:")
            return

        # Obtain monitor information using ctypes.
        monitors = get_monitors()
        logging.debug("Detected monitors: " + str(monitors))
        if len(monitors) > 1:
            target_monitor = monitors[1]
            logging.debug(f"Using second monitor: {target_monitor}")
        else:
            target_monitor = monitors[0]
            logging.debug("Only one monitor available; using primary monitor.")

        screen_x, screen_y, screen_width, screen_height = target_monitor
        logging.debug(f"Target screen: ({screen_x}, {screen_y}, {screen_width}, {screen_height})")

        # Scale the image if it's larger than the monitor dimensions (without upscaling).
        img_width, img_height = img.size
        scale = min(screen_width / img_width, screen_height / img_height, 1)
        new_size = (int(img_width * scale), int(img_height * scale))
        logging.debug(f"Scaling factor: {scale}, new image size: {new_size}")
        if scale < 1:
            resample_method = getattr(Image, "Resampling", Image).LANCZOS
            img = img.resize(new_size, resample_method)
            logging.debug("Image resized.")
        else:
            logging.debug("No resizing needed.")

        # Create a normal Toplevel window.
        win = ctk.CTkToplevel(self)
        win.title(npc_name)
        win.geometry(f"{screen_width}x{screen_height}+{screen_x}+{screen_y}")
        win.update_idletasks()
        logging.debug("Window created on target monitor with screen size.")

        # IMPORTANT: Pass the Toplevel window as the master for the PhotoImage.
        portrait_img = ImageTk.PhotoImage(img, master=win)
        # Persist the image reference to prevent garbage collection.
        self.node_images[f"window_{npc_name}"] = portrait_img

        # Create a frame with a black background to hold the content.
        content_frame = tk.Frame(win, bg="white")
        content_frame.pack(fill="both", expand=True)

        # Display the NPC name.
        name_label = tk.Label(content_frame, text=npc_name,
                            font=("Arial", 40, "bold"),
                            fg="white", bg="white")
        name_label.pack(pady=20)
        logging.debug("NPC name label created.")

        # Display the portrait image.
        image_label = tk.Label(content_frame, image=portrait_img, bg="#2B2B2B")
        image_label.image = portrait_img  # Persist reference
        image_label.pack(expand=True)
        logging.debug("Portrait image label created.")

        # Move the window 1920 pixels to the right.
        new_x = screen_x + 0 # 1920
        win.geometry(f"{screen_width}x{screen_height}+{new_x}+{screen_y}")
        logging.debug(f"Window moved 1920 pixels to the right: new x-coordinate is {new_x}")

        # Bind a click event to close the window.
        win.bind("<Button-1>", lambda e: win.destroy())
        logging.debug("Window displayed; waiting for click to close.")

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
        # Use the existing text helper to process the summary
        summary = format_longtext(summary)
        scenario_tag = f"scenario_{scenario_title.replace(' ', '_')}"
        self.graph["nodes"].append({
            "type": "scenario",
            "name": scenario_title,
            "x": center_x,
            "y": center_y,
            "color": "darkolivegreen",
            "data": {**scenario, "Summary": summary}
        })
        self.node_positions[scenario_tag] = (center_x, center_y)

        # --------------------
        # 1) NPC nodes on the top half (arc: 30° to 150°)
        # --------------------
        npcs_list = scenario.get("NPCs", [])
        npcs_count = len(npcs_list)
        if npcs_count > 0:
            arc_start_npcs = 30    # starting angle in degrees (upper right-ish)
            arc_end_npcs = 150     # ending angle in degrees (upper left-ish)
            offset_npcs = 350      # distance from the scenario node

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
                # Process NPC Description using your existing helper to remove RTF formatting.
                desc = npc_data.get("Description", "")
                desc = format_longtext(desc)
                npc_data["Description"] = desc
                npc_tag = f"npc_{npc_name.replace(' ', '_')}"
                self.graph["nodes"].append({
                    "type": "npc",
                    "name": npc_name,
                    "x": x,
                    "y": y,
                    "color": "darkslateblue",
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
            arc_end_places = 330    # ending angle in degrees (lower right)
            offset_places = 350     # distance from the scenario node

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
                # Process Place Description using the text helper.
                pd = place_data.get("Description", "")
                pd = format_longtext(pd)
                place_data["Description"] = pd
                place_tag = f"place_{place_name.replace(' ', '_')}"
                self.graph["nodes"].append({
                    "type": "place",
                    "name": place_name,
                    "x": x,
                    "y": y,
                    "color": "sienna",
                    "data": place_data
                })
                self.node_positions[place_tag] = (x, y)
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
        # Path to your custom overlay PNG
        node_png_path = os.path.join("assets", "scenario_node.png")
        # Maximum dimensions for overlay if needed
        MAX_OVERLAY_WIDTH = 200
        MAX_OVERLAY_HEIGHT = 200
        GAP = 5      # gap between portrait and text
        PAD = 10     # padding around content
        NPC_TEXT_WRAP = 120  # maximum width for text in NPC nodes

        # Define darker default colors for each node type:
        default_colors = {
            "scenario": "darkolivegreen",
            "npc": "darkslateblue",
            "place": "sienna"
        }

        # Ensure node_bboxes exists
        if not hasattr(self, "node_bboxes"):
            self.node_bboxes = {}
        else:
            self.node_bboxes.clear()

        for node in self.graph["nodes"]:
            node_type = node["type"]  # e.g., "scenario", "npc", "place"
            node_name = node["name"]
            x, y = node["x"], node["y"]

            # Use the node's color if set; otherwise, use the darker default for its type.
            color = node.get("color", default_colors.get(node_type, "darkslategray"))
            node_tag = f"{node_type}_{node_name.replace(' ', '_')}"

            # For text content, use 'Summary' for scenario nodes; otherwise, use 'Description'
            if node_type == "scenario":
                text_content = f"{node_name}\n{node['data'].get('Summary', '')}"
            else:
                text_content = f"{node_name}\n{node['data'].get('Description', '')}"

            # Create a text font; white text for contrast
            text_font = tkFont.Font(family="Arial", size=9, weight="bold")

            # Measure text size with a forced wrap width
            forced_wrap = NPC_TEXT_WRAP if node_type == "npc" else MAX_OVERLAY_WIDTH - 2 * PAD
            temp_id = self.canvas.create_text(0, 0, text=text_content, font=text_font, width=forced_wrap, anchor="nw")
            bbox = self.canvas.bbox(temp_id)
            self.canvas.delete(temp_id)
            if bbox:
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
            else:
                text_w, text_h = (80, 40)

            # For NPC nodes, load portrait if available
            portrait = None
            p_w = p_h = 0
            if node_type == "npc":
                portrait, (p_w, p_h) = self.load_portrait(node["data"].get("Portrait", ""), node_tag)

            # Determine desired dimensions:
            if node_type == "npc" and portrait and p_w > 0:
                # Node width = portrait width + GAP + text width + padding on both sides
                desired_width = p_w + GAP + text_w + 2 * PAD
                # Height is the max of portrait height or text height plus padding
                desired_height = max(p_h, text_h) + 2 * PAD
            else:
                # For non-NPC nodes or if no portrait, ensure a minimum size
                desired_width = max(text_w + 2 * PAD, MAX_OVERLAY_WIDTH)
                desired_height = max(text_h + 2 * PAD, MAX_OVERLAY_HEIGHT)

            # Load the overlay image and resize it to the desired dimensions.
            try:
                overlay_img = Image.open(node_png_path)
                overlay_img = overlay_img.resize((int(desired_width), int(desired_height)), Image.Resampling.LANCZOS)
            except Exception as e:
                print(f"Error loading overlay: {e}")
                overlay_img = None

            # Compute bounding box based on desired dimensions (centered at (x, y))
            left = x - (desired_width / 2)
            top = y - (desired_height / 2)
            right = x + (desired_width / 2)
            bottom = y + (desired_height / 2)

            # Draw a solid colored rectangle as the background (no border)
            rect_id = self.canvas.create_rectangle(
                left, top, right, bottom,
                fill=color, outline="", width=0,
                tags=("node", node_tag)
            )
            self.node_rectangles[node_tag] = rect_id

            # Draw the overlay image on top, if available
            if overlay_img:
                overlay_photo = ImageTk.PhotoImage(overlay_img, master=self.canvas)
                if not hasattr(self, "node_holder_images"):
                    self.node_holder_images = {}
                self.node_holder_images[node_tag] = overlay_photo
                self.canvas.create_image(x, y, image=overlay_photo, tags=("node", node_tag))

            # Draw node content:
            if node_type == "npc" and portrait and p_w > 0:
                # Draw the portrait on the left.
                portrait_x = left + PAD + (p_w / 2)
                portrait_y = y  # vertically centered
                self.canvas.create_image(
                    portrait_x, portrait_y,
                    image=portrait,
                    anchor="center",
                    tags=("node", node_tag)
                )
                # Draw the text to the right of the portrait.
                text_x = portrait_x + (p_w / 2) + GAP + (text_w / 2)
                self.canvas.create_text(
                    text_x, y,
                    text=text_content,
                    font=text_font,
                    fill="white",
                    width=forced_wrap,
                    anchor="center",
                    tags=("node", node_tag)
                )
            else:
                # For scenario or place nodes (or NPC nodes without portrait), center the text.
                self.canvas.create_text(
                    x, y,
                    text=text_content,
                    font=text_font,
                    fill="white",
                    width=desired_width - 2 * PAD,
                    anchor="center",
                    tags=("node", node_tag)
                )

            # Save the node bounding box for link calculations.
            self.node_bboxes[node_tag] = (left, top, right, bottom)




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
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        items = self.canvas.find_closest(x, y)
        if not items:
            return
        item_id = items[0]
        tags = self.canvas.gettags(item_id)
        if "link" in tags:
            return

        node_tag = None
        for t in tags:
            if t.startswith("scenario_") or t.startswith("npc_") or t.startswith("place_"):
                node_tag = t
                break
        if not node_tag:
            return

        if node_tag.startswith("scenario_"):
            scenario_template = load_template("scenarios")
            if self.scenario:
                GenericEditorWindow(None, self.scenario, scenario_template)
        else:
            if node_tag.startswith("npc_"):
                entity_type = "NPCs"
                entity_name = node_tag.replace("npc_", "").replace("_", " ")
                entity = self.npcs.get(entity_name)
                template_path = "npcs/npcs_template.json"
            elif node_tag.startswith("place_"):
                entity_type = "Places"
                entity_name = node_tag.replace("place_", "").replace("_", " ")
                entity = self.places.get(entity_name)
                template_path = "places/places_template.json"
            elif node_tag.startswith("faction_"):
                entity_type = "Factions"
                entity_name = node_tag.replace("faction_", "").replace("_", " ")
                entity = self.factions.get(entity_name)
                template_path = "factions/factions_template.json"
            else:
                return

            if not entity:
                messagebox.showerror("Error", f"{entity_type[:-1]} '{entity_name}' not found.")
                return

            import tkinter as tk
            win = tk.Toplevel(self)
            win.title(entity_name)
            # Import the factory function.
            # Pass your actual open_entity_tab callback if available; otherwise, None.
            detail_frame = create_entity_detail_frame(entity_type, entity, master=win, open_entity_callback=open_entity_window)
            detail_frame.pack(fill="both", expand=True)





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
        if self.selected_node and self.selected_node.startswith("npc_"):
            node_menu.add_command(label="Display Portrait", command=self.display_portrait_window)
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