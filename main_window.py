import sqlite3
import customtkinter as ctk
import json
import os
import subprocess
import time
import requests
import shutil

from tkinter import filedialog, messagebox, Toplevel, Listbox, MULTIPLE
from modules.generic.generic_list_view import GenericListView
from modules.generic.generic_model_wrapper import GenericModelWrapper
from modules.helpers.window_helper import position_window_at_top
from docx import Document
from modules.generic.scenario_detail_view import ScenarioDetailView
from modules.npcs.npc_graph_editor import NPCGraphEditor  # Import the graph editor
from modules.scenarios.scenario_graph_editor import ScenarioGraphEditor
from modules.helpers.template_loader import load_template
from modules.generic.generic_editor_window import GenericEditorWindow
from modules.helpers import rich_text_editor, text_helpers
from modules.helpers.rich_text_editor import RichTextEditor
from modules.scenarios.scenario_importer import ScenarioImportWindow
from modules.generic.export_for_foundry import preview_and_export_foundry
from PIL import Image, ImageTk
from modules.helpers.config_helper import ConfigHelper
from modules.helpers.swarmui_helper import get_available_models

SWARMUI_PROCESS = None

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


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
            view.add_items(items)
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


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("GMCampaignDesigner")
        self.geometry("1920x980")
        self.minsize(1920, 980)

        self.attributes("-fullscreen", True)

        position_window_at_top(self)

        icon_path = os.path.join("assets", "GMCampaignDesigner.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        self.init_db()

        # Main layout frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True)

        # Sidebar frame on the left
        sidebar_frame = ctk.CTkFrame(main_frame, width=220)
        sidebar_frame.pack(side="left", fill="y", padx=5, pady=5)
        sidebar_frame.pack_propagate(False)

        # Inner frame for padding/centering in sidebar
        sidebar_inner = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
        sidebar_inner.pack(fill="both", expand=True, padx=5, pady=5)

        # Content frame on the right
        self.content_frame = ctk.CTkFrame(main_frame)
        self.content_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Logo (60x60)
        logo_path = os.path.join("assets", "GMCampaignDesigner logo.png")
        if os.path.exists(logo_path):
            logo_image = Image.open(logo_path).resize((60, 60))
            logo = ctk.CTkImage(light_image=logo_image, dark_image=logo_image, size=(100, 100))
            self.logo_image = logo
            logo_label = ctk.CTkLabel(sidebar_inner, image=logo, text="")
            logo_label.pack(pady=(0, 3), anchor="center")

        # Header label
        header_label = ctk.CTkLabel(sidebar_inner, text="Campaign Tools", font=("Helvetica", 16, "bold"))
        header_label.pack(pady=(0, 5), anchor="center")

        # Model loading
        self.models_path = ConfigHelper.get("Paths", "models_path", fallback=r"E:\SwarmUI\SwarmUI\Models\Stable-diffusion")
        self.model_options = get_available_models()

        # Database display container (blue border)
        db_container = ctk.CTkFrame(
            sidebar_inner,
            fg_color="transparent",
            border_color="#005fa3",
            border_width=2,
            corner_radius=8
        )
        db_container.pack(pady=(0, 5), anchor="center", fill="x", padx=5)

        db_title_label = ctk.CTkLabel(
            db_container,
            text="Database:",
            font=("Segoe UI", 16, "bold"),
            fg_color="transparent",
            text_color="white"
        )
        db_title_label.pack(pady=(3, 0), anchor="center")

        db_path = ConfigHelper.get("Database", "path", fallback="default_campaign.db")
        db_name = os.path.splitext(os.path.basename(db_path))[0]

        self.db_name_label = ctk.CTkLabel(
            db_container,
            text=db_name,
            font=("Segoe UI", 14, "italic"),
            fg_color="transparent",
            text_color="white"
        )
        self.db_name_label.pack(pady=(0, 3), anchor="center")

        # Initialize wrappers
        self.place_wrapper = GenericModelWrapper("places")
        self.npc_wrapper = GenericModelWrapper("npcs")
        self.faction_wrapper = GenericModelWrapper("factions")
        self.object_wrapper = GenericModelWrapper("objects")

        # Button config
        button_config = {
            "width": 180,
            "height": 32,
            "anchor": "center",
            "corner_radius": 12,
            "fg_color": "#0077CC",
            "hover_color": "#005fa3",
            "border_width": 1,
            "border_color": "#005fa3",
            "font": ("Segoe UI", 13, "bold"),
        }

        # Database Tools section
        db_frame = ctk.CTkFrame(sidebar_inner, fg_color="transparent", border_width=2, border_color="#2E4A5F", corner_radius=8)
        db_frame.pack(fill="x", pady=(5, 5), padx=0)
        ctk.CTkLabel(db_frame, text="Tools", font=("Helvetica", 16, "bold"), fg_color="transparent").pack(pady=(2, 2))
        ctk.CTkButton(db_frame, text="Change Data\nStorage", command=self.change_database_storage, **button_config).pack(pady=2)
        ctk.CTkButton(db_frame, text="Set SwarmUI Path", command=self.select_swarmui_path, **button_config).pack(pady=2)
        ctk.CTkLabel(db_frame, text="", fg_color="transparent").pack(pady=(0, 1))

        # Managing section
        manage_frame = ctk.CTkFrame(sidebar_inner, fg_color="transparent", border_width=2, border_color="#2E4A5F", corner_radius=8)
        manage_frame.pack(fill="x", pady=(0, 5), padx=0)
        inner_frame = ctk.CTkFrame(manage_frame, fg_color="transparent")
        inner_frame.pack(fill="x", padx=5, pady=3)
        ctk.CTkLabel(inner_frame, text="Managing", font=("Helvetica", 16, "bold"), fg_color="transparent").pack(pady=(2, 2))
        ctk.CTkButton(inner_frame, text="Manage Scenarios", command=lambda: self.open_entity("scenarios"), **button_config).pack(pady=2)
        ctk.CTkButton(inner_frame, text="Manage NPCs", command=lambda: self.open_entity("npcs"), **button_config).pack(pady=2)
        ctk.CTkButton(inner_frame, text="Manage Factions", command=lambda: self.open_entity("factions"), **button_config).pack(pady=2)
        ctk.CTkButton(inner_frame, text="Manage Places", command=lambda: self.open_entity("places"), **button_config).pack(pady=2)
        ctk.CTkButton(inner_frame, text="Manage Objects", command=lambda: self.open_entity("objects"), **button_config).pack(pady=2)
        ctk.CTkLabel(inner_frame, text="", fg_color="transparent").pack(pady=(0, 1))

        # Tools section
        tools_frame = ctk.CTkFrame(sidebar_inner, fg_color="transparent", border_width=2, border_color="#2E4A5F", corner_radius=8)
        tools_frame.pack(fill="x", pady=(0, 5), padx=0)
        ctk.CTkLabel(tools_frame, text="Tools", font=("Helvetica", 16, "bold"), fg_color="transparent").pack(pady=(2, 2))
        ctk.CTkButton(tools_frame, text="Export Scenarios", command=self.preview_and_export_scenarios, **button_config).pack(pady=2)
        ctk.CTkButton(tools_frame, text="Open GM Screen", command=self.open_gm_screen, **button_config).pack(pady=2)
        ctk.CTkButton(tools_frame, text="Open NPC\nGraph Editor", command=self.open_npc_graph_editor, **button_config).pack(pady=2)
        ctk.CTkButton(tools_frame, text="Open Scenario\nGraph Editor", command=self.open_scenario_graph_editor, **button_config).pack(pady=2)
        ctk.CTkLabel(tools_frame, text="", fg_color="transparent").pack(pady=(0, 1))

        # Generating section
        gen_frame = ctk.CTkFrame(sidebar_inner, fg_color="transparent", border_width=2, border_color="#2E4A5F", corner_radius=8)
        gen_frame.pack(fill="x", pady=(0, 5), padx=0)
        ctk.CTkLabel(gen_frame, text="Generating", font=("Helvetica", 16, "bold"), fg_color="transparent").pack(pady=(2, 2))
        ctk.CTkButton(gen_frame, text="Generate NPC\nPortraits", command=self.generate_missing_npc_portraits, **button_config).pack(pady=2)
        ctk.CTkButton(gen_frame, text="Associate NPC\nPortraits", command=self.associate_npc_portraits, **button_config).pack(pady=2)
        
        ctk.CTkButton(gen_frame, text="Import Scenario", command=self.open_scenario_importer, **button_config).pack(pady=2)
        ctk.CTkButton(gen_frame, text="Export Scenarios\nfor Foundry", command=self.export_foundry, **button_config).pack(pady=2)
        ctk.CTkLabel(gen_frame, text="", fg_color="transparent").pack(pady=(0, 1))

        # Exit button at bottom
        # Add a red cross exit button to the upper-right corner of the main window.
        exit_button = ctk.CTkButton(self, text="✕", command=self.destroy,
                                    fg_color="red", hover_color="#AA0000",
                                    width=20, height=20, corner_radius=15)
        exit_button.place(relx=0.9999, rely=0.01, anchor="ne")
    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def open_entity(self, entity):
        self.clear_content()
        container = ctk.CTkFrame(self.content_frame)
        container.pack(fill="both", expand=True)
        model_wrapper = GenericModelWrapper(entity)
        template = load_template(entity)
        view = GenericListView(container, model_wrapper, template)
        view.pack(fill="both", expand=True)
        load_button = ctk.CTkButton(container,
                                    text=f"Load {entity.capitalize()}",
                                    command=lambda: load_items_from_json(view, entity))
        load_button.pack(pady=5)

    def open_gm_screen(self):
        scenario_wrapper = GenericModelWrapper("scenarios")
        scenarios = scenario_wrapper.load_items()
        if not scenarios:
            messagebox.showwarning("No Scenarios", "No scenarios available.")
            return
        self.clear_content()
        container = ctk.CTkFrame(self.content_frame, fg_color="#2B2B2B")
        container.pack(fill="both", expand=True)
        select_label = ctk.CTkLabel(container, text="Select a Scenario", font=("Helvetica", 16, "bold"), fg_color="#2B2B2B", text_color="white")
        select_label.pack(pady=10)
        listbox = Listbox(container, selectmode="single", height=15, bg="#2B2B2B", fg="white", highlightthickness=0, bd=0)
        listbox.pack(fill="both", expand=True, padx=10, pady=10)
        for scenario in scenarios:
            listbox.insert("end", scenario["Title"])
        def open_selected_scenario():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a scenario.")
                return
            selected_scenario = scenarios[selection[0]]
            self.clear_content()
            detail_container = ctk.CTkFrame(self.content_frame)
            detail_container.pack(fill="both", expand=True)
            scenario_detail_view = ScenarioDetailView(detail_container, scenario_item=selected_scenario)
            scenario_detail_view.pack(fill="both", expand=True)
        open_button = ctk.CTkButton(container, text="Open Scenario", command=open_selected_scenario)
        open_button.pack(pady=10)

    def open_npc_graph_editor(self):
        self.clear_content()
        container = ctk.CTkFrame(self.content_frame)
        container.pack(fill="both", expand=True)
        npc_graph_editor = NPCGraphEditor(container, self.npc_wrapper, self.faction_wrapper)
        npc_graph_editor.pack(fill="both", expand=True)

    def open_scenario_graph_editor(self):
        self.clear_content()
        container = ctk.CTkFrame(self.content_frame)
        container.pack(fill="both", expand=True)
        scenario_wrapper = GenericModelWrapper("scenarios")
        npc_wrapper = GenericModelWrapper("npcs")
        place_wrapper = GenericModelWrapper("places")
        editor = ScenarioGraphEditor(container, scenario_wrapper, npc_wrapper, place_wrapper)
        editor.pack(fill="both", expand=True)

    def export_foundry(self):
        preview_and_export_foundry(self)

    def open_scenario_importer(self):
        self.clear_content()
        container = ctk.CTkFrame(self.content_frame)
        container.pack(fill="both", expand=True)
        ScenarioImportWindow(container)

    def change_database_storage(self):
        choice = messagebox.askquestion("Change Database", "Do you want to open an existing database file?")
        if choice == "yes":
            file_path = filedialog.askopenfilename(
                title="Select Database",
                filetypes=[("SQLite DB Files", "*.db"), ("All Files", "*.*")]
            )
            if not file_path:
                return
            new_db_path = file_path
        else:
            new_db_path = filedialog.asksaveasfilename(
                title="Create New Database",
                defaultextension=".db",
                filetypes=[("SQLite DB Files", "*.db"), ("All Files", "*.*")]
            )
            if not new_db_path:
                return
            conn = sqlite3.connect(new_db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    npc_name TEXT,
                    x INTEGER,
                    y INTEGER,
                    color TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    npc_name1 TEXT,
                    npc_name2 TEXT,
                    text TEXT,
                    arrow_mode TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shapes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT,
                    x INTEGER,
                    y INTEGER,
                    w INTEGER,
                    h INTEGER,
                    color TEXT,
                    tag TEXT,
                    z INTEGER
                )
            ''')
            conn.commit()
            conn.close()
        ConfigHelper.set("Database", "path", new_db_path)
        self.init_db()
        self.place_wrapper = GenericModelWrapper("places")
        self.npc_wrapper = GenericModelWrapper("npcs")
        self.faction_wrapper = GenericModelWrapper("factions")
        self.object_wrapper = GenericModelWrapper("objects")
        db_name = os.path.splitext(os.path.basename(new_db_path))[0]
        self.db_name_label.configure(text=f"{db_name}")

    def init_db(self):
        db_path = ConfigHelper.get("Database", "path", fallback="default_campaign.db")
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS npcs (
                Name TEXT PRIMARY KEY,
                Role TEXT,
                Description TEXT,
                Secret TEXT,
                Quote TEXT,
                RoleplayingCues TEXT,
                Personality TEXT,
                Motivation TEXT,
                Background TEXT,
                Traits TEXT,
                Genre TEXT,
                Factions TEXT,
                Objects TEXT,
                Portrait TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS scenarios (
                Title TEXT PRIMARY KEY,
                Summary TEXT,
                Secrets TEXT,
                Places TEXT,
                NPCs TEXT,
                Objects TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS factions (
                Name TEXT PRIMARY KEY,
                Description TEXT,
                Secrets TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS places (
                Name TEXT PRIMARY KEY,
                Description TEXT,
                NPCs TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS objects (
                Name TEXT PRIMARY KEY,
                Description TEXT,
                Secrets TEXT,
                Portrait TEXT
            )
        ''')
        self.update_table_schema( self.conn, self.cursor )
        self.conn.commit()
        self.conn.close()
        

    def select_swarmui_path(self):
        folder = filedialog.askdirectory(title="Select SwarmUI Path")
        if folder:
            ConfigHelper.set("Paths", "swarmui_path", folder)
            messagebox.showinfo("SwarmUI Path Set", f"SwarmUI path set to:\n{folder}")

    def launch_swarmui(self):
        global SWARMUI_PROCESS
        # Retrieve the SwarmUI path from config.ini
        swarmui_path = ConfigHelper.get("Paths", "swarmui_path", fallback=r"E:\SwarmUI\SwarmUI")
        SWARMUI_CMD = os.path.join(swarmui_path, "launch-windows.bat")
        env = os.environ.copy()
        env.pop('VIRTUAL_ENV', None)
        if SWARMUI_PROCESS is None or SWARMUI_PROCESS.poll() is not None:
            try:
                SWARMUI_PROCESS = subprocess.Popen(
                    SWARMUI_CMD,
                    shell=True,
                    cwd=swarmui_path,
                    env=env
                )
                time.sleep(120.0)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to launch SwarmUI: {e}")

    def cleanup_swarmui(self):
        global SWARMUI_PROCESS
        if SWARMUI_PROCESS is not None and SWARMUI_PROCESS.poll() is None:
            SWARMUI_PROCESS.terminate()

    def generate_portrait_for_npc(self, npc):
        self.launch_swarmui()
        SWARM_API_URL = "http://127.0.0.1:7801"
        try:
            session_url = f"{SWARM_API_URL}/API/GetNewSession"
            session_response = requests.post(session_url, json={}, headers={"Content-Type": "application/json"})
            session_data = session_response.json()
            session_id = session_data.get("session_id")
            if not session_id:
                print(f"Failed to obtain session ID for NPC {npc.get('Name', 'Unknown')}")
                return
            npc_name = npc.get("Name", "Unknown")
            npc_role = npc.get("Role", "Unknown")
            npc_faction = npc.get("Factions", "Unknown")
            npc_desc = npc.get("Description", "Unknown")
            npc_desc = text_helpers.format_longtext(npc_desc)
            prompt = f"{npc_name} {npc_desc} {npc_role} {npc_faction}"
            prompt_data = {
                "session_id": session_id,
                "images": 1,
                "prompt": prompt,
                "negativeprompt": ("blurry, low quality, comics style, mangastyle, paint style, watermark, ugly, "
                                "monstrous, too many fingers, too many legs, too many arms, bad hands, "
                                "unrealistic weapons, bad grip on equipment, nude"),
                "model": self.selected_model.get(),
                "width": 1024,
                "height": 1024,
                "cfgscale": 9,
                "steps": 20,
                "seed": -1
            }
            generate_url = f"{SWARM_API_URL}/API/GenerateText2Image"
            image_response = requests.post(generate_url, json=prompt_data, headers={"Content-Type": "application/json"})
            image_data = image_response.json()
            images = image_data.get("images")
            if not images or len(images) == 0:
                print(f"Image generation failed for NPC '{npc_name}'")
                return
            image_url = f"{SWARM_API_URL}/{images[0]}"
            downloaded_image = requests.get(image_url)
            if downloaded_image.status_code != 200:
                print(f"Failed to download generated image for NPC '{npc_name}'")
                return
            output_filename = f"{npc_name.replace(' ', '_')}_portrait.png"
            with open(output_filename, "wb") as f:
                f.write(downloaded_image.content)
            GENERATED_FOLDER = "assets/generated"
            os.makedirs(GENERATED_FOLDER, exist_ok=True)
            shutil.copy(output_filename, os.path.join(GENERATED_FOLDER, output_filename))
            npc["Portrait"] = self.copy_and_resize_portrait(npc, output_filename)
            os.remove(output_filename)
            print(f"Generated portrait for NPC '{npc_name}'")
        except Exception as e:
            print(f"Error generating portrait for NPC '{npc.get('Name', 'Unknown')}': {e}")

    def generate_missing_npc_portraits(self):
        def confirm_model_and_continue():
            ConfigHelper.set("LastUsed", "model", self.selected_model.get())
            top.destroy()
            self.generate_portraits_continue()
        top = ctk.CTkToplevel(self)
        top.title("Select AI Model")
        top.geometry("400x200")
        top.transient(self)
        top.grab_set()
        ctk.CTkLabel(top, text="Select AI Model to use for portrait generation:").pack(pady=20)
        last_model = ConfigHelper.get("LastUsed", "model", fallback=None)
        if last_model in self.model_options:
            self.selected_model = ctk.StringVar(value=last_model)
        else:
            self.selected_model = ctk.StringVar(value=self.model_options[0])
        ctk.CTkOptionMenu(top, values=self.model_options, variable=self.selected_model).pack(pady=10)
        ctk.CTkButton(top, text="Continue", command=confirm_model_and_continue).pack(pady=10)

    def generate_portraits_continue(self):
        # Open a new database connection.
        db_path = ConfigHelper.get("Database", "path", fallback="default_campaign.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Retrieve all NPC records.
        cursor.execute("SELECT * FROM npcs")
        npc_rows = cursor.fetchall()
        modified = False

        for npc in npc_rows:
            portrait = npc["Portrait"] if npc["Portrait"] is not None else ""
            if not portrait.strip():
                # Convert the row to a dictionary so that generate_portrait_for_npc works as expected.
                npc_dict = dict(npc)
                self.generate_portrait_for_npc(npc_dict)
                if npc_dict.get("Portrait"):
                    # Update the portrait field in the database.
                    cursor.execute("UPDATE npcs SET Portrait = ? WHERE Name = ?", (npc_dict["Portrait"], npc["Name"]))
                    modified = True

        if modified:
            conn.commit()
            print("Updated NPC database with generated portraits.")
        else:
            print("No NPCs were missing portraits.")

        conn.close()

    def copy_and_resize_portrait(self, npc, src_path):
        PORTRAIT_FOLDER = "assets/portraits"
        MAX_PORTRAIT_SIZE = (1024, 1024)
        os.makedirs(PORTRAIT_FOLDER, exist_ok=True)
        npc_name = npc.get("Name", "Unnamed").replace(" ", "_")
        ext = os.path.splitext(src_path)[-1].lower()
        dest_filename = f"{npc_name}_{id(self)}{ext}"
        dest_path = os.path.join(PORTRAIT_FOLDER, dest_filename)
        with Image.open(src_path) as img:
            img = img.convert("RGB")
            img.thumbnail(MAX_PORTRAIT_SIZE)
            img.save(dest_path)
        return dest_path

    def preview_and_export_scenarios(self):
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
            self.preview_and_save(selected_scenarios)
            selection_window.destroy()
        ctk.CTkButton(selection_window, text="Export Selected", command=export_selected).pack(pady=5)

    def preview_and_save(self, selected_scenarios):
        place_items = {place["Name"]: place for place in self.place_wrapper.load_items()}
        npc_items = {npc["Name"]: npc for npc in self.npc_wrapper.load_items()}
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
            doc.add_heading("Summary", level=3)
            if isinstance(summary, dict):
                p = doc.add_paragraph()
                run = p.add_run(summary.get("text", ""))
                apply_formatting(run, summary.get("formatting", {}))
            else:
                doc.add_paragraph(str(summary))
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
                npc = npc_items.get(npc_name, {"Name": npc_name, "Role": "Unknown",
                                            "Description": {"text": "Unknown NPC", "formatting": {}}})
                p = doc.add_paragraph(f"- {npc['Name']} ({npc['Role']}, {npc.get('Faction', 'Unknown')}): ")
                description = npc['Description']
                if isinstance(description, dict):
                    run = p.add_run(description.get("text", ""))
                    apply_formatting(run, description.get("formatting", {}))
                else:
                    p.add_run(str(description))
        doc.save(file_path)
        messagebox.showinfo("Export Successful", f"Scenario exported successfully to:\n{file_path}")

    def normalize_name(self, name):
        """
        Normalize a name by converting to lowercase and replacing underscores with spaces.
        """
        return name.lower().replace('_', ' ').strip()

    def build_portrait_mapping(self):
        """
        Reads the assets/portraits/dir.txt file and builds a dictionary mapping
        normalized NPC names to their corresponding portrait filenames.
        """
        mapping = {}
        dir_txt_path = os.path.join("assets", "portraits", "dir.txt")
        if not os.path.exists(dir_txt_path):
            print(f"dir.txt not found at {dir_txt_path}")
            return mapping

        with open(dir_txt_path, "r", encoding="cp1252") as f:
            for line in f:
                line = line.strip()
                # Process only lines that end with .png
                if not line.lower().endswith(".png"):
                    continue
                # Assume the file name is the last token (ignoring date/size info)
                tokens = line.split()
                file_name = tokens[-1]
                if file_name.lower() == "dir.txt":
                    continue
                # Remove the file extension and split by underscores
                base_name = os.path.splitext(file_name)[0]
                parts = base_name.split("_")
                filtered_parts = []
                for part in parts:
                    # Skip "portrait" and parts that are purely digits (likely timestamps)
                    if part.lower() == "portrait" or part.isdigit():
                        continue
                    filtered_parts.append(part)
                if filtered_parts:
                    # Join the remaining parts to form a candidate NPC name
                    candidate = " ".join(filtered_parts)
                    normalized_candidate = self.normalize_name(candidate)
                    mapping[normalized_candidate] = file_name
        return mapping

    def associate_npc_portraits(self):
        """
        Associates each NPC in the database with the matching portrait file
        found in the assets/portraits directory (as defined by dir.txt).

        The function reads each NPC from the database and, if its Portrait field is empty,
        normalizes its Name and checks for a match in the portrait mapping.
        On finding a match, the Portrait field is updated with the relative path.
        """
        portrait_mapping = self.build_portrait_mapping()
        if not portrait_mapping:
            print("No portrait mapping was built.")
            return

        # Open the database using the configuration settings
        db_path = ConfigHelper.get("Database", "path", fallback="default_campaign.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT Name, Portrait FROM npcs")
        npc_rows = cursor.fetchall()
        modified = False

        for npc in npc_rows:
            npc_name = npc["Name"].strip()
            normalized_npc = self.normalize_name(npc_name)
            if normalized_npc in portrait_mapping:
                portrait_file = portrait_mapping[normalized_npc]
                # Only update if the Portrait field is empty
                if not npc["Portrait"] or npc["Portrait"].strip() == "":
                    new_portrait_path = os.path.join("assets", "portraits", portrait_file)
                    cursor.execute("UPDATE npcs SET Portrait = ? WHERE Name = ?", (new_portrait_path, npc_name))
                    print(f"Associated portrait '{portrait_file}' with NPC '{npc_name}'")
                    modified = True

        if modified:
            conn.commit()
            print("NPC database updated with associated portraits.")
        else:
            print("No NPC records were updated. Either all have portraits or no matches were found.")

        conn.close()

    def update_table_schema(self, conn, cursor):
        def alter_table_if_missing(table, required_columns):
            # Get list of existing columns for the table.
            cursor.execute(f"PRAGMA table_info({table})")
            existing_columns = {row["name"] for row in cursor.fetchall()}
            for col, col_def in required_columns.items():
                if col not in existing_columns:
                    # Note: SQLite's ALTER TABLE command doesn't allow modifying an existing PK constraint.
                    alter_query = f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"
                    cursor.execute(alter_query)
                    print(f"Added column '{col}' to table '{table}'.")

        # Define required columns for each table.
        npcs_columns = {
            "Name": "TEXT",  # already part of PK if table was created with IF NOT EXISTS.
            "Role": "TEXT",
            "Description": "TEXT",
            "Secret": "TEXT",
            "Quote": "TEXT",
            "RoleplayingCues": "TEXT",
            "Personality": "TEXT",
            "Motivation": "TEXT",
            "Background": "TEXT",
            "Traits": "TEXT",
            "Genre": "TEXT",
            "Factions": "TEXT",
            "Objects": "TEXT",
            "Portrait": "TEXT"
        }
        scenarios_columns = {
            "Title": "TEXT",
            "Summary": "TEXT",
            "Secrets": "TEXT",
            "Places": "TEXT",
            "NPCs": "TEXT",
            "Objects": "TEXT"
        }
        factions_columns = {
            "Name": "TEXT",
            "Description": "TEXT",
            "Secrets": "TEXT"
        }
        places_columns = {
            "Name": "TEXT",
            "Description": "TEXT",
            "NPCs": "TEXT"
        }
        objects_columns = {
            "Name": "TEXT",
            "Description": "TEXT",
            "Secrets": "TEXT",
            "Portrait": "TEXT"
        }

        alter_table_if_missing("npcs", npcs_columns)
        alter_table_if_missing("scenarios", scenarios_columns)
        alter_table_if_missing("factions", factions_columns)
        alter_table_if_missing("places", places_columns)
        alter_table_if_missing("objects", objects_columns)


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()