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
            "Factions": GenericModelWrapper("factions"),
            "Objects": GenericModelWrapper("objects"),
            "Creatures": GenericModelWrapper("creatures")
        }

def insert_text(parent, header, content):
    label = ctk.CTkLabel(parent, text=f"{header}:", font=("Arial", 14, "bold"))
    label.pack(anchor="w", padx=10)
    box = ctk.CTkTextbox(parent, wrap="word", height=80)
    # Ensure content is a plain string.
    if isinstance(content, dict):
        content = content.get("text", "")
    elif isinstance(content, list):
        content = " ".join(map(str, content))
    else:
        content = str(content)
    # For debugging, you can verify:
    # print("DEBUG: content =", repr(content))

    # Override the insert method to bypass the CTkTextbox wrapper.
    box.insert = box._textbox.insert
    # Now use box.insert normally.
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

def insert_links(parent, header, items, linked_type, open_entity_callback):
    ctk.CTkLabel(parent, text=f"{header}:", font=("Arial", 14, "bold")).pack(anchor="w", padx=10)
    for item in items:
        label = CTkLabel(parent, text=item, text_color="#00BFFF", cursor="hand2")
        label.pack(anchor="w", padx=10)
        if open_entity_callback is not None:
            # Capture the current values with lambda defaults.
            label.bind("<Button-1>", lambda event, l=linked_type, i=item: open_entity_callback(l, i))


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

    
   
def create_entity_detail_frame(entity_type, entity, master, open_entity_callback=None):
    # Create a scrollable container instead of a plain frame.
    scrollable_container = ctk.CTkScrollableFrame(master)
    scrollable_container.pack(fill="both", expand=True)

    # Create the actual content frame inside the scrollable container.
    content_frame = ctk.CTkFrame(scrollable_container)
    content_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # This local cache is used for portrait images (if any).
    content_frame.portrait_images = {}

    # If entity_type is "NPCs" and the entity has a valid Portrait, load and show it.
    if (entity_type == "NPCs" or entity_type == "Creatures") and "Portrait" in entity and os.path.exists(entity["Portrait"]):
        try:
            img = Image.open(entity["Portrait"])
            img = img.resize(PORTRAIT_SIZE, Image.Resampling.LANCZOS)
            ctk_image = CTkImage(light_image=img, size=PORTRAIT_SIZE)
            portrait_label = CTkLabel(content_frame, image=ctk_image, text="")
            portrait_label.image = ctk_image  # persist reference
            portrait_label.entity_name = entity.get("Name", "")
            portrait_label.is_portrait = True
            content_frame.portrait_images[entity.get("Name", "")] = ctk_image
            portrait_label.pack(pady=10)
            content_frame.portrait_label = portrait_label
        except Exception as e:
            print(f"[DEBUG] Error loading portrait for {entity.get('Name','')}: {e}")

    # Create fields from the template.
    template = load_template(entity_type.lower())
    for field in template["fields"]:
        field_name = field["name"]
        field_type = field["type"]
        # Skip the Portrait field if already handled.
        if (entity_type == "NPCs" or entity_type == "Creatures") and field_name == "Portrait":
            continue
        if field_type == "longtext":
            insert_longtext(content_frame, field_name, entity.get(field_name, ""))
        elif field_type == "text":
            insert_text(content_frame, field_name, entity.get(field_name, ""))
        elif field_type == "list":
            linked_type = field.get("linked_type", None)
            if linked_type:
                insert_links(content_frame, field_name, entity.get(field_name) or [], linked_type, open_entity_callback)
    # Return the scrollable container so that whoever creates the window or tab gets a frame with scrollbars.
    return scrollable_container

def open_entity_window(entity_type, name):
        # Look up the entity using the wrappers dictionary.
        wrapper = wrappers[entity_type]
        items = wrapper.load_items()
        key = "Title" if entity_type == "Scenarios" else "Name"
        entity = next((i for i in items if i.get(key) == name), None)
        if not entity:
            messagebox.showerror("Error", f"{entity_type[:-1]} '{name}' not found.")
            return

        # Create a new window.
        new_window = ctk.CTkToplevel()
        new_window.title(f"{entity_type[:-1]}: {name}")
        new_window.geometry("1000x600")
        new_window.minsize(1000, 600)
        new_window.configure(padx=10, pady=10)

        # Create a scrollable container inside the new window.
        scrollable_container = ctk.CTkScrollableFrame(new_window)
        scrollable_container.pack(fill="both", expand=True)

        # Build the detail frame and pack it into the container.
        detail_frame = create_entity_detail_frame(
            entity_type, entity, master=scrollable_container,
            open_entity_callback=open_entity_window  # Pass this same callback if you want links inside to work similarly.
        )
        detail_frame.pack(fill="both", expand=True)
