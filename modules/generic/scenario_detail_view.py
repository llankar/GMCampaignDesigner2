import customtkinter as ctk
from modules.generic.generic_model_wrapper import GenericModelWrapper

class ScenarioDetailView(ctk.CTkFrame):
    def __init__(self, master, scenario_item, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.scenario = scenario_item
        self.place_wrapper = GenericModelWrapper("places")
        self.npc_wrapper = GenericModelWrapper("npcs")

        self.tabs = {}
        self.current_tab = None

        # Top bar for tabs
        self.tab_bar = ctk.CTkFrame(self, height=40)
        self.tab_bar.pack(side="top", fill="x")

        # Main content area
        self.content_area = ctk.CTkFrame(self)
        self.content_area.pack(side="top", fill="both", expand=True)

        # Create main scenario tab
        self.add_tab("Scenario", self.create_scenario_frame())

        # Add the permanent "+" button for new scratchpads
        self.add_button = ctk.CTkButton(self.tab_bar, text="+", width=40, command=self.add_empty_tab)
        self.add_button.pack(side="right", padx=5)

    def add_tab(self, name, content_frame):
        if name in self.tabs:
            self.show_tab(name)
            return

        # Create tab button with label + close button
        tab_frame = ctk.CTkFrame(self.tab_bar, height=30)
        tab_frame.pack(side="left", padx=2, pady=5)

        tab_button = ctk.CTkButton(tab_frame, text=name, command=lambda: self.show_tab(name), width=150)
        tab_button.pack(side="left")

        close_button = ctk.CTkButton(tab_frame, text="❌", width=30, command=lambda: self.close_tab(name))
        close_button.pack(side="left")

        self.tabs[name] = {"button_frame": tab_frame, "content_frame": content_frame}

        content_frame.pack_forget()  # Hide until shown
        self.show_tab(name)

    def show_tab(self, name):
        if self.current_tab and self.current_tab in self.tabs:
            self.tabs[self.current_tab]["content_frame"].pack_forget()

        self.current_tab = name
        self.tabs[name]["content_frame"].pack(fill="both", expand=True)

    def close_tab(self, name):
        if len(self.tabs) == 1:
            # If this is the last tab, do nothing (silently ignore close request)
            return

        self.tabs[name]["button_frame"].destroy()
        self.tabs[name]["content_frame"].destroy()
        del self.tabs[name]

        if self.current_tab == name:
            remaining_tabs = list(self.tabs.keys())
            if remaining_tabs:
                self.show_tab(remaining_tabs[0])
            else:
                self.current_tab = None


    def add_empty_tab(self):
        new_tab_name = f"Note {self.tab_counter()}"
        frame = self.create_note_frame(new_tab_name)
        self.add_tab(new_tab_name, frame)

    def tab_counter(self):
        return sum(1 for name in self.tabs if name.startswith("Note"))

    def create_note_frame(self, title):
        frame = ctk.CTkFrame(self.content_area)
        ctk.CTkLabel(frame, text=f"This is {title}", font=("Arial", 14, "italic")).pack(pady=20)
        return frame

    def create_scenario_frame(self):
        frame = ctk.CTkFrame(self.content_area)

        ctk.CTkLabel(frame, text=self.scenario.get("Title", "Unnamed Scenario"), font=("Arial", 20, "bold")).pack(pady=5, anchor="w", padx=10)

        self.insert_text(frame, "Summary", self.scenario.get("Summary"))
        self.insert_text(frame, "Secrets", self.scenario.get("Secrets", "No secrets provided."))
        self.insert_links(frame, "Places", self.scenario.get("Places", []), self.show_place_tab)
        self.insert_links(frame, "NPCs", self.scenario.get("NPCs", []), self.show_npc_tab)

        return frame

    def insert_text(self, parent, header, content):
        ctk.CTkLabel(parent, text=f"{header}:", font=("Arial", 16, "bold")).pack(anchor="w", padx=10)
        content_text = content.get("text", "") if isinstance(content, dict) else content

        box = ctk.CTkTextbox(parent, wrap="word", height=80)
        box.insert("1.0", content_text)
        box.configure(state="disabled")
        box.pack(fill="x", padx=10, pady=5)

    def insert_links(self, parent, header, items, callback):
        ctk.CTkLabel(parent, text=f"{header}:", font=("Arial", 16, "bold")).pack(anchor="w", padx=10)

        box = ctk.CTkTextbox(parent, wrap="word", height=100)
        box.pack(fill="x", padx=10, pady=5)

        for item in items:
            tag = item.replace(" ", "_")
            box.insert("end", f"{item}\n", tag)
            box.tag_config(tag, foreground="blue", underline=True)
            box.tag_bind(tag, "<Button-1>", lambda e, name=item: callback(name))

        box.configure(state="disabled")

    def show_place_tab(self, place_name):
        places = {p["Name"]: p for p in self.place_wrapper.load_items()}
        place = places.get(place_name, {"Description": "No description."})

        frame = ctk.CTkFrame(self.content_area)
        ctk.CTkLabel(frame, text=place_name, font=("Arial", 18, "bold")).pack(pady=5, anchor="w", padx=10)

        box = ctk.CTkTextbox(frame, wrap="word", height=200)
        box.insert("1.0", place["Description"])
        box.configure(state="disabled")
        box.pack(fill="both", expand=True, padx=10, pady=5)

        self.add_tab(place_name, frame)

    def show_npc_tab(self, npc_name):
        npcs = {n["Name"]: n for n in self.npc_wrapper.load_items()}
        npc = npcs.get(npc_name, {"Role": "Unknown", "Description": "No description."})

        npc_desc = npc["Description"].get("text", npc["Description"]) if isinstance(npc["Description"], dict) else npc["Description"]

        frame = ctk.CTkFrame(self.content_area)
        ctk.CTkLabel(frame, text=f"{npc_name} ({npc.get('Role', 'Unknown')})", font=("Arial", 18, "bold")).pack(pady=5, anchor="w", padx=10)

        box = ctk.CTkTextbox(frame, wrap="word", height=200)
        box.insert("1.0", npc_desc)
        box.configure(state="disabled")
        box.pack(fill="both", expand=True, padx=10, pady=5)

        self.add_tab(npc_name, frame)
