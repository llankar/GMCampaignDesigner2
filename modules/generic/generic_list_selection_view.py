import re
import time
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk

class GenericListSelectionView(ctk.CTkFrame):
    def __init__(self, master, entity_type, model_wrapper, template, on_select_callback=None, *args, **kwargs):
        """
        :param master: Parent widget.
        :param entity_type: String representing the entity type.
        :param model_wrapper: A wrapper that provides a load_items() method.
        :param template: A dict defining the fields for the entity.
        :param on_select_callback: Function to call when an entity is selected (e.g. double-clicked). Receives the entity dict.
        """
        super().__init__(master, *args, **kwargs)
        self.entity_type = entity_type
        self.model_wrapper = model_wrapper
        self.template = template
        self.on_select_callback = on_select_callback

        # Load data and initialize filtered list.
        self.items = self.model_wrapper.load_items()
        self.filtered_items = self.items.copy()

        # Determine the unique field (e.g., "Name") as the first field that is not "Portrait"
        self.unique_field = next((f["name"] for f in self.template["fields"] if f["name"] != "Portrait"), None)
        # Define extra columns as every field except "Portrait" and the unique field.
        self.columns = [f["name"] for f in self.template["fields"] if f["name"] not in ["Portrait", self.unique_field]]

        # Create a search bar.
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)
        self.search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        search_entry.bind("<KeyRelease>", lambda event: self.filter_items())

        # Create the Treeview.
        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree = ttk.Treeview(tree_frame, columns=self.columns, show="tree headings", selectmode="browse")
        # The tree column (#0) shows the unique field.
        self.tree.heading("#0", text=self.unique_field)
        self.tree.column("#0", width=150, anchor="w")
        # Set up extra columns.
        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="w")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # Bind a double-click event to trigger selection.
        self.tree.bind("<Double-1>", self.on_double_click)
        self.refresh_list()

    def refresh_list(self):
        """Clear the tree and insert all filtered items."""
        self.tree.delete(*self.tree.get_children())
        for item in self.filtered_items:
            raw_val = item.get(self.unique_field, "")
            if isinstance(raw_val, dict):
                raw_val = raw_val.get("text", "")
            iid = self.sanitize_id(raw_val or f"item_{int(time.time()*1000)}")
            # Build extra column values.
            values = [str(item.get(col, "")) for col in self.columns]
            self.tree.insert("", "end", iid=iid, text=raw_val, values=values)

    def filter_items(self):
        """Filter items based on the search entry."""
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
        # Find the selected item based on the unique field.
        selected_item = next(
            (item for item in self.filtered_items 
            if self.sanitize_id(str(item.get(self.unique_field, ""))) == item_id),
            None
        )
        if selected_item and self.on_select_callback:
            # Determine the entity's name using "Name" or fallback to "Title"
            entity_name = selected_item.get("Name", selected_item.get("Title", "Unnamed"))
            # Call the callback with both the entity type and the entity name.
            self.on_select_callback(self.entity_type, entity_name)


    def sanitize_id(self, s):
        """Utility to create a safe id for the tree."""
        sanitized = re.sub(r'[^a-zA-Z0-9]+', '_', str(s))
        return sanitized.strip('_')
