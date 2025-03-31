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
        # We'll keep image cache if needed for later but not used in Treeview columns now.
        self.image_cache = {}

        # Check if template includes a Portrait field.
        self.has_portrait = any(f["name"] == "Portrait" for f in self.template["fields"])
        
        # Determine the unique field (e.g., "Name") – first non-Portrait field.
        unique_field = next((f["name"] for f in self.template["fields"] if f["name"] != "Portrait"), None)
        self.unique_field = unique_field

        # Build extra columns.
        # If a portrait exists, we want a separate "Portrait" column plus any other fields
        # excluding the unique field.
        if self.has_portrait:
            # The first extra column is "Portrait", then any other field except Portrait and unique field.
            self.columns = ["Portrait"] + [f["name"] for f in self.template["fields"] 
                                           if f["name"] not in ["Portrait", unique_field]]
        else:
            self.columns = [f["name"] for f in self.template["fields"] if f["name"] != unique_field]

        # Setup search bar.
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)
        self.search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        search_entry.bind("<Return>", lambda event: self.filter_items(self.search_var.get()))
        ctk.CTkButton(search_frame, text="Filter", command=lambda: self.filter_items(self.search_var.get())).pack(side="left", padx=5)
        ctk.CTkButton(search_frame, text="Add", command=self.add_item).pack(side="left", padx=5)

        # Setup Treeview frame.
        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Create the Treeview.
        # Using show="tree headings" to display column #0 (the tree column) and the additional columns.
        self.tree = ttk.Treeview(tree_frame, columns=self.columns, show="tree headings", selectmode="browse")
        
        # Column #0 is dedicated to the Name (unique field).
        self.tree.heading("#0", text="Name", command=lambda: self.sort_column(self.unique_field))
        self.tree.column("#0", width=180, anchor="w")
        
        # Set up the extra columns.
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
        self.batch_index = 0
        self.batch_size = 50  # Adjust batch size if needed.
        self.insert_next_batch()

    def insert_next_batch(self):
        end_index = min(self.batch_index + self.batch_size, len(self.filtered_items))
        for i in range(self.batch_index, end_index):
            item = self.filtered_items[i]
            # Get the unique field value for column #0.
            raw_val = item.get(self.unique_field, "")
            if isinstance(raw_val, dict):
                raw_val = raw_val.get("text", "")
            unique_value = sanitize_id(raw_val or f"item_{int(time.time() * 1000)}")
            name_text = self.clean_value(item.get(self.unique_field, ""))
            
            if self.has_portrait:
                # For the portrait column, if a portrait was chosen and file exists, show a placeholder (e.g., basename) 
                # Otherwise, use an empty string.
                portrait_path = item.get("Portrait", "")
                if portrait_path and os.path.exists(portrait_path):
                    # Option: use the file basename as an indicator.
                    portrait_text = os.path.basename(portrait_path)
                else:
                    portrait_text = ""
                # For remaining extra columns, build values for each.
                # Note: self.columns[0] is "Portrait", so we skip it here.
                extra_values = tuple(self.clean_value(item.get(col, "")) for col in self.columns[1:])
                # Build the full tuple: first element for the "Portrait" column, then extra columns.
                values = (portrait_text,) + extra_values
                try:
                    self.tree.insert("", "end", iid=unique_value, text=name_text, values=values)
                except Exception as e:
                    print("[ERROR] inserting item with portrait:", e, unique_value, values)
            else:
                values = tuple(self.clean_value(item.get(col, "")) for col in self.columns)
                try:
                    self.tree.insert("", "end", iid=unique_value, text=name_text, values=values)
                except Exception as e:
                    print("[ERROR] inserting item without portrait:", e, unique_value, values)
        self.batch_index = end_index
        if self.batch_index < len(self.filtered_items):
            self.after(50, self.insert_next_batch)

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
        # Determine effective sort key (refine this as needed)
        if self.has_portrait:
            try:
                idx = self.columns.index(column_name)
            except ValueError:
                sort_col = column_name
            else:
                if idx < len(self.columns) - 1:
                    sort_col = self.columns[idx + 1]
                else:
                    sort_col = column_name
        else:
            try:
                idx = self.columns.index(column_name)
            except ValueError:
                sort_col = column_name
            else:
                if idx < len(self.columns):
                    sort_col = self.columns[idx]
                else:
                    sort_col = column_name

        if not hasattr(self, "sort_directions"):
            self.sort_directions = {}
        ascending = self.sort_directions.get(sort_col, True)
        self.sort_directions[sort_col] = not ascending

        self.filtered_items.sort(key=lambda x: str(x.get(sort_col, "")), reverse=not ascending)
        self.refresh_list()

    def on_double_click(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        found_item = next((item for item in self.filtered_items 
                           if sanitize_id(str(item.get(self.unique_field, ""))) == item_id), None)
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
        menu.post(event.x_root, event.y_root)

    def delete_item_by_id(self, item_id):
        self.items = [item for item in self.items 
                      if sanitize_id(str(item.get(self.unique_field, ""))) != item_id]
        self.model_wrapper.save_items(self.items)
        self.filter_items(self.search_var.get())

    def update_portrait(self, item_id):
        # Implement portrait update logic if necessary.
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
