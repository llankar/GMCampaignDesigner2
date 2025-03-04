import customtkinter as ctk
from tkinter import messagebox
from modules.helpers.text_helpers import format_longtext


class GenericListView(ctk.CTkFrame):
    def __init__(self, master, model_wrapper, template, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.model_wrapper = model_wrapper
        self.template = template

        self.search_var = ctk.StringVar()

        # Barre de recherche avec ajout bouton
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(pady=5, fill="x")

        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)

        # Bind Enter key to trigger the filter
        search_entry.bind("<Return>", lambda event: self.filter_items())

        search_button = ctk.CTkButton(search_frame, text="Filter", command=self.filter_items)
        search_button.pack(side="left", padx=5)
        add_button = ctk.CTkButton(search_frame, text="Add", command=self.add_item)
        add_button.pack(side="left", padx=5)

        # Cadre de la liste
        self.list_frame = ctk.CTkFrame(self)
        self.list_frame.pack(fill="both", expand=True)

        self.items = self.model_wrapper.load_items()
        self.filtered_items = self.items.copy()

        self.create_table_header()
        self.refresh_list()

    def create_table_header(self):
        """ Crée la ligne d'entête avec un vrai alignement grid. """
        headers = [field["name"] for field in self.template["fields"]] + ["Actions"]

        for col, header in enumerate(headers):
            if header != "Actions":  # Only make non-action columns clickable
                button = ctk.CTkButton(self.list_frame, text=header, anchor="w", command=lambda col=col: self.sort_column(col))
                button.grid(row=0, column=col, sticky="w", pady=(0, 2), padx=5)
            else:
                label = ctk.CTkLabel(self.list_frame, text=header, anchor="w", padx=5)
                label.grid(row=0, column=col, sticky="w", pady=(0, 2))

    def refresh_list(self):
        """ Recharge la liste avec les items filtrés. """
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        self.create_table_header()

        if not self.filtered_items:
            ctk.CTkLabel(self.list_frame, text="No items found.").grid(row=1, column=0, columnspan=len(self.template["fields"]) + 1, pady=10)
            return

        for row_index, item in enumerate(self.filtered_items, start=1):
            self.create_item_row(item, row_index)

    def create_item_row(self, item, row_index):
        """ Crée une ligne pour un item avec une vraie grille alignée. """
        for col, field in enumerate(self.template["fields"]):
            value = item.get(field["name"], "")
            if field["type"] == "longtext":
                value = format_longtext(value, max_length=100)

            label = ctk.CTkLabel(self.list_frame, text=value, anchor="w", padx=5, wraplength=200)
            label.grid(row=row_index, column=col, sticky="w", pady=2)

        # Actions (Edit / Delete)
        action_frame = ctk.CTkFrame(self.list_frame)
        action_frame.grid(row=row_index, column=len(self.template["fields"]), sticky="w")

        ctk.CTkButton(action_frame, text="Edit", command=lambda i=item: self.edit_item(i)).pack(side="left", padx=2)
        ctk.CTkButton(action_frame, text="Delete", command=lambda i=item: self.delete_item(i)).pack(side="left", padx=2)

    def filter_items(self):
        """ Filtrage selon la recherche. """
        query = self.search_var.get().strip().lower()
        if not query:
            self.filtered_items = self.items.copy()
        else:
            self.filtered_items = [
                item for item in self.items
                if any(query in str(v).lower() for v in item.values())
            ]
        self.refresh_list()

    def add_item(self):
        """ Ajoute un nouvel item. """
        new_item = {}
        if self.model_wrapper.edit_item(new_item, creation_mode=True):
            self.items.append(new_item)
            self.model_wrapper.save_items(self.items)
            self.filter_items()

    def edit_item(self, item):
        """ Édite un item existant. """
        if self.model_wrapper.edit_item(item, creation_mode=False):
            self.model_wrapper.save_items(self.items)
            self.filter_items()

    def delete_item(self, item):
        """ Supprime un item existant. """
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete '{item.get('Name', 'Unnamed')}'?"):
            self.items.remove(item)
            self.model_wrapper.save_items(self.items)
            self.filter_items()

    def sort_column(self, col_index):
        """ Trie la liste des éléments par la colonne cliquée. """
        field_name = self.template["fields"][col_index]["name"]
        
        # Assurez-vous de manipuler les données correctement
        def get_sort_value(item):
            value = item.get(field_name, "")
            # Si c'est un dictionnaire (par exemple un longtext ou un autre champ structuré)
            if isinstance(value, dict):
                return value.get("text", "")
            return value  # Retourne la valeur telle quelle si ce n'est pas un dictionnaire

        # Tri des items par la colonne sélectionnée
        self.filtered_items.sort(key=lambda x: get_sort_value(x))
        self.refresh_list()
[]