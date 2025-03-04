import customtkinter as ctk
from tkinter import messagebox
from modules.helpers.text_helpers import format_longtext

class GenericListView(ctk.CTkFrame):
    def __init__(self, master, model_wrapper, template, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.model_wrapper = model_wrapper
        self.template = template

        self.search_var = ctk.StringVar()

        # Search bar with Add button
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(pady=5, fill="x")

        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)

        search_entry.bind("<Return>", lambda event: self.filter_items())

        ctk.CTkButton(search_frame, text="Filter", command=self.filter_items).pack(side="left", padx=5)
        ctk.CTkButton(search_frame, text="Add", command=self.add_item).pack(side="left", padx=5)

        # Frame with scrollbar
        list_container = ctk.CTkFrame(self)
        list_container.pack(fill="both", expand=True)

        self.canvas = ctk.CTkCanvas(list_container, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ctk.CTkScrollbar(list_container, command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.list_frame = ctk.CTkFrame(self.canvas)
        self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")

        self.list_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.items = self.model_wrapper.load_items()
        self.filtered_items = self.items.copy()

        self.create_table_header()
        self.refresh_list()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def create_table_header(self):
        headers = [field["name"] for field in self.template["fields"]] + ["Actions"]

        for col, header in enumerate(headers):
            if header != "Actions":
                button = ctk.CTkButton(self.list_frame, text=header, anchor="w", command=lambda col=col: self.sort_column(col))
                button.grid(row=0, column=col, sticky="w", pady=(0, 2), padx=5)
            else:
                label = ctk.CTkLabel(self.list_frame, text=header, anchor="w", padx=5)
                label.grid(row=0, column=col, sticky="w", pady=(0, 2))

    def refresh_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        self.create_table_header()

        if not self.filtered_items:
            ctk.CTkLabel(self.list_frame, text="No items found.").grid(row=1, column=0, columnspan=len(self.template["fields"]) + 1, pady=10)
            return

        for row_index, item in enumerate(self.filtered_items, start=1):
            self.create_item_row(item, row_index)

    def create_item_row(self, item, row_index):
        for col, field in enumerate(self.template["fields"]):
            value = item.get(field["name"], "")
            if field["type"] == "longtext":
                value = format_longtext(value, max_length=100)

            label = ctk.CTkLabel(self.list_frame, text=value, anchor="w", padx=5, wraplength=200)
            label.grid(row=row_index, column=col, sticky="w", pady=2)

        action_frame = ctk.CTkFrame(self.list_frame)
        action_frame.grid(row=row_index, column=len(self.template["fields"]), sticky="w")

        ctk.CTkButton(action_frame, text="Edit", command=lambda i=item: self.edit_item(i)).pack(side="left", padx=2)
        ctk.CTkButton(action_frame, text="Delete", command=lambda i=item: self.delete_item(i)).pack(side="left", padx=2)

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

    def add_item(self, new_item=None):
        if new_item is None:
            new_item = {}
            if not self.model_wrapper.edit_item(new_item, creation_mode=True):
                return
        self.items.append(new_item)
        self.model_wrapper.save_items(self.items)
        self.filter_items()

    def edit_item(self, item):
        if self.model_wrapper.edit_item(item, creation_mode=False):
            self.model_wrapper.save_items(self.items)
            self.filter_items()

    def delete_item(self, item):
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete '{item.get('Name', 'Unnamed')}'?"):
            self.items.remove(item)
            self.model_wrapper.save_items(self.items)
            self.filter_items()

    def sort_column(self, col_index):
        field_name = self.template["fields"][col_index]["name"]

        def get_sort_value(item):
            value = item.get(field_name, "")
            if isinstance(value, dict):
                return value.get("text", "")
            return value

        self.filtered_items.sort(key=lambda x: get_sort_value(x))
        self.refresh_list()