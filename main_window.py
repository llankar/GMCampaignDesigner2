import customtkinter as ctk
import json
from tkinter import filedialog, messagebox, Toplevel, Listbox, MULTIPLE
from modules.generic.generic_list_view import GenericListView
from modules.generic.generic_model_wrapper import GenericModelWrapper
from modules.helpers.window_helper import position_window_at_top
from docx import Document


def load_template(entity_name):
    with open(f"modules/{entity_name}/{entity_name}_template.json", "r", encoding="utf-8") as f:
        return json.load(f)

def apply_formatting(run, formatting):
    if formatting.get('bold'):
        run.bold = True
    if formatting.get('italic'):
        run.italic = True
    if formatting.get('underline'):
        run.underline = True

def preview_and_export_scenarios():
    scenario_wrapper = GenericModelWrapper("scenarios")
    scenario_items = scenario_wrapper.load_items()

    if not scenario_items:
        messagebox.showwarning("No Scenarios", "There are no scenarios available.")
        return

    selection_window = Toplevel()
    selection_window.title("Select Scenarios to Export")
    selection_window.geometry("400x300")

    listbox = Listbox(selection_window, selectmode=MULTIPLE, height=15)
    listbox.pack(fill="both", expand=True, padx=10, pady=10)

    scenario_titles = [scenario.get("Title", "Unnamed Scenario") for scenario in scenario_items]
    for title in scenario_titles:
        listbox.insert("end", title)

    def export_selected():
        selected_indices = listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select at least one scenario to export.")
            return

        selected_scenarios = [scenario_items[i] for i in selected_indices]
        preview_scenarios(selected_scenarios)
        selection_window.destroy()

    ctk.CTkButton(selection_window, text="Preview Selected", command=export_selected).pack(pady=5)

def preview_scenarios(selected_scenarios):
    place_wrapper = GenericModelWrapper("places")
    npc_wrapper = GenericModelWrapper("npcs")

    place_items = {place["Name"]: place for place in place_wrapper.load_items()}
    npc_items = {npc["Name"]: npc for npc in npc_wrapper.load_items()}

    preview_window = Toplevel()
    preview_window.title("Preview Export")
    preview_window.geometry("600x500")

    text_preview = ctk.CTkTextbox(preview_window, wrap="word")
    text_preview.pack(fill="both", expand=True, padx=10, pady=10)

    preview_content = "Campaign Scenarios\n\n"

    for scenario in selected_scenarios:
        title = scenario.get("Title", "Unnamed Scenario")
        summary = scenario.get("Summary", {"text": "No description provided.", "formatting": {}})
        if isinstance(summary, dict):
            preview_content += f"{title}\n{summary['text']}\n\n"
        else:
            preview_content += f"{title}\n{summary}\n\n"

        preview_content += "Places:\n"
        for place_name in scenario.get("Places", []):
            place = place_items.get(place_name, {"Name": place_name, "Description": "Unknown Place"})
            preview_content += f"- {place['Name']}: {place['Description']}\n"

        preview_content += "NPCs:\n"
        for npc_name in scenario.get("NPCs", []):
            npc = npc_items.get(npc_name, {"Name": npc_name, "Role": "Unknown", "Description": {"text": "Unknown NPC", "formatting": {}}})
            description = npc['Description']
            if isinstance(description, dict):
                preview_content += f"- {npc['Name']} ({npc['Role']}, {npc.get('Faction', 'Unknown')}): {description['text']}\n"
            else:
                preview_content += f"- {npc['Name']} ({npc['Role']}, {npc.get('Faction', 'Unknown')}): {description}\n"

        preview_content += "\n"

    text_preview.insert("1.0", preview_content)

    ctk.CTkButton(preview_window, text="Save to Word", command=lambda: save_to_docx(selected_scenarios, place_items, npc_items)).pack(pady=5)

def save_to_docx(selected_scenarios, place_items, npc_items):
    file_path = filedialog.asksaveasfilename(
        defaultextension=".docx",
        filetypes=[("Word Files", "*.docx"), ("All Files", "*.*")],
        title="Save Scenario Export"
    )
    if not file_path:
        return

    try:
        doc = Document()
        doc.add_heading("Campaign Scenarios", level=1)

        for scenario in selected_scenarios:
            title = scenario.get("Title", "Unnamed Scenario")
            summary = scenario.get("Summary", {"text": "No description provided.", "formatting": {}})

            doc.add_heading(title, level=2)
            if isinstance(summary, dict):
                p = doc.add_paragraph()
                run = p.add_run(summary['text'])
                apply_formatting(run, summary.get('formatting', {}))
            else:
                doc.add_paragraph(summary)

            doc.add_heading("Places", level=3)
            for place_name in scenario.get("Places", []):
                place = place_items.get(place_name, {"Name": place_name, "Description": "Unknown Place"})
                doc.add_paragraph(f"- {place['Name']}: {place['Description']}")

            doc.add_heading("NPCs", level=3)
            for npc_name in scenario.get("NPCs", []):
                npc = npc_items.get(npc_name, {"Name": npc_name, "Role": "Unknown", "Description": {"text": "Unknown NPC", "formatting": {}}})
                p = doc.add_paragraph(f"- {npc['Name']} ({npc['Role']}, {npc.get('Faction', 'Unknown')}): ")
                description = npc['Description']
                if isinstance(description, dict):
                    run = p.add_run(description['text'])
                    apply_formatting(run, description.get('formatting', {}))
                else:
                    p.add_run(str(description))

        doc.save(file_path)
        messagebox.showinfo("Export Successful", f"Scenario exported successfully to:\n{file_path}")
    except PermissionError:
        messagebox.showerror("File Error", "Failed to save the file. Please close it if it's open and try again.")

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
        ctk.CTkButton(self, text="Export Scenarios", command=preview_and_export_scenarios).pack(pady=5)

    def open_entity(self, entity):
        window = ctk.CTkToplevel(self)
        window.title(f"Manage {entity.capitalize()}")
        window.geometry("1000x600")
        window.transient(self)
        window.lift()
        window.focus_force()

        model_wrapper = GenericModelWrapper(entity)
        model_wrapper.master = window
        template = load_template(entity)

        view = GenericListView(window, model_wrapper, template)
        view.pack(fill="both", expand=True)

        if entity in ["factions", "places", "npcs"]:
            ctk.CTkButton(
                window,
                text=f"Load {entity.capitalize()}",
                command=lambda: load_items_from_json(view, entity)
            ).pack(pady=5)

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
