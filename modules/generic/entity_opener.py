import customtkinter as ctk
from tkinter import messagebox
import os
from modules.scenarios.scenario_detail_view import ScenarioDetailView
from modules.generic.generic_model_wrapper import GenericModelWrapper
from modules.helpers.template_loader import load_template

def open_detached_npc(npc_name):
    """
    Opens the specified NPC in a brand-new Toplevel window
    using a minimal ScenarioDetailView to show the NPC data
    (but not as a tab).
    """
    # 1. Load the NPC from JSON
    npc_wrapper = GenericModelWrapper("npcs")
    items = npc_wrapper.load_items()
    item = next((i for i in items if i.get("Name") == npc_name), None)
    if not item:
        messagebox.showerror("Error", f"NPC '{npc_name}' not found.")
        return

    # 2. Create a new Toplevel window
    window = ctk.CTkToplevel()
    window.title(f"NPC: {npc_name}")
    window.geometry("800x600")

    # 3. Create a minimal ScenarioDetailView (or a custom UI) for display
  
    dummy_scenario = {"Title": f"Entity: {npc_name}"}
    detail_view = ScenarioDetailView(window, scenario_item=dummy_scenario)
    detail_view.pack(fill="both", expand=True)

    # 4. Create just the single NPC frame inside this detail view
    #    (no new tabs, no attach/detach)
    entity_frame = detail_view.create_entity_frame("NPCs", item)
    entity_frame.pack(fill="both", expand=True)
    
