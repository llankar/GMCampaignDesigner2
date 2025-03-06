import customtkinter as ctk
import os
import json
from tkinter import Listbox, MULTIPLE, messagebox
from PIL import Image, ImageTk
from functools import partial
from modules.generic.generic_model_wrapper import GenericModelWrapper


class ScenarioDetailView(ctk.CTkFrame):
    def __init__(self, master, scenario_item, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.scenario = scenario_item

        # Setup model wrappers and templates
        self.wrappers = {
            "Scenarios": GenericModelWrapper("scenarios"),
            "Places": GenericModelWrapper("places"),
            "NPCs": GenericModelWrapper("npcs"),
            "Factions": GenericModelWrapper("factions")
        }

        self.templates = {
            "Scenarios": self.load_template("scenarios\\scenarios_template.json"),
            "Places": self.load_template("places\\places_template.json"),
            "NPCs": self.load_template("npcs\\npcs_template.json"),
            "Factions": self.load_template("factions\\factions_template.json")
        }

        self.tabs = {}
        self.current_tab = None

        self.tab_bar = ctk.CTkFrame(self, height=40)
        self.tab_bar.pack(side="top", fill="x")

        self.content_area = ctk.CTkFrame(self)
        self.content_area.pack(fill="both", expand=True)

        self.add_button = ctk.CTkButton(self.tab_bar, text="+", width=40, command=self.add_new_tab)
        self.add_button.pack(side="right", padx=5)

        scenario_name = scenario_item.get("Title", "Unnamed Scenario")
        self.add_tab(scenario_name, self.create_entity_frame("Scenarios", scenario_item))

    def load_template(self, filename):
        base_path = os.path.dirname(__file__)
        template_path = os.path.join(base_path, "..", filename)
        with open(template_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def add_tab(self, name, content_frame):
        if name in self.tabs:
            self.show_tab(name)
            return

        tab_frame = ctk.CTkFrame(self.tab_bar)
        tab_frame.pack(side="left", padx=2, pady=5)

        tab_button = ctk.CTkButton(tab_frame, text=name, width=150, command=lambda: self.show_tab(name))
        tab_button.pack(side="left")

        close_button = ctk.CTkButton(tab_frame, text="❌", width=30, command=lambda: self.close_tab(name))
        close_button.pack(side="left")

        self.tabs[name] = {"button_frame": tab_frame, "content_frame": content_frame, "button": tab_button}

        content_frame.pack_forget()
        self.show_tab(name)

        self.reposition_add_button()

    def show_tab(self, name):
        if self.current_tab and self.current_tab in self.tabs:
            # Reset style for previous tab
            self.tabs[self.current_tab]["button"].configure(fg_color=("gray75", "gray25"))

            # Hide old content
            self.tabs[self.current_tab]["content_frame"].pack_forget()

        # Set new tab
        self.current_tab = name

        # Highlight active tab
        self.tabs[name]["button"].configure(fg_color=("gray55", "gray15"))

        # Show content
        self.tabs[name]["content_frame"].pack(fill="both", expand=True)

    def close_tab(self, name):
        if len(self.tabs) == 1:
            return

        self.tabs[name]["button_frame"].destroy()
        self.tabs[name]["content_frame"].destroy()
        del self.tabs[name]

        if self.current_tab == name and self.tabs:
            self.show_tab(next(iter(self.tabs)))

        self.reposition_add_button()


    def reposition_add_button(self):
        self.add_button.pack_forget()
        self.add_button.pack(side="right", padx=5)

    def add_new_tab(self):
        options = ["Factions", "Places", "NPCs", "Scenarios", "Empty Tab"]

        popup = ctk.CTkToplevel(self)
        popup.title("Create New Tab")
        popup.geometry("300x250")
        popup.transient(self.winfo_toplevel())
        popup.grab_set()
        popup.focus_force()

        ctk.CTkLabel(popup, text="Choose tab type:").pack(pady=10)
        for option in options:
            ctk.CTkButton(popup, text=option, command=lambda o=option: self.open_selection_window(o, popup)).pack(pady=2)

    def open_selection_window(self, entity_type, popup):
        popup.destroy()

        if entity_type == "Empty Tab":
            self.add_tab(f"Note {len(self.tabs)}", self.create_note_frame())
            return

        wrapper = self.wrappers[entity_type]
        items = wrapper.load_items()

        select_win = ctk.CTkToplevel(self)
        select_win.title(f"Select {entity_type}")
        select_win.geometry("400x300")
        select_win.transient(self.winfo_toplevel())
        select_win.grab_set()
        select_win.focus_force()

        listbox = Listbox(select_win, selectmode=MULTIPLE)
        listbox.pack(fill="both", expand=True, padx=10, pady=10)

        item_names = [item.get("Name", item.get("Title", "Unnamed")) for item in items]
        for name in item_names:
            listbox.insert("end", name)

        def open_selected():
            for i in listbox.curselection():
                self.open_entity_tab(entity_type, item_names[i])
            select_win.destroy()

        ctk.CTkButton(select_win, text="Open Selected", command=open_selected).pack(pady=5)

    def open_entity_tab(self, entity_type, name):
        wrapper = self.wrappers[entity_type]
        items = wrapper.load_items()

        key = "Title" if entity_type == "Scenarios" else "Name"
        item = next((i for i in items if i.get(key) == name), None)

        if not item:
            messagebox.showerror("Error", f"{entity_type[:-1]} '{name}' not found.")
            return

        frame = self.create_entity_frame(entity_type, item)
        self.add_tab(name, frame)

    def create_entity_frame(self, entity_type, entity):
        frame = ctk.CTkFrame(self.content_area)
        template = self.templates[entity_type]

        if entity_type == "NPCs" and "Portrait" in entity and os.path.exists(entity["Portrait"]):
            # Display portrait at the top
            img = Image.open(entity["Portrait"])
            img = img.resize((200, 200), Image.Resampling.LANCZOS)
            ctk_image = ctk.CTkImage(light_image=img, size=(200, 200))
            portrait_label = ctk.CTkLabel(frame, image=ctk_image, text="")
            portrait_label.pack(pady=10)

        for field in template["fields"]:
            field_name = field["name"]
            field_type = field["type"]

            # Skip "Portrait" field for NPCs since it's handled manually above
            if entity_type == "NPCs" and field_name == "Portrait":
                continue

            if field_type in ["text", "longtext"]:
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
        text_box = ctk.CTkTextbox(frame, wrap="word", height=500)
        text_box.pack(fill="both", expand=True, padx=10, pady=5)
        frame.text_box = text_box
        return frame
