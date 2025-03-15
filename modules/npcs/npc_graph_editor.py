import json
import os
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
from modules.helpers.template_loader import load_template
from modules.generic.entity_selection_dialog import EntitySelectionDialog
from modules.generic.generic_model_wrapper import GenericModelWrapper

PORTRAIT_FOLDER = "assets/portraits"
MAX_PORTRAIT_SIZE = (64, 64)

class NPCGraphEditor(ctk.CTkFrame):  # Change inheritance to CTkFrame
    def __init__(self, master, npc_wrapper: GenericModelWrapper, faction_wrapper: GenericModelWrapper, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.npc_wrapper = npc_wrapper
        self.faction_wrapper = faction_wrapper
        self.npcs = {npc["Name"]: npc for npc in self.npc_wrapper.load_items()}

        self.graph = {"nodes": [], "links": []}
        self.node_positions = {}
        self.node_images = {}

        self.selected_node = None
        self.selected_items = []
        self.drag_start = None

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

        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.on_drag)

        # Add these bindings after canvas creation
        self.canvas.bind("<MouseWheel>", self._on_mousewheel_y)  # Windows
        self.canvas.bind("<Shift-MouseWheel>", self._on_mousewheel_x)  # Windows with Shift
        self.canvas.bind("<Button-4>", self._on_mousewheel_y)  # Linux
        self.canvas.bind("<Button-5>", self._on_mousewheel_y)  # Linux
        self.canvas.bind("<Shift-Button-4>", self._on_mousewheel_x)  # Linux with Shift
        self.canvas.bind("<Shift-Button-5>", self._on_mousewheel_x)  # Linux with Shift

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
    def init_toolbar(self):
        toolbar = ctk.CTkFrame(self)
        toolbar.pack(fill="x", padx=5, pady=5)

        ctk.CTkButton(toolbar, text="Add NPC", command=self.add_npc).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Add Faction", command=self.add_faction).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Save", command=self.save_graph).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Load", command=self.load_graph).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Add Link", command=self.start_link_creation).pack(side="left", padx=5)  # NEW BUTTON
   
    def start_link_creation(self):
        self.canvas.bind("<Button-1>", self.select_first_node)

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
        dialog.geometry("400x150")  # Increased size
        dialog.transient(self)
        dialog.grab_set()
        dialog.focus_force()

        ctk.CTkLabel(dialog, text="Link Text:").pack(pady=5)
        link_text_var = ctk.StringVar()
        link_text_entry = ctk.CTkEntry(dialog, textvariable=link_text_var)
        link_text_entry.pack(pady=5)
        link_text_entry.bind("<Return>", lambda event: on_add_link())  # Bind ENTER key

        def on_add_link():
            link_text = link_text_var.get()
            self.add_link(self.first_node, self.second_node, link_text)
            dialog.destroy()
            self.canvas.bind("<Button-1>", self.start_drag)  # Rebind to start_drag after link creation

        ctk.CTkButton(dialog, text="Add Link", command=on_add_link).pack(pady=10)

        # Set focus to the text field after the window is fully initialized
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

        self.draw_graph()
        self.canvas.bind("<Button-1>", self.start_drag)  # Rebind to start_drag after link creation

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

            self.draw_graph()

        # Collect unique factions from the NPC list
        factions = sorted(set(npc.get("Faction", "Unknown") for npc in self.npcs.values() if npc.get("Faction")))

        if not factions:
            messagebox.showerror("Error", "No factions found in NPC data.")
            return

        dialog = FactionSelectionDialog(self, factions, on_faction_selected)
        self.wait_window(dialog)

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

        # Update scroll region during drag
        bbox = self.canvas.bbox("all")
        if bbox:
            padding = 50
            scroll_region = (bbox[0]-padding, bbox[1]-padding,
                            bbox[2]+padding, bbox[3]+padding)
            self.canvas.configure(scrollregion=scroll_region)

        # Redraw the graph to update link positions
        self.draw_graph()

    def draw_graph(self):
        self.canvas.delete("all")
        self.node_images.clear()

        NODE_WIDTH = 100
        TEXT_LINE_HEIGHT = 25
        TEXT_TOTAL_HEIGHT = 2 * TEXT_LINE_HEIGHT + 4
        TEXT_PADDING = 5

        # Draw links first
        for link in self.graph["links"]:
            npc_name1 = link["npc_name1"]
            npc_name2 = link["npc_name2"]
            link_text = link["text"]

            tag1 = f"npc_{npc_name1.replace(' ', '_')}"
            tag2 = f"npc_{npc_name2.replace(' ', '_')}"

            x1, y1 = self.node_positions.get(tag1, (0, 0))
            x2, y2 = self.node_positions.get(tag2, (0, 0))

            self.canvas.create_line(x1, y1, x2, y2, fill="black", tags=("link",))

            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2

            self.canvas.create_text(mid_x, mid_y, text=link_text, fill="red", font=("Arial", 10, "bold"), tags=("link_text",))

        # Draw nodes
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

            if has_portrait:
                self.canvas.create_image(
                    x, y - node_height // 2 + portrait_height // 2,
                    image=self.node_images[npc_name], tags=(tag,)
                )

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
            
            words = npc_name.split()
            if len(words) >= 2:
                wrapped_name = f"{words[0]}\n{' '.join(words[1:])}"
            else:
                wrapped_name = npc_name
            lines = wrapped_name.splitlines()
            number_of_lines = len(lines)
            node_height = portrait_height + (number_of_lines * TEXT_LINE_HEIGHT) + (TEXT_PADDING if has_portrait else 0) + 10
            self.canvas.create_rectangle(
                x - NODE_WIDTH // 2, y - node_height // 2,
                x + NODE_WIDTH // 2, y + node_height // 2,
                fill="lightblue", tags=(tag,)
            )
            if has_portrait:
                text_y = y - node_height // 2 + portrait_height + TEXT_PADDING + TEXT_LINE_HEIGHT // 2 + 8
                self.canvas.create_image(
                    x, y - node_height // 2 + portrait_height // 2,
                    image=self.node_images[npc_name], tags=(tag,))
            
            else:
                text_y = y-4
           
            self.canvas.create_text(
                x, text_y+4,
                text=wrapped_name,
                fill="black",
                font=("Arial", 8, "bold"),
                width=NODE_WIDTH - 4,
                justify="center",
                tags=(tag,)
            )

        # After all elements are drawn, calculate proper scroll region
        self.canvas.update_idletasks()
        bbox = self.canvas.bbox("all")
        if bbox:
            # Add padding to ensure all content is visible
            padding = 50
            scroll_region = (bbox[0]-padding, bbox[1]-padding, 
                            bbox[2]+padding, bbox[3]+padding)
            self.canvas.configure(scrollregion=scroll_region)
            
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
