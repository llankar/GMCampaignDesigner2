import os

# Dossiers concernés
MODULES = ["factions", "npcs", "places", "scenarios"]

# Chemin racine où se trouvent les modules
BASE_PATH = "modules"

# Template de chaque ModelWrapper
WRAPPER_TEMPLATE = """
from modules.{module}.{module}_model import load_{module}, save_{module}
from modules.{module}.{singular}_editor_window import {Singular}EditorWindow

class {Capitalized}ModelWrapper:
    @staticmethod
    def load_items():
        return load_{module}()

    @staticmethod
    def save_items(items):
        save_{module}(items)

    @staticmethod
    def edit_item(item, creation_mode=False):
        editor = {Singular}EditorWindow(None, item, creation_mode=creation_mode)
        editor.wait_window()
        return editor.saved
""".strip()

def generate_wrapper(module):
    singular = module[:-1]  # faction, npc, place, scenario
    content = WRAPPER_TEMPLATE.format(
        module=module,
        singular=singular,
        Singular=singular.capitalize(),
        Capitalized=module.capitalize()
    )

    wrapper_path = os.path.join(BASE_PATH, module, f"{module}_model_wrapper.py")

    # Création du fichier
    with open(wrapper_path, "w", encoding="utf-8") as file:
        file.write(content)

    print(f"✅ {module}_model_wrapper.py créé dans {wrapper_path}")

def generate_all_wrappers():
    for module in MODULES:
        generate_wrapper(module)

if __name__ == "__main__":
    generate_all_wrappers()
    print("✅ Tous les wrappers sont créés !")
