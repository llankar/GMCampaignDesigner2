from modules.generic.generic_editor_window import GenericEditorWindow
import orjson
import os

class GenericModelWrapper:
    def __init__(self, entity_type):
        self.entity_type = entity_type
        self.data_file = os.path.join("data", f"{entity_type}.json")
        self._cache = None

    def load_items(self):
        if self._cache is not None:
            return self._cache
        if not os.path.exists(self.data_file):
            self._cache = []
        else:
            with open(self.data_file, "rb") as f:
                self._cache = orjson.loads(f.read())
        return self._cache

    def save_items(self, items):
        with open(self.data_file, "wb") as f:
            f.write(orjson.dumps(items, option=orjson.OPT_INDENT_2))
        self._cache = items  # Refresh the cache


    def edit_item(self, item, creation_mode=False):
        editor = GenericEditorWindow(self.master, item, self.template, creation_mode)
        self.master.wait_window(editor)
        return editor.saved
