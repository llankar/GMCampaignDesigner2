import os
import json
import sqlite3
import subprocess
import time
import requests
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, Listbox, MULTIPLE, PhotoImage
#import logging

import customtkinter as ctk
from PIL import Image, ImageTk
from docx import Document

# Modular helper imports
from modules.helpers.window_helper import position_window_at_top
from modules.helpers.template_loader import load_template
from modules.helpers.config_helper import ConfigHelper
from modules.helpers.swarmui_helper import get_available_models
from modules.helpers.db_helper import init_db
from modules.ui.tooltip import ToolTip
from modules.ui.icon_button import create_icon_button

from modules.generic.generic_list_view import GenericListView
from modules.generic.generic_model_wrapper import GenericModelWrapper
from modules.scenarios.scenario_detail_view import ScenarioDetailView
from modules.npcs.npc_graph_editor import NPCGraphEditor
from modules.scenarios.scenario_graph_editor import ScenarioGraphEditor
from modules.generic.generic_editor_window import GenericEditorWindow
from modules.scenarios.scenario_importer import ScenarioImportWindow
from modules.generic.export_for_foundry import preview_and_export_foundry
from modules.helpers import text_helpers
from modules.web.npc_graph_webviewer import launch_web_viewer

# Set up CustomTkinter appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Global process variable for SwarmUI
SWARMUI_PROCESS = None

#logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("GMCampaignDesigner")
        self.geometry("1920x980")
        self.minsize(1920, 980)
        self.attributes("-fullscreen", True)

        position_window_at_top(self)
        self.set_window_icon()
        self.init_db()
        self.create_layout()
        self.load_icons()
        self.create_sidebar()
        self.create_content_area()
        self.create_exit_button()
        self.load_model_config()
        self.init_wrappers()

    # ---------------------------
    # Setup and Layout Methods
    # ---------------------------
    def set_window_icon(self):
        icon_path = os.path.join("assets", "GMCampaignDesigner.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        icon_image = PhotoImage(file=os.path.join("assets", "GMCampaignDesigner logo.png"))
        self.tk.call('wm', 'iconphoto', self._w, icon_image)

    def init_db(self):
        db_path = ConfigHelper.get("Database", "path", fallback="default_campaign.db")
        init_db(db_path, self.update_table_schema)

    def update_table_schema(self, conn, cursor):
        def alter_table_if_missing(table, required_columns):
            cursor.execute(f"PRAGMA table_info({table})")
            existing_columns = {row["name"] for row in cursor.fetchall()}
            for col, col_def in required_columns.items():
                if col not in existing_columns:
                    alter_query = f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"
                    cursor.execute(alter_query)
                    #logging.debug("Added column '%s' to table '%s'.", col, table)
        npcs_columns = {
            "Name": "TEXT",
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
            "Creatures": "TEXT",
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
        creatures_columns = {
            "Name": "TEXT",
            "Type": "TEXT",
            "Description": "TEXT",
            "Weakness": "TEXT",
            "Powers": "TEXT",
            "Stats": "TEXT",
            "Background": "TEXT",
            "Genre": "TEXT",
            "Portrait": "TEXT"
        }
        alter_table_if_missing("npcs", npcs_columns)
        alter_table_if_missing("scenarios", scenarios_columns)
        alter_table_if_missing("factions", factions_columns)
        alter_table_if_missing("places", places_columns)
        alter_table_if_missing("objects", objects_columns)
        alter_table_if_missing("creatures", creatures_columns)

    def create_layout(self):
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True)

    def load_icons(self):
        self.icons = {
            "change_db": self.load_icon("database_icon.png", size=(64, 64)),
            "swarm_path": self.load_icon("folder_icon.png", size=(64, 64)),
            "manage_scenarios": self.load_icon("scenario_icon.png", size=(64, 64)),
            "manage_npcs": self.load_icon("npc_icon.png", size=(64, 64)),
            "manage_creatures": self.load_icon("creature_icon.png", size=(64, 64)),
            "manage_factions": self.load_icon("faction_icon.png", size=(64, 64)),
            "manage_places": self.load_icon("places_icon.png", size=(64, 64)),
            "manage_objects": self.load_icon("objects_icon.png", size=(64, 64)),
            "export_scenarios": self.load_icon("export_icon.png", size=(64, 64)),
            "gm_screen": self.load_icon("gm_screen_icon.png", size=(64, 64)),
            "npc_graph": self.load_icon("npc_graph_icon.png", size=(64, 64)),
            "scenario_graph": self.load_icon("scenario_graph_icon.png", size=(64, 64)),
            "generate_portraits": self.load_icon("generate_icon.png", size=(64, 64)),
            "associate_portraits": self.load_icon("associate_icon.png", size=(64, 64)),
            "import_scenario": self.load_icon("import_icon.png", size=(64, 64)),
            "export_foundry": self.load_icon("export_foundry_icon.png", size=(64, 64))
        }

    def load_icon(self, file_name, size=(64, 64)):
        path = os.path.join("assets", file_name)
        try:
            pil_image = Image.open(path)
        except Exception as e:
            #logging.error("Error loading %s: %s", path, e)
            return None
        return ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=size)

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self.main_frame, width=220)
        self.sidebar_frame.pack(side="left", fill="y", padx=5, pady=5)
        self.sidebar_frame.pack_propagate(False)
        self.sidebar_inner = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.sidebar_inner.pack(fill="both", expand=True, padx=5, pady=5)

        # Logo
        logo_path = os.path.join("assets", "GMCampaignDesigner logo.png")
        if os.path.exists(logo_path):
            logo_image = Image.open(logo_path).resize((60, 60))
            logo = ctk.CTkImage(light_image=logo_image, dark_image=logo_image, size=(100, 100))
            self.logo_image = logo
            logo_label = ctk.CTkLabel(self.sidebar_inner, image=logo, text="")
            logo_label.pack(pady=(0, 3), anchor="center")

        # Header label
        header_label = ctk.CTkLabel(self.sidebar_inner, text="Campaign Tools", font=("Helvetica", 16, "bold"))
        header_label.pack(pady=(0, 5), anchor="center")

        # Database display container
        db_container = ctk.CTkFrame(self.sidebar_inner, fg_color="transparent",
                                    border_color="#005fa3", border_width=2, corner_radius=8)
        db_container.pack(pady=(0, 5), anchor="center", fill="x", padx=5)
        db_title_label = ctk.CTkLabel(db_container, text="Database:", font=("Segoe UI", 16, "bold"),
                                    fg_color="transparent", text_color="white")
        db_title_label.pack(pady=(3, 0), anchor="center")
        db_path = ConfigHelper.get("Database", "path", fallback="default_campaign.db")
        db_name = os.path.splitext(os.path.basename(db_path))[0]
        self.db_name_label = ctk.CTkLabel(db_container, text=db_name,
                                        font=("Segoe UI", 14, "italic"), fg_color="transparent", text_color="white")
        self.db_name_label.pack(pady=(0, 3), anchor="center")

        self.create_icon_grid()

    def create_icon_grid(self):
        icons_frame = ctk.CTkFrame(self.sidebar_inner, fg_color="transparent")
        icons_frame.pack(fill="both", expand=True, padx=5, pady=5)
        columns = 2
        for col in range(columns):
            icons_frame.grid_columnconfigure(col, weight=1)
        icons_list = [
            ("change_db", "Change Data Storage", self.change_database_storage),
            ("swarm_path", "Set SwarmUI Path", self.select_swarmui_path),
            ("manage_scenarios", "Manage Scenarios", lambda: self.open_entity("scenarios")),
            ("manage_npcs", "Manage NPCs", lambda: self.open_entity("npcs")),
            ("manage_creatures", "Manage Creatures", lambda: self.open_entity("creatures")),
            ("manage_factions", "Manage Factions", lambda: self.open_entity("factions")),
            ("manage_places", "Manage Places", lambda: self.open_entity("places")),
            ("manage_objects", "Manage Objects", lambda: self.open_entity("objects")),
            ("export_scenarios", "Export Scenarios", self.preview_and_export_scenarios),
            ("gm_screen", "Open GM Screen", self.open_gm_screen),
            ("npc_graph", "Open NPC Graph Editor", self.open_npc_graph_editor),
            ("scenario_graph", "Open Scenario Graph Editor", self.open_scenario_graph_editor),
            ("generate_portraits", "Generate Portraits", self.generate_missing_portraits),
            ("associate_portraits", "Associate NPC Portraits", self.associate_npc_portraits),
            ("import_scenario", "Import Scenario", self.open_scenario_importer),
            ("export_foundry", "Export Scenarios for Foundry", self.export_foundry)
        ]
        self.icon_buttons = []
        for idx, (icon_key, tooltip, cmd) in enumerate(icons_list):
            row = idx // columns
            col = idx % columns
            btn = create_icon_button(icons_frame, self.icons[icon_key], tooltip, cmd)
            btn.grid(row=row, column=col, padx=10, pady=10)
            self.icon_buttons.append(btn)

    def create_content_area(self):
        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

    def create_exit_button(self):
        exit_button = ctk.CTkButton(self, text="✕", command=self.destroy,
                                    fg_color="red", hover_color="#AA0000",
                                    width=20, height=20, corner_radius=15)
        exit_button.place(relx=0.9999, rely=0.01, anchor="ne")

    def load_model_config(self):
        self.models_path = ConfigHelper.get("Paths", "models_path",
                                            fallback=r"E:\SwarmUI\SwarmUI\Models\Stable-diffusion")
        self.model_options = get_available_models()

    def init_wrappers(self):
        self.place_wrapper = GenericModelWrapper("places")
        self.npc_wrapper = GenericModelWrapper("npcs")
        self.faction_wrapper = GenericModelWrapper("factions")
        self.object_wrapper = GenericModelWrapper("objects")
        self.creature_wrapper = GenericModelWrapper("creatures")

    # =============================================================
    # Methods Called by Icon Buttons (Event Handlers)
    # =============================================================
    def clear_main_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def open_entity(self, entity):
        self.clear_main_content()
        container = ctk.CTkFrame(self.content_frame)
        container.pack(fill="both", expand=True)
        model_wrapper = GenericModelWrapper(entity)
        template = load_template(entity)
        view = GenericListView(container, model_wrapper, template)
        view.pack(fill="both", expand=True)
        load_button = ctk.CTkButton(
            container,
            text=f"Load {entity.capitalize()}",
            command=lambda: self.load_items_from_json(view, entity)
        )
        load_button.pack(pady=5)

    def load_items_from_json(self, view, entity_name):
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

    def open_gm_screen(self):
        scenario_wrapper = GenericModelWrapper("scenarios")
        scenarios = scenario_wrapper.load_items()
        if not scenarios:
            messagebox.showwarning("No Scenarios", "No scenarios available.")
            return
        self.clear_main_content()
        container = ctk.CTkFrame(self.content_frame, fg_color="#2B2B2B")
        container.pack(fill="both", expand=True)
        select_label = ctk.CTkLabel(
            container,
            text="Select a Scenario",
            font=("Helvetica", 16, "bold"),
            fg_color="#2B2B2B",
            text_color="white"
        )
        select_label.pack(pady=10)
        listbox = Listbox(
            container,
            selectmode="single",
            height=15,
            bg="#2B2B2B",
            fg="white",
            highlightthickness=0,
            bd=0
        )
        listbox.pack(fill="both", expand=True, padx=10, pady=10)
        for scenario in scenarios:
            listbox.insert("end", scenario["Title"])
        def open_selected_scenario():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a scenario.")
                return
            selected_scenario = scenarios[selection[0]]
            self.clear_main_content()
            detail_container = ctk.CTkFrame(self.content_frame)
            detail_container.pack(fill="both", expand=True)
            scenario_detail_view = ScenarioDetailView(detail_container, scenario_item=selected_scenario)
            scenario_detail_view.pack(fill="both", expand=True)
        open_button = ctk.CTkButton(container, text="Open Scenario", command=open_selected_scenario)
        open_button.pack(pady=10)

    def open_npc_graph_editor(self):
        self.clear_main_content()
        container = ctk.CTkFrame(self.content_frame)
        container.pack(fill="both", expand=True)
        npc_graph_editor = NPCGraphEditor(container, self.npc_wrapper, self.faction_wrapper)
        npc_graph_editor.pack(fill="both", expand=True)

    def open_scenario_graph_editor(self):
        self.clear_main_content()
        container = ctk.CTkFrame(self.content_frame)
        container.pack(fill="both", expand=True)
        scenario_wrapper = GenericModelWrapper("scenarios")
        npc_wrapper = GenericModelWrapper("npcs")
        creature_wrapper = GenericModelWrapper("creatures")
        place_wrapper = GenericModelWrapper("places")
        editor = ScenarioGraphEditor(container, scenario_wrapper, npc_wrapper, creature_wrapper, place_wrapper)
        editor.pack(fill="both", expand=True)

    def export_foundry(self):
        preview_and_export_foundry(self)

    def open_scenario_importer(self):
        self.clear_main_content()
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

    def select_swarmui_path(self):
        folder = filedialog.askdirectory(title="Select SwarmUI Path")
        if folder:
            ConfigHelper.set("Paths", "swarmui_path", folder)
            messagebox.showinfo("SwarmUI Path Set", f"SwarmUI path set to:\n{folder}")

    def launch_swarmui(self):
        global SWARMUI_PROCESS
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

    # ------------------------------------------------------
    # Unified Generate Portraits for NPCs and Creatures
    # ------------------------------------------------------
    def generate_missing_portraits(self):
        top = ctk.CTkToplevel(self)
        top.title("Generate Portraits")
        top.geometry("300x150")
        top.transient(self)
        top.grab_set()
        # Use ctk.StringVar (not CTkStringVar)
        selection = ctk.StringVar(value="NPC")
        ctk.CTkLabel(top, text="Generate portraits for:").pack(pady=10)
        ctk.CTkRadioButton(top, text="NPCs", variable=selection, value="NPC").pack(pady=5)
        ctk.CTkRadioButton(top, text="Creatures", variable=selection, value="Creature").pack(pady=5)
        def on_confirm():
            choice = selection.get()
            top.destroy()
            if choice == "NPC":
                self.generate_missing_npc_portraits()
            else:
                self.generate_missing_creature_portraits()
        ctk.CTkButton(top, text="Continue", command=on_confirm).pack(pady=10)

    def generate_missing_npc_portraits(self):
        def confirm_model_and_continue():
            ConfigHelper.set("LastUsed", "model", self.selected_model.get())
            top.destroy()
            self.generate_portraits_continue_npcs()
        top = ctk.CTkToplevel(self)
        top.title("Select AI Model for NPCs")
        top.geometry("400x200")
        top.transient(self)
        top.grab_set()
        ctk.CTkLabel(top, text="Select AI Model to use for NPC portrait generation:").pack(pady=20)
        last_model = ConfigHelper.get("LastUsed", "model", fallback=None)
        # Use ctk.StringVar
        if last_model in self.model_options:
            self.selected_model = ctk.StringVar(value=last_model)
        else:
            self.selected_model = ctk.StringVar(value=self.model_options[0])
        ctk.CTkOptionMenu(top, values=self.model_options, variable=self.selected_model).pack(pady=10)
        ctk.CTkButton(top, text="Continue", command=confirm_model_and_continue).pack(pady=10)

    def generate_portraits_continue_npcs(self):
        db_path = ConfigHelper.get("Database", "path", fallback="default_campaign.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM npcs")
        npc_rows = cursor.fetchall()
        modified = False
        for npc in npc_rows:
            portrait = npc["Portrait"] if npc["Portrait"] is not None else ""
            if not portrait.strip():
                npc_dict = dict(npc)
                self.generate_portrait_for_npc(npc_dict)
                if npc_dict.get("Portrait"):
                    cursor.execute("UPDATE npcs SET Portrait = ? WHERE Name = ?", (npc_dict["Portrait"], npc["Name"]))
                    modified = True
        if modified:
            conn.commit()
            print("Updated NPC database with generated portraits.")
        else:
            print("No NPCs were missing portraits.")
        conn.close()

    def generate_missing_creature_portraits(self):
        def confirm_model_and_continue():
            ConfigHelper.set("LastUsed", "model", self.selected_model.get())
            top.destroy()
            self.generate_portraits_continue_creatures()
        top = ctk.CTkToplevel(self)
        top.title("Select AI Model for Creatures")
        top.geometry("400x200")
        top.transient(self)
        top.grab_set()
        ctk.CTkLabel(top, text="Select AI Model to use for creature portrait generation:").pack(pady=20)
        last_model = ConfigHelper.get("LastUsed", "model", fallback=None)
        if last_model in self.model_options:
            self.selected_model = ctk.StringVar(value=last_model)
        else:
            self.selected_model = ctk.StringVar(value=self.model_options[0])
        ctk.CTkOptionMenu(top, values=self.model_options, variable=self.selected_model).pack(pady=10)
        ctk.CTkButton(top, text="Continue", command=confirm_model_and_continue).pack(pady=10)

    def generate_portraits_continue_creatures(self):
        db_path = ConfigHelper.get("Database", "path", fallback="default_campaign.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM creatures")
        creature_rows = cursor.fetchall()
        modified = False
        for creature in creature_rows:
            portrait = creature["Portrait"] if creature["Portrait"] is not None else ""
            if not portrait.strip():
                creature_dict = dict(creature)
                self.generate_portrait_for_creature(creature_dict)
                if creature_dict.get("Portrait"):
                    cursor.execute("UPDATE creatures SET Portrait = ? WHERE Name = ?", (creature_dict["Portrait"], creature_dict["Name"]))
                    modified = True
        if modified:
            conn.commit()
            print("Updated creature database with generated portraits.")
        else:
            print("No creatures were missing portraits.")
        conn.close()

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

    def generate_portrait_for_creature(self, creature):
        self.launch_swarmui()
        SWARM_API_URL = "http://127.0.0.1:7801"
        try:
            session_url = f"{SWARM_API_URL}/API/GetNewSession"
            session_response = requests.post(session_url, json={}, headers={"Content-Type": "application/json"})
            session_data = session_response.json()
            session_id = session_data.get("session_id")
            if not session_id:
                print(f"Failed to obtain session ID for Creature {creature.get('Name', 'Unknown')}")
                return
            creature_name = creature.get("Name", "Unknown")
            creature_desc = creature.get("Description", "Unknown")
            stats = creature.get("Stats", "")
            creature_desc_formatted = text_helpers.format_longtext(creature_desc)
            prompt = f"{creature_name} {creature_desc_formatted} {stats}"
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
                print(f"Image generation failed for Creature '{creature_name}'")
                return
            image_url = f"{SWARM_API_URL}/{images[0]}"
            downloaded_image = requests.get(image_url)
            if downloaded_image.status_code != 200:
                print(f"Failed to download generated image for Creature '{creature_name}'")
                return
            output_filename = f"{creature_name.replace(' ', '_')}_portrait.png"
            with open(output_filename, "wb") as f:
                f.write(downloaded_image.content)
            GENERATED_FOLDER = "assets/generated"
            os.makedirs(GENERATED_FOLDER, exist_ok=True)
            shutil.copy(output_filename, os.path.join(GENERATED_FOLDER, output_filename))
            creature["Portrait"] = self.copy_and_resize_portrait(creature, output_filename)
            os.remove(output_filename)
            print(f"Generated portrait for Creature '{creature_name}'")
        except Exception as e:
            print(f"Error generating portrait for Creature '{creature.get('Name', 'Unknown')}': {e}")

    def copy_and_resize_portrait(self, entity, src_path):
        PORTRAIT_FOLDER = "assets/portraits"
        MAX_PORTRAIT_SIZE = (1024, 1024)
        os.makedirs(PORTRAIT_FOLDER, exist_ok=True)
        name = entity.get("Name", "Unnamed").replace(" ", "_")
        ext = os.path.splitext(src_path)[-1].lower()
        dest_filename = f"{name}_{id(self)}{ext}"
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
        listbox = Listbox(selection_window, selectmode="multiple", height=15)
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
        creature_items = {creature["Name"]: creature for creature in self.creature_wrapper.load_items()}
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
                self.apply_formatting(run, summary.get("formatting", {}))
            else:
                doc.add_paragraph(str(summary))

            doc.add_heading("Secrets", level=3)
            if isinstance(secrets, dict):
                p = doc.add_paragraph()
                run = p.add_run(secrets.get("text", ""))
                self.apply_formatting(run, secrets.get("formatting", {}))
            else:
                doc.add_paragraph(str(secrets))

            # Places Section
            doc.add_heading("Places", level=3)
            for place_name in scenario.get("Places", []):
                place = place_items.get(place_name, {"Name": place_name, "Description": "Unknown Place"})
                if isinstance(place["Description"], dict):
                    description_text = place["Description"].get("text", "Unknown Place")
                else:
                    description_text = place["Description"]
                doc.add_paragraph(f"- {place['Name']}: {description_text}")

            # NPCs Section
            doc.add_heading("NPCs", level=3)
            for npc_name in scenario.get("NPCs", []):
                npc = npc_items.get(npc_name, {"Name": npc_name, "Role": "Unknown",
                                                "Description": {"text": "Unknown NPC", "formatting": {}}})
                p = doc.add_paragraph(f"- {npc['Name']} ({npc['Role']}, {npc.get('Faction', 'Unknown')}): ")
                description = npc['Description']
                if isinstance(description, dict):
                    run = p.add_run(description.get("text", ""))
                    self.apply_formatting(run, description.get("formatting", {}))
                else:
                    p.add_run(str(description))

            # Creatures Section
            doc.add_heading("Creatures", level=3)
            for creature_name in scenario.get("Creatures", []):
                creature = creature_items.get(creature_name, {
                    "Name": creature_name,
                    "Stats": {"text": "No Stats", "formatting": {}},
                    "Powers": {"text": "No Powers", "formatting": {}},
                    "Description": {"text": "Unknown Creature", "formatting": {}}
                })
                stats = creature["Stats"]
                if isinstance(stats, dict):
                    stats_text = stats.get("text", "No Stats")
                else:
                    stats_text = stats
                powers = creature.get("Powers", "Unknown")
                if isinstance(powers, dict):
                    powers_text = powers.get("text", "No Powers")
                else:
                    powers_text = powers
                p = doc.add_paragraph(f"- {creature['Name']} ({stats_text}, {powers_text}): ")
                description = creature["Description"]
                if isinstance(description, dict):
                    run = p.add_run(description.get("text", ""))
                    self.apply_formatting(run, description.get("formatting", {}))
                else:
                    p.add_run(str(description))
        doc.save(file_path)
        messagebox.showinfo("Export Successful", f"Scenario exported successfully to:\n{file_path}")

    def apply_formatting(self, run, formatting):
        if formatting.get('bold'):
            run.bold = True
        if formatting.get('italic'):
            run.italic = True
        if formatting.get('underline'):
            run.underline = True

    def normalize_name(self, name):
        return name.lower().replace('_', ' ').strip()

    def build_portrait_mapping(self):
        mapping = {}
        dir_txt_path = os.path.join("assets", "portraits", "dir.txt")
        if not os.path.exists(dir_txt_path):
            print(f"dir.txt not found at {dir_txt_path}")
            return mapping
        with open(dir_txt_path, "r", encoding="cp1252") as f:
            for line in f:
                line = line.strip()
                if not line.lower().endswith(".png"):
                    continue
                tokens = line.split()
                file_name = tokens[-1]
                if file_name.lower() == "dir.txt":
                    continue
                base_name = os.path.splitext(file_name)[0]
                parts = base_name.split("_")
                filtered_parts = []
                for part in parts:
                    if part.lower() == "portrait" or part.isdigit():
                        continue
                    filtered_parts.append(part)
                if filtered_parts:
                    candidate = " ".join(filtered_parts)
                    normalized_candidate = self.normalize_name(candidate)
                    mapping[normalized_candidate] = file_name
        return mapping

    def associate_npc_portraits(self):
        portrait_mapping = self.build_portrait_mapping()
        if not portrait_mapping:
            print("No portrait mapping was built.")
            return
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
            cursor.execute(f"PRAGMA table_info({table})")
            existing_columns = {row["name"] for row in cursor.fetchall()}
            for col, col_def in required_columns.items():
                if col not in existing_columns:
                    alter_query = f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"
                    cursor.execute(alter_query)
                    print(f"Added column '{col}' to table '{table}'.")
        npcs_columns = {
            "Name": "TEXT",
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
            "Creatures": "TEXT",
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
            "NPCs": "TEXT",
            "Secrets": "TEXT",
            "PlayerDisplay": "BOOLEAN",
            "Portrait": "TEXT"
        }
        objects_columns = {
            "Name": "TEXT",
            "Description": "TEXT",
            "Secrets": "TEXT",
            "Portrait": "TEXT"
        }
        creatures_columns = {
            "Name": "TEXT",
            "Type": "TEXT",
            "Description": "TEXT",
            "Weakness": "TEXT",
            "Powers": "TEXT",
            "Stats": "TEXT",
            "Background": "TEXT",
            "Genre": "TEXT",
            "Portrait": "TEXT"
        }
        alter_table_if_missing("npcs", npcs_columns)
        alter_table_if_missing("scenarios", scenarios_columns)
        alter_table_if_missing("factions", factions_columns)
        alter_table_if_missing("places", places_columns)
        alter_table_if_missing("objects", objects_columns)
        alter_table_if_missing("creatures", creatures_columns)

    def launch_swarmui(self):
        global SWARMUI_PROCESS
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


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()