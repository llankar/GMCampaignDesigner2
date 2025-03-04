import customtkinter as ctk
from modules.generic.generic_list_view import GenericListView
from modules.generic.generic_model_wrapper import GenericModelWrapper
import json
from modules.helpers.window_helper import position_window_at_top
from tkinter import filedialog, messagebox

def load_template(entity_name):
    with open(f"modules/{entity_name}/{entity_name}_template.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_items_from_json(view, entity_name):
    file_path = filedialog.askopenfilename(
        title=f"Select {entity_name.capitalize()} JSON File",
        filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
    )
    if file_path:
        try:
            with open(file_path, 'r', encoding="utf-8") as file:
                data = json.load(file)
                items = data.get(entity_name, [])
                if not items:
                    messagebox.showwarning(f"No {entity_name.capitalize()}", f"No {entity_name} found in the selected file.")
                    return

                for item in items:
                    view.add_item(item)

                messagebox.showinfo("Success", f"Loaded {len(items)} {entity_name}.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load {entity_name}:\n{e}")

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
        model_wrapper.master = window  # IMPORTANT for the editor
        template = load_template(entity)

        view = GenericListView(window, model_wrapper, template)
        view.pack(fill="both", expand=True)

        if entity in ["factions", "places", "npcs", "scenarios"]:
            ctk.CTkButton(
                window,
                text=f"Load {entity.capitalize()}",
                command=lambda: load_items_from_json(view, entity)
            ).pack(pady=5)

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
