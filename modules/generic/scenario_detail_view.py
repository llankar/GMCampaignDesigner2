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

PORTRAIT_FOLDER = "assets/portraits"
MAX_PORTRAIT_SIZE = (32, 32)  # Thumbnail size for lists

class ScenarioDetailView(ctk.CTkFrame):
    def __init__(self, master, scenario_item, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        # Persistent cache for portrait images
        self.portrait_images = {}  
        self.scenario = scenario_item

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

        self.tab_bar = ctk.CTkFrame(self, height=40)
        self.tab_bar.pack(side="top", fill="x")

        self.content_area = ctk.CTkFrame(self)
        self.content_area.pack(fill="both", expand=True)

        self.add_button = ctk.CTkButton(self.tab_bar, text="+", width=40, command=self.add_new_tab)

        scenario_name = scenario_item.get("Title", "Unnamed Scenario")
        # Pass a factory lambda that recreates the frame with a new master.
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
        detach_button = ctk.CTkButton(tab_frame, text="Detach", width=50,
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
            self.tabs[name]["detach_button"].configure(
                text="Detach",
                command=lambda: self.toggle_detach_tab(name)
            )
        else:
            self.detach_tab(name)
            self.tabs[name]["detach_button"].configure(
                text="Reattach",
                command=lambda: self.toggle_detach_tab(name)
            )

    def detach_tab(self, name):
        print(f"[DETACH] Start detaching tab: {name}")
        if self.tabs[name]["detached"]:
            print(f"[DETACH] Tab '{name}' is already detached.")
            return

        # Remove the old content frame from the main content area.
        old_frame = self.tabs[name]["content_frame"]
        old_frame.pack_forget()

        # Create the detached window.
        detached_window = ctk.CTkToplevel(self)
        detached_window.title(name)
        # Disable the close (X) button.
        detached_window.protocol("WM_DELETE_WINDOW", lambda: None)
        print(f"[DETACH] Detached window created: {detached_window}")

        # Use the stored factory function to recreate the content frame in the detached window.
        factory = self.tabs[name].get("factory")
        if factory is None:
            new_frame = old_frame
        else:
            new_frame = factory(detached_window)
        new_frame.pack(fill="both", expand=True)
        print(f"[DETACH] New frame in detached window created: {new_frame}")

        # Check if the new frame already has a portrait label.
        if hasattr(new_frame, "portrait_label"):
            self.tabs[name]["portrait_label"] = new_frame.portrait_label
            print(f"[DETACH] Using existing portrait label from new frame.")
        else:
            # Optionally, if there is no portrait label, recreate it.
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



    def reattach_tab(self, name):
        print(f"[REATTACH] Start reattaching tab: {name}")
        if not self.tabs[name].get("detached", False):
            print(f"[REATTACH] Tab '{name}' is not detached.")
            return

        # Destroy the detached window.
        detached_window = self.tabs[name]["window"]
        if detached_window:
            detached_window.destroy()
            print("[REATTACH] Detached window destroyed.")

        # Recreate the content frame using the factory function with the main content area as master.
        factory = self.tabs[name].get("factory")
        if factory is None:
            new_frame = self.tabs[name]["content_frame"]
        else:
            new_frame = factory(self.content_area)
        new_frame.pack(fill="both", expand=True)
        self.tabs[name]["content_frame"] = new_frame
        self.tabs[name]["detached"] = False
        self.tabs[name]["window"] = None
        self.show_tab(name)
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
        if self.current_tab and self.current_tab in self.tabs:
            self.tabs[self.current_tab]["button"].configure(fg_color=("gray75", "gray25"))
            self.tabs[self.current_tab]["content_frame"].pack_forget()

        self.current_tab = name
        self.tabs[name]["button"].configure(fg_color=("gray55", "gray15"))
        self.tabs[name]["content_frame"].pack(fill="both", expand=True)

    def add_new_tab(self):
        options = ["Factions", "Places", "NPCs", "Scenarios", "Empty Tab", "NPC Graph"]
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
        if entity_type == "Empty Tab":
            self.add_tab(f"Note {len(self.tabs) + 1}", self.create_note_frame())
            return
        elif entity_type == "NPC Graph":
            self.add_tab("NPC Graph", self.create_npc_graph_frame())
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

    def create_note_frame(self):
        frame = ctk.CTkFrame(self.content_area)
        toolbar = ctk.CTkFrame(frame)
        toolbar.pack(fill="x", padx=5, pady=5)
        save_button = ctk.CTkButton(toolbar, text="Save Note", command=lambda: self.save_note_to_file(frame, f"Note_{len(self.tabs)}"))
        save_button.pack(side="right", padx=5)
        text_box = ctk.CTkTextbox(frame, wrap="word", height=500)
        text_box.pack(fill="both", expand=True, padx=10, pady=5)
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

    def create_npc_graph_frame(self):
        frame = ctk.CTkFrame(self.content_area)
        NPCGraphEditor(frame, self.wrappers["NPCs"], self.wrappers["Factions"]).pack(fill="both", expand=True)
        return frame

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
