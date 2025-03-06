import os
import json
from modules.generic.generic_editor_window import GenericEditorWindow

class GenericModelWrapper:
    def __init__(self, entity_type):
        self.entity_type = entity_type
        # Define the path to the data file, e.g. data/npcs.json for "npcs"
        self.data_file = os.path.join(os.path.dirname(__file__), "..", "..", "data", f"{entity_type}.json")
        # Define the path to the template file, e.g. modules/npcs/npcs_template.json for "npcs"
        self.template_file = os.path.join(os.path.dirname(__file__), "..", entity_type, f"{entity_type}_template.json")
        
        # Load the template if it exists; otherwise, set a default empty template.
        if os.path.exists(self.template_file):
            with open(self.template_file, "r", encoding="utf-8") as f:
                self.template = json.load(f)
        else:
            self.template = {"fields": []}
        
        # The master (parent window) will be set by the ListView later.
        self.master = None

    def load_items(self):
        if not os.path.exists(self.data_file):
            return []
        with open(self.data_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_items(self, items):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)

    def edit_item(self, item, creation_mode=False):
        # Create the editor window using self.template.
        editor = GenericEditorWindow(self.master, item, self.template, creation_mode)
        # Wait for the editor window to close.
        self.master.wait_window(editor)
        return editor.saved
