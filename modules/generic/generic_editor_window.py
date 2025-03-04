import customtkinter as ctk
import json
import os
from modules.helpers.rich_text_editor import RichTextEditor
from modules.helpers.window_helper import position_window_at_top

FACTIONS_FILE = "data/factions.json"
NPCS_FILE = "data/npcs.json"
PLACES_FILE = "data/places.json"

def load_factions_list():
    if os.path.exists(FACTIONS_FILE):
        with open(FACTIONS_FILE, "r", encoding="utf-8") as f:
            return [faction["Name"] for faction in json.load(f)]
    return []

def load_npcs_list():
    if os.path.exists(NPCS_FILE):
        with open(NPCS_FILE, "r", encoding="utf-8") as f:
            return [npc["Name"] for npc in json.load(f)]
    return []

def load_places_list():
    if os.path.exists(PLACES_FILE):
        with open(PLACES_FILE, "r", encoding="utf-8") as f:
            return [place["Name"] for place in json.load(f)]
    return []

class GenericEditorWindow(ctk.CTkToplevel):
    def __init__(self, master, item, template, creation_mode=False):
        super().__init__(master)

        self.item = item
        self.template = template
        self.saved = False
        self.field_widgets = {}

        self.transient(master)
        self.lift()
        self.grab_set()
        self.focus_force()

        self.title("Create Item" if creation_mode else "Edit Item")

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True)

        self.scroll_frame = ctk.CTkScrollableFrame(self.main_frame)
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        for field in template["fields"]:
            ctk.CTkLabel(self.scroll_frame, text=field["name"]).pack(pady=(5, 0), anchor="w")

            if field["type"] == "longtext":
                self.create_longtext_field(field)

            elif field["name"] == "Faction":
                self.create_faction_field(field)

            elif field["name"] in ["NPCs", "Places"]:
                self.create_dynamic_combobox_list(field)

            else:
                self.create_text_entry(field)

        self.create_action_bar()

        self.geometry("1000x600")
        self.minsize(1000, 600)

        self.update_idletasks()
        position_window_at_top(self)

    # === Création des champs ===

    def create_longtext_field(self, field):
        value = self.item.get(field["name"], "")

        editor = RichTextEditor(self.scroll_frame)

        if isinstance(value, dict):
            editor.load_text_data(value)
        else:
            editor.text_widget.insert("1.0", value)

        editor.pack(fill="both", expand=True, pady=5)
        self.field_widgets[field["name"]] = editor

    def create_faction_field(self, field):
        factions_list = load_factions_list()
        combobox = ctk.CTkComboBox(self.scroll_frame, values=factions_list)
        combobox.pack(fill="x", pady=5)
        current_faction = self.item.get("Faction", "")
        if current_faction in factions_list:
            combobox.set(current_faction)
        self.field_widgets[field["name"]] = combobox

    def create_dynamic_combobox_list(self, field):
        container = ctk.CTkFrame(self.scroll_frame)
        container.pack(fill="x", pady=5)

        combobox_list = []

        if field["name"] == "NPCs":
            options_list = load_npcs_list()
        elif field["name"] == "Places":
            options_list = load_places_list()
        else:
            options_list = []

        initial_values = self.item.get(field["name"], [])

        def add_combobox(initial_value=None):
            row = ctk.CTkFrame(container)
            row.pack(fill="x", pady=2)

            combobox = ctk.CTkComboBox(row, values=options_list)
            if initial_value and initial_value in options_list:
                combobox.set(initial_value)
            combobox.pack(side="left", expand=True, fill="x")

            remove_button = ctk.CTkButton(row, text="X", width=30, command=lambda: remove_this(row, combobox))
            remove_button.pack(side="right", padx=5)

            combobox_list.append(combobox)

        def remove_this(row, combobox):
            combobox_list.remove(combobox)
            row.destroy()

        for value in initial_values:
            add_combobox(value)

        add_button = ctk.CTkButton(self.scroll_frame, text=f"Add {field['name'][6:]}", command=lambda: add_combobox())
        add_button.pack(anchor="w", pady=2)

        self.field_widgets[field["name"]] = combobox_list

    def create_text_entry(self, field):
        entry = ctk.CTkEntry(self.scroll_frame)
        entry.insert(0, self.item.get(field["name"], ""))
        entry.pack(fill="x", pady=5)
        self.field_widgets[field["name"]] = entry

    def create_action_bar(self):
        action_bar = ctk.CTkFrame(self.main_frame)
        action_bar.pack(fill="x", pady=5)

        ctk.CTkButton(action_bar, text="Cancel", command=self.destroy).pack(side="right", padx=5)
        ctk.CTkButton(action_bar, text="Save", command=self.save).pack(side="right", padx=5)

    # === Sauvegarde ===

    def save(self):
        for field in self.template["fields"]:
            widget = self.field_widgets[field["name"]]

            if field["type"] == "longtext":
                self.item[field["name"]] = widget.get_text_data()

            elif field["name"] == "Faction":
                self.item[field["name"]] = widget.get()

            elif field["name"] in ["Places", "NPCs"]:
                self.item[field["name"]] = [cb.get() for cb in widget if cb.get()]

            else:
                self.item[field["name"]] = widget.get()

        self.saved = True
        self.destroy()
