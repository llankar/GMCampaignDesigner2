import re
import time
import os
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

from modules.generic.generic_editor_window import GenericEditorWindow

PORTRAIT_FOLDER = "assets/portraits"
MAX_PORTRAIT_SIZE = (1024, 1024)
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

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
        # We no longer need an image cache since portraits are removed.
        # self.image_cache = {}

        # Remove portrait column altogether.
        # Even if the template includes "Portrait", we ignore it.
        unique_field = next((f["name"] for f in self.template["fields"] if f["name"] != "Portrait"), None)
        self.unique_field = unique_field

        # Define extra columns as every field except "Portrait" and the unique field.
        self.columns = [f["name"] for f in self.template["fields"] if f["name"] not in ["Portrait", unique_field]]

        # Setup search bar
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=(5,45), pady=5)
        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)
        self.search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        search_entry.bind("<Return>", lambda event: self.filter_items(self.search_var.get()))
        ctk.CTkButton(search_frame, text="Filter", command=lambda: self.filter_items(self.search_var.get())).pack(side="left", padx=5)
        ctk.CTkButton(search_frame, text="Add", command=self.add_item).pack(side="left", padx=5)

        # Setup Treeview frame with a dark background.
        tree_frame = ctk.CTkFrame(self, fg_color="#2B2B2B")
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Create a local ttk style for the Treeview.
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Custom.Treeview",
                        background="#2B2B2B",      # dark gray for cells
                        fieldbackground="#2B2B2B", # dark gray for the empty area
                        foreground="white",       # white text
                        rowheight=25,
                        font=("Sego UI", 10, "bold"))
        style.configure("Custom.Treeview.Heading",
                        background="#2B2B2B",
                        foreground="white",
                        font=("Sego UI", 10, "bold"))
        style.map("Custom.Treeview", background=[("selected", "#2B2B2B")])

        # Create the Treeview with extra columns defined in self.columns.
        self.tree = ttk.Treeview(tree_frame,
                                 columns=self.columns,
                                 show="tree headings",
                                 selectmode="browse",
                                 style="Custom.Treeview")
        # Column #0 displays only the unique field ("Name").
        self.tree.heading("#0", text="Name", command=lambda: self.sort_column(self.unique_field))
        self.tree.column("#0", width=180, anchor="w")

        # Setup extra columns using their own names as headers.
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
        # Clear the treeview and begin batch insertion.
        self.tree.delete(*self.tree.get_children())
        self.batch_index = 0
        self.batch_size = 50  # Adjust as needed
        self.insert_next_batch()

    def insert_next_batch(self):
        end_index = min(self.batch_index + self.batch_size, len(self.filtered_items))
        for i in range(self.batch_index, end_index):
            item = self.filtered_items[i]
            raw_val = item.get(self.unique_field, "")
            if isinstance(raw_val, dict):
                raw_val = raw_val.get("text", "")
            unique_value = sanitize_id(raw_val or f"item_{int(time.time() * 1000)}")
            name_text = self.clean_value(item.get(self.unique_field, ""))
            # Build values for extra columns: use empty string if missing.
            values = tuple(self.clean_value(item.get(col, "")) for col in self.columns)
            try:
                self.tree.insert("", "end", iid=unique_value, text=name_text, values=values)
            except Exception as e:
                print("[ERROR] inserting item:", e, unique_value, values)
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

    def sort_column(self, column_name):
        # Determine effective sort key.
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
            editor = GenericEditorWindow(self.master, found_item, self.template, self.model_wrapper, creation_mode=False)
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

    def add_item(self):
        new_item = {}
        if self.open_editor(new_item, creation_mode=True):
            self.items.append(new_item)
            self.model_wrapper.save_items(self.items)
            self.filter_items(self.search_var.get())

    def open_editor(self, item, creation_mode=False):
        editor = GenericEditorWindow(self.master, item, self.template,self.model_wrapper, creation_mode)
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
    
    def add_items(self, items):
        added_count = 0
        for item in items:
            # Check for duplicates by sanitized unique field
            new_id = sanitize_id(str(item.get(self.unique_field, "")))
            if not any(sanitize_id(str(i.get(self.unique_field, ""))) == new_id for i in self.items):
                self.items.append(item)
                added_count += 1
        if added_count:
            self.model_wrapper.save_items(self.items)
            self.filter_items(self.search_var.get())
        