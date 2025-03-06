import customtkinter as ctk
from tkinter import messagebox, filedialog
from customtkinter import CTkLabel, CTkImage
from PIL import Image
import os

from modules.helpers.text_helpers import format_longtext
from modules.generic.generic_editor_window import GenericEditorWindow

PORTRAIT_FOLDER = "assets/portraits"
MAX_PORTRAIT_SIZE = (128, 128)


class GenericListView(ctk.CTkFrame):
    def __init__(self, master, model_wrapper, template, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.model_wrapper = model_wrapper
        self.template = template  # Template provided to the ListView
        os.makedirs(PORTRAIT_FOLDER, exist_ok=True)

        # Top bar for search/filter/add
        self.search_var = ctk.StringVar()
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        search_entry.bind("<Return>", lambda event: self.filter_items())

        ctk.CTkButton(search_frame, text="Filter", command=self.filter_items).pack(side="left", padx=5)
        ctk.CTkButton(search_frame, text="Add", command=self.add_item).pack(side="left", padx=5)

        # Scrollable frame to hold the entire table (header + data rows)
        self.table_frame = ctk.CTkScrollableFrame(self)
        self.table_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Define columns in the scrollable frame
        self.table_frame.grid_columnconfigure(0, weight=0)  # portrait
        self.table_frame.grid_columnconfigure(1, weight=1)  # main fields
        self.table_frame.grid_columnconfigure(2, weight=0)  # actions

        # Load data
        self.items = self.model_wrapper.load_items()
        self.filtered_items = self.items.copy()

        # For caching loaded thumbnails
        self.image_cache = {}

        # Prepare a list of column headers (including or excluding "Portrait")
        self.headers = []
        self.has_portrait = any(f["name"] == "Portrait" for f in self.template["fields"])
        if self.has_portrait:
            self.headers.append("Portrait")
        # Add all fields except "Portrait"
        for f in self.template["fields"]:
            if f["name"] != "Portrait":
                self.headers.append(f["name"])
        self.headers.append("Actions")

        # Create header row
        self.create_table_header()
        # Populate data rows
        self.refresh_list()

    def create_table_header(self):
        """Creates a single row (row=0) for column headers using grid layout."""
        total_columns = len(self.headers)
        if self.has_portrait:
            self.table_frame.grid_columnconfigure(0, minsize=60)
        for i in range(1, total_columns - 1):
            self.table_frame.grid_columnconfigure(i, weight=1)
        self.table_frame.grid_columnconfigure(total_columns - 1, minsize=40)

        for col_index, header_text in enumerate(self.headers):
            if header_text not in ["Portrait", "Actions"]:
                header_button = ctk.CTkButton(
                    self.table_frame, text=header_text, anchor="w",
                    command=lambda c=header_text: self.sort_column(c)
                )
                header_button.grid(row=0, column=col_index, sticky="ew", padx=5, pady=2)
            else:
                label = ctk.CTkLabel(self.table_frame, text=header_text, anchor="w")
                label.grid(row=0, column=col_index, sticky="ew", padx=5, pady=2)

    def refresh_list(self):
        """Clears existing data rows and rebuilds them under the header row."""
        for child in self.table_frame.winfo_children():
            if int(child.grid_info()["row"]) > 0:
                child.destroy()

        row_index = 1
        for item in self.filtered_items:
            self.create_item_row(item, row_index)
            row_index += 1

    def create_item_row(self, item, row_index):
        """Creates a single row in the grid for the given item.
           Clicking on any non-portrait field will open the editor.
           A small red cross at the end deletes the item.
        """
        col_index = 0

        # 1) Portrait column (if present)
        if self.has_portrait:
            portrait_path = item.get("Portrait", "")

            def on_portrait_click(event=None):
                self.set_portrait(item)

            if portrait_path and os.path.exists(portrait_path):
                if portrait_path in self.image_cache:
                    ctk_image = self.image_cache[portrait_path]
                else:
                    ctk_image = self.load_image_thumbnail(portrait_path)
                    self.image_cache[portrait_path] = ctk_image
                portrait_label = ctk.CTkLabel(self.table_frame, text="", image=ctk_image)
                portrait_label.grid(row=row_index, column=col_index, padx=5, pady=2)
                portrait_label.bind("<Button-1>", on_portrait_click)
            else:
                no_image_label = ctk.CTkLabel(self.table_frame, text="[No Image]")
                no_image_label.grid(row=row_index, column=col_index, padx=5, pady=2)
                no_image_label.bind("<Button-1>", on_portrait_click)
            col_index += 1

        # 2) Other fields: each field cell triggers editing on click.
        for f in self.template["fields"]:
            if f["name"] == "Portrait":
                continue
            value = item.get(f["name"], "")
            if f.get("type", "").lower() == "longtext":
                try:
                    value = format_longtext(value, max_length=100)
                except Exception:
                    value = str(value)
            label = ctk.CTkLabel(self.table_frame, text=str(value), anchor="w")
            label.grid(row=row_index, column=col_index, sticky="ew", padx=5, pady=2)
            # Instead of calling the wrapper's edit_item (which may not have a template),
            # we use our own method to open the editor using the ListView's template.
            label.bind("<Button-1>", lambda event, i=item: self.open_editor(i))
            col_index += 1

        # 3) Actions column: a small red cross for deletion.
        delete_button = ctk.CTkButton(
            self.table_frame,
            text="❌",
            width=30,
            fg_color="red",
            hover_color="darkred",
            command=lambda i=item: self.delete_item(i)
        )
        delete_button.grid(row=row_index, column=col_index, padx=5, pady=2, sticky="e")

    def load_image_thumbnail(self, path):
        """Load and resize the portrait to a thumbnail."""
        img = Image.open(path)
        img.thumbnail((32, 32))
        ctk_img = CTkImage(light_image=img, size=(32, 32))
        return ctk_img

    def set_portrait(self, item):
        """Prompts user to select a portrait image, resizes, and saves it."""
        file_path = filedialog.askopenfilename(
            title="Select Portrait Image",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp")]
        )
        if not file_path:
            return
        if not os.path.exists(PORTRAIT_FOLDER):
            os.makedirs(PORTRAIT_FOLDER)

        npc_name = item.get("Name", "Unnamed").replace(" ", "_")
        ext = os.path.splitext(file_path)[-1].lower()
        dest_filename = f"{npc_name}_{len(self.items)}{ext}"
        dest_path = os.path.join(PORTRAIT_FOLDER, dest_filename)

        with Image.open(file_path) as img:
            img = img.convert("RGB")
            img.thumbnail(MAX_PORTRAIT_SIZE)
            img.save(dest_path)

        item["Portrait"] = dest_path
        self.model_wrapper.save_items(self.items)
        self.refresh_list()

    def filter_items(self):
        """Filter the items list by a search query and refresh."""
        query = self.search_var.get().strip().lower()
        if not query:
            self.filtered_items = self.items.copy()
        else:
            self.filtered_items = [
                i for i in self.items if any(query in str(v).lower() for v in i.values())
            ]
        self.refresh_list()

    def open_editor(self, item, creation_mode=False):
        """Opens the editor window using the template provided to the ListView.
           Returns True if the item was saved, False otherwise.
        """
        editor = GenericEditorWindow(self.master, item, self.template, creation_mode)
        self.master.wait_window(editor)
        return editor.saved

    def add_item(self):
        """Add a new item by opening the editor in creation mode."""
        new_item = {}
        if not self.open_editor(new_item, creation_mode=True):
            return
        self.items.append(new_item)
        self.model_wrapper.save_items(self.items)
        self.filter_items()

    def edit_item(self, item):
        """Edit an existing item."""
        if self.open_editor(item, creation_mode=False):
            self.model_wrapper.save_items(self.items)
            self.filter_items()

    def delete_item(self, item):
        """Delete an item from the list."""
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete '{item.get('Name', 'Unnamed')}'?"):
            self.items.remove(item)
            self.model_wrapper.save_items(self.items)
            self.filter_items()

    def sort_column(self, column_name):
        """
        Sort the filtered items by the specified column_name.
        If column_name is 'Portrait' or 'Actions', we skip.
        """
        if column_name in ["Portrait", "Actions"]:
            return
        self.filtered_items.sort(key=lambda x: str(x.get(column_name, "")))
        self.refresh_list()
