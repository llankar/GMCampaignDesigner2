import json
import os
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk, Menu
from PIL import Image, ImageTk
from modules.generic.generic_list_selection_view import GenericListSelectionView
from modules.helpers.template_loader import load_template
from modules.generic.generic_model_wrapper import GenericModelWrapper
import math
#import logging
from screeninfo import get_monitors
from modules.npcs import npc_opener
import tkinter as tk  # standard tkinter
from PIL import Image, ImageTk
import os, ctypes
from ctypes import wintypes


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
#logging.basicConfig(level=logging.ERROR)

# Constants for portrait folder and max portrait size
PORTRAIT_FOLDER = "assets/portraits"
MAX_PORTRAIT_SIZE = (64, 64)

# ─────────────────────────────────────────────────────────────────────────
# CLASS: NPCGraphEditor
# A custom graph editor for NPCs and factions using CustomTkinter.
# Supports adding nodes, links, dragging, context menus, and saving/loading.
# ─────────────────────────────────────────────────────────────────────────
class NPCGraphEditor(ctk.CTkFrame):
    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: __init__
    # Initializes the editor, loads NPC data, sets up graph structures, canvas, 
    # scrollbars, and event bindings.
    # ─────────────────────────────────────────────────────────────────────────
    def __init__(self, master, npc_wrapper: GenericModelWrapper, faction_wrapper: GenericModelWrapper, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.selected_shape = None
        self.link_canvas_ids = {}
        self.npc_wrapper = npc_wrapper
        self.faction_wrapper = faction_wrapper
        self.npcs = {npc["Name"]: npc for npc in self.npc_wrapper.load_items()}
        
        # Graph structure to hold nodes and links
        self.graph = {
            "nodes": [],
            "links": [],
            "shapes": []  # 
        }
        self.shapes = {}  # this is for managing shape canvas objects
        self.shape_counter = 0  # if not already added

        # Dictionaries for node data
        self.node_positions = {}  # Current (x, y) positions of nodes
        self.node_images = {}     # Loaded images for node portraits
        self.node_rectangles = {} # Canvas rectangle IDs (for color changes)
        self.node_bboxes = {}     # Bounding boxes for nodes (used for arrow offsets)
        self.shape_counter = 0  # For unique shape tags

        # Variables for selection and dragging
        self.selected_node = None
        self.selected_items = []  # All canvas items belonging to the selected node
        self.drag_start = None    # Starting point for dragging
        self.selected_link = None # Currently selected link for context menus
        
        # Initialize the toolbar and canvas frame
        self.init_toolbar()
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
        
        # Bind mouse events for dragging and context menus
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<ButtonRelease-1>", self.end_drag)
        
        # Bind mouse wheel scrolling (Windows and Linux)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel_y)
        self.canvas.bind("<Shift-MouseWheel>", self._on_mousewheel_x)
        self.canvas.bind("<Button-4>", self._on_mousewheel_y)
        self.canvas.bind("<Button-5>", self._on_mousewheel_y)
        self.canvas.bind("<Shift-Button-4>", self._on_mousewheel_x)
        self.canvas.bind("<Shift-Button-5>", self._on_mousewheel_x)
    # Bind double-click on any NPC element to open the editor window
        self.canvas.bind("<Double-Button-1>", self.open_npc_editor)

 # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: open_npc_editor
    # Opens the Generic Editor Window for the clicked NPC.
    # ─────────────────────────────────────────────────────────────────────────
    def open_npc_editor(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        item = self.canvas.find_closest(x, y)
        if not item:
            return
        tags = self.canvas.gettags(item[0])
        npc_tag = next((t for t in tags if t.startswith("npc_")), None)
        if not npc_tag:
            return
        # Convert tag back to NPC name (assuming spaces were replaced with underscores)
        npc_name = npc_tag.replace("npc_", "").replace("_", " ")
        npc_item = self.npcs.get(npc_name)
        if not npc_item:
            messagebox.showerror("Error", f"NPC '{npc_name}' not found in data.")
            return
        print(f"Opening editor for NPC: {npc_name}")
        npc_opener.open_npc_editor_window(npc_name)
        # ─────────────────────────────────────────────────────────────────────────
    def display_portrait_window(self):
        """Display the NPC's portrait in a normal window (with decorations) that is
        sized and positioned to cover the second monitor (if available).  
        """
        #logging.debug("Entering display_portrait_window")
        
        # Check if a valid NPC is selected.
        if not self.selected_node or not self.selected_node.startswith("npc_"):
            messagebox.showerror("Error", "No NPC selected.")
           #logging.error("No NPC selected.")
            return

        # Extract NPC name from the node tag.
        npc_name = self.selected_node.replace("npc_", "").replace("_", " ")
       #logging.debug(f"Extracted NPC name: {npc_name}")

        npc_data = self.npcs.get(npc_name)
        if not npc_data:
            messagebox.showerror("Error", f"NPC '{npc_name}' not found.")
           #logging.error(f"NPC '{npc_name}' not found.")
            return

        portrait_path = npc_data.get("Portrait", "")
       #logging.debug(f"Portrait path: {portrait_path}")
        if not portrait_path or not os.path.exists(portrait_path):
            messagebox.showerror("Error", "No valid portrait found for this NPC.")
           #logging.error("No valid portrait found.")
            return

        try:
            img = Image.open(portrait_path)
           #logging.debug(f"Image opened successfully, original size: {img.size}")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading portrait: {e}")
           #logging.exception("Error loading portrait:")
            return

        # Obtain monitor information using ctypes.
        monitors = get_monitors()
       #logging.debug("Detected monitors: " + str(monitors))

        # Choose the second monitor if available; otherwise, use the primary monitor.
        if len(monitors) > 1:
            target_monitor = monitors[1]
           #logging.debug(f"Using second monitor: {target_monitor}")
        else:
            target_monitor = monitors[0]
           #logging.debug("Only one monitor available; using primary monitor.")

        screen_x, screen_y, screen_width, screen_height = target_monitor
       #logging.debug(f"Target screen: ({screen_x}, {screen_y}, {screen_width}, {screen_height})")

        # Scale the image if it's larger than the monitor dimensions (without upscaling).
        img_width, img_height = img.size
        scale = min(screen_width / img_width, screen_height / img_height, 1)
        new_size = (int(img_width * scale), int(img_height * scale))
       #logging.debug(f"Scaling factor: {scale}, new image size: {new_size}")
        if scale < 1:
            resample_method = getattr(Image, "Resampling", Image).LANCZOS
            img = img.resize(new_size, resample_method)
           #logging.debug("Image resized.")
        
        portrait_img = ImageTk.PhotoImage(img)
        # Persist the image reference to prevent garbage collection.
        self.node_images[f"window_{npc_name}"] = portrait_img

        # Create a normal Toplevel window (with standard window decorations).
        win = ctk.CTkToplevel(self)
        win.title(npc_name)
        # Set the window geometry to match the target monitor's dimensions and position.
        win.geometry(f"{screen_width}x{screen_height}+{screen_x}+{screen_y}")
        win.update_idletasks()
       #logging.debug("Window created on target monitor with screen size.")

        # Create a frame with a black background to hold the content.
        content_frame = tk.Frame(win, bg="white")
        content_frame.pack(fill="both", expand=True)

        # Add a label to display the NPC name.
        name_label = tk.Label(content_frame, text=npc_name,
                            font=("Arial", 40, "bold"),
                            fg="white", bg="white")
        name_label.pack(pady=20)
       #logging.debug("NPC name label created.")

        # Add a label to display the portrait image.
        image_label = tk.Label(content_frame, image=portrait_img, bg="white")
        image_label.image = portrait_img  # persist reference
        image_label.pack(expand=True)
       #logging.debug("Portrait image label created.")
        new_x = screen_x + 0 #1920
        win.geometry(f"{screen_width}x{screen_height}+{new_x}+{screen_y}")
       #logging.debug(f"Window moved 1920 pixels to the right: new x-coordinate is {new_x}")        
        # Bind a click event to close the window.
        win.bind("<Button-1>", lambda e: win.destroy())
       #logging.debug("Window displayed; waiting for click to close.")

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: _on_mousewheel_y
    # Scrolls the canvas vertically based on mouse wheel input.
    # ─────────────────────────────────────────────────────────────────────────
    def _on_mousewheel_y(self, event):
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")

    def get_state(self):
        return {
            "graph": self.graph.copy(),
            "node_positions": self.node_positions.copy(),
            # include any other state needed
        }

    def set_state(self, state):
        self.graph = state.get("graph", {}).copy()
        self.node_positions = state.get("node_positions", {}).copy()
        self.draw_graph()  # Refresh the drawing

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: _on_mousewheel_x
    # Scrolls the canvas horizontally based on mouse wheel input.
    # ─────────────────────────────────────────────────────────────────────────
    def _on_mousewheel_x(self, event):
        if event.num == 4 or event.delta > 0:
            self.canvas.xview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas.xview_scroll(1, "units")

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: init_toolbar
    # Creates a toolbar with buttons for adding NPCs, factions, saving, loading, and adding links.
    # ─────────────────────────────────────────────────────────────────────────
    def init_toolbar(self):
        toolbar = ctk.CTkFrame(self)
        toolbar.pack(fill="x", padx=5, pady=5)

        ctk.CTkButton(toolbar, text="Add NPC", command=self.add_npc).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Add Faction", command=self.add_faction).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Add Link", command=self.start_link_creation).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Save", command=self.save_graph).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Load", command=self.load_graph).pack(side="left", padx=5)

        # 🆕 Add Shape Buttons
        ctk.CTkButton(toolbar, text="Add Rectangle", command=lambda: self.add_shape("rectangle")).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Add Oval", command=lambda: self.add_shape("oval")).pack(side="left", padx=5)
        

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: start_link_creation
    # Temporarily rebinds left-click to select the first node for a new link.
    # ─────────────────────────────────────────────────────────────────────────
    def start_link_creation(self):
        self.canvas.bind("<Button-1>", self.select_first_node)

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: select_first_node
    # Selects the first node for a new link based on the nearest canvas item.
    # ─────────────────────────────────────────────────────────────────────────
    def select_first_node(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        item = self.canvas.find_closest(x, y)
        if not item:
            return
        tags = self.canvas.gettags(item[0])
        self.first_node = next((t for t in tags if t.startswith("npc_")), None)
        if self.first_node:
            self.canvas.bind("<Button-1>", self.select_second_node)

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: select_second_node
    # Selects the second node for a new link and then opens the link text dialog.
    # ─────────────────────────────────────────────────────────────────────────
    def select_second_node(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        item = self.canvas.find_closest(x, y)
        if not item:
            return
        tags = self.canvas.gettags(item[0])
        self.second_node = next((t for t in tags if t.startswith("npc_")), None)
        if self.second_node:
            self.canvas.unbind("<Button-1>")
            self.prompt_link_text()

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: prompt_link_text
    # Opens a dialog for the user to enter link text, then adds the link.
    # ─────────────────────────────────────────────────────────────────────────
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
            self.canvas.bind("<Button-1>", self.start_drag)
        ctk.CTkButton(dialog, text="Add Link", command=on_add_link).pack(pady=10)
        dialog.after(100, link_text_entry.focus_set)

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: add_link
    # Adds a new link between two nodes with the specified link text.
    # ─────────────────────────────────────────────────────────────────────────
    def add_link(self, tag1, tag2, link_text):
        if tag1 not in self.node_positions or tag2 not in self.node_positions:
            messagebox.showerror("Error", "One or both NPCs not found.")
            return
        npc_name1 = tag1.replace("npc_", "").replace("_", " ")
        npc_name2 = tag2.replace("npc_", "").replace("_", " ")
        self.graph["links"].append({
            "npc_name1": npc_name1,
            "npc_name2": npc_name2,
            "text": link_text,
            "arrow_mode": "both"  # Options: "none", "start", "end", "both"
        })
        self.draw_graph()

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: add_npc
    # Opens an NPC selection dialog and binds the next click to place the NPC.
    # ─────────────────────────────────────────────────────────────────────────
    def add_npc(self):
        def on_npc_selected(npc_name):
            # Lookup the full NPC dictionary using the npc wrapper.
            npc_list = self.npc_wrapper.load_items()
            selected_npc = None
            for npc in npc_list:
                if npc.get("Name") == npc_name:
                    selected_npc = npc
                    break
            if not selected_npc:
                messagebox.showerror("Error", f"NPC '{npc_name}' not found.")
                return
            self.pending_npc = selected_npc
            if dialog.winfo_exists():
                dialog.destroy()
            self.canvas.bind("<Button-1>", self.place_pending_npc)

        npc_template = load_template("npcs")
        dialog = ctk.CTkToplevel(self)
        dialog.title("Select NPC")
        dialog.geometry("1200x800")
        dialog.transient(self)
        dialog.grab_set()
        dialog.focus_force()
        # The new GenericListSelectionView returns the NPC name (string)
        selection_view = GenericListSelectionView(
            dialog,
            "NPCs",
            self.npc_wrapper,
            npc_template,
            on_select_callback=lambda et, npc: on_npc_selected(npc)
        )
        selection_view.pack(fill="both", expand=True)
        dialog.wait_window()




    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: place_pending_npc
    # Places the selected NPC at the mouse click location and updates the graph.
    # ─────────────────────────────────────────────────────────────────────────
    def place_pending_npc(self, event):
        npc_name = self.pending_npc["Name"]
        tag = f"npc_{npc_name.replace(' ', '_')}"
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.graph["nodes"].append({
            "npc_name": npc_name,
            "x": x,
            "y": y,
            "color": "#1D3572"
        })
        self.node_positions[tag] = (x, y)
        self.pending_npc = None
        self.canvas.unbind("<Button-1>")
        self.canvas.bind("<Button-1>", self.start_drag)
        self.draw_graph()

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: add_faction
    # Opens a faction selection dialog and adds all NPCs from the selected faction.
    # ─────────────────────────────────────────────────────────────────────────
    def add_faction(self):
        # Flatten factions from all NPCs.
        all_factions = []
        for npc in self.npcs.values():
            faction_value = npc.get("Factions")
            if not faction_value:
                continue
            if isinstance(faction_value, list):
                all_factions.extend(faction_value)
            else:
                all_factions.append(faction_value)
        factions = sorted(set(all_factions))
        if not factions:
            messagebox.showerror("Error", "No factions found in NPC data.")
            return

        # Wrap each faction string in a dictionary with a "Name" field.
        items = [{"Name": f} for f in factions]
        # Define a simple template for factions.
        template = {"fields": [{"name": "Name", "type": "text"}]}
        
        # Create a dummy model wrapper that returns our wrapped faction items.
        class DummyModelWrapper:
            def load_items(self):
                return items
        dummy_wrapper = DummyModelWrapper()

        # Define the callback.
        def on_faction_selected(faction_name):
            # Close the selection popup immediately.
            if selection_popup.winfo_exists():
                selection_popup.destroy()
            # Build a list of NPCs that have the selected faction.
            faction_npcs = []
            for npc in self.npcs.values():
                faction_value = npc.get("Factions")
                if not faction_value:
                    continue
                if isinstance(faction_value, list):
                    if faction_name in faction_value:
                        faction_npcs.append(npc)
                else:
                    if faction_value == faction_name:
                        faction_npcs.append(npc)
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
                self.graph["nodes"].append({
                    "npc_name": npc_name,
                    "x": x,
                    "y": y,
                    "color": "#1D3572"
                })
                self.node_positions[tag] = (x, y)
            self.draw_graph()

        # Create a new selection popup.
        selection_popup = ctk.CTkToplevel(self)
        selection_popup.title("Select Faction")
        selection_popup.geometry("1200x800")
        selection_popup.transient(self.winfo_toplevel())
        selection_popup.grab_set()
        selection_popup.focus_force()
        
        
        # Instantiate the selection view with our dummy wrapper.
        selection_view = GenericListSelectionView(
            selection_popup,
            "Factions",
            dummy_wrapper,
            template,
            on_select_callback=lambda et, faction: on_faction_selected(faction)
        )
        selection_view.pack(fill="both", expand=True)
        selection_popup.wait_window()

    def update_links_positions_for_node(self, node_tag):
        node_name = node_tag.replace("npc_", "").replace("_", " ")
        for link in self.graph["links"]:
            if node_name in (link["npc_name1"], link["npc_name2"]):
                key = (link["npc_name1"], link["npc_name2"])
                canvas_ids = self.link_canvas_ids.get(key)
                if canvas_ids:
                    tag1 = f"npc_{link['npc_name1'].replace(' ', '_')}"
                    tag2 = f"npc_{link['npc_name2'].replace(' ', '_')}"
                    x1, y1 = self.node_positions.get(tag1, (0, 0))
                    x2, y2 = self.node_positions.get(tag2, (0, 0))

                    # Update line coordinates directly
                    self.canvas.coords(canvas_ids["line"], x1, y1, x2, y2)

                    # Update text position
                    mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
                    self.canvas.coords(canvas_ids["text"], mid_x, mid_y)

                    # Delete old arrowheads
                    for arrow_id in canvas_ids["arrows"]:
                        self.canvas.delete(arrow_id)
                    canvas_ids["arrows"] = []

                    # Redraw arrowheads at new position
                    arrow_mode = link.get("arrow_mode", "end")
                    if arrow_mode in ("start", "both"):
                        arrow_id = self.draw_arrowhead(x1, y1, x2, y2, tag1)
                        canvas_ids["arrows"].append(arrow_id)
                    if arrow_mode in ("end", "both"):
                        arrow_id = self.draw_arrowhead(x2, y2, x1, y1, tag2)
                        canvas_ids["arrows"].append(arrow_id)

    
    def update_links_for_node(self, node_tag):
        # Delete only existing links and associated arrowheads/text
        self.canvas.delete("link")
        self.canvas.delete("arrowhead")
        self.canvas.delete("link_text")

        # Redraw only links involving the moved node
        node_name = node_tag.replace("npc_", "").replace("_", " ")
        affected_links = [
            link for link in self.graph["links"]
            if link["npc_name1"] == node_name or link["npc_name2"] == node_name
        ]
        for link in affected_links:
            self.draw_one_link(link)

        self.canvas.tag_lower("link")
        self.canvas.tag_raise("arrowhead")
        self.canvas.tag_raise("link_text")
    
    def delete_shape(self, tag):
        # Delete from canvas
        self.canvas.delete(tag)
        # Delete from internal storage
        if tag in self.shapes:
            del self.shapes[tag]
        self.graph["shapes"] = [s for s in self.graph["shapes"] if s["tag"] != tag]
    

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: on_right_click
    # Determines whether a link or node was right-clicked and displays the appropriate context menu.
    # ─────────────────────────────────────────────────────────────────────────
    def on_right_click(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        item = self.canvas.find_closest(x, y)
        if not item:
            return

        tags = self.canvas.gettags(item[0])
        if "link" in tags:
            self.show_link_menu(int(x), int(y))
            self.selected_link = self.get_link_by_position(x, y)
        elif any(tag.startswith("npc_") for tag in tags):
            self.selected_node = next((t for t in tags if t.startswith("npc_")), None)
            self.show_node_menu(x, y)
        elif any(tag.startswith("shape_") for tag in tags):
            shape_tag = next((t for t in tags if t.startswith("shape_")), None)
            if shape_tag:
                self.show_shape_menu(x, y, shape_tag)


    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: show_color_menu
    # Displays a color selection menu for changing the node color.
    # ─────────────────────────────────────────────────────────────────────────
    def show_color_menu(self, x, y):
        COLORS = [
            "red", "green", "blue", "yellow", "purple",
            "orange", "pink", "cyan", "magenta", "lightgray"
        ]
        color_menu = Menu(self.canvas, tearoff=0)
        for color in COLORS:
            color_menu.add_command(label=color, command=lambda c=color: self.change_node_color(c))
        color_menu.post(int(x), int(y))

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: show_link_menu
    # Displays a context menu for links with a submenu for arrow mode selection.
    # ─────────────────────────────────────────────────────────────────────────
    def show_link_menu(self, x, y):
        link_menu = Menu(self.canvas, tearoff=0)
        arrow_submenu = Menu(link_menu, tearoff=0)
        arrow_submenu.add_command(label="No Arrows", command=lambda: self.set_arrow_mode("none"))
        arrow_submenu.add_command(label="Arrow at Start", command=lambda: self.set_arrow_mode("start"))
        arrow_submenu.add_command(label="Arrow at End", command=lambda: self.set_arrow_mode("end"))
        arrow_submenu.add_command(label="Arrows at Both Ends", command=lambda: self.set_arrow_mode("both"))
        link_menu.add_cascade(label="Arrow Mode", menu=arrow_submenu)
        link_menu.post(x, y)

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: show_node_menu
    # Displays a context menu for nodes with options to delete the node or change its color.
    # ─────────────────────────────────────────────────────────────────────────
    def show_node_menu(self, x, y):
        node_menu = Menu(self.canvas, tearoff=0)
        node_menu.add_command(label="Delete Node", command=self.delete_node)
        node_menu.add_separator()
        node_menu.add_command(label="Change Color", command=lambda: self.show_color_menu(x, y))
        node_menu.add_command(label="Display Portrait Window", command=self.display_portrait_window)
        node_menu.post(int(x), int(y))

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: set_arrow_mode
    # Sets the arrow_mode for the currently selected link.
    # ─────────────────────────────────────────────────────────────────────────
    def set_arrow_mode(self, new_mode):
        if not self.selected_link:
            return
        for link in self.graph["links"]:
            if (link["npc_name1"] == self.selected_link["npc_name1"]
                    and link["npc_name2"] == self.selected_link["npc_name2"]):
                link["arrow_mode"] = new_mode
                break
        self.draw_graph()

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: delete_node
    # Deletes the currently selected node and removes any links involving it.
    # ─────────────────────────────────────────────────────────────────────────
    def delete_node(self):
        if not self.selected_node:
            return
        node_name = self.selected_node.replace("npc_", "").replace("_", " ")
        self.graph["nodes"] = [node for node in self.graph["nodes"] if node["npc_name"] != node_name]
        self.graph["links"] = [link for link in self.graph["links"]
                               if link["npc_name1"] != node_name and link["npc_name2"] != node_name]
        if self.selected_node in self.node_positions:
            del self.node_positions[self.selected_node]
        self.draw_graph()

    def redraw_after_drag(self):
        self.draw_graph()
        self._redraw_scheduled = False


    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: draw_nodes
    # Iterates over all nodes in the graph, draws their rectangles, portraits, and labels,
    # and calculates/stores their bounding boxes.
    # ─────────────────────────────────────────────────────────────────────────
    def draw_nodes(self):
        NODE_WIDTH = 150
        TEXT_LINE_HEIGHT = 20
        TEXT_PADDING = 10

        # Path to your node PNG file
        node_holder_path = os.path.join("assets", "npc_node.png")

        for node in self.graph["nodes"]:
            npc_name = node["npc_name"]
            tag = f"npc_{npc_name.replace(' ', '_')}"
            x, y = self.node_positions.get(tag, (node["x"], node["y"]))

            # NPC data
            npc_data = self.npcs.get(npc_name, {})
            role = npc_data.get("Role", "")

            # Handle Factions to avoid showing Python list/dict with braces
            faction_value = npc_data.get("Factions", "")
            if isinstance(faction_value, list):
                faction_text = ", ".join(str(f) for f in faction_value)
            elif isinstance(faction_value, (set, dict)):
                faction_text = ", ".join(str(f) for f in faction_value)
            else:
                faction_text = str(faction_value) if faction_value else ""

            # Build text lines: first is name, then role, then faction.
            lines = [npc_name, role, faction_text]
            # Filter out any empty strings
            lines = [line for line in lines if line.strip()]

            # Handle portrait if available
            portrait_path = npc_data.get("Portrait", "")
            has_portrait = portrait_path and os.path.exists(portrait_path)
            portrait_height = 0
            portrait_width = 0
            if has_portrait:
                img = Image.open(portrait_path)
                orig_w, orig_h = img.size
                max_portrait_width = NODE_WIDTH - 4
                max_portrait_height = 80
                ratio = min(max_portrait_width / orig_w, max_portrait_height / orig_h)
                portrait_width = int(orig_w * ratio)
                portrait_height = int(orig_h * ratio)
                img = img.resize((portrait_width, portrait_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.node_images[npc_name] = photo

            # Calculate node height based on portrait and text
            node_height = portrait_height + (len(lines) * TEXT_LINE_HEIGHT) + TEXT_PADDING + 20

            # Draw a colored rectangle as the background
            node_color = node.get("color", "#1D3572")
            rect_id = self.canvas.create_rectangle(
                x - NODE_WIDTH // 2, y - node_height // 2,
                x + NODE_WIDTH // 2, y + node_height // 2,
                fill=node_color,
                outline="",
                width=2,
                tags=(tag,)
            )
            self.node_rectangles[tag] = rect_id

            # Draw the PNG overlay if it exists
            if os.path.exists(node_holder_path):
                holder_img = Image.open(node_holder_path)
                holder_img = holder_img.resize((NODE_WIDTH, node_height), Image.Resampling.LANCZOS)
                holder_photo = ImageTk.PhotoImage(holder_img)
                if not hasattr(self, "node_holder_images"):
                    self.node_holder_images = {}
                self.node_holder_images[npc_name] = holder_photo
                self.canvas.create_image(x, y, image=holder_photo, tags=(tag,))

            # Store bounding box for link calculations
            left = x - (NODE_WIDTH // 2)
            top = y - (node_height // 2)
            right = x + (NODE_WIDTH // 2)
            bottom = y + (node_height // 2)
            self.node_bboxes[tag] = (left, top, right, bottom)

            # Determine vertical starting point
            current_y = top + TEXT_PADDING
            if has_portrait:
                portrait_center_y = current_y + (portrait_height // 2)
                self.canvas.create_image(x, portrait_center_y,
                                        image=self.node_images[npc_name],
                                        tags=(tag,))
                current_y += portrait_height + TEXT_PADDING

            # Draw each line of text separately.
            # The first line (name) is bold; others are normal.
            for i, line in enumerate(lines):
                if i == 0:
                    font = ("Arial", 9, "bold")
                else:
                    font = ("Arial", 9)
                self.canvas.create_text(
                    x, current_y + i * TEXT_LINE_HEIGHT,
                    text=line,
                    fill="white",
                    font=font,
                    tags=(tag,)
                )

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: draw_all_links
    # Iterates over all links in the graph and draws them, then lowers link elements behind nodes.
    # ─────────────────────────────────────────────────────────────────────────
    def draw_all_links(self):
        for link in self.graph["links"]:
            self.draw_one_link(link)
        self.canvas.tag_lower("link")

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: draw_one_link
    # Draws a single link between two nodes, including its arrowheads (if any) and text.
    # ─────────────────────────────────────────────────────────────────────────
    def draw_one_link(self, link):
        tag1 = f"npc_{link['npc_name1'].replace(' ', '_')}"
        tag2 = f"npc_{link['npc_name2'].replace(' ', '_')}"
        x1, y1 = self.node_positions.get(tag1, (0, 0))
        x2, y2 = self.node_positions.get(tag2, (0, 0))

        line_id = self.canvas.create_line(x1, y1, x2, y2, fill="#5BB8FF", tags=("link",))
        arrow_mode = link.get("arrow_mode", "end")

        arrow_ids = []
        if arrow_mode in ("start", "both"):
            arrow_ids.append(self.draw_arrowhead(x1, y1, x2, y2, tag1))
        if arrow_mode in ("end", "both"):
            arrow_ids.append(self.draw_arrowhead(x2, y2, x1, y1, tag2))

        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        text_id = self.canvas.create_text(mid_x, mid_y,
                                        text=link["text"],
                                        fill="white",
                                        font=("Arial", 10, "bold"),
                                        tags=("link_text",))

        # Store Canvas IDs clearly linked by npc pair
        key = (link["npc_name1"], link["npc_name2"])
        self.link_canvas_ids[key] = {
            "line": line_id,
            "arrows": arrow_ids,
            "text": text_id
        }


    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: draw_arrowhead
    # Draws a triangular arrowhead near a node, offset outside the node's bounding box.
    # ─────────────────────────────────────────────────────────────────────────
    def draw_arrowhead(self, start_x, start_y, end_x, end_y, node_tag):
        arrow_length = 10
        angle = math.atan2(end_y - start_y, end_x - start_x)
        left, top, right, bottom = self.node_bboxes.get(
            node_tag, (start_x - 50, start_y - 25, start_x + 50, start_y + 25)
        )
        half_w = (right - left) / 2
        half_h = (bottom - top) / 2
        node_radius = math.sqrt(half_w**2 + half_h**2)
        arrow_offset_extra = -20
        arrow_offset = node_radius + arrow_offset_extra
        arrow_apex_x = start_x + arrow_offset * math.cos(angle)
        arrow_apex_y = start_y + arrow_offset * math.sin(angle)

        # RETURN the polygon ID so it can be deleted later
        return self.canvas.create_polygon(
            arrow_apex_x, arrow_apex_y,
            arrow_apex_x + arrow_length * math.cos(angle + math.pi / 6),
            arrow_apex_y + arrow_length * math.sin(angle + math.pi / 6),
            arrow_apex_x + arrow_length * math.cos(angle - math.pi / 6),
            arrow_apex_y + arrow_length * math.sin(angle - math.pi / 6),
            fill="#5BB8FF",
            outline="white",
            tags=("link", "arrowhead")
    )


    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: save_graph
    # Updates node positions and saves the current graph (nodes and links) to a JSON file.
    # ─────────────────────────────────────────────────────────────────────────
    def save_graph(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json")
        if file_path:
            for node in self.graph["nodes"]:
                tag = f"npc_{node['npc_name'].replace(' ', '_')}"
                x, y = self.node_positions.get(tag, (node["x"], node["y"]))
                node["x"] = x
                node["y"] = y
            for link in self.graph["links"]:
                if "arrow_mode" not in link:
                    link["arrow_mode"] = "both"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.graph, f, indent=2)

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: load_graph
    # Loads a graph from a JSON file, rebuilds node positions, and sets default values.
    # ─────────────────────────────────────────────────────────────────────────
    def load_graph(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                self.graph = json.load(f)
            if "shapes" not in self.graph:
                self.graph["shapes"] = []
            
            # Reload node positions and links as before...
            self.node_positions = {
                f"npc_{n['npc_name'].replace(' ', '_')}": (n["x"], n["y"])
                for n in self.graph["nodes"]
            }
            for node in self.graph["nodes"]:
                # only default to blue if no color was saved
                node.setdefault("color", "#1D3572")
            for link in self.graph["links"]:
                link["arrow_mode"] = link.get("arrow_mode", "both")
            
            # Rebuild shapes from saved data.
            self.shapes.clear()
            # Sort shapes by their z-order so that lower ones are drawn first.
            shapes_sorted = sorted(self.graph.get("shapes", []), key=lambda s: s.get("z", 0))
            for shape in shapes_sorted:
                self.shapes[shape["tag"]] = shape
            
            # Update shape_counter so that new shapes will have unique tags.
            max_counter = -1
            for shape in self.graph["shapes"]:
                try:
                    # Assume tag format is "shape_<number>"
                    num = int(shape["tag"].split("_")[1])
                    if num > max_counter:
                        max_counter = num
                except (IndexError, ValueError):
                    pass
            self.shape_counter = max_counter + 1

            self.draw_graph()




    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: change_node_color
    # Changes the color of the currently selected node, updating both the canvas and the graph data.
    # ─────────────────────────────────────────────────────────────────────────
    def change_node_color(self, color):
        if self.selected_node:
            rect_id = self.node_rectangles[self.selected_node]
            self.canvas.itemconfig(rect_id, fill=color)
            for node in self.graph["nodes"]:
                if node["npc_name"] == self.selected_node.replace("npc_", "").replace("_", " "):
                    node["color"] = color
                    break
    def change_shape_color(self, tag, color):
        self.canvas.itemconfig(tag, fill=color)
        shape = self.shapes.get(tag)
        if shape:
            shape["color"] = color

    def show_shape_menu(self, x, y, shape_tag):
        shape_menu = Menu(self.canvas, tearoff=0)

        # Color submenu
        color_menu = Menu(shape_menu, tearoff=0)
        COLORS = [
            "red", "green", "blue", "yellow", "purple",
            "orange", "pink", "cyan", "magenta", "lightgray"
        ]
        for color in COLORS:
            color_menu.add_command(
                label=color,
                command=lambda c=color: self.change_shape_color(shape_tag, c)
            )

         # Add a Resize option
        shape_menu.add_cascade(label="Change Color", menu=color_menu)
        shape_menu.add_separator()
        shape_menu.add_command(label="Change shape size", command=lambda: self.activate_resize_mode(shape_tag))
        shape_menu.add_separator()
        shape_menu.add_command(label="Bring to Front", command=lambda: self.bring_to_front(shape_tag))
        shape_menu.add_command(label="Send to Back", command=lambda: self.send_to_back(shape_tag))  
        shape_menu.add_separator()
        shape_menu.add_command(label="Delete Shape", command=lambda: self.delete_shape(shape_tag))
        shape_menu.post(int(x), int(y))

    def bring_to_front(self, shape_tag):
        # Raise the shape on the canvas.
        self.canvas.tag_raise(shape_tag)
        shape = self.shapes.get(shape_tag)
        if shape:
            # Set the shape's z property to a value higher than all others.
            max_z = max((s.get("z", 0) for s in self.shapes.values()), default=0)
            shape["z"] = max_z + 1
            # Update the order in the graph's shapes list.
            self.graph["shapes"].sort(key=lambda s: s.get("z", 0))

    def send_to_back(self, shape_tag):
        # Lower the shape on the canvas.
        self.canvas.tag_lower(shape_tag)
        shape = self.shapes.get(shape_tag)
        if shape:
            # Set the shape's z property to a value lower than all others.
            min_z = min((s.get("z", 0) for s in self.shapes.values()), default=0)
            shape["z"] = min_z - 1
            self.graph["shapes"].sort(key=lambda s: s.get("z", 0))

    def activate_resize_mode(self, shape_tag):
        shape = self.shapes.get(shape_tag)
        if not shape:
            return

        # Calculate bottom-right corner (if that’s your chosen anchor).
        x, y, w, h = shape["x"], shape["y"], shape["w"], shape["h"]
        corner_x = x + w // 2
        corner_y = y + h // 2

        handle_size = 10
        handle_id = self.canvas.create_rectangle(
            corner_x - handle_size // 2, corner_y - handle_size // 2,
            corner_x + handle_size // 2, corner_y + handle_size // 2,
            fill="gray", tags=("resize_handle", shape_tag)
        )

        # Ensure the handle is on top
        self.canvas.tag_raise(handle_id)

        # Bind events to the handle
        self.canvas.tag_bind(handle_id, "<Button-1>", self.start_resizing, add="+")
        self.canvas.tag_bind(handle_id, "<B1-Motion>", self.do_resizing, add="+")
        self.canvas.tag_bind(handle_id, "<ButtonRelease-1>", self.end_resizing, add="+")

    def start_resizing(self, event):
        # Retrieve the shape tag from the current item.
        self.resizing_shape_tag = self.canvas.gettags("current")[1]  # second tag is shape_tag
        shape = self.shapes.get(self.resizing_shape_tag)
        if not shape:
            return
        # Store the shape's center as a fixed anchor.
        self.resize_center = (shape["x"], shape["y"])
        # Record the starting mouse position (if needed for reference)
        self.resize_start = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        self.original_width = shape["w"]
        self.original_height = shape["h"]

    def do_resizing(self, event):
        if not self.resizing_shape_tag:
            return
        shape = self.shapes.get(self.resizing_shape_tag)
        if not shape:
            return
        # Use the stored center as the anchor.
        cx, cy = self.resize_center
        current_x = self.canvas.canvasx(event.x)
        current_y = self.canvas.canvasy(event.y)
        # Calculate new dimensions relative to the fixed center.
        new_width = max(10, 2 * (current_x - cx))
        new_height = max(10, 2 * (current_y - cy))
        shape["w"] = new_width
        shape["h"] = new_height

        # Recompute the bounding box so the center remains unchanged.
        left   = cx - new_width / 2
        top    = cy - new_height / 2
        right  = cx + new_width / 2
        bottom = cy + new_height / 2

        # Update the canvas coordinates for the shape.
        self.canvas.coords(shape["canvas_id"], left, top, right, bottom)

        # Move the resize handle to the new bottom-right corner.
        handle_id = shape.get("resize_handle")
        if handle_id:
            self.canvas.coords(handle_id,
                            right - 5, bottom - 5,
                            right + 5, bottom + 5)

    def end_resizing(self, event):
        # Clean up the resize mode; remove the handle.
        shape = self.shapes.get(self.resizing_shape_tag)
        if shape and "resize_handle" in shape:
            self.canvas.delete(shape["resize_handle"])
            del shape["resize_handle"]
        self.resizing_shape_tag = None
        self.resize_start = None
        self.resize_center = None

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: distance_point_to_line
    # Calculates the distance from a point to a given line segment.
    # ─────────────────────────────────────────────────────────────────────────
    def distance_point_to_line(self, px, py, x1, y1, x2, y2):
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(px - x1, py - y1)
        t = ((px - x1) * dx + (py - y1) * dy) / (dx*dx + dy*dy)
        t = max(0, min(1, t))
        nearest_x = x1 + t * dx
        nearest_y = y1 + t * dy
        return math.hypot(px - nearest_x, py - nearest_y)

    # ─────────────────────────────────────────────────────────────────────────
    # FUNCTION: get_link_by_position
    # Returns the link that is within a threshold distance from the given (x, y) point.
    # ─────────────────────────────────────────────────────────────────────────
    def get_link_by_position(self, x, y):
        threshold = 50  # Threshold for hit-testing
        for link in self.graph["links"]:
            npc_name1 = link["npc_name1"]
            npc_name2 = link["npc_name2"]
            tag1 = f"npc_{npc_name1.replace(' ', '_')}"
            tag2 = f"npc_{npc_name2.replace(' ', '_')}"
            x1, y1 = self.node_positions.get(tag1, (0, 0))
            x2, y2 = self.node_positions.get(tag2, (0, 0))
            distance = self.distance_point_to_line(x, y, x1, y1, x2, y2)
            if distance < threshold:
                return link
        return None


    def add_shape(self, shape_type):
        x, y = 200, 200
        width, height = 120, 80
        tag = f"shape_{self.shape_counter}"
        self.shape_counter += 1
        shape = {"type": shape_type, "x": x, "y": y, "w": width, "h": height, "color": "lightgray", "tag": tag}
        self.graph["shapes"].append(shape)
        self.shapes[tag] = shape
        self.draw_shape(shape)

    def draw_shape(self, shape):
        x, y, w, h = shape["x"], shape["y"], shape["w"], shape["h"]
        left = x - w//2
        top = y - h//2
        right = x + w//2
        bottom = y + h//2
        tag = shape["tag"]
        if shape["type"] == "rectangle":
            shape_id = self.canvas.create_rectangle(left, top, right, bottom, fill=shape["color"], tags=(tag, "shape"))
        else:
            shape_id = self.canvas.create_oval(left, top, right, bottom, fill=shape["color"], tags=(tag, "shape"))
        shape["canvas_id"] = shape_id

    def draw_all_shapes(self):
        # Sort shapes based on the stored z-index.
        shapes_sorted = sorted(self.graph.get("shapes", []), key=lambda s: s.get("z", 0))
        for shape in shapes_sorted:
            self.shapes[shape["tag"]] = shape
            self.draw_shape(shape)

    def save_graph(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json")
        if file_path:
            # Save node positions, etc.
            for node in self.graph["nodes"]:
                tag = f"npc_{node['npc_name'].replace(' ', '_')}"
                x, y = self.node_positions.get(tag, (node["x"], node["y"]))
                node["x"] = x
                node["y"] = y

            for link in self.graph["links"]:
                if "arrow_mode" not in link:
                    link["arrow_mode"] = "both"

            # Update each shape's data.
            for shape in self.graph.get("shapes", []):
                tag = shape["tag"]
                if tag in self.shapes:
                    shape_obj = self.shapes[tag]
                    shape["x"] = shape_obj["x"]
                    shape["y"] = shape_obj["y"]
                    shape["w"] = shape_obj["w"]
                    shape["h"] = shape_obj["h"]
                    shape["z"] = shape_obj.get("z", 0)
                    shape.pop("canvas_id", None)
                    shape.pop("resize_handle", None)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.graph, f, indent=2)

    def draw_graph(self):
        self.canvas.delete("all")
        self.node_images.clear()
        self.node_bboxes = {}
        self.draw_all_shapes()
        self.draw_nodes()
        self.draw_all_links()
        self.canvas.update_idletasks()
        bbox = self.canvas.bbox("all")
        if bbox:
            padding = 50
            self.canvas.configure(scrollregion=(
                bbox[0] - padding, bbox[1] - padding,
                bbox[2] + padding, bbox[3] + padding
            ))
        # Check if there are any "link" items before using them as reference.
        if self.canvas.find_withtag("link"):
            self.canvas.tag_lower("node", "link")
        else:
            self.canvas.tag_lower("node")
        # Lower "shape" below "link" if possible.
        if self.canvas.find_withtag("shape") and self.canvas.find_withtag("link"):
            self.canvas.tag_lower("shape", "link")
        elif self.canvas.find_withtag("shape"):
            self.canvas.tag_lower("shape")


    def start_drag(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        item = self.canvas.find_closest(x, y)
        if not item:
            return
        tags = self.canvas.gettags(item[0])
        self.selected_node = next((t for t in tags if t.startswith("npc_")), None)
        self.selected_shape = next((t for t in tags if t.startswith("shape_")), None)
        self.selected_items = self.canvas.find_withtag(self.selected_node or self.selected_shape)
        self.drag_start = (x, y)

    def on_drag(self, event):
        if not (self.selected_node or self.selected_shape) or not self.drag_start:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        dx = x - self.drag_start[0]
        dy = y - self.drag_start[1]
        for item in self.selected_items:
            self.canvas.move(item, dx, dy)
        if self.selected_node:
            old_x, old_y = self.node_positions[self.selected_node]
            self.node_positions[self.selected_node] = (old_x + dx, old_y + dy)
            self.update_links_positions_for_node(self.selected_node)
        if self.selected_shape:
            shape = self.shapes[self.selected_shape]
            shape["x"] += dx
            shape["y"] += dy
        self.drag_start = (x, y)

    def end_drag(self, event):
        self.selected_node = None
        self.selected_shape = None
        self.selected_items = []
        self.drag_start = None
