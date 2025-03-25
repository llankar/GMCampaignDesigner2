import customtkinter as ctk
import json
import os
import requests 
import subprocess
import time
import shutil
from modules.helpers import rich_text_editor, text_helpers
from modules.helpers.rich_text_editor import RichTextEditor
from modules.helpers.window_helper import position_window_at_top
from PIL import Image, ImageTk
from tkinter import filedialog,  messagebox


FACTIONS_FILE = "data/factions.json"
NPCS_FILE = "data/npcs.json"
PLACES_FILE = "data/places.json"
SWARMUI_PROCESS = None


def load_factions_list():
    if os.path.exists(FACTIONS_FILE):
        with open(FACTIONS_FILE, "r", encoding="utf-8") as f:
            return [faction["Name"] for faction in json.load(f)]
    return []

def load_npcs_list():
    if os.path.exists(NPCS_FILE):
        with open(NPCS_FILE, "r", encoding="utf-8") as f:
            return [npc["Name"] for npc in json.load(f)]
    return []

def load_places_list():
    if os.path.exists(PLACES_FILE):
        with open(PLACES_FILE, "r", encoding="utf-8") as f:
            return [place["Name"] for place in json.load(f)]
    return []

class GenericEditorWindow(ctk.CTkToplevel):
    def __init__(self, master, item, template, creation_mode=False):
        super().__init__(master)

        self.item = item
        self.template = template
        self.saved = False
        self.field_widgets = {}

        self.transient(master)
        self.lift()
        self.grab_set()
        self.focus_force()

        self.title("Create Item" if creation_mode else "Edit Item")

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True)

        self.scroll_frame = ctk.CTkScrollableFrame(self.main_frame)
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        for field in template["fields"]:
            ctk.CTkLabel(self.scroll_frame, text=field["name"]).pack(pady=(5, 0), anchor="w")

            if field["type"] == "longtext":
                self.create_longtext_field(field)
            elif field["name"] in ["NPCs", "Places", "Faction"]:
                self.create_dynamic_combobox_list(field)
            elif field["name"] == "Portrait":
                self.create_portrait_field(field)
            else:
                self.create_text_entry(field)

        self.create_action_bar()

        # Instead of a fixed geometry, update layout and compute the required size.
        self.update_idletasks()
        req_width = self.winfo_reqwidth()
        req_height = self.winfo_reqheight()
        # Enforce a minimum size if needed.
        min_width, min_height = 1000, 880
        if req_width < min_width:
            req_width = min_width
        if req_height < min_height:
            req_height = min_height
        self.geometry(f"{req_width}x{req_height}")
        self.minsize(req_width, req_height)

        # Optionally, adjust window position.
        position_window_at_top(self)



    # === Création des champs ===

    def create_longtext_field(self, field):
        value = self.item.get(field["name"], "")

        editor = RichTextEditor(self.scroll_frame)

        if isinstance(value, dict):
            editor.load_text_data(value)
        else:
            editor.text_widget.insert("1.0", value)

        editor.pack(fill="both", expand=True, pady=5)
        self.field_widgets[field["name"]] = editor

    def on_combo_mousewheel(self, event, combobox):
        # Get the current selection and available options.
        options = combobox.cget("values")
        if not options:
            return
        current_val = combobox.get()
        try:
            idx = options.index(current_val)
        except ValueError:
            idx = 0

        # Determine scroll direction.
        if event.num == 4 or event.delta > 0:
            # Scroll up: go to previous option.
            new_idx = max(0, idx - 1)
        elif event.num == 5 or event.delta < 0:
            # Scroll down: go to next option.
            new_idx = min(len(options) - 1, idx + 1)
        else:
            new_idx = idx

        combobox.set(options[new_idx])
    
    def create_dynamic_combobox_list(self, field):
        container = ctk.CTkFrame(self.scroll_frame)
        container.pack(fill="x", pady=5)

        combobox_list = []

        if field["name"] == "NPCs":
            options_list = load_npcs_list()
        elif field["name"] == "Places":
            options_list = load_places_list()
        elif field["name"] == "Faction":
            options_list = load_factions_list()
        else:
            options_list = []

        initial_values = self.item.get(field["name"], [])

        def add_combobox(initial_value=None):
            row = ctk.CTkFrame(container)
            row.pack(fill="x", pady=2)
            
            var = ctk.StringVar()
            # Create a read-only entry to display the selected value:
            entry = ctk.CTkEntry(row, textvariable=var, state="readonly")
            entry.pack(side="left", expand=True, fill="x")
            
            # Set initial value:
            if initial_value and initial_value in options_list:
                var.set(initial_value)
            else:
                var.set(options_list[0] if options_list else "")

            # Button to open dropdown:
            btn = ctk.CTkButton(row, text="▼", width=30, command=lambda: open_dropdown(entry, var))
            btn.pack(side="left", padx=5)
            
            combobox_list.append(entry)

        def remove_this(row, widget):
            row.destroy()
            combobox_list.remove(widget)

        def open_dropdown(widget, var):
            # Position dropdown just below the widget
            x = widget.winfo_rootx()
            y = widget.winfo_rooty() + widget.winfo_height()
            dropdown = self.CustomDropdown(self, options=options_list, command=lambda val: var.set(val))
            dropdown.geometry(f"+{x}+{y}")
            dropdown.focus_set()

        for value in initial_values:
            add_combobox(value)

        add_button = ctk.CTkButton(self.scroll_frame, text=f"Add {field['name'][6:]}", command=add_combobox)
        add_button.pack(anchor="w", pady=2)

        self.field_widgets[field["name"]] = combobox_list



    def create_text_entry(self, field):
        entry = ctk.CTkEntry(self.scroll_frame)
        entry.insert(0, self.item.get(field["name"], ""))
        entry.pack(fill="x", pady=5)
        self.field_widgets[field["name"]] = entry

    def create_action_bar(self):
        action_bar = ctk.CTkFrame(self.main_frame)
        action_bar.pack(fill="x", pady=5)

        ctk.CTkButton(action_bar, text="Cancel", command=self.destroy).pack(side="right", padx=5)
        ctk.CTkButton(action_bar, text="Save", command=self.save).pack(side="right", padx=5)

    # === Sauvegarde ===

    def save(self):
        for field in self.template["fields"]:
            widget = self.field_widgets[field["name"]]

            if field["type"] == "longtext":
                self.item[field["name"]] = widget.get_text_data()

            elif field["name"] in ["Places", "NPCs", "Faction"]:
                self.item[field["name"]] = [cb.get() for cb in widget if cb.get()]
            elif field["name"] == "Portrait":
                self.item[field["name"]] = self.portrait_path  # Use the stored path
            else:
                self.item[field["name"]] = widget.get()
        self.saved = True
        self.destroy()
    def create_portrait_field(self, field):
        frame = ctk.CTkFrame(self.scroll_frame)
        frame.pack(fill="x", pady=5)

        self.portrait_path = self.item.get("Portrait", "")

        if self.portrait_path and os.path.exists(self.portrait_path):
            image = Image.open(self.portrait_path).resize((64, 64))
            self.portrait_image = ctk.CTkImage(light_image=image, size=(64, 64))
            self.portrait_label = ctk.CTkLabel(frame, image=self.portrait_image, text="")
        else:
            self.portrait_label = ctk.CTkLabel(frame, text="[No Image]")
        self.portrait_label.pack(side="left", padx=5)

        ctk.CTkButton(frame, text="Select Portrait", command=self.select_portrait).pack(side="left", padx=5)
        ctk.CTkButton(frame, text="Create Portrait with description", command=self.create_portrait_with_swarmui).pack(side="left", padx=5)

        self.field_widgets[field["name"]] = self.portrait_path
    
    def launch_swarmui(self):
        global SWARMUI_PROCESS
        SWARMUI_CMD = "launch-windows.bat"
        # Create a copy of the current environment and modify it as needed
        env = os.environ.copy()
        # Optionally remove the virtual environment variables if not needed:
        env.pop('VIRTUAL_ENV', None)
        # Adjust PATH if necessary to point to the system Python
        #env["PATH"] = "C:\\Path\\to\\system\\python;" + env["PATH"]
        
        if SWARMUI_PROCESS is None or SWARMUI_PROCESS.poll() is not None:
            try:
                SWARMUI_PROCESS = subprocess.Popen(
                    SWARMUI_CMD,
                    shell=True,
                    cwd=r"E:\SwarmUI\SwarmUI",
                    env=env
                )
                # Optionally, wait a little bit here for the process to initialize.
                time.sleep(120.0)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to launch SwarmUI: {e}")
    def cleanup_swarmui(self):
        """
        Terminate the SwarmUI process if it is running.
        """
        global SWARMUI_PROCESS
        if SWARMUI_PROCESS is not None and SWARMUI_PROCESS.poll() is None:
            SWARMUI_PROCESS.terminate()
    
    def create_portrait_with_swarmui(self):
        SWARM_API_URL = "http://127.0.0.1:7801"  # Change if needed
        self.launch_swarmui()
        """
        Generates a portrait image using the SwarmUI API and associates the resulting
        image with the current NPC by updating its 'Portrait' field.
        """
        try:
            # Step 1: Obtain a new session from SwarmUI
            session_url = f"{SWARM_API_URL}/API/GetNewSession"
            session_response = requests.post(session_url, json={}, headers={"Content-Type": "application/json"})
            session_data = session_response.json()
            session_id = session_data.get("session_id")
            if not session_id:
                messagebox.showerror("Error", "Failed to obtain session ID from Swarm API.")
                return

            # Build a prompt based on the current NPC's data (you can enhance this as needed)
            npc_name = self.item.get("Name", "Unknown")
            npc_role = self.item.get("Role", "Unknown")
            npc_faction = self.item.get("Faction", "Unknown")
            npc_desc = self.item.get("Description", "Unknown") 
            npc_desc =  text_helpers.format_longtext(npc_desc)
            npc_desc = f"{npc_desc} {npc_role} {npc_faction}"
            prompt = f"{npc_desc}"

            # Step 2: Define image generation parameters
            prompt_data = {
                "session_id": session_id,
                "images": 1,  # Only one portrait needed
                "prompt": prompt,
                "negativeprompt": "blurry, low quality, comics style, mangastyle, paint style, watermark, ugly, monstrous, too many fingers, too many legs, too many arms, bad hands, unrealistic weapons, bad grip on equipment, nude",
                "model": "cinenautsXLATRUE_cinenautsV30",
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
                messagebox.showerror("Error", "Image generation failed. Check API response.")
                return

            # Step 3: Download the first generated image
            image_url = f"{SWARM_API_URL}/{images[0]}"
            downloaded_image = requests.get(image_url)
            if downloaded_image.status_code != 200:
                messagebox.showerror("Error", "Failed to download the generated image.")
                return

            # Step 4: Save the image locally and update the NPC's Portrait field
            output_filename = f"{npc_name.replace(' ', '_')}_portrait.png"
            with open(output_filename, "wb") as f:
                f.write(downloaded_image.content)

            # Associate the generated portrait with the NPC data.
            self.portrait_path = self.copy_and_resize_portrait(output_filename)
            self.portrait_label.configure(text=os.path.basename(self.portrait_path))
            #copy the outputfilename file to the assets/generated folder
            GENERATED_FOLDER = "assets/generated"
            os.makedirs(GENERATED_FOLDER, exist_ok=True)
            shutil.copy(output_filename, os.path.join(GENERATED_FOLDER, output_filename))

            # messagebox.showinfo("Success", f"Portrait saved as {output_filename} and associated with the NPC.")

            # Optional: Update the portrait display in the UI.
            # For example, if you have a portrait label (self.portrait_label), reload the image:
            # from PIL import ImageTk, Image
            # img = Image.open(output_filename).resize((64, 64))
            # self.portrait_image = ctk.CTkImage(light_image=img, size=(64, 64))
            # self.portrait_label.configure(image=self.portrait_image, text="")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")



    def select_portrait(self):
        file_path = filedialog.askopenfilename(
            title="Select Portrait Image",
            filetypes=[
                ("Image Files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp"),
                ("PNG Files", "*.png"),
                ("JPEG Files", "*.jpg;*.jpeg"),
                ("GIF Files", "*.gif"),
                ("Bitmap Files", "*.bmp"),
                ("WebP Files", "*.webp"),
                ("All Files", "*.*")
            ]
        )

        if file_path:
            self.portrait_path = self.copy_and_resize_portrait(file_path)
            self.portrait_label.configure(text=os.path.basename(self.portrait_path))

    def copy_and_resize_portrait(self, src_path):
        PORTRAIT_FOLDER = "assets/portraits"
        MAX_PORTRAIT_SIZE = (1024, 1024)

        os.makedirs(PORTRAIT_FOLDER, exist_ok=True)

        npc_name = self.item.get("Name", "Unnamed").replace(" ", "_")
        ext = os.path.splitext(src_path)[-1].lower()
        dest_filename = f"{npc_name}_{id(self)}{ext}"
        dest_path = os.path.join(PORTRAIT_FOLDER, dest_filename)

        with Image.open(src_path) as img:
            img = img.convert("RGB")
            img.thumbnail(MAX_PORTRAIT_SIZE)
            img.save(dest_path)

        return dest_path
    class CustomDropdown(ctk.CTkToplevel):
        def __init__(self, master, options, command, **kwargs):
            super().__init__(master, **kwargs)
            self.command = command  # Callback when an option is selected.
            self.options = options
            self.overrideredirect(True)  # Remove window decorations
            self.scrollable = ctk.CTkScrollableFrame(self)
            self.scrollable.pack(fill="both", expand=True)
            for opt in options:
                btn = ctk.CTkButton(self.scrollable, text=opt, command=lambda o=opt: self.select(o))
                btn.pack(fill="x", padx=5, pady=2)
            # Bind mouse wheel events on the scrollable frame.
            self.scrollable.bind("<MouseWheel>", self.on_mousewheel)
            self.scrollable.bind("<Button-4>", self.on_mousewheel)  # Linux up
            self.scrollable.bind("<Button-5>", self.on_mousewheel)  # Linux down

        def on_mousewheel(self, event):
            if event.num == 4 or event.delta > 0:
                self.scrollable._parent_canvas.yview_scroll(-1, "units")
            elif event.num == 5 or event.delta < 0:
                self.scrollable._parent_canvas.yview_scroll(1, "units")

        def select(self, option):
            self.command(option)
            self.destroy()

