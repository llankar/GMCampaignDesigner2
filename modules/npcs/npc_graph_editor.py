import json
import os
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk, Menu
from PIL import Image, ImageTk
from modules.helpers.template_loader import load_template
from modules.generic.entity_selection_dialog import EntitySelectionDialog
from modules.generic.generic_model_wrapper import GenericModelWrapper
import math

PORTRAIT_FOLDER = "assets/portraits"
MAX_PORTRAIT_SIZE = (64, 64)

class NPCGraphEditor(ctk.CTkFrame):  # Change inheritance to CTkFrame
    def __init__(self, master, npc_wrapper: GenericModelWrapper, faction_wrapper: GenericModelWrapper, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.npc_wrapper = npc_wrapper
        self.faction_wrapper = faction_wrapper
        self.npcs = {npc["Name"]: npc for npc in self.npc_wrapper.load_items()}

        # Graph data
        self.graph = {"nodes": [], "links": []}

        # Node references
        self.node_positions = {}
        self.node_images = {}
        self.node_rectangles = {}  # Stores the rectangle item IDs for color changes
        self.node_bboxes = {}      # NEW: Stores bounding boxes (left, top, right, bottom)

        # Link / node selection
        self.selected_node = None
        self.selected_items = []
        self.drag_start = None
        self.selected_link = None

        # Initialize toolbar first
        self.init_toolbar()

        # Create canvas frame and scrollbars
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

        # Bind events
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<Button-3>", self.on_right_click)

        # Mouse wheel scrolling
        self.canvas.bind("<MouseWheel>", self._on_mousewheel_y)      # Windows
        self.canvas.bind("<Shift-MouseWheel>", self._on_mousewheel_x)  # Windows + Shift
        self.canvas.bind("<Button-4>", self._on_mousewheel_y)          # Linux
        self.canvas.bind("<Button-5>", self._on_mousewheel_y)          # Linux
        self.canvas.bind("<Shift-Button-4>", self._on_mousewheel_x)    # Linux + Shift
        self.canvas.bind("<Shift-Button-5>", self._on_mousewheel_x)    # Linux + Shift

    # ─────────────────────────────────────────────────────────────────────────
    # SCROLLING
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
    # TOOLBAR
    # ─────────────────────────────────────────────────────────────────────────
    def init_toolbar(self):
        toolbar = ctk.CTkFrame(self)
        toolbar.pack(fill="x", padx=5, pady=5)

        ctk.CTkButton(toolbar, text="Add NPC", command=self.add_npc).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Add Faction", command=self.add_faction).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Save", command=self.save_graph).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Load", command=self.load_graph).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Add Link", command=self.start_link_creation).pack(side="left", padx=5)

    # ─────────────────────────────────────────────────────────────────────────
    # LINK CREATION
    # ─────────────────────────────────────────────────────────────────────────
    def start_link_creation(self):
        # Temporarily override the left-click binding to pick the first node
        self.canvas.bind("<Button-1>", self.select_first_node)

    def select_first_node(self, event):
        item = self.canvas.find_closest(event.x, event.y)
        if not item:
            return
        item_id = item[0]
        tags = self.canvas.gettags(item_id)
        self.first_node = next((t for t in tags if t.startswith("npc_")), None)
        if self.first_node:
            # Now the next left-click picks the second node
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
        dialog.geometry("400x150")  # Increased size
        dialog.transient(self)
        dialog.grab_set()
        dialog.focus_force()

        ctk.CTkLabel(dialog, text="Link Text:").pack(pady=5)
        link_text_var = ctk.StringVar()
        link_text_entry = ctk.CTkEntry(dialog, textvariable=link_text_var)
        link_text_entry.pack(pady=5)

        # Press ENTER to add link
        link_text_entry.bind("<Return>", lambda event: on_add_link())

        def on_add_link():
            link_text = link_text_var.get()
            self.add_link(self.first_node, self.second_node, link_text)
            dialog.destroy()
            # Rebind left-click to normal drag
            self.canvas.bind("<Button-1>", self.start_drag)

        ctk.CTkButton(dialog, text="Add Link", command=on_add_link).pack(pady=10)
        dialog.after(100, link_text_entry.focus_set)

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
            "arrow_mode": "both"  # or "end", "start", or "none"
        })
        self.draw_graph()

    # ─────────────────────────────────────────────────────────────────────────
    # ADDING NPCs and FACTIONS
    # ─────────────────────────────────────────────────────────────────────────
    def add_npc(self):
        def on_npc_selected(npc):
            self.pending_npc = npc
            # Next click places this NPC
            self.canvas.bind("<Button-1>", self.place_pending_npc)

        npc_template = load_template("npcs")
        dialog = EntitySelectionDialog(self, "NPCs", self.npc_wrapper, npc_template, on_npc_selected)
        dialog.wait_window()

    def place_pending_npc(self, event):
        # We place the chosen NPC at the mouse click location
        npc_name = self.pending_npc["Name"]
        tag = f"npc_{npc_name.replace(' ', '_')}"
        self.graph["nodes"].append({
            "npc_name": npc_name,
            "x": event.x,
            "y": event.y,
            "color": "lightblue"  # Default color
        })
        self.node_positions[tag] = (event.x, event.y)
        self.pending_npc = None

        # Restore normal left-click binding
        self.canvas.unbind("<Button-1>")
        self.canvas.bind("<Button-1>", self.start_drag)
        self.draw_graph()

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
                self.filtered_factions = list(factions)
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
                    btn = ctk.CTkButton(self.list_frame, text=faction,
                                        command=lambda f=faction: self.select_faction(f))
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

            # Add each NPC of this faction to the graph
            for i, npc in enumerate(faction_npcs):
                npc_name = npc["Name"]
                tag = f"npc_{npc_name.replace(' ', '_')}"
                x = start_x + i * spacing
                y = start_y

                self.graph["nodes"].append({
                    "npc_name": npc_name,
                    "x": x,
                    "y": y,
                    "color": "lightblue"
                })
                self.node_positions[tag] = (x, y)

            self.draw_graph()

        # Collect unique factions from the NPC list
        factions = sorted(set(npc.get("Faction", "Unknown")
                              for npc in self.npcs.values() if npc.get("Faction")))

        if not factions:
            messagebox.showerror("Error", "No factions found in NPC data.")
            return

        dialog = FactionSelectionDialog(self, factions, on_faction_selected)
        self.wait_window(dialog)

    # ─────────────────────────────────────────────────────────────────────────
    # DRAGGING NODES
    # ─────────────────────────────────────────────────────────────────────────
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

        # Move all items that share the selected node tag
        for item in self.selected_items:
            self.canvas.move(item, dx, dy)

        # Update node_positions
        old_x, old_y = self.node_positions[self.selected_node]
        self.node_positions[self.selected_node] = (old_x + dx, old_y + dy)

        self.drag_start = (event.x, event.y)

        # Update scroll region during drag
        bbox = self.canvas.bbox("all")
        if bbox:
            padding = 50
            scroll_region = (bbox[0] - padding, bbox[1] - padding,
                             bbox[2] + padding, bbox[3] + padding)
            self.canvas.configure(scrollregion=scroll_region)

        # Redraw links so they follow the moved node
        self.draw_graph()

    # ─────────────────────────────────────────────────────────────────────────
    # RIGHT-CLICK MENU
    # ─────────────────────────────────────────────────────────────────────────
    def on_right_click(self, event):
        item = self.canvas.find_closest(event.x, event.y)
        if not item:
            return
        item_id = item[0]
        tags = self.canvas.gettags(item_id)

        if "link" in tags:
            # Right-click on a link
            self.show_link_menu(event.x, event.y)
            self.selected_link = self.get_link_by_position(event.x, event.y)
            print(f"Right-clicked on link: {self.selected_link}")
        else:
            # Possibly right-click on a node
            self.selected_node = next((t for t in tags if t.startswith("npc_")), None)
            if self.selected_node:
                self.show_color_menu(event.x, event.y)

    def show_color_menu(self, x, y):
        COLORS = [
            "red", "green", "blue", "yellow", "purple",
            "orange", "pink", "cyan", "magenta", "lightgray"
        ]
        color_menu = Menu(self.canvas, tearoff=0)
        for color in COLORS:
            color_menu.add_command(label=color, command=lambda c=color: self.change_node_color(c))
        color_menu.post(x, y)

    def show_link_menu(self, x, y):
        link_menu = Menu(self.canvas, tearoff=0)
        
        # Submenu for arrow mode
        arrow_submenu = Menu(link_menu, tearoff=0)
        arrow_submenu.add_command(label="No Arrows", command=lambda: self.set_arrow_mode("none"))
        arrow_submenu.add_command(label="Arrow at Start", command=lambda: self.set_arrow_mode("start"))
        arrow_submenu.add_command(label="Arrow at End", command=lambda: self.set_arrow_mode("end"))
        arrow_submenu.add_command(label="Arrows at Both Ends", command=lambda: self.set_arrow_mode("both"))
        
        link_menu.add_cascade(label="Arrow Mode", menu=arrow_submenu)
        
        link_menu.post(x, y)
    def set_arrow_mode(self, new_mode):
        """
        Sets the arrow_mode (none, start, end, both) of the currently selected link.
        """
        if not self.selected_link:
            print("No link selected, cannot set arrow mode.")
            return
        
        # Update the link in self.graph to the chosen arrow_mode
        for link in self.graph["links"]:
            if (link["npc_name1"] == self.selected_link["npc_name1"]
                    and link["npc_name2"] == self.selected_link["npc_name2"]):
                link["arrow_mode"] = new_mode
                print(f"Updated link arrow_mode to '{new_mode}'")
                break
        
        self.draw_graph()

    # ─────────────────────────────────────────────────────────────────────────
    # DRAW GRAPH - MAIN ENTRY POINT
    # ─────────────────────────────────────────────────────────────────────────
    def draw_graph(self):
        """
        Erases the canvas, draws all nodes, then draws all links
        using bounding-box offset for arrowheads.
        """
        self.canvas.delete("all")
        self.node_images.clear()
        self.node_bboxes = {}  # We'll rebuild bounding boxes each time

        self.draw_nodes()
        self.draw_all_links()

        # Raise arrowheads and text on top of nodes
        self.canvas.tag_raise("arrowhead")
        self.canvas.tag_raise("link_text")

        # Update scroll region
        self.canvas.update_idletasks()
        bbox = self.canvas.bbox("all")
        if bbox:
            padding = 50
            scroll_region = (
                bbox[0] - padding,
                bbox[1] - padding,
                bbox[2] + padding,
                bbox[3] + padding
            )
            self.canvas.configure(scrollregion=scroll_region)

    # ─────────────────────────────────────────────────────────────────────────
    # DRAWING NODES
    # ─────────────────────────────────────────────────────────────────────────
    def draw_nodes(self):
        NODE_WIDTH = 100
        TEXT_LINE_HEIGHT = 25
        TEXT_PADDING = 5

        for node in self.graph["nodes"]:
            npc_name = node["npc_name"]
            tag = f"npc_{npc_name.replace(' ', '_')}"
            # Use node_positions if available, else fallback to node coords
            x, y = self.node_positions.get(tag, (node["x"], node["y"]))
            color = node.get("color", "lightblue")

            # Check if there's a portrait
            portrait_path = self.npcs.get(npc_name, {}).get("Portrait", "")
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

            # Wrap the name if it's more than one word
            words = npc_name.split()
            if len(words) >= 2:
                wrapped_name = f"{words[0]}\n{' '.join(words[1:])}"
            else:
                wrapped_name = npc_name

            lines = wrapped_name.splitlines()
            number_of_lines = len(lines)
            node_height = (
                portrait_height
                + (number_of_lines * TEXT_LINE_HEIGHT)
                + (TEXT_PADDING if has_portrait else 0)
                + 10
            )

            # Calculate bounding box
            left = x - (NODE_WIDTH // 2)
            top = y - (node_height // 2)
            right = x + (NODE_WIDTH // 2)
            bottom = y + (node_height // 2)

            # Draw rectangle
            rectangle_id = self.canvas.create_rectangle(
                left, top, right, bottom,
                fill=color, tags=(tag,)
            )
            # Store rectangle ID for color changes
            self.node_rectangles[tag] = rectangle_id
            # Also store bounding box for arrow offset
            self.node_bboxes[tag] = (left, top, right, bottom)

            # Draw the portrait if available
            if has_portrait:
                self.canvas.create_image(
                    x, top + (portrait_height // 2),
                    image=self.node_images[npc_name], tags=(tag,)
                )
                text_y = top + portrait_height + TEXT_PADDING + (TEXT_LINE_HEIGHT // 2) + 8
            else:
                text_y = y - 4

            # Draw the NPC name text
            self.canvas.create_text(
                x, text_y + 4,
                text=wrapped_name,
                fill="black",
                font=("Arial", 8, "bold"),
                width=NODE_WIDTH - 4,
                justify="center",
                tags=(tag,)
            )

    # ─────────────────────────────────────────────────────────────────────────
    # DRAWING LINKS
    # ─────────────────────────────────────────────────────────────────────────
    def draw_all_links(self):
        """
        Draws all links in the graph. Each link is drawn behind the nodes,
        but arrowheads and link text are raised on top.
        """
        for link in self.graph["links"]:
            self.draw_one_link(link)

        # Ensure lines go behind node rectangles
        self.canvas.tag_lower("link")

    def draw_one_link(self, link):
        tag1 = f"npc_{link['npc_name1'].replace(' ', '_')}"
        tag2 = f"npc_{link['npc_name2'].replace(' ', '_')}"

        # Centers of node1 and node2
        x1, y1 = self.node_positions.get(tag1, (0, 0))
        x2, y2 = self.node_positions.get(tag2, (0, 0))

        # Draw the main line
        self.canvas.create_line(x1, y1, x2, y2, fill="black", tags=("link",))

        # arrow_mode can be "none", "start", "end", or "both"
        arrow_mode = link.get("arrow_mode", "end")

        # If "start" or "both", draw an arrow near node1, pointing node1 → node2
        if arrow_mode in ("start", "both"):
            self.draw_arrowhead(x1, y1, x2, y2, tag1)

        # If "end" or "both", draw an arrow near node2, pointing node2 → node1
        if arrow_mode in ("end", "both"):
            self.draw_arrowhead(x2, y2, x1, y1, tag2)

        # Draw link text at midpoint
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        self.canvas.create_text(
            mid_x, mid_y,
            text=link["text"],
            fill="red",
            font=("Arial", 10, "bold"),
            tags=("link_text",)
        )


    def draw_arrowhead(self, start_x, start_y, end_x, end_y, node_tag):
        """
        Draws an arrow near (start_x, start_y), pointing toward (end_x, end_y).
        'node_tag' is the node at (start_x, start_y), so we can look up its bbox.
        """
        arrow_length = 10
        angle = math.atan2(end_y - start_y, end_x - start_x)

        # Retrieve bounding box for the node at (start_x, start_y)
        left, top, right, bottom = self.node_bboxes.get(
            node_tag, (start_x - 50, start_y - 25, start_x + 50, start_y + 25)
        )
        half_w = (right - left) / 2
        half_h = (bottom - top) / 2

        # Approximate the node as a circle => radius is half the diagonal
        node_radius = math.sqrt(half_w**2 + half_h**2)

        # Extra gap so arrow tip is outside the rectangle
        arrow_offset_extra = -27
        arrow_offset = node_radius + arrow_offset_extra

        # Shift apex in the direction from (start_x,start_y) to (end_x,end_y)
        arrow_apex_x = start_x + arrow_offset * math.cos(angle)
        arrow_apex_y = start_y + arrow_offset * math.sin(angle)

        # Create the triangular arrowhead
        self.canvas.create_polygon(
            arrow_apex_x, arrow_apex_y,
            arrow_apex_x + arrow_length * math.cos(angle + math.pi / 6),
            arrow_apex_y + arrow_length * math.sin(angle + math.pi / 6),
            arrow_apex_x + arrow_length * math.cos(angle - math.pi / 6),
            arrow_apex_y + arrow_length * math.sin(angle - math.pi / 6),
            fill="black",
            outline="black",
            tags=("arrowhead",)
        )


    # ─────────────────────────────────────────────────────────────────────────
    # SAVE / LOAD
    # ─────────────────────────────────────────────────────────────────────────
    def save_graph(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json")
        if file_path:
            # Update node coords from node_positions
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

            # Rebuild node_positions
            self.node_positions = {
                f"npc_{n['npc_name'].replace(' ', '_')}": (n["x"], n["y"])
                for n in self.graph["nodes"]
            }
            # Default color if missing
            for node in self.graph["nodes"]:
                node["color"] = node.get("color", "lightblue")

            self.draw_graph()

    # ─────────────────────────────────────────────────────────────────────────
    # COLOR CHANGES
    # ─────────────────────────────────────────────────────────────────────────
    def change_node_color(self, color):
        if self.selected_node:
            rect_id = self.node_rectangles[self.selected_node]
            self.canvas.itemconfig(rect_id, fill=color)
            # Update color in the graph data
            for node in self.graph["nodes"]:
                if node["npc_name"] == self.selected_node.replace("npc_", "").replace("_", " "):
                    node["color"] = color
                    break

    
    # ─────────────────────────────────────────────────────────────────────────
    # LINK HIT-TESTING
    # ─────────────────────────────────────────────────────────────────────────
    def distance_point_to_line(self, px, py, x1, y1, x2, y2):
        """
        Calculate the distance from (px, py) to the line segment (x1, y1) -> (x2, y2).
        """
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(px - x1, py - y1)
        t = ((px - x1) * dx + (py - y1) * dy) / (dx*dx + dy*dy)
        t = max(0, min(1, t))
        nearest_x = x1 + t * dx
        nearest_y = y1 + t * dy
        return math.hypot(px - nearest_x, py - nearest_y)

    def get_link_by_position(self, x, y):
        for link in self.graph["links"]:
            npc_name1 = link["npc_name1"]
            npc_name2 = link["npc_name2"]
            tag1 = f"npc_{npc_name1.replace(' ', '_')}"
            tag2 = f"npc_{npc_name2.replace(' ', '_')}"

            x1, y1 = self.node_positions.get(tag1, (0, 0))
            x2, y2 = self.node_positions.get(tag2, (0, 0))

            dist = self.distance_point_to_line(x, y, x1, y1, x2, y2)
            print(f"Checking link: {link} | Distance to line: {dist}")
            if dist < 10:
                print(f"Identified link: {link}")
                return link
        return None
