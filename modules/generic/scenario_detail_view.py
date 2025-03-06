import customtkinter as ctk
import os
from tkinter import Listbox, MULTIPLE, messagebox
from PIL import Image, ImageTk
from modules.generic.generic_model_wrapper import GenericModelWrapper
from functools import partial

class ScenarioDetailView(ctk.CTkFrame):
    def __init__(self, master, scenario_item, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.scenario = scenario_item
        self.place_wrapper = GenericModelWrapper("places")
        self.npc_wrapper = GenericModelWrapper("npcs")
        self.scenario_wrapper = GenericModelWrapper("scenarios")
        self.faction_wrapper = GenericModelWrapper("factions")

        self.tabs = {}
        self.current_tab = None

        self.tab_bar = ctk.CTkFrame(self, height=40)
        self.tab_bar.pack(side="top", fill="x")

        self.content_area = ctk.CTkFrame(self)
        self.content_area.pack(fill="both", expand=True)

        self.add_button = ctk.CTkButton(self.tab_bar, text="+", width=40, command=self.add_new_tab)
        self.add_button.pack(side="right", padx=5)

        scenario_name = scenario_item.get("Title", "Unnamed Scenario")
        self.add_tab(scenario_name, self.create_scenario_frame(scenario_item))

    def add_tab(self, name, content_frame):
        if name in self.tabs:
            self.show_tab(name)
            return

        tab_frame = ctk.CTkFrame(self.tab_bar)
        tab_frame.pack(side="left", padx=2, pady=5)

        tab_button = ctk.CTkButton(tab_frame, text=name, command=lambda: self.show_tab(name), width=150)
        tab_button.pack(side="left")

        close_button = ctk.CTkButton(tab_frame, text="❌", width=30, command=lambda: self.close_tab(name))
        close_button.pack(side="left")

        self.tabs[name] = {"button_frame": tab_frame, "content_frame": content_frame}

        content_frame.pack_forget()
        self.show_tab(name)

        self.reposition_add_button()

    def reposition_add_button(self):
        self.add_button.pack_forget()
        self.add_button.pack(side="left", padx=5)

    def show_tab(self, name):
        if self.current_tab and self.current_tab in self.tabs:
            self.tabs[self.current_tab]["content_frame"].pack_forget()

        self.current_tab = name
        self.tabs[name]["content_frame"].pack(fill="both", expand=True)

    def close_tab(self, name):
        if len(self.tabs) == 1:
            return

        self.tabs[name]["button_frame"].destroy()
        self.tabs[name]["content_frame"].destroy()
        del self.tabs[name]

        if self.current_tab == name and self.tabs:
            self.show_tab(next(iter(self.tabs)))

        self.reposition_add_button()

    def add_new_tab(self):
        options = ["Factions", "Places", "NPCs", "Scenarios", "Empty Tab"]

        popup = ctk.CTkToplevel(self)
        popup.title("Create New Tab")
        popup.geometry("300x250")

        popup.transient(self.winfo_toplevel())
        popup.grab_set()
        popup.focus_force()

        ctk.CTkLabel(popup, text="Choose tab type:").pack(pady=10)
        for option in options:
            ctk.CTkButton(popup, text=option, command=lambda o=option: self.open_selection_window(o, popup)).pack(pady=2)

    def open_selection_window(self, entity_type, popup):
        popup.destroy()

        if entity_type == "Empty Tab":
            self.add_tab(f"Note {len(self.tabs)}", self.create_note_frame())
            return

        wrapper_map = {
            "Factions": self.faction_wrapper,
            "Places": self.place_wrapper,
            "NPCs": self.npc_wrapper,
            "Scenarios": self.scenario_wrapper
        }

        wrapper = wrapper_map.get(entity_type)
        if not wrapper:
            messagebox.showerror("Error", f"Unknown entity type: {entity_type}")
            return

        items = wrapper.load_items()

        select_win = ctk.CTkToplevel(self)
        select_win.title(f"Select {entity_type}")
        select_win.geometry("400x300")

        select_win.transient(self.winfo_toplevel())
        select_win.grab_set()
        select_win.focus_force()

        listbox = Listbox(select_win, selectmode=MULTIPLE, height=15)
        listbox.pack(fill="both", expand=True, padx=10, pady=10)

        item_names = [item.get("Name", item.get("Title", "Unnamed")) for item in items]
        for name in item_names:
            listbox.insert("end", name)

        def open_selected():
            selected_indices = listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("No Selection", "Please select at least one item.")
                return

            for i in selected_indices:
                self.open_entity_tab(entity_type, item_names[i])

            select_win.destroy()

        ctk.CTkButton(select_win, text="Open Selected", command=open_selected).pack(pady=5)

    def open_entity_tab(self, entity_type, name):
        wrapper_map = {
            "Factions": (self.faction_wrapper, "Name"),
            "Places": (self.place_wrapper, "Name"),
            "NPCs": (self.npc_wrapper, "Name"),
            "Scenarios": (self.scenario_wrapper, "Title")
        }

        wrapper, key = wrapper_map[entity_type]
        items = wrapper.load_items()

        item = next((i for i in items if i.get(key) == name), None)

        if not item:
            messagebox.showerror("Error", f"{entity_type[:-1]} '{name}' not found.")
            return

        if entity_type == "NPCs":
            frame = self.create_npc_frame(item)
        elif entity_type == "Scenarios":
            frame = self.create_scenario_frame(item)
        else:
            frame = self.create_text_frame(name, item.get("Description", "No description available."))

        self.add_tab(name, frame)

    def create_scenario_frame(self, scenario):
        frame = ctk.CTkFrame(self.content_area)
        self.insert_text(frame, "Summary", scenario.get("Summary", ""))
        self.insert_text(frame, "Secrets", scenario.get("Secrets", "No secrets provided."))
        self.insert_links(frame, "Places", scenario.get("Places", []), self.show_place_tab)
        self.insert_links(frame, "NPCs", scenario.get("NPCs", []), self.show_npc_tab)
        return frame

    def create_npc_frame(self, npc):
        frame = ctk.CTkFrame(self.content_area)

        if "Portrait" in npc and os.path.exists(npc["Portrait"]):
            img = Image.open(npc["Portrait"])
            img = img.resize((150, 150), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            portrait_label = ctk.CTkLabel(frame, image=photo)
            portrait_label.image = photo
            portrait_label.pack(pady=5)

        self.insert_text(frame, "Description", npc.get("Description", "No description available."))
        return frame

    def create_text_frame(self, title, content):
        frame = ctk.CTkFrame(self.content_area)
        self.insert_text(frame, title, content)
        return frame

    def create_note_frame(self):
        frame = ctk.CTkFrame(self.content_area)

        label = ctk.CTkLabel(frame, text="Note Taking", font=("Arial", 16, "bold"))
        label.pack(anchor="w", padx=10, pady=(5, 2))

        text_box = ctk.CTkTextbox(frame, wrap="word", height=500)
        text_box.pack(fill="both", expand=True, padx=10, pady=5)

        frame.text_box = text_box
        return frame

    def insert_text(self, parent, header, content):
        ctk.CTkLabel(parent, text=f"{header}:", font=("Arial", 16, "bold")).pack(anchor="w", padx=10)
        box = ctk.CTkTextbox(parent, wrap="word", height=80)
        box.insert("1.0", content.get("text", content) if isinstance(content, dict) else content)
        box.configure(state="disabled")
        box.pack(fill="x", padx=10, pady=5)

    def insert_links(self, parent, header, items, callback):
        ctk.CTkLabel(parent, text=f"{header}:", font=("Arial", 16, "bold")).pack(anchor="w", padx=10)
        for item in items:
            label = ctk.CTkLabel(parent, text=item, text_color="blue", cursor="hand2")
            label.pack(anchor="w", padx=10)
            label.bind("<Button-1>", partial(self._linked_item_clicked, callback, item))

    def _linked_item_clicked(self, callback, item, event):
        callback(item)


    def _linked_item_clicked(self, callback, item, event):
        callback(item)

    def show_place_tab(self, place_name):
        self.open_entity_tab("Places", place_name)

    def show_npc_tab(self, npc_name):
        self.open_entity_tab("NPCs", npc_name)

    def create_note_frame(self):
        frame = ctk.CTkFrame(self.content_area)
        
        label = ctk.CTkLabel(frame, text="Note Taking", font=("Arial", 16, "bold"))
        label.pack(anchor="w", padx=10, pady=(5, 2))

        text_box = ctk.CTkTextbox(frame, wrap="word", height=500)  # Grand espace
        text_box.pack(fill="both", expand=True, padx=10, pady=5)

        # Préremplir (facultatif)
        text_box.insert("1.0", "Start writing your notes here...")

        # Stocker pour un éventuel futur accès (ex: sauvegarde ou relecture)
        frame.text_box = text_box

        return frame

