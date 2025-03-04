import customtkinter as ctk
from modules.generic.generic_editor_window import GenericEditorWindow

class GenericListView(ctk.CTkFrame):
    def __init__(self, master, model, template):
        super().__init__(master)
        self.model = model
        self.template = template
        self.items = model.load()
        self.filtered_items = self.items.copy()
        self.search_var = ctk.StringVar()

        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x")
        ctk.CTkEntry(search_frame, textvariable=self.search_var).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(search_frame, text="Filter", command=self.filter_items).pack(side="left")
        ctk.CTkButton(self, text="Add", command=self.add_item).pack(pady=5)

        self.list_frame = ctk.CTkFrame(self)
        self.list_frame.pack(fill="both", expand=True)
        self.refresh_list()

    def refresh_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        for item in self.filtered_items:
            row = ctk.CTkFrame(self.list_frame)
            row.pack(fill="x")
            for field in self.template["fields"]:
                value = item.get(field["name"], "")
                ctk.CTkLabel(row, text=str(value)).pack(side="left")
            ctk.CTkButton(row, text="Edit", command=lambda i=item: self.edit_item(i)).pack(side="right")

    def add_item(self):
        item = {}
        editor = GenericEditorWindow(self, item, self.template)
        self.wait_window(editor)
        if editor.saved:
            self.items.append(item)
            self.model.save(self.items)
            self.filter_items()

    def edit_item(self, item):
        editor = GenericEditorWindow(self, item, self.template)
        self.wait_window(editor)
        self.model.save(self.items)
        self.filter_items()

    def filter_items(self):
        query = self.search_var.get().lower()
        self.filtered_items = [i for i in self.items if query in str(i).lower()]
        self.refresh_list()
