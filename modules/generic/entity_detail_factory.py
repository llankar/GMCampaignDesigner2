import os
import customtkinter as ctk
from PIL import Image
from customtkinter import CTkLabel, CTkImage, CTkTextbox
from modules.helpers.text_helpers import format_longtext
from modules.helpers.template_loader import load_template
from modules.generic.generic_model_wrapper import GenericModelWrapper
from tkinter import Toplevel, messagebox
from tkinter import ttk

# Configure portrait size.
PORTRAIT_SIZE = (200, 200)
_open_entity_windows = {}
wrappers = {
            "Scenarios": GenericModelWrapper("scenarios"),
            "Places": GenericModelWrapper("places"),
            "NPCs": GenericModelWrapper("npcs"),
            "Factions": GenericModelWrapper("factions"),
            "Objects": GenericModelWrapper("objects"),
            "Creatures": GenericModelWrapper("creatures"),
            "PCs": GenericModelWrapper("pcs"),
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


def open_entity_tab(entity_type, name, master):
    """
    Opens (or focuses) a detail window for the given entity_type/name.
    Debug prints added to trace why/when new windows are created.
    """
    print(f"[DEBUG] open_entity_tab called with entity_type={entity_type!r}, name={name!r}")

    # 1) Build a unique key and look for an existing window
    window_key = f"{entity_type}:{name}"
    print(f"[DEBUG] computed window_key={window_key!r}")
    existing = _open_entity_windows.get(window_key)
    print(f"[DEBUG] lookup existing window: {existing!r}")
    if existing:
        alive = existing.winfo_exists()
        print(f"[DEBUG] existing.winfo_exists() = {alive}")
        if alive:
            print(f"[DEBUG] -> focusing existing window for {window_key}")
            existing.deiconify()
            existing.lift()
            return
        else:
            print(f"[DEBUG] -> found dead window object, removing from registry")
            _open_entity_windows.pop(window_key, None)

    # 2) Load the data item
    print(f"[DEBUG] loading items for type={entity_type}")
    wrapper = wrappers.get(entity_type)
    if not wrapper:
        print(f"[DEBUG] ERROR: unknown wrapper for {entity_type}")
        messagebox.showerror("Error", f"Unknown type '{entity_type}'")
        return

    items = wrapper.load_items()
    print(f"[DEBUG] loaded {len(items)} items")
    key_field = "Title" if entity_type == "Scenarios" else "Name"
    item = next((i for i in items if i.get(key_field) == name), None)
    print(f"[DEBUG] lookup item by key_field={key_field!r}: found={item is not None}")
    if not item:
        print(f"[DEBUG] ERROR: item not found")
        messagebox.showerror("Error", f"{entity_type[:-1]} '{name}' not found.")
        return

    # 3) Create a new Toplevel window
    print(f"[DEBUG] creating new CTkToplevel for {window_key}")
    new_window = ctk.CTkToplevel()
    new_window.title(f"{entity_type[:-1]}: {name}")
    new_window.geometry("1000x600")
    new_window.minsize(1000, 600)
    new_window.configure(padx=10, pady=10)

    # 4) Build the scrollable detail frame inside it
    print(f"[DEBUG] building scrollable detail frame")
    scrollable_container = ctk.CTkScrollableFrame(new_window)
    scrollable_container.pack(fill="both", expand=True)
    frame = create_entity_detail_frame(
        entity_type,
        item,
        master=scrollable_container,
        open_entity_callback=open_entity_tab
    )
    frame.pack(fill="both", expand=True)

    # 5) Register it and hook the close event
    print(f"[DEBUG] registering new window in _open_entity_windows[{window_key!r}]")
    _open_entity_windows[window_key] = new_window

    def _on_close():
        print(f"[DEBUG] window {window_key!r} closing, removing from registry")
        _open_entity_windows.pop(window_key, None)
        new_window.destroy()

    new_window.protocol("WM_DELETE_WINDOW", _on_close)
    print(f"[DEBUG] open_entity_tab completed for {window_key}")

def unwrap_value(val):
    """
    If val is a dict with a 'text' key, return that.
    Otherwise, return str(val) (or '' if None).
    """
    if isinstance(val, dict):
        return val.get("text", "")
    if val is None:
        return ""
    return str(val)

def insert_npc_table(parent, header, npc_names, open_entity_callback):
    """
    Displays NPCs in rows, with columns:
    Name | Secret | Background | Factions | Traits
    The Name column is styled like links (blue) and is clickable.
    """
    CTkLabel(parent, text=f"{header}:", font=("Arial", 14, "bold"))\
        .pack(anchor="w", padx=10, pady=(10, 2))

    table = ctk.CTkFrame(parent)
    table.pack(fill="both", expand=True, padx=10, pady=(0,10))

    cols         = ["Name", "Secret", "Background", "Factions", "Traits"]
    weights      = [1, 2, 2, 1, 4]
    wrap_lengths = [120, 250, 250, 150, 500]
    text_heights = {1: 50, 2: 50, 4: 75}

    for idx, w in enumerate(weights):
        table.grid_columnconfigure(idx, weight=w)

    # Header row
    for c, col_name in enumerate(cols):
        CTkLabel(table, text=col_name, font=("Arial", 12, "bold"))\
            .grid(row=0, column=c, padx=5, pady=5, sticky="nsew")

    # Load NPC data
    npc_wrapper = GenericModelWrapper("npcs")
    all_npcs    = npc_wrapper.load_items()
    npc_map     = {npc.get("Name"): npc for npc in all_npcs}

    for r, npc_name in enumerate(npc_names, start=1):
        data = npc_map.get(npc_name, {}) or {}

        # Prepare values
        secret_text     = format_longtext(unwrap_value(data.get("Secret")),     max_length=2000)
        background_text = format_longtext(unwrap_value(data.get("Background")), max_length=2000)
        factions_list   = data.get("Factions") or []
        traits_text     = format_longtext(unwrap_value(data.get("Traits")), max_length=2000)

        def unwrap_list(lst):
            out = []
            for item in lst:
                if isinstance(item, dict):
                    out.append(item.get("text", ""))
                else:
                    out.append(str(item))
            return out

        factions_text = ", ".join(unwrap_list(factions_list))
        

        values = [
            data.get("Name", ""),
            secret_text,
            background_text,
            factions_text,
            traits_text
        ]

        for c, txt in enumerate(values):
            if c in text_heights:
                # long‑text columns as a disabled textbox
                widget = CTkTextbox(table, wrap="word", height=text_heights[c])
                widget.insert = widget._textbox.insert
                widget.insert("1.0", txt)
                widget.configure(state="disabled")
            else:
                # Name column styled like link
                if c == 0:
                    widget = CTkLabel(
                        table,
                        text=txt,
                        text_color="#00BFFF",
                        font=("Arial", 12, "underline"),
                        cursor="hand2"
                    )
                    if open_entity_callback:
                        widget.bind(
                            "<Button-1>",
                            lambda e, nm=npc_name: open_entity_callback("NPCs", nm)
                        )
                else:
                    widget = CTkLabel(
                        table,
                        text=txt,
                        font=("Arial", 12),
                        wraplength=wrap_lengths[c],
                        justify="left"
                    )

            widget.grid(row=r, column=c, padx=5, pady=5, sticky="nsew")

def create_scenario_detail_frame(entity_type,scenario_item,master,open_entity_callback=None):
    """
    Build a scrollable detail view for a scenario with:
    1) A header zone (raw Title + Summary, no labels)
    2) The rest of the fields rendered via your insert_* helpers,
        with lists going through insert_links so callbacks fire.
    """
    # — Outer scrollable container —
    frame = ctk.CTkFrame(master)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    # ——— HEADER ———
    CTkLabel(
        frame,
        text=scenario_item.get("Title", ""),
        font=("Arial", 28, "bold")
    ).pack(anchor="w", pady=(0, 5))

    CTkLabel(
        frame,
        text=format_longtext(scenario_item.get("Summary", "")),
        font=("Arial", 14),
        wraplength=1620,
        justify="left"
    ).pack(fill="x", pady=(0, 15))

    ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)
    CTkLabel(
        frame,
        text="Secrets",
        font=("Arial", 18)
    ).pack(anchor="w", pady=(0, 5))
    CTkLabel(
        frame,
        text=format_longtext(scenario_item.get("Secrets", "")),
        font=("Arial", 14),
        wraplength=1620,
        justify="left"
    ).pack(fill="x", pady=(0, 15))
    ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)
    # ——— BODY: render all other fields via your helpers ———
    tpl = load_template(entity_type.lower())
    for field in tpl["fields"]:
        name = field["name"]
        if name in ("Title", "Summary", "Secrets"):
            continue
        ftype = field["type"]
        value = scenario_item.get(name, "")
        if ftype == "text":
            insert_text(frame, name, value)
        elif ftype == "longtext":
            insert_longtext(frame, name, value)
        elif ftype == "list":
            linked = field.get("linked_type")
            items  = scenario_item.get(name) or []
            if linked == "NPCs":
                items = scenario_item.get("NPCs", [])
                insert_npc_table(frame, "NPCs", items, open_entity_callback)
            else:
                insert_links(frame, name, items, linked, open_entity_callback)

        # separator after each section
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)

    return frame

def create_entity_detail_frame(entity_type, entity, master, open_entity_callback=None):
    """
    Routes Scenarios through our custom header/body and
    everything else through the generic detail path.
    """
    if entity_type == "Scenarios":
        return create_scenario_detail_frame(
            entity_type,
            entity,
            master,
            open_entity_callback
        )

    # Create a scrollable container instead of a plain frame.
    
    # Create the actual content frame inside the scrollable container.
    content_frame = ctk.CTkFrame(master)
    content_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # This local cache is used for portrait images (if any).
    content_frame.portrait_images = {}

    # If entity_type is "NPCs" and the entity has a valid Portrait, load and show it.
    portrait_path = entity.get("Portrait")
    if (entity_type in {"NPCs", "PCs", "Creatures"}) and portrait_path and os.path.exists(portrait_path):
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
        if (entity_type == "NPCs" or entity_type == "PCs" or entity_type == "Creatures") and field_name == "Portrait":
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
    return content_frame

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
