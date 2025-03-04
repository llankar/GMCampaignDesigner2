import json
import os
from modules.generic.generic_editor_window import GenericEditorWindow

class GenericModelWrapper:
    def __init__(self, entity_type):
        self.entity_type = entity_type
        self.data_file = os.path.join(os.path.dirname(__file__), "..", "..", "data", f"{entity_type}.json")
        self.template_file = os.path.join(os.path.dirname(__file__), "..", entity_type, f"{entity_type}_template.json")

        # Charger le template au démarrage
        with open(self.template_file, "r", encoding="utf-8") as f:
            self.template = json.load(f)

        self.master = None  # Défini plus tard lors de l'ouverture de la fenêtre

    def load_items(self):
        if not os.path.exists(self.data_file):
            return []
        with open(self.data_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_items(self, items):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)

    def edit_item(self, item, creation_mode=False):
        editor = GenericEditorWindow(self.master, item, self.template, creation_mode)
        self.master.wait_window(editor)
        return editor.saved
