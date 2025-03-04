import customtkinter as ctk
from modules.generic.generic_list_view import GenericListView
from modules.factions.factions_model import load as load_factions, save as save_factions
from modules.places.places_model import load as load_places, save as save_places
from modules.npcs.npcs_model import load as load_npcs, save as save_npcs
from modules.scenarios.scenarios_model import load as load_scenarios, save as save_scenarios
import json
import os

BASE_DIR = os.path.dirname(__file__)

def load_template(entity_name):
    with open(f"modules/{entity_name}/{entity_name}_template.json", "r", encoding="utf-8") as f:
        return json.load(f)

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("GMCampaignDesigner2")
        self.geometry("1280x720")

        ctk.CTkButton(self, text="Manage Factions", command=lambda: self.open_entity("factions", FactionsModelWrapper())).pack(pady=5)
        ctk.CTkButton(self, text="Manage Places", command=lambda: self.open_entity("places", PlacesModelWrapper())).pack(pady=5)
        ctk.CTkButton(self, text="Manage NPCs", command=lambda: self.open_entity("npcs", NpcsModelWrapper())).pack(pady=5)
        ctk.CTkButton(self, text="Manage Scenarios", command=lambda: self.open_entity("scenarios", ScenariosModelWrapper())).pack(pady=5)

    def open_entity(self, entity, model):
        window = ctk.CTkToplevel(self)
        window.title(f"Manage {entity.capitalize()}")
        template = load_template(entity)
        view = GenericListView(window, model, template)
        view.pack(fill="both", expand=True)

class FactionsModelWrapper:
    def load(self): return load_factions()
    def save(self, items): save_factions(items)

class PlacesModelWrapper:
    def load(self): return load_places()
    def save(self, items): save_places(items)

class NpcsModelWrapper:
    def load(self): return load_npcs()
    def save(self, items): save_npcs(items)

class ScenariosModelWrapper:
    def load(self): return load_scenarios()
    def save(self, items): save_scenarios(items)

if __name__ == '__main__':
    app = MainWindow()
    app.mainloop()
