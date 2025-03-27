import os
import customtkinter as ctk
from PIL import Image
from customtkinter import CTkLabel, CTkImage, CTkTextbox
from modules.helpers.text_helpers import format_longtext
from modules.helpers.template_loader import load_template
from modules.generic.generic_model_wrapper import GenericModelWrapper
from tkinter import Toplevel, messagebox

# Configure portrait size.
PORTRAIT_SIZE = (200, 200)
wrappers = {
            "Scenarios": GenericModelWrapper("scenarios"),
            "Places": GenericModelWrapper("places"),
            "NPCs": GenericModelWrapper("npcs"),
            "Factions": GenericModelWrapper("factions")
        }

def insert_text(parent, header, content):
    ctk.CTkLabel(parent, text=f"{header}:", font=("Arial", 14, "bold")).pack(anchor="w", padx=10)
    box = CTkTextbox(parent, wrap="word", height=80)
    box.insert("1.0", content)
    box.configure(state="disabled")
    box.pack(fill="x", padx=10, pady=5)

def insert_longtext(parent, header, content):
    ctk.CTkLabel(parent, text=f"{header}:", font=("Arial", 14, "bold")).pack(anchor="w", padx=10)
    formatted_text = format_longtext(content, max_length=2000)
    box = CTkTextbox(parent, wrap="word", height=120)
    box.insert("1.0", formatted_text)
    box.configure(state="disabled")
    box.pack(fill="x", padx=10, pady=5)

def insert_links(parent, header, items, linked_type, master):
    ctk.CTkLabel(parent, text=f"{header}:", font=("Arial", 14, "bold")).pack(anchor="w", padx=10)
    for item in items:
        label = CTkLabel(parent, text=item, text_color="blue", cursor="hand2")
        label.pack(anchor="w", padx=10)
        # Capture the current 'item' by assigning it to a default parameter (i)
        label.bind("<Button-1>", lambda event, l=linked_type, i=item, m=master: open_entity_tab(l, i, m))

def open_entity_tab(entity_type , name, master):
    wrapper = wrappers[entity_type]
    items = wrapper.load_items()
    key = "Title" if entity_type == "Scenarios" else "Name"
    item = next((i for i in items if i.get(key) == name), None)
    if not item:
        messagebox.showerror("Error", f"{entity_type[:-1]} '{name}' not found.")
        return
    
    # Then add the frame to a new separate window.
    new_window = ctk.CTkToplevel()
    new_window.title(f"{entity_type[:-1]}: {name}")
    new_window.geometry("1000x600")
    new_window.minsize(1000, 600)
    new_window.configure(padx=10, pady=10)

    # Create a scrollable container inside the new window.
    scrollable_container = ctk.CTkScrollableFrame(new_window)
    scrollable_container.pack(fill="both", expand=True)

    # Create the detail frame and pack it into the scrollable container.
    frame = create_entity_detail_frame(entity_type, item, master=scrollable_container)
    frame.pack(fill="both", expand=True)

    new_window.mainloop()

    
   
def create_entity_detail_frame(entity_type, entity, master): 
    """
    Create and return a CTkFrame displaying the details of an entity.
    This function uses a template (loaded dynamically based on entity_type)
    to determine which fields to display. It shows a portrait (if available),
    text fields, longtext fields, and clickable lists (via insert_links) that
    use open_entity_callback to open a detailed view for linked entities.
    
    Parameters:
      - entity_type: e.g., "NPCs" or "Places"
      - entity: a dictionary containing the entity's data.
      - master: the parent widget for the returned frame.
      - open_entity_callback: an optional callback that takes (entity_type, entity_name)
         and opens the detailed view for that entity.
    """
    # Load the template based on entity_type. Adjust the path if needed.
    template = load_template(entity_type.lower() )
    

    frame = ctk.CTkFrame(master)
    frame.portrait_images = {}  # local cache to keep image references

    if entity_type == "NPCs" and "Portrait" in entity and os.path.exists(entity["Portrait"]):
        try:
            img = Image.open(entity["Portrait"])
            img = img.resize(PORTRAIT_SIZE, Image.Resampling.LANCZOS)
            ctk_image = CTkImage(light_image=img, size=PORTRAIT_SIZE)
            portrait_label = CTkLabel(frame, image=ctk_image, text="")
            portrait_label.image = ctk_image  # persist reference
            portrait_label.entity_name = entity.get("Name", "")
            portrait_label.is_portrait = True
            frame.portrait_images[entity.get("Name", "")] = ctk_image
            portrait_label.pack(pady=10)
            frame.portrait_label = portrait_label
        except Exception as e:
            print(f"[DEBUG] Error loading portrait for {entity.get('Name','')}: {e}")

    # Iterate over template fields and add each field to the frame.
    for field in template["fields"]:
        field_name = field["name"]
        field_type = field["type"]
        # Skip the Portrait field if already handled.
        if entity_type == "NPCs" and field_name == "Portrait":
            continue
        if field_type == "longtext":
            insert_longtext(frame, field_name, entity.get(field_name, ""))
        elif field_type == "text":
            insert_text(frame, field_name, entity.get(field_name, ""))
        elif field_type == "list":
            linked_type = field.get("linked_type", None)
            if linked_type:
                print(f"[DEBUG] name={field_name} entity= {entity.get(field_name)}")
                insert_links(frame, field_name, entity.get(field_name, []), linked_type, master)
            
    return frame
