import customtkinter as ctk

class NPCGraphToolbar(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master

        ctk.CTkButton(self, text="Add NPC", command=self.master.add_npc).pack(side="left", padx=5)
        ctk.CTkButton(self, text="Add Faction", command=self.master.add_faction).pack(side="left", padx=5)
        ctk.CTkButton(self, text="Save", command=self.master.save_graph).pack(side="left", padx=5)
        ctk.CTkButton(self, text="Load", command=self.master.load_graph).pack(side="left", padx=5)
        ctk.CTkButton(self, text="Add Link", command=self.master.start_link_creation).pack(side="left", padx=5)
        ctk.CTkButton(self, text="Add Rectangle", command=self.master.add_rectangle).pack(side="left", padx=5)
