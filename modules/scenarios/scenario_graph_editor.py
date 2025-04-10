import json
import math
import customtkinter as ctk
import tkinter.font as tkFont
import re

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
import os, ctypes
from ctypes import wintypes
from modules.generic.entity_detail_factory import create_entity_detail_frame, open_entity_window
from modules.helpers.config_helper import ConfigHelper
from modules.helpers.text_helpers import format_longtext

PORTRAIT_FOLDER = "assets/portraits"
MAX_PORTRAIT_SIZE = (64, 64)
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
logging.basicConfig(level=logging.DEBUG)

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

# A helper function to remove basic RTF formatting flags.
def clean_longtext(data, max_length=2000):
    # First, get the plain text using your existing helper.
    text = format_longtext(data, max_length)
    # Remove curly braces.
    text = re.sub(r'[{}]', '', text)
    # Remove backslash control words (simple approach).
    text = re.sub(r'\\[a-zA-Z]+\s?', '', text)
    return text.strip()

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
        self.node_images = {}  # Prevent garbage collection of PhotoImage objects

        # Preload NPC and Place data for quick lookup.
        self.npcs = {npc["Name"]: npc for npc in self.npc_wrapper.load_items()}
        self.places = {pl["Name"]: pl for pl in self.place_wrapper.load_items()}

        self.scenario = None

        # Graph structure.
        self.graph = {"nodes": [], "links": []}
        self.node_positions = {}   # Maps node_tag -> (x, y)
        self.node_rectangles = {}  # Maps node_tag -> rectangle_id
        self.selected_node = None
        self.selected_items = []
        self.drag_start = None

        self.init_toolbar()

        # Create canvas with scrollbars.
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

        # Global mouse events.
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

    def init_toolbar(self):
        toolbar = ctk.CTkFrame(self)
        toolbar.pack(fill="x", padx=5, pady=5)
        ctk.CTkButton(toolbar, text="Select Scenario", command=self.select_scenario).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Save Graph", command=self.save_graph).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Load Graph", command=self.load_graph).pack(side="left", padx=5)

    def select_scenario(self):
        scenario_template = load_template("scenarios")
        def on_scenario_selected(scenario_data):
            self.load_scenario(scenario_data)
        dialog = EntitySelectionDialog(
            self, "Scenarios", self.scenario_wrapper, scenario_template, on_scenario_selected
        )
        dialog.wait_window()

    def display_portrait_window(self):
        logging.debug("Entering display_portrait_window")
        if not self.selected_node or not self.selected_node.startswith("npc_"):
            messagebox.showerror("Error", "No NPC selected.")
            return

        npc_name = self.selected_node.replace("npc_", "").replace("_", " ")
        logging.debug(f"Extracted NPC name: {npc_name}")
        npc_data = self.npcs.get(npc_name)
        if not npc_data:
            messagebox.showerror("Error", f"NPC '{npc_name}' not found.")
            return

        portrait_path = npc_data.get("Portrait", "")
        if not portrait_path or not os.path.exists(portrait_path):
            messagebox.showerror("Error", "No valid portrait found for this NPC.")
            return

        try:
            img = Image.open(portrait_path)
        except Exception as e:
            messagebox.showerror("Error", f"Error loading portrait: {e}")
            return

        monitors = get_monitors()
        target_monitor = monitors[1] if len(monitors) > 1 else monitors[0]
        screen_x, screen_y, screen_width, screen_height = target_monitor
        img_width, img_height = img.size
        scale = min(screen_width / img_width, screen_height / img_height, 1)
        new_size = (int(img_width * scale), int(img_height * scale))
        if scale < 1:
            resample_method = getattr(Image, "Resampling", Image).LANCZOS
            img = img.resize(new_size, resample_method)

        win = ctk.CTkToplevel(self)
        win.title(npc_name)
        win.geometry(f"{screen_width}x{screen_height}+{screen_x}+{screen_y}")
        win.update_idletasks()

        portrait_img = ImageTk.PhotoImage(img, master=win)
        self.node_images[f"window_{npc_name}"] = portrait_img

        content_frame = tk.Frame(win, bg="white")
        content_frame.pack(fill="both", expand=True)
        name_label = tk.Label(content_frame, text=npc_name,
                            font=("Arial", 40, "bold"),
                            fg="white", bg="white")
        name_label.pack(pady=20)
        image_label = tk.Label(content_frame, image=portrait_img, bg="#2B2B2B")
        image_label.image = portrait_img
        image_label.pack(expand=True)

        new_x = screen_x
        win.geometry(f"{screen_width}x{screen_height}+{new_x}+{screen_y}")
        win.bind("<Button-1>", lambda e: win.destroy())

    def load_scenario(self, scenario):
        # Use full text; no truncation—wrapping will be handled by canvas.
        summary = scenario.get("Summary", "")
        # Clean RTF flags using clean_longtext if needed.
        summary = clean_longtext(summary, max_length=5000)
        self.scenario = scenario
        self.graph = {"nodes": [], "links": []}
        self.node_positions.clear()

        center_x, center_y = 400, 300
        scenario_title = scenario.get("Title", "No Title")
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

        # NPC nodes
        npcs_list = scenario.get("NPCs", [])
        npcs_count = len(npcs_list)
        if npcs_count > 0:
            arc_start_npcs = 30
            arc_end_npcs = 150
            offset_npcs = 350

            for i, npc_name in enumerate(npcs_list):
                if npc_name not in self.npcs:
                    continue
                angle_deg = (arc_start_npcs if npcs_count == 1
                            else arc_start_npcs + i * (arc_end_npcs - arc_start_npcs) / (npcs_count - 1))
                angle_rad = math.radians(angle_deg)
                x = center_x + offset_npcs * math.cos(angle_rad)
                y = center_y + offset_npcs * math.sin(angle_rad)
                npc_data = self.npcs[npc_name]
                desc = npc_data.get("Description", "")
                desc = clean_longtext(desc, max_length=5000)
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

        # Place nodes
        places_list = scenario.get("Places", [])
        places_count = len(places_list)
        if places_count > 0:
            arc_start_places = 210
            arc_end_places = 330
            offset_places = 350

            for j, place_name in enumerate(places_list):
                if place_name not in self.places:
                    continue
                angle_deg = (arc_start_places if places_count == 1
                            else arc_start_places + j * (arc_end_places - arc_start_places) / (places_count - 1))
                angle_rad = math.radians(angle_deg)
                x = center_x + offset_places * math.cos(angle_rad)
                y = center_y + offset_places * math.sin(angle_rad)
                place_data = self.places[place_name]
                pd = place_data.get("Description", "")
                pd = clean_longtext(pd, max_length=5000)
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

    def load_portrait(self, portrait_path, node_tag):
        if not portrait_path or not os.path.exists(portrait_path):
            return None, (0, 0)
        try:
            img = Image.open(portrait_path)
            resample_method = getattr(Image, "Resampling", Image).LANCZOS
            img.thumbnail(MAX_PORTRAIT_SIZE, resample_method)
            portrait_image = ImageTk.PhotoImage(img, master=self.canvas)
            self.node_images[node_tag] = portrait_image
            return portrait_image, img.size
        except Exception as e:
            print(f"Error loading portrait for {node_tag}: {e}")
            return None, (0, 0)

    def draw_nodes(self):
        node_png_path = os.path.join("assets", "scenario_node.png")
        # For scenario/place nodes, use a larger wrap width; NPC nodes use a smaller wrap.
        MAX_OVERLAY_WIDTH = 300
        MAX_OVERLAY_HEIGHT = 250
        NPC_TEXT_WRAP = 120
        GAP = 5
        PAD = 10

        default_colors = {
            "scenario": "darkolivegreen",
            "npc": "darkslateblue",
            "place": "sienna"
        }

        if not hasattr(self, "node_bboxes"):
            self.node_bboxes = {}
        else:
            self.node_bboxes.clear()

        def measure_text_height(text, font_obj, wrap_width):
            temp_id = self.canvas.create_text(0, 0, text=text, font=font_obj, width=wrap_width, anchor="nw")
            bbox = self.canvas.bbox(temp_id)
            self.canvas.delete(temp_id)
            if bbox:
                return bbox[3] - bbox[1]
            return 0

        for node in self.graph["nodes"]:
            node_type = node["type"]
            node_name = node["name"]
            x, y = node["x"], node["y"]
            color = node.get("color", default_colors.get(node_type, "darkslategray"))
            node_tag = f"{node_type}_{node_name.replace(' ', '_')}"

            # Split text: title is node name (bold), body is Summary (scenario) or Description (others)
            title_text = node_name
            if node_type == "scenario":
                body_text = node["data"].get("Summary", "")
                wrap_width = MAX_OVERLAY_WIDTH - 2 * PAD
            elif node_type == "place":
                body_text = node["data"].get("Description", "")
                wrap_width = MAX_OVERLAY_WIDTH - 2 * PAD
            else:
                body_text = node["data"].get("Description", "")
                wrap_width = NPC_TEXT_WRAP

            title_font = tkFont.Font(family="Arial", size=10, weight="bold")
            body_font = tkFont.Font(family="Arial", size=9)

            title_h = measure_text_height(title_text, title_font, wrap_width)
            body_h = measure_text_height(body_text, body_font, wrap_width)
            gap_between = 4
            total_text_height = title_h + gap_between + body_h

            portrait = None
            p_w = p_h = 0
            if node_type == "npc":
                portrait, (p_w, p_h) = self.load_portrait(node["data"].get("Portrait", ""), node_tag)

            if node_type == "npc" and portrait and p_w > 0:
                desired_width = p_w + GAP + NPC_TEXT_WRAP + 2 * PAD
                desired_height = max(p_h, total_text_height) + 2 * PAD
            else:
                desired_width = max((wrap_width + 2 * PAD), MAX_OVERLAY_WIDTH)
                desired_height = max(total_text_height + 2 * PAD, MAX_OVERLAY_HEIGHT)

            try:
                overlay_img = Image.open(node_png_path)
                overlay_img = overlay_img.resize((int(desired_width), int(desired_height)), Image.Resampling.LANCZOS)
            except Exception as e:
                print(f"Error loading overlay: {e}")
                overlay_img = None

            left = x - (desired_width / 2)
            top = y - (desired_height / 2)
            right = x + (desired_width / 2)
            bottom = y + (desired_height / 2)

            rect_id = self.canvas.create_rectangle(
                left, top, right, bottom,
                fill=color, outline="", width=0,
                tags=("node", node_tag)
            )
            self.node_rectangles[node_tag] = rect_id

            if overlay_img:
                overlay_photo = ImageTk.PhotoImage(overlay_img, master=self.canvas)
                if not hasattr(self, "node_holder_images"):
                    self.node_holder_images = {}
                self.node_holder_images[node_tag] = overlay_photo
                self.canvas.create_image(x, y, image=overlay_photo, tags=("node", node_tag))

            if node_type == "npc" and portrait and p_w > 0:
                portrait_x = left + PAD + (p_w / 2)
                portrait_y = y
                self.canvas.create_image(
                    portrait_x, portrait_y,
                    image=portrait,
                    anchor="center",
                    tags=("node", node_tag)
                )
                text_area_x = left + PAD + p_w + GAP
                text_area_width = desired_width - (p_w + GAP + 2 * PAD)
                content_top = y - (total_text_height / 2)
                self.canvas.create_text(
                    text_area_x + text_area_width / 2,
                    content_top + title_h / 2,
                    text=title_text,
                    font=title_font,
                    fill="white",
                    width=text_area_width,
                    anchor="center",
                    tags=("node", node_tag)
                )
                self.canvas.create_text(
                    text_area_x + text_area_width / 2,
                    content_top + title_h + gap_between + body_h / 2,
                    text=body_text,
                    font=body_font,
                    fill="white",
                    width=text_area_width,
                    anchor="center",
                    tags=("node", node_tag)
                )
            else:
                content_top = y - (total_text_height / 2)
                self.canvas.create_text(
                    x, content_top + title_h / 2,
                    text=title_text,
                    font=title_font,
                    fill="white",
                    width=wrap_width,
                    anchor="center",
                    tags=("node", node_tag)
                )
                self.canvas.create_text(
                    x, content_top + title_h + gap_between + body_h / 2,
                    text=body_text,
                    font=body_font,
                    fill="white",
                    width=wrap_width,
                    anchor="center",
                    tags=("node", node_tag)
                )

            self.node_bboxes[node_tag] = (left, top, right, bottom)

    def draw_links(self):
        for link in self.graph["links"]:
            self.draw_one_link(link)
        self.canvas.tag_lower("link")

    def draw_one_link(self, link):
        tag_from = link["from"]
        tag_to = link["to"]
        x1, y1 = self.node_positions.get(tag_from, (0, 0))
        x2, y2 = self.node_positions.get(tag_to, (0, 0))
        line_id = self.canvas.create_line(
            x1, y1, x2, y2, fill="black", width=2, tags=("link",)
        )
        self.canvas.tag_lower(line_id)

    def start_drag(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        items = self.canvas.find_closest(x, y)
        if not items:
            return
        item_id = items[0]
        tags = self.canvas.gettags(item_id)
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
                GenericEditorWindow(None, self.scenario, scenario_template, self.scenario_wrapper, True)
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
            detail_frame = create_entity_detail_frame(entity_type, entity, master=win, open_entity_callback=open_entity_window)
            detail_frame.pack(fill="both", expand=True)

    def on_right_click(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        items = self.canvas.find_closest(x, y)
        if not items:
            return
        item_id = items[0]
        tags = self.canvas.gettags(item_id)
        if "link" in tags:
            return
        node_tag = next((t for t in tags if t.startswith("scenario_")
                        or t.startswith("npc_")
                        or t.startswith("place_")), None)
        if node_tag:
            self.selected_node = node_tag
            self.show_node_menu(x, y)

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
        self.graph["nodes"] = [n for n in self.graph["nodes"] if n["name"] != node_name]
        self.graph["links"] = [l for l in self.graph["links"]
                            if l["from"] != self.selected_node and l["to"] != self.selected_node]
        if self.selected_node in self.node_positions:
            del self.node_positions[self.selected_node]
        self.draw_graph()

    def save_graph(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json")
        if file_path:
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
        return {
            "graph": self.graph,
            "node_positions": self.node_positions,
        }

    def set_state(self, state):
        self.graph = state.get("graph", {})
        self.node_positions = state.get("node_positions", {})
        self.draw_graph()