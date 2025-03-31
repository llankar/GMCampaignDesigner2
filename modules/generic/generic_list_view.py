import re
import time
import os
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

from modules.helpers.text_helpers import format_longtext
from modules.generic.generic_editor_window import GenericEditorWindow

PORTRAIT_FOLDER = "assets/portraits"
MAX_PORTRAIT_SIZE = (1024, 1024)

def sanitize_id(s):
    sanitized = re.sub(r'[^a-zA-Z0-9]+', '_', str(s))
    return sanitized.strip('_')

class GenericListView(ctk.CTkFrame):
    def __init__(self, master, model_wrapper, template, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.model_wrapper = model_wrapper
        self.template = template
        os.makedirs(PORTRAIT_FOLDER, exist_ok=True)

        self.items = self.model_wrapper.load_items()
        self.filtered_items = self.items.copy()
        self.image_cache = {}

        self.has_portrait = any(f["name"] == "Portrait" for f in self.template["fields"])
        
        # Columns setup: Portrait in '#0', rest in columns
        unique_field = next((f["name"] for f in self.template["fields"] if f["name"] != "Portrait"), None)

        if self.has_portrait:
            self.columns = [f["name"] for f in self.template["fields"] if f["name"] != "Portrait"]
        else:
            # Do not include unique_field in columns if there's no portrait
            self.columns = [f["name"] for f in self.template["fields"] if f["name"] not in ["Portrait", unique_field]]

        # Search bar
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)
        self.search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        search_entry.bind("<Return>", lambda event: self.filter_items(self.search_var.get()))
        ctk.CTkButton(search_frame, text="Filter", command=lambda: self.filter_items(self.search_var.get())).pack(side="left", padx=5)
        ctk.CTkButton(search_frame, text="Add", command=self.add_item).pack(side="left", padx=5)

        # Treeview frame
        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Proper tree setup to allow image display
        self.tree = ttk.Treeview(tree_frame, columns=self.columns, show="tree headings", selectmode="browse")
        
        self.tree.heading("#0", text="Portrait" if self.has_portrait else "Name")
        self.tree.column("#0", width=60 if self.has_portrait else 150, anchor="center")

        for col in self.columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c))
            self.tree.column(col, width=150, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.on_right_click)

        self.refresh_list()

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        unique_field = next((f["name"] for f in self.template["fields"] if f["name"] != "Portrait"), None)
        for item in self.filtered_items:
            raw_val = item.get(unique_field, "")
            if isinstance(raw_val, dict):
                raw_val = raw_val.get("text", "")
            unique_value = sanitize_id(raw_val or f"item_{int(time.time() * 1000)}")
            if self.has_portrait:
                portrait_path = item.get("Portrait", "")
                if portrait_path and os.path.exists(portrait_path):
                    image = self.image_cache.get(portrait_path)
                    if not image:
                        image = self.load_image_thumbnail(portrait_path)
                        self.image_cache[portrait_path] = image
                else:
                    image = ""
                # Utiliser le champ unique (par exemple, 'Name') comme texte dans la colonne d'arbre
                tree_text = self.clean_value(item.get(unique_field, ""))
                # Construire la liste des valeurs en retirant le champ unique pour éviter la duplication
                values = [self.clean_value(item.get(col, "")) for col in self.columns if col != unique_field]
                try:
                    self.tree.insert("", "end", iid=unique_value, text=tree_text, image=image, values=values)
                except Exception as e:
                    print("[ERROR] inserting item with portrait:", e, unique_value, values)
            else:
                # Branche pour les entités sans portrait (inchangée)
                values = [self.clean_value(item.get(col, "")) for col in self.columns if col != unique_field]
                tree_text = self.clean_value(raw_val)
                try:
                    self.tree.insert("", "end", iid=unique_value, text=tree_text, values=values)
                except Exception as e:
                    print("[ERROR] inserting item without portrait:", e, unique_value, values)



    def clean_value(self, val):
        if val is None:
            return ""
        elif isinstance(val, dict):
            return self.clean_value(val.get("text", ""))
        elif isinstance(val, list):
            return ", ".join(self.clean_value(elem) for elem in val if elem is not None)
        return str(val).replace("{", "").replace("}", "").strip()

    def load_image_thumbnail(self, path):
        try:
            img = Image.open(path)
            img.thumbnail((32, 32))
            return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"[ERROR] loading image: {path}, {e}")
            return None

    def sort_column(self, column_name):
        self.filtered_items.sort(key=lambda x: str(x.get(column_name, "")))
        self.refresh_list()

    def on_double_click(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        unique_field = next((f["name"] for f in self.template["fields"] if f["name"] != "Portrait"), None)
        found_item = next((item for item in self.filtered_items if sanitize_id(str(item.get(unique_field, ""))) == item_id), None)
        if found_item:
            editor = GenericEditorWindow(self.master, found_item, self.template, creation_mode=False)
            self.master.wait_window(editor)
            if editor.saved:
                self.model_wrapper.save_items(self.items)
                self.refresh_list()

    def on_right_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        self.tree.selection_set(item_id)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Delete", command=lambda: self.delete_item_by_id(item_id))
        if self.has_portrait:
            menu.add_command(label="Update Portrait", command=lambda: self.update_portrait(item_id))
        menu.post(event.x_root, event.y_root)

    def delete_item_by_id(self, item_id):
        unique_field = next((f["name"] for f in self.template["fields"] if f["name"] != "Portrait"), None)
        self.items = [item for item in self.items if sanitize_id(str(item.get(unique_field, ""))) != item_id]
        self.model_wrapper.save_items(self.items)
        self.filter_items(self.search_var.get())

    def update_portrait(self, item_id):
        # implement portrait update logic if necessary
        pass

    def add_item(self):
        new_item = {}
        if self.open_editor(new_item, creation_mode=True):
            self.items.append(new_item)
            self.model_wrapper.save_items(self.items)
            self.filter_items(self.search_var.get())

    def open_editor(self, item, creation_mode=False):
        editor = GenericEditorWindow(self.master, item, self.template, creation_mode)
        self.master.wait_window(editor)
        return editor.saved

    def filter_items(self, query):
        query = query.strip().lower()
        if query:
            self.filtered_items = [
                i for i in self.items if any(query in self.clean_value(v).lower() for v in i.values())
            ]
        else:
            self.filtered_items = self.items.copy()
        self.refresh_list()
