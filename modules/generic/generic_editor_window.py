import customtkinter as ctk
import json
import os
from modules.helpers.rich_text_editor import RichTextEditor
from modules.helpers.window_helper import position_window_at_top
from PIL import Image, ImageTk
from tkinter import filedialog



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
            elif field["name"] == "Portrait":
                self.create_portrait_field(field)
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
            elif field["name"] == "Portrait":
                self.item[field["name"]] = self.portrait_path  # Use the stored path
            else:
                self.item[field["name"]] = widget.get()
        self.saved = True
        self.destroy()
    def create_portrait_field(self, field):
        frame = ctk.CTkFrame(self.scroll_frame)
        frame.pack(fill="x", pady=5)

        self.portrait_path = self.item.get("Portrait", "")

        if self.portrait_path and os.path.exists(self.portrait_path):
            image = Image.open(self.portrait_path).resize((64, 64))
            self.portrait_image = ImageTk.PhotoImage(image)
            self.portrait_label = ctk.CTkLabel(frame, image=self.portrait_image, text="")
        else:
            self.portrait_label = ctk.CTkLabel(frame, text="[No Image]")

        self.portrait_label.pack(side="left", padx=5)

        ctk.CTkButton(frame, text="Select Portrait", command=self.select_portrait).pack(side="left", padx=5)

        self.field_widgets[field["name"]] = self.portrait_path


    def select_portrait(self):
        file_path = filedialog.askopenfilename(
            title="Select Portrait Image",
            filetypes=[
                ("Image Files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp"),
                ("PNG Files", "*.png"),
                ("JPEG Files", "*.jpg;*.jpeg"),
                ("GIF Files", "*.gif"),
                ("Bitmap Files", "*.bmp"),
                ("WebP Files", "*.webp"),
                ("All Files", "*.*")
            ]
        )

        if file_path:
            self.portrait_path = self.copy_and_resize_portrait(file_path)
            self.portrait_label.configure(text=os.path.basename(self.portrait_path))

    def copy_and_resize_portrait(self, src_path):
        PORTRAIT_FOLDER = "assets/portraits"
        MAX_PORTRAIT_SIZE = (128, 128)

        os.makedirs(PORTRAIT_FOLDER, exist_ok=True)

        npc_name = self.item.get("Name", "Unnamed").replace(" ", "_")
        ext = os.path.splitext(src_path)[-1].lower()
        dest_filename = f"{npc_name}_{id(self)}{ext}"
        dest_path = os.path.join(PORTRAIT_FOLDER, dest_filename)

        with Image.open(src_path) as img:
            img = img.convert("RGB")
            img.thumbnail(MAX_PORTRAIT_SIZE)
            img.save(dest_path)

        return dest_path
