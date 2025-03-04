import customtkinter as ctk
import json
import os
from modules.helpers.rich_text_editor import RichTextEditor
from modules.helpers.window_helper import position_window_at_top

FACTIONS_FILE = "data/factions.json"

def load_factions_list():
    if os.path.exists(FACTIONS_FILE):
        with open(FACTIONS_FILE, "r", encoding="utf-8") as f:
            factions = json.load(f)
            return [faction["Name"] for faction in factions]
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
                value = item.get(field["name"], "")

                editor = RichTextEditor(self.scroll_frame)

                if isinstance(value, dict):
                    editor.load_text_data(value)
                else:
                    editor.text_widget.insert("1.0", value)

                editor.pack(fill="both", expand=True, pady=5)
                self.field_widgets[field["name"]] = editor

            elif field["name"] == "Faction":
                factions_list = load_factions_list()
                combobox = ctk.CTkComboBox(self.scroll_frame, values=factions_list)
                combobox.pack(fill="x", pady=5)
                current_faction = item.get("Faction", "")
                if current_faction in factions_list:
                    combobox.set(current_faction)
                self.field_widgets[field["name"]] = combobox

            else:
                entry = ctk.CTkEntry(self.scroll_frame)
                entry.insert(0, item.get(field["name"], ""))
                entry.pack(fill="x", pady=5)
                self.field_widgets[field["name"]] = entry

        # Barre d'action (toujours visible)
        action_bar = ctk.CTkFrame(self.main_frame)
        action_bar.pack(fill="x", pady=5)

        ctk.CTkButton(action_bar, text="Cancel", command=self.destroy).pack(side="right", padx=5)
        ctk.CTkButton(action_bar, text="Save", command=self.save).pack(side="right", padx=5)

        self.geometry("1000x600")
        self.minsize(1000, 600)

        self.update_idletasks()
        position_window_at_top(self)

    def save(self):
        for field in self.template["fields"]:
            widget = self.field_widgets[field["name"]]

            if field["type"] == "longtext":
                self.item[field["name"]] = widget.get_text_data()
            elif field["name"] == "Faction":
                self.item["Faction"] = widget.get()
            else:
                self.item[field["name"]] = widget.get()

        self.saved = True
        self.destroy()
