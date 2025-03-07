import customtkinter as ctk
import json
import os

from tkinter import filedialog, messagebox, Toplevel, Listbox, MULTIPLE
from modules.generic.generic_list_view import GenericListView
from modules.generic.generic_model_wrapper import GenericModelWrapper
from modules.helpers.window_helper import position_window_at_top
from docx import Document
from modules.generic.scenario_detail_view import ScenarioDetailView
from modules.npcs.npc_graph_editor import NPCGraphEditor  # Import the graph editor
from modules.helpers.template_loader import load_template

# Other imports...


def load_items_from_json(view, entity_name):
    file_path = filedialog.askopenfilename(
        title=f"Load {entity_name.capitalize()} from JSON",
        filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
    )
    if not file_path:
        return

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            items = data.get(entity_name, [])

            for item in items:
                view.add_item(item)

            messagebox.showinfo("Success", f"{len(items)} {entity_name} loaded successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load {entity_name}: {e}")


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
        preview_and_save(selected_scenarios)
        selection_window.destroy()

    ctk.CTkButton(selection_window, text="Export Selected", command=export_selected).pack(pady=5)

def preview_and_save(selected_scenarios):
    
    place_items = {place["Name"]: place for place in place_wrapper.load_items()}
    npc_items = {npc["Name"]: npc for npc in npc_wrapper.load_items()}

    file_path = filedialog.asksaveasfilename(
        defaultextension=".docx",
        filetypes=[("Word Files", "*.docx"), ("All Files", "*.*")],
        title="Save Scenario Export"
    )
    if not file_path:
        return

    doc = Document()
    doc.add_heading("Campaign Scenarios", level=1)

    for scenario in selected_scenarios:
        title = scenario.get("Title", "Unnamed Scenario")
        summary = scenario.get("Summary", "No description provided.")
        secrets = scenario.get("Secrets", "No secrets provided.")
        doc.add_heading(title, level=2)
        
        # Export Summary using current formatting logic
        doc.add_heading("Summary", level=3)
        if isinstance(summary, dict):
            p = doc.add_paragraph()
            run = p.add_run(summary.get("text", ""))
            apply_formatting(run, summary.get("formatting", {}))
        else:
            doc.add_paragraph(str(summary))
        
        # Export Secrets using current formatting logic
        doc.add_heading("Secrets", level=3)
        if isinstance(secrets, dict):
            p = doc.add_paragraph()
            run = p.add_run(secrets.get("text", ""))
            apply_formatting(run, secrets.get("formatting", {}))
        else:
            doc.add_paragraph(str(secrets))

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

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("GMCampaignDesigner")
        position_window_at_top(self)
        self.geometry("600x800")
        self.place_wrapper = GenericModelWrapper("places")
        self.npc_wrapper = GenericModelWrapper("npcs")
        self.faction_wrapper = GenericModelWrapper("factions")

        ctk.CTkButton(self, text="Manage Factions", command=lambda: self.open_entity("factions")).pack(pady=5)
        ctk.CTkButton(self, text="Manage Places", command=lambda: self.open_entity("places")).pack(pady=5)
        ctk.CTkButton(self, text="Manage NPCs", command=lambda: self.open_entity("npcs")).pack(pady=5)
        ctk.CTkButton(self, text="Manage Scenarios", command=lambda: self.open_entity("scenarios")).pack(pady=5)
        ctk.CTkButton(self, text="Export Scenarios", command=preview_and_export_scenarios).pack(pady=5)
        ctk.CTkButton(self, text="Open GM Screen", command=self.open_gm_screen).pack(pady=5)
        ctk.CTkButton(self, text="Manage NPC Graphs", command=self.open_npc_graph_editor).pack(pady=5)  # NEW BUTTON
       
    def open_entity(self, entity):
        window = ctk.CTkToplevel(self)
        window.title(f"Manage {entity.capitalize()}")
        window.geometry("1500x700")
        window.transient(self)
        window.lift()
        window.focus_force()

        model_wrapper = GenericModelWrapper(entity)
        model_wrapper.master = window
        template = load_template(entity)

        view = GenericListView(window, model_wrapper, template)
        view.pack(fill="both", expand=True)

        if entity in ["factions", "places", "npcs", "scenarios"]:
            ctk.CTkButton(
                window,
                text=f"Load {entity.capitalize()}",
                command=lambda: load_items_from_json(view, entity)
            ).pack(pady=5)
    def open_gm_screen(self):
        scenario_wrapper = GenericModelWrapper("scenarios")
        scenarios = scenario_wrapper.load_items()

        if not scenarios:
            messagebox.showwarning("No Scenarios", "No scenarios available.")
            return

        select_win = ctk.CTkToplevel(self)
        select_win.title("Select Scenario")
        select_win.geometry("800x600")

        scenario_titles = [scenario["Title"] for scenario in scenarios]

        listbox = Listbox(select_win, selectmode="single", height=15)
        listbox.pack(fill="both", expand=True, padx=10, pady=10)

        for title in scenario_titles:
            listbox.insert("end", title)

        def open_selected_scenario():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a scenario.")
                return

            selected_scenario = scenarios[selection[0]]

            gm_screen_win = ctk.CTkToplevel(self)
            gm_screen_win.title("GM Screen")
            gm_screen_win.geometry("1280x720")

            scenario_detail_view = ScenarioDetailView(gm_screen_win, scenario_item=selected_scenario)
            scenario_detail_view.pack(fill="both", expand=True)

            # Properly destroy select_win after safely opening the new window
            select_win.after(100, select_win.destroy)

        ctk.CTkButton(select_win, text="Open Scenario", command=open_selected_scenario).pack(pady=10)
    
    def open_npc_graph_editor(self):
        NPCGraphEditor(self, self.npc_wrapper, self.faction_wrapper)


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()