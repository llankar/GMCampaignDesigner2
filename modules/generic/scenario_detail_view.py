import customtkinter as ctk
import os
import json
from tkinter import filedialog, messagebox
from PIL import Image
from functools import partial
from modules.generic.generic_model_wrapper import GenericModelWrapper
from modules.helpers.text_helpers import format_longtext
from customtkinter import CTkLabel, CTkImage
from modules.npcs.npc_graph_editor import NPCGraphEditor
from modules.scenarios.scenario_graph_editor import ScenarioGraphEditor

PORTRAIT_FOLDER = "assets/portraits"
MAX_PORTRAIT_SIZE = (32, 32)  # Thumbnail size for lists

class ScenarioDetailView(ctk.CTkFrame):
    def __init__(self, master, scenario_item, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        # Persistent cache for portrait images
        self.portrait_images = {}
        self.scenario = scenario_item

        # Load your detach and reattach icon files (adjust file paths and sizes as needed)
        self.detach_icon = CTkImage(light_image=Image.open("assets/detach_icon.png"),
                                    dark_image=Image.open("assets/detach_icon.png"),
                                    size=(20, 20))
        self.reattach_icon = CTkImage(light_image=Image.open("assets/reattach_icon.png"),
                                    dark_image=Image.open("assets/reattach_icon.png"),
                                    size=(20, 20))

        self.wrappers = {
            "Scenarios": GenericModelWrapper("scenarios"),
            "Places": GenericModelWrapper("places"),
            "NPCs": GenericModelWrapper("npcs"),
            "Factions": GenericModelWrapper("factions")
        }

        self.templates = {
            "Scenarios": self.load_template("scenarios/scenarios_template.json"),
            "Places": self.load_template("places/places_template.json"),
            "NPCs": self.load_template("npcs/npcs_template.json"),
            "Factions": self.load_template("factions/factions_template.json")
        }

        self.tabs = {}
        self.current_tab = None

        # A container to hold both the scrollable tab area and the plus button
        self.tab_bar_container = ctk.CTkFrame(self, height=60)
        self.tab_bar_container.pack(side="top", fill="x")

        # The scrollable canvas for tabs
        self.tab_bar_canvas = ctk.CTkCanvas(self.tab_bar_container, height=40, highlightthickness=0)
        self.tab_bar_canvas.pack(side="top", fill="x", expand=True)

        # Horizontal scrollbar at the bottom
        self.h_scrollbar = ctk.CTkScrollbar(
            self.tab_bar_container,
            orientation="horizontal",
            command=self.tab_bar_canvas.xview
        )
        self.h_scrollbar.pack(side="bottom", fill="x")

        # The actual frame that holds the tab buttons
        self.tab_bar = ctk.CTkFrame(self.tab_bar_canvas, height=40)
        self.tab_bar_id = self.tab_bar_canvas.create_window((0, 0), window=self.tab_bar, anchor="nw")

        # Connect the scrollbar to the canvas
        self.tab_bar_canvas.configure(xscrollcommand=self.h_scrollbar.set)

        # Update the scroll region when the tab bar resizes
        self.tab_bar.bind("<Configure>", lambda e: self.tab_bar_canvas.configure(
            scrollregion=self.tab_bar_canvas.bbox("all")))

        # The plus button stays on the right side of the container
        self.add_button = ctk.CTkButton(
            self.tab_bar_container,
            text="+",
            width=40,
            command=self.add_new_tab
        )
        self.add_button.pack(side="right", padx=5, pady=5)

        # Main content area for scenario details
        self.content_area = ctk.CTkFrame(self)
        self.content_area.pack(fill="both", expand=True)

        # Example usage: create the first tab from the scenario_item
        scenario_name = scenario_item.get("Title", "Unnamed Scenario")
        self.add_tab(
            scenario_name,
            self.create_entity_frame("Scenarios", scenario_item),
            content_factory=lambda master: self.create_entity_frame("Scenarios", scenario_item, master=master)
        )




    def load_template(self, filename):
        base_path = os.path.dirname(__file__)
        template_path = os.path.join(base_path, "..", filename)
        with open(template_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def add_tab(self, name, content_frame, content_factory=None):
        tab_frame = ctk.CTkFrame(self.tab_bar)
        tab_frame.pack(side="left", padx=2, pady=5)

        tab_button = ctk.CTkButton(tab_frame, text=name, width=150,
                                   command=lambda: self.show_tab(name))
        tab_button.pack(side="left")

        close_button = ctk.CTkButton(tab_frame, text="❌", width=30,
                                     command=lambda: self.close_tab(name))
        close_button.pack(side="left")

        # Create the detach button and store its reference.
        detach_button = ctk.CTkButton(tab_frame,image=self.detach_icon, text="", width=50,
                                      command=lambda: self.toggle_detach_tab(name))
        detach_button.pack(side="left")

        portrait_label = getattr(content_frame, "portrait_label", None)
        self.tabs[name] = {
            "button_frame": tab_frame,
            "content_frame": content_frame,
            "button": tab_button,
            "detach_button": detach_button,
            "detached": False,
            "window": None,
            "portrait_label": portrait_label,
            "factory": content_factory
        }

        content_frame.pack_forget()
        self.show_tab(name)
        self.reposition_add_button()

    def toggle_detach_tab(self, name):
        if self.tabs[name]["detached"]:
            self.reattach_tab(name)
            # After reattaching, show the detach icon
            self.tabs[name]["detach_button"].configure(image=self.detach_icon)
        else:
            self.detach_tab(name)
            # When detached, change to the reattach icon
            self.tabs[name]["detach_button"].configure(image=self.reattach_icon)

    def detach_tab(self, name):
        print(f"[DETACH] Start detaching tab: {name}")
        if self.tabs[name]["detached"]:
            print(f"[DETACH] Tab '{name}' is already detached.")
            return

        old_frame = self.tabs[name]["content_frame"]
        old_frame.pack_forget()

        detached_window = ctk.CTkToplevel(self)
        detached_window.title(name)
        detached_window.protocol("WM_DELETE_WINDOW", lambda: None)
        print(f"[DETACH] Detached window created: {detached_window}")

        # Check if this is a Note tab; handle separately
        if name.startswith("Note") and hasattr(old_frame, "text_box"):
            current_text = old_frame.text_box.get("1.0", "end-1c")
            new_frame = self.create_note_frame(detached_window, initial_text=current_text)
        else:
            factory = self.tabs[name].get("factory")
            if factory is None:
                new_frame = old_frame
            else:
                new_frame = factory(detached_window)
                # For tabs with state (like NPC Graph), restore state from graph_editor
                if hasattr(old_frame, "graph_editor") and hasattr(old_frame.graph_editor, "get_state"):
                    saved_state = old_frame.graph_editor.get_state()
                    if saved_state and hasattr(new_frame, "graph_editor") and hasattr(new_frame.graph_editor, "set_state"):
                        new_frame.graph_editor.set_state(saved_state)
                if hasattr(old_frame, "scenario_graph_editor") and hasattr(old_frame.scenario_graph_editor, "get_state"):
                    saved_state = old_frame.scenario_graph_editor.get_state()
                    if saved_state and hasattr(new_frame, "scenario_graph_editor") and hasattr(new_frame.scenario_graph_editor, "set_state"):
                        new_frame.scenario_graph_editor.set_state(saved_state)

        new_frame.pack(fill="both", expand=True)
        new_frame.update_idletasks()
        req_width = new_frame.winfo_reqwidth()
        req_height = new_frame.winfo_reqheight()

        if not hasattr(ScenarioDetailView, 'detached_count'):
            ScenarioDetailView.detached_count = 0
        offset_x = ScenarioDetailView.detached_count * (req_width + 10)
        offset_y = 0
        detached_window.geometry(f"{req_width}x{req_height}+{offset_x}+{offset_y}")
        ScenarioDetailView.detached_count += 1

        print(f"[DETACH] New frame in detached window created: {new_frame}")

        # (Optional) Update portrait label if needed…
        if hasattr(new_frame, "portrait_label"):
            self.tabs[name]["portrait_label"] = new_frame.portrait_label
            print(f"[DETACH] Using existing portrait label from new frame.")
        else:
            portrait_label = self.tabs[name].get("portrait_label")
            if portrait_label and portrait_label.winfo_exists():
                portrait_key = getattr(portrait_label, "entity_name", None)
                if portrait_key and portrait_key in self.portrait_images:
                    new_portrait_label = ctk.CTkLabel(new_frame, image=self.portrait_images[portrait_key], text="")
                    new_portrait_label.image = self.portrait_images[portrait_key]
                    new_portrait_label.entity_name = portrait_key
                    new_portrait_label.is_portrait = True
                    new_portrait_label.pack(pady=10)
                    print(f"[DETACH] Recreated portrait label for entity '{portrait_key}'.")
                    self.tabs[name]["portrait_label"] = new_portrait_label

        self.tabs[name]["detached"] = True
        self.tabs[name]["window"] = detached_window
        self.tabs[name]["content_frame"] = new_frame
        print(f"[DETACH] Tab '{name}' successfully detached.")

        # Reorder detached windows after detaching (if you have that function)
        if hasattr(self, "reorder_detached_windows"):
            self.reorder_detached_windows()


    def create_note_frame(self, master=None, initial_text=""):
        if master is None:
            master = self.content_area
        frame = ctk.CTkFrame(master)
        toolbar = ctk.CTkFrame(frame)
        toolbar.pack(fill="x", padx=5, pady=5)
        save_button = ctk.CTkButton(
            toolbar,
            text="Save Note",
            command=lambda: self.save_note_to_file(frame, f"Note_{len(self.tabs)}")
        )
        save_button.pack(side="right", padx=5)
        text_box = ctk.CTkTextbox(frame, wrap="word", height=500)
        text_box.pack(fill="both", expand=True, padx=10, pady=5)
        text_box.insert("1.0", initial_text)
        frame.text_box = text_box
        return frame


    def reattach_tab(self, name):
        print(f"[REATTACH] Start reattaching tab: {name}")
        if not self.tabs[name].get("detached", False):
            print(f"[REATTACH] Tab '{name}' is not detached.")
            return

        detached_window = self.tabs[name]["window"]
        current_frame = self.tabs[name]["content_frame"]

        # Save state from the graph editor in the detached frame
        saved_state = None
        if hasattr(current_frame, "graph_editor") and hasattr(current_frame.graph_editor, "get_state"):
            saved_state = current_frame.graph_editor.get_state()
        if hasattr(current_frame, "scenario_graph_editor") and hasattr(current_frame.scenario_graph_editor, "get_state"):
            saved_state = current_frame.scenario_graph_editor.get_state()

        # Special handling for note tabs (if any)
        current_text = ""
        if name.startswith("Note") and hasattr(current_frame, "text_box"):
            current_text = current_frame.text_box.get("1.0", "end-1c")
            
        if detached_window:
            detached_window.destroy()
            print("[REATTACH] Detached window destroyed.")

        factory = self.tabs[name].get("factory")
        if factory is None:
            new_frame = current_frame
        else:
            if name.startswith("Note"):
                new_frame = factory(self.content_area, initial_text=current_text)
            else:
                new_frame = factory(self.content_area)
            # Restore the graph state if available
            if saved_state and hasattr(new_frame, "graph_editor") and hasattr(new_frame.graph_editor, "set_state"):
                new_frame.graph_editor.set_state(saved_state)
            if saved_state and hasattr(new_frame, "scenario_graph_editor") and hasattr(new_frame.scenario_graph_editor, "set_state"):
                new_frame.scenario_graph_editor.set_state(saved_state)
        new_frame.pack(fill="both", expand=True)
            
        self.tabs[name]["content_frame"] = new_frame
        self.tabs[name]["detached"] = False
        self.tabs[name]["window"] = None
        self.show_tab(name)
        self.reorder_detached_windows()
        print(f"[REATTACH] Tab '{name}' reattached successfully.")



    def close_tab(self, name):
        if len(self.tabs) == 1:
            return
        if self.tabs[name].get("detached", False) and self.tabs[name].get("window"):
            self.tabs[name]["window"].destroy()
        self.tabs[name]["button_frame"].destroy()
        self.tabs[name]["content_frame"].destroy()
        del self.tabs[name]
        if self.current_tab == name and self.tabs:
            self.show_tab(next(iter(self.tabs)))
        self.reposition_add_button()

    def reposition_add_button(self):
        self.add_button.pack_forget()
        if self.tabs:
            last_tab_frame = list(self.tabs.values())[-1]["button_frame"]
            self.add_button.pack(side="left", padx=5, after=last_tab_frame)
        else:
            self.add_button.pack(side="left", padx=5)

    def show_tab(self, name):
        # Hide content for the current tab if it's not detached.
        if self.current_tab and self.current_tab in self.tabs:
            if not self.tabs[self.current_tab]["detached"]:
                self.tabs[self.current_tab]["content_frame"].pack_forget()
            self.tabs[self.current_tab]["button"].configure(fg_color=("gray75", "gray25"))
        self.current_tab = name
        self.tabs[name]["button"].configure(fg_color=("gray55", "gray15"))
        # Only pack the content into the main content area if the tab is not detached.
        if not self.tabs[name]["detached"]:
            self.tabs[name]["content_frame"].pack(fill="both", expand=True)

    def add_new_tab(self):
        # Added "Scenario Graph Editor" to the list of options.
        options = ["Factions", "Places", "NPCs", "Scenarios", "Note Tab", "NPC Graph", "Scenario Graph Editor"]
        popup = ctk.CTkToplevel(self)
        popup.title("Create New Tab")
        popup.geometry("300x250")
        popup.transient(self.winfo_toplevel())
        popup.grab_set()
        popup.focus_force()
        for option in options:
            ctk.CTkButton(popup, text=option,
                        command=lambda o=option: self.open_selection_window(o, popup)).pack(pady=2)

    def open_selection_window(self, entity_type, popup):
        popup.destroy()
        if entity_type == "Note Tab":
            self.add_tab(
                f"Note {len(self.tabs) + 1}",
                self.create_note_frame(), 
                content_factory=lambda master, initial_text="": self.create_note_frame(master=master, initial_text=initial_text)
            )
            return
        elif entity_type == "NPC Graph":
            self.add_tab("NPC Graph", self.create_npc_graph_frame(),
                        content_factory=lambda master: self.create_npc_graph_frame(master))
            return
        # New branch for Scenario Graph Editor:
        elif entity_type == "Scenario Graph Editor":
            self.add_tab("Scenario Graph Editor", self.create_scenario_graph_frame(),
                        content_factory=lambda master: self.create_scenario_graph_frame(master))
            return

        model_wrapper = self.wrappers[entity_type]
        template = self.templates[entity_type]
        selection_popup = ctk.CTkToplevel(self)
        selection_popup.title(f"Select {entity_type}")
        selection_popup.geometry("600x500")
        selection_popup.transient(self.winfo_toplevel())
        selection_popup.grab_set()
        selection_popup.focus_force()
        view = EntitySelectionView(selection_popup, entity_type, model_wrapper, template, self)
        view.pack(fill="both", expand=True)

    def open_entity_tab(self, entity_type, name):
        wrapper = self.wrappers[entity_type]
        items = wrapper.load_items()
        key = "Title" if entity_type == "Scenarios" else "Name"
        item = next((i for i in items if i.get(key) == name), None)
        if not item:
            messagebox.showerror("Error", f"{entity_type[:-1]} '{name}' not found.")
            return
        # Create the initial frame using the default content_area.
        frame = self.create_entity_frame(entity_type, item)
        # Pass a factory function that recreates the frame with a given master.
        self.add_tab(
            name,
            frame,
            content_factory=lambda master: self.create_entity_frame(entity_type, item, master=master)
        )
    def create_scenario_graph_frame(self, master=None):
        if master is None:
            master = self.content_area
        frame = ctk.CTkFrame(master)
        # Create a ScenarioGraphEditor widget.
        # Note: Ensure that self.wrappers contains "Scenarios", "NPCs", and "Places" as required.
        scenario_graph_editor = ScenarioGraphEditor(
            frame,
            self.wrappers["Scenarios"],
            self.wrappers["NPCs"],
            self.wrappers["Places"]
        )
        scenario_graph_editor.pack(fill="both", expand=True)
        frame.scenario_graph_editor = scenario_graph_editor  # Optional: store a reference for state management.
        return frame

    def create_entity_frame(self, entity_type, entity, master=None):
        if master is None:
            master = self.content_area
        frame = ctk.CTkFrame(master)
        template = self.templates[entity_type]
        if entity_type == "NPCs" and "Portrait" in entity and os.path.exists(entity["Portrait"]):
            img = Image.open(entity["Portrait"])
            img = img.resize((200, 200), Image.Resampling.LANCZOS)
            ctk_image = ctk.CTkImage(light_image=img, size=(200, 200))
            portrait_label = ctk.CTkLabel(frame, image=ctk_image, text="")
            portrait_label.image = ctk_image
            portrait_label.entity_name = entity["Name"]
            portrait_label.is_portrait = True
            self.portrait_images[entity["Name"]] = ctk_image
            portrait_label.pack(pady=10)
            print(f"[DEBUG] Created portrait label for {entity['Name']}: is_portrait={portrait_label.is_portrait}, entity_name={portrait_label.entity_name}")
            frame.portrait_label = portrait_label
        for field in template["fields"]:
            field_name = field["name"]
            field_type = field["type"]
            if entity_type == "NPCs" and field_name == "Portrait":
                continue
            if field_type == "longtext":
                self.insert_longtext(frame, field_name, entity.get(field_name, ""))
            elif field_type == "text":
                self.insert_text(frame, field_name, entity.get(field_name, ""))
            elif field_type == "list":
                linked_type = field.get("linked_type", None)
                if linked_type:
                    self.insert_links(frame, field_name, entity.get(field_name, []), linked_type)
        return frame

    def insert_text(self, parent, header, content):
        ctk.CTkLabel(parent, text=f"{header}:", font=("Arial", 14, "bold")).pack(anchor="w", padx=10)
        box = ctk.CTkTextbox(parent, wrap="word", height=80)
        box.insert("1.0", content)
        box.configure(state="disabled")
        box.pack(fill="x", padx=10, pady=5)

    def insert_longtext(self, parent, header, content):
        ctk.CTkLabel(parent, text=f"{header}:", font=("Arial", 14, "bold")).pack(anchor="w", padx=10)
        formatted_text = format_longtext(content, max_length=2000)
        box = ctk.CTkTextbox(parent, wrap="word", height=120)
        box.insert("1.0", formatted_text)
        box.configure(state="disabled")
        box.pack(fill="x", padx=10, pady=5)

    def insert_links(self, parent, header, items, linked_type):
        ctk.CTkLabel(parent, text=f"{header}:", font=("Arial", 14, "bold")).pack(anchor="w", padx=10)
        for item in items:
            label = ctk.CTkLabel(parent, text=item, text_color="blue", cursor="hand2")
            label.pack(anchor="w", padx=10)
            label.bind("<Button-1>", partial(self._on_link_clicked, linked_type, item))

    def _on_link_clicked(self, linked_type, item, event=None):
        self.open_entity_tab(linked_type + "s", item)

    def create_note_frame(self, master=None, initial_text=""):
        if master is None:
            master = self.content_area
        frame = ctk.CTkFrame(master)
        toolbar = ctk.CTkFrame(frame)
        toolbar.pack(fill="x", padx=5, pady=5)
        save_button = ctk.CTkButton(
            toolbar,
            text="Save Note",
            command=lambda: self.save_note_to_file(frame, f"Note_{len(self.tabs)}")
        )
        save_button.pack(side="right", padx=5)
        text_box = ctk.CTkTextbox(frame, wrap="word", height=500)
        text_box.pack(fill="both", expand=True, padx=10, pady=5)
        text_box.insert("1.0", initial_text)
        frame.text_box = text_box
        return frame


    def save_note_to_file(self, note_frame, default_name):
        file_path = filedialog.asksaveasfilename(
            initialfile=default_name,
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")],
            title="Save Note As"
        )
        if not file_path:
            return
        content = note_frame.text_box.get("1.0", "end-1c")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
        messagebox.showinfo("Saved", f"Note saved to {file_path}")
    
    def create_npc_graph_frame(self, master=None):
        if master is None:
            master = self.content_area
        frame = ctk.CTkFrame(master)
        graph_editor = NPCGraphEditor(frame, self.wrappers["NPCs"], self.wrappers["Factions"])
        graph_editor.pack(fill="both", expand=True)
        frame.graph_editor = graph_editor  # Save a reference for state management
        return frame
    
    def reorder_detached_windows(self):
        screen_width = self.winfo_screenwidth()
        margin = 10  # space between windows and screen edge
        current_x = margin
        current_y = margin
        max_row_height = 0

        for name, tab in self.tabs.items():
            if tab.get("detached") and tab.get("window") is not None:
                window = tab["window"]
                window.update_idletasks()
                req_width = window.winfo_reqwidth()
                req_height = window.winfo_reqheight()
                # If adding this window would go beyond screen width, wrap to next line
                if current_x + req_width + margin > screen_width:
                    current_x = margin
                    current_y += max_row_height + margin
                    max_row_height = 0
                window.geometry(f"{req_width}x{req_height}+{current_x}+{current_y}")
                current_x += req_width + margin
                if req_height > max_row_height:
                    max_row_height = req_height

class EntitySelectionView(ctk.CTkFrame):
    def __init__(self, master, entity_type, model_wrapper, template, scenario_detail_view, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.entity_type = entity_type
        self.model_wrapper = model_wrapper
        self.template = template
        self.scenario_detail_view = scenario_detail_view
        self.items = self.model_wrapper.load_items()
        self.filtered_items = self.items.copy()
        self.image_cache = {}
        os.makedirs(PORTRAIT_FOLDER, exist_ok=True)
        self.search_var = ctk.StringVar()
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        search_entry.bind("<KeyRelease>", lambda event: self.filter_items())
        self.table_frame = ctk.CTkScrollableFrame(self)
        self.table_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.headers = []
        self.has_portrait = any(f["name"] == "Portrait" for f in self.template["fields"])
        if self.has_portrait:
            self.headers.append("Portrait")
        for f in self.template["fields"]:
            if f["name"] != "Portrait":
                self.headers.append(f["name"])
        self.create_table_header()
        self.refresh_list()
        ctk.CTkButton(self, text="Open Selected", command=self.open_selected).pack(side="bottom", pady=5)

    def create_table_header(self):
        total_columns = len(self.headers)
        if self.has_portrait:
            self.table_frame.grid_columnconfigure(0, minsize=60)
        for i in range(1, total_columns):
            self.table_frame.grid_columnconfigure(i, weight=1)
        for col_index, header_text in enumerate(self.headers):
            header_button = ctk.CTkButton(
                self.table_frame, text=header_text, anchor="w",
                command=lambda c=header_text: self.sort_column(c)
            )
            header_button.grid(row=0, column=col_index, sticky="ew", padx=5, pady=2)

    def refresh_list(self):
        for child in self.table_frame.winfo_children():
            if int(child.grid_info()["row"]) > 0:
                child.destroy()
        for row_index, item in enumerate(self.filtered_items, start=1):
            self.create_item_row(item, row_index)

    def create_item_row(self, item, row_index):
        col_index = 0
        if self.has_portrait:
            portrait_path = item.get("Portrait", "")
            if portrait_path and os.path.exists(portrait_path):
                if portrait_path in self.image_cache:
                    ctk_image = self.image_cache[portrait_path]
                else:
                    ctk_image = self.load_image_thumbnail(portrait_path)
                    self.image_cache[portrait_path] = ctk_image
                portrait_label = CTkLabel(self.table_frame, text="", image=ctk_image)
                portrait_label.grid(row=row_index, column=col_index, padx=5, pady=2)
                portrait_label.bind("<Button-1>", lambda e, i=item: self.open_entity(i))
            else:
                label = CTkLabel(self.table_frame, text="[No Image]")
                label.grid(row=row_index, column=col_index, padx=5, pady=2)
                label.bind("<Button-1>", lambda e, i=item: self.open_entity(i))
            col_index += 1
        for field in self.template["fields"]:
            if field["name"] == "Portrait":
                continue
            value = item.get(field["name"], "")
            field_type = field.get("type", "text")
            if field_type == "longtext":
                try:
                    value = format_longtext(value, max_length=200)
                except Exception:
                    value = str(value)
                label = CTkLabel(
                    self.table_frame,
                    text=value,
                    anchor="nw",
                    justify="left",
                    wraplength=500
                )
            else:
                label = CTkLabel(
                    self.table_frame,
                    text=str(value),
                    anchor="nw",
                    justify="left"
                )
            label.grid(row=row_index, column=col_index, sticky="nw", padx=5, pady=2)
            label.bind("<Button-1>", lambda e, i=item: self.open_entity(i))
            col_index += 1

    def load_image_thumbnail(self, path):
        img = Image.open(path)
        img.thumbnail(MAX_PORTRAIT_SIZE)
        ctk_img = CTkImage(light_image=img, dark_image=img, size=MAX_PORTRAIT_SIZE)
        return ctk_img

    def filter_items(self):
        query = self.search_var.get().strip().lower()
        if not query:
            self.filtered_items = self.items.copy()
        else:
            self.filtered_items = [i for i in self.items if any(query in str(v).lower() for v in i.values())]
        self.refresh_list()

    def sort_column(self, column_name):
        self.filtered_items.sort(key=lambda x: str(x.get(column_name, "")).lower())
        self.refresh_list()

    def open_entity(self, item):
        entity_name = item.get("Name", item.get("Title", "Unnamed"))
        self.scenario_detail_view.open_entity_tab(self.entity_type, entity_name)
        self.master.destroy()

    def open_selected(self):
        if not self.filtered_items:
            messagebox.showwarning("No Selection", "No items available to open.")
            return
        self.open_entity(self.filtered_items[0])
    
    