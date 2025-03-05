import customtkinter as ctk
from tkinter import messagebox, filedialog
from customtkinter import CTkLabel, CTkImage 
from PIL import Image
from modules.helpers.text_helpers import format_longtext
import os
import shutil

PORTRAIT_FOLDER = "assets/portraits"
MAX_PORTRAIT_SIZE = (128, 128)  # Resize to this size for storage

class GenericListView(ctk.CTkFrame):
    def __init__(self, master, model_wrapper, template, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.model_wrapper = model_wrapper
        self.template = template

        os.makedirs(PORTRAIT_FOLDER, exist_ok=True)

        self.search_var = ctk.StringVar()

        search_frame = ctk.CTkFrame(self)
        search_frame.pack(pady=5, fill="x")

        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)

        search_entry.bind("<Return>", lambda event: self.filter_items())

        ctk.CTkButton(search_frame, text="Filter", command=self.filter_items).pack(side="left", padx=5)
        ctk.CTkButton(search_frame, text="Add", command=self.add_item).pack(side="left", padx=5)

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

        self.canvas.bind("<Enter>", lambda _: self.bind_mousewheel())
        self.canvas.bind("<Leave>", lambda _: self.unbind_mousewheel())

        self.items = self.model_wrapper.load_items()
        self.filtered_items = self.items.copy()

        self.create_table_header()
        self.refresh_list()

    def bind_mousewheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def unbind_mousewheel(self):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        if self.canvas.winfo_exists():
            self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def create_table_header(self):
        headers = [field["name"] for field in self.template["fields"] if field["name"] != "Portrait"]

        has_portrait = any(f["name"] == "Portrait" for f in self.template["fields"])
        if has_portrait:
            headers.insert(0, "Portrait")

        headers.append("Actions")

        for col, header in enumerate(headers):
            if header != "Actions":
                sort_index = col - (1 if has_portrait and col > 0 else 0)
                button = ctk.CTkButton(self.list_frame, text=header, anchor="w",
                                    command=lambda idx=sort_index: self.sort_column(idx) if sort_index >= 0 else None)
                button.grid(row=0, column=col, sticky="w", pady=(0, 2), padx=5)
            else:
                label = ctk.CTkLabel(self.list_frame, text=header, anchor="w", padx=5)
                label.grid(row=0, column=col, sticky="w", pady=(0, 2))

    def refresh_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        self.create_table_header()

        if not self.filtered_items:
            ctk.CTkLabel(self.list_frame, text="No items found.").grid(row=1, column=0, columnspan=len(self.template["fields"]) + 2, pady=10)
            return

        for row_index, item in enumerate(self.filtered_items, start=1):
            self.create_item_row(item, row_index)

    def create_item_row(self, item, row_index):
        has_portrait = any(f["name"] == "Portrait" for f in self.template["fields"])

        col_offset = 0
        if has_portrait:
            portrait_path = item.get("Portrait", "")

            def on_portrait_click(event=None):
                self.set_portrait(item)

            if portrait_path and os.path.exists(portrait_path):
                img = Image.open(portrait_path)
                ctk_image = CTkImage(light_image=img, size=(32, 32))
                portrait_label = CTkLabel(self.list_frame, image=ctk_image, text="")
                portrait_label.image = ctk_image
                portrait_label.grid(row=row_index, column=0, padx=5)
                portrait_label.bind("<Button-1>", on_portrait_click)
            else:
                no_image_label = ctk.CTkLabel(self.list_frame, text="[No Image]")
                no_image_label.grid(row=row_index, column=0, padx=5)
                no_image_label.bind("<Button-1>", on_portrait_click)

            col_offset = 1

        # Fill other columns (excluding Portrait if not present)
        visible_fields = [f for f in self.template["fields"] if f["name"] != "Portrait"]
        for col, field in enumerate(visible_fields):
            value = item.get(field["name"], "")
            if field["type"] == "longtext":
                value = format_longtext(value, max_length=100)

            label = ctk.CTkLabel(self.list_frame, text=value, anchor="w", padx=5, wraplength=200)
            label.grid(row=row_index, column=col + col_offset, sticky="w", pady=2)

        # Actions column is always after the data columns
        action_frame = ctk.CTkFrame(self.list_frame)
        action_frame.grid(row=row_index, column=len(visible_fields) + col_offset, sticky="w")

        ctk.CTkButton(action_frame, text="Edit", command=lambda i=item: self.edit_item(i)).pack(side="left", padx=2)
        ctk.CTkButton(action_frame, text="Delete", command=lambda i=item: self.delete_item(i)).pack(side="left", padx=2)


    def set_portrait(self, item):
        file_path = filedialog.askopenfilename(
            title="Select Portrait Image",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp")]
        )

        if not file_path:
            return

        if not os.path.exists(PORTRAIT_FOLDER):
            os.makedirs(PORTRAIT_FOLDER)

        # Generate a filename (can use NPC name if available)
        npc_name = item.get("Name", "Unnamed").replace(" ", "_")
        ext = os.path.splitext(file_path)[-1].lower()
        dest_filename = f"{npc_name}_{len(self.items)}{ext}"
        dest_path = os.path.join(PORTRAIT_FOLDER, dest_filename)

        # Resize and save to the portraits folder
        with Image.open(file_path) as img:
            img = img.convert("RGB")
            img.thumbnail(MAX_PORTRAIT_SIZE)
            img.save(dest_path)

        # Update the item with the relative path
        item["Portrait"] = dest_path
        self.model_wrapper.save_items(self.items)
        self.refresh_list()

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
        if col_index < 0:
            return
        field_name = self.template["fields"][col_index]["name"]
        self.filtered_items.sort(key=lambda x: x.get(field_name, ""))
        self.refresh_list()

    def destroy(self):
        self.unbind_mousewheel()
        super().destroy()
