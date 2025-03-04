import customtkinter as ctk
from modules.generic.generic_list_view import GenericListView
from modules.generic.generic_model_wrapper import GenericModelWrapper
import json
from modules.helpers.window_helper import position_window_at_top

def load_template(entity_name):
    with open(f"modules/{entity_name}/{entity_name}_template.json", "r", encoding="utf-8") as f:
        return json.load(f)

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("GMCampaignDesigner")
        self.geometry("1280x720")
        position_window_at_top(self)

        ctk.CTkButton(self, text="Manage Factions", command=lambda: self.open_entity("factions")).pack(pady=5)
        ctk.CTkButton(self, text="Manage Places", command=lambda: self.open_entity("places")).pack(pady=5)
        ctk.CTkButton(self, text="Manage NPCs", command=lambda: self.open_entity("npcs")).pack(pady=5)
        ctk.CTkButton(self, text="Manage Scenarios", command=lambda: self.open_entity("scenarios")).pack(pady=5)

    def open_entity(self, entity):
        window = ctk.CTkToplevel(self)
        window.title(f"Manage {entity.capitalize()}")
        window.geometry("1000x600")
        window.transient(self)
        window.lift()
        window.focus_force()

        model_wrapper = GenericModelWrapper(entity)
        model_wrapper.master = window  # IMPORTANT pour l'éditeur
        template = load_template(entity)

        view = GenericListView(window, model_wrapper, template)
        view.pack(fill="both", expand=True)

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
