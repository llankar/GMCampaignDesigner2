import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import time
import re

class GenericListSelectionView(ctk.CTkFrame):
    def __init__(self, master, entity_type, model_wrapper, template, on_select_callback=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.entity_type = entity_type
        self.model_wrapper = model_wrapper
        self.template = template
        self.on_select_callback = on_select_callback

        # Load items and prepare columns
        self.items = self.model_wrapper.load_items()
        self.filtered_items = self.items.copy()
        # Use the first field that is not "Portrait" as the unique field
        self.unique_field = next((f["name"] for f in self.template["fields"] if f["name"] != "Portrait"), None)
        # Extra columns: all fields except "Portrait" and the unique field
        self.columns = [f["name"] for f in self.template["fields"] if f["name"] not in ["Portrait", self.unique_field]]

        # --- Create Search Bar ---
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)
        self.search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        search_entry.bind("<KeyRelease>", lambda event: self.filter_items())

        # --- Create a container for the Treeview with a dark background ---
        tree_frame = ctk.CTkFrame(self, fg_color="#2B2B2B")
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Create a local ttk style for the Treeview ---
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Custom.Treeview",
                        background="#2B2B2B",      # dark gray for cells
                        fieldbackground="#2B2B2B", # dark gray for the empty area
                        foreground="white",       # white text
                        rowheight=25)
        style.configure("Custom.Treeview.Heading",
                        background="#2B2B2B",
                        foreground="white")
        style.map("Custom.Treeview", background=[("selected", "#2B2B2B")])

        # --- Create the Treeview using the custom style ---
        self.tree = ttk.Treeview(tree_frame,
                                 columns=self.columns,
                                 show="tree headings",
                                 selectmode="browse",
                                 style="Custom.Treeview")
        self.tree.heading("#0", text=self.unique_field)
        self.tree.column("#0", width=150, anchor="w")
        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="w")
        # Add a vertical scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # Bind double-click event
        self.tree.bind("<Double-1>", self.on_double_click)
        self.refresh_list()

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for item in self.filtered_items:
            # For the unique field (usually "Name")
            raw_val = item.get(self.unique_field, "")
            if isinstance(raw_val, dict):
                raw_val = raw_val.get("text", "")
            iid = self.sanitize_id(raw_val or f"item_{int(time.time()*1000)}")
            
            # For the extra columns, if the value is a dict, show just the "text"
            def get_display_value(val):
                if isinstance(val, dict):
                    return val.get("text", "")
                return str(val)
            
            values = [get_display_value(item.get(col, "")) for col in self.columns]
            self.tree.insert("", "end", iid=iid, text=raw_val, values=values)


    def filter_items(self):
        query = self.search_var.get().strip().lower()
        if not query:
            self.filtered_items = self.items.copy()
        else:
            self.filtered_items = [
                item for item in self.items
                if any(query in str(v).lower() for v in item.values())
            ]
        self.refresh_list()

    def on_double_click(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        selected_item = next(
            (item for item in self.filtered_items if self.sanitize_id(str(item.get(self.unique_field, ""))) == item_id),
            None
        )
        if selected_item and self.on_select_callback:
            entity_name = selected_item.get("Name", selected_item.get("Title", "Unnamed"))
            self.on_select_callback(self.entity_type, entity_name)

    def sanitize_id(self, s):
        return re.sub(r'[^a-zA-Z0-9]+', '_', str(s)).strip('_')
