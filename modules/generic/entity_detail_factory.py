import os
import customtkinter as ctk
from PIL import Image
from customtkinter import CTkLabel, CTkImage, CTkTextbox
from modules.helpers.text_helpers import format_longtext
from modules.helpers.template_loader import load_template
from modules.generic.generic_model_wrapper import GenericModelWrapper
from tkinter import Toplevel, messagebox
from tkinter import ttk
from modules.ui.image_viewer import show_portrait

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
    box = ctk.CTkTextbox(parent, wrap="word", height=40)
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

    # Convert to string and format
    if isinstance(content, dict):
        text = content.get("text", "")
    else:
        text = str(content)
    formatted_text = format_longtext(text, max_length=2000)

    box = CTkTextbox(parent, wrap="word")
    box.insert = box._textbox.insert
    box.insert("1.0", formatted_text)
    box.configure(state="disabled")
    box.pack(fill="x", padx=10, pady=5)

    # Resize after layout
    def update_height():
        lines = int(box._textbox.count("1.0", "end", "displaylines")[0])
        clamped = max(2, min(lines, 20))
        box.configure(height=clamped)

    box.after(100, update_height)

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
    CTkLabel(parent, text=f"{header}:", font=("Arial", 14, "bold"))\
        .pack(anchor="w", padx=10, pady=(1, 2))

    table = ctk.CTkFrame(parent)
    table.pack(fill="both", expand=True, padx=10, pady=(0,0))

    cols         = ["Portrait", "Name", "Secret", "Background",  "Traits", "Factions"]
    weights      = [0,         1,       2,        2,            4,          1     ]
    wrap_lengths = [0,       120,     250,      250,          500,        100   ]
    text_heights = {2: 60, 3: 60, 4: 60}

    # configure columns
    for idx, w in enumerate(weights):
        table.grid_columnconfigure(idx, weight=w)

    # configure all rows to expand equally (after we place them)
    # we'll do that after row creation below

    # header row
    for c, col_name in enumerate(cols):
        CTkLabel(table, text=col_name, font=("Arial", 12, "bold"))\
            .grid(row=0, column=c, padx=5, pady=1, sticky="nsew")

    # load data
    wrapper = GenericModelWrapper("npcs")
    all_npcs = wrapper.load_items()
    npc_map   = {npc["Name"]: npc for npc in all_npcs}

    for r, name in enumerate(npc_names, start=1):
        data = npc_map.get(name, {}) or {}

        # portrait
        portrait_path = data.get("Portrait")
        if portrait_path and os.path.exists(portrait_path):
            img = Image.open(portrait_path).resize((40,40), Image.Resampling.LANCZOS)
            photo = CTkImage(light_image=img, size=(40,40))
            widget = CTkLabel(table, image=photo, text="", anchor="center")
            widget.image = photo
            # clicking the thumbnail pops up the full‑screen viewer
            widget.bind(
                "<Button-1>",
                lambda e, p=portrait_path, n=name: show_portrait(p, n)
            )
        else:
            widget = CTkLabel(table, text="", anchor="center")
        widget.grid(row=r, column=0, padx=5, pady=5, sticky="nsew")

        # other columns
        secret     = format_longtext(data.get("Secret",""))
        background = format_longtext(data.get("Background",""))
        factions   = ", ".join(data.get("Factions") or [])
        traits     = format_longtext(data.get("Traits"))

        values = [name, secret, background, traits, factions]
        for c, txt in enumerate(values, start=1):
            if c in text_heights:
                cell = CTkTextbox(table, wrap="word", height=text_heights[c])
                cell.insert = cell._textbox.insert
                cell.insert("1.0", txt)
                cell.configure(state="disabled")
            else:
                if c == 1:
                    cell = CTkLabel(
                        table,
                        text=txt,
                        text_color="#00BFFF",
                        font=("Arial", 12, "underline"),
                        cursor="hand2",
                        anchor="center",
                        justify="center"

                    )
                    if open_entity_callback:
                        cell.bind(
                            "<Button-1>",
                            lambda e, nm=name: open_entity_callback("NPCs", nm)
                        )
                else:
                    cell = CTkLabel(
                        table,
                        text=txt,
                        font=("Arial", 12),
                        wraplength=wrap_lengths[c],
                        justify="left",
                        anchor="w"
                    )
            cell.grid(row=r, column=c, padx=5, pady=5, sticky="nsew")

        # make this row expandable so portrait centers vertically
        table.grid_rowconfigure(r, weight=1)

def insert_creature_table(parent, header, creature_names, open_entity_callback):
    CTkLabel(parent, text=f"{header}:", font=("Arial", 14, "bold")) \
        .pack(anchor="w", padx=10, pady=(1, 2))

    table = ctk.CTkFrame(parent)
    table.pack(fill="both", expand=True, padx=10, pady=(0,0))

    cols         = ["Portrait", "Name", "Weakness", "Powers", "Stats"]
    weights      = [0,         1,       3,          3,        2     ]
    wrap_lengths = [0,       150,     400,        400,      300   ]
    text_heights = {2: 60, 3: 60,    4: 60}

    for idx, w in enumerate(weights):
        table.grid_columnconfigure(idx, weight=w)

    for c, col in enumerate(cols):
        CTkLabel(table, text=col, font=("Arial", 12, "bold")) \
            .grid(row=0, column=c, padx=5, pady=1, sticky="nsew")

    wrapper       = GenericModelWrapper("creatures")
    all_creatures = wrapper.load_items()
    creature_map  = {cr["Name"]: cr for cr in all_creatures}

    for r, name in enumerate(creature_names, start=1):
        data = creature_map.get(name, {}) or {}

        # portrait
        portrait_path = data.get("Portrait")
        if portrait_path and os.path.exists(portrait_path):
            img = Image.open(portrait_path).resize((40,40), Image.Resampling.LANCZOS)
            photo = CTkImage(light_image=img, size=(40,40))
            widget = CTkLabel(table, image=photo, text="", anchor="center")
            widget.image = photo
            widget.bind(
                "<Button-1>",
                lambda e, p=portrait_path, n=name: show_portrait(p, n)
            )
        else:
            widget = CTkLabel(table, text="", anchor="center")
        widget.grid(row=r, column=0, padx=5, pady=5, sticky="nsew")

        # other columns
        weakness = format_longtext(data.get("Weakness",""), max_length=2000)
        powers   = format_longtext(data.get("Powers",""),   max_length=2000)
        stats    = format_longtext(data.get("Stats",""),    max_length=2000)

        values = [name, weakness, powers, stats]
        for c, txt in enumerate(values, start=1):
            if c in text_heights:
                cell = CTkTextbox(table, wrap="word", height=text_heights[c])
                cell.insert = cell._textbox.insert
                cell.insert("1.0", txt)
                cell.configure(state="disabled")
            else:
                if c == 1:
                    cell = CTkLabel(
                        table,
                        text=txt,
                        text_color="#00BFFF",
                        font=("Arial", 12, "underline"),
                        cursor="hand2",
                        anchor="center",
                        justify="center"
                    )
                    if open_entity_callback:
                        cell.bind(
                            "<Button-1>",
                            lambda e, nm=name: open_entity_callback("Creatures", nm)
                        )
                else:
                    cell = CTkLabel(
                        table,
                        text=txt,
                        font=("Arial", 12),
                        wraplength=wrap_lengths[c],
                        justify="left",
                        anchor="w"
                    )
            cell.grid(row=r, column=c, padx=5, pady=5, sticky="nsew")

        table.grid_rowconfigure(r, weight=1)

def insert_places_table(parent, header, place_names, open_entity_callback):
    """
    Render a table of Places (excluding PlayerDisplay) with columns:
    Portrait, Name, Description, NPCs, Secrets
    """
    # Section header
    CTkLabel(parent, text=f"{header}:", font=("Arial", 14, "bold")) \
        .pack(anchor="w", padx=10, pady=(1, 2))

    # Table container
    table = ctk.CTkFrame(parent)
    table.pack(fill="both", expand=True, padx=10, pady=(0, 0))

    # Column defs
    cols         = ["Portrait", "Name", "Description", "NPCs", "Secrets"]
    weights      = [0,          1,      2,             1,      1    ]
    wrap_lengths = [0,        150,    400,           200,    200  ]
    # only Description (2) and Secrets (4) get scrollboxes
    text_heights = {2: 60,  4: 60}

    # configure columns
    for idx, w in enumerate(weights):
        table.grid_columnconfigure(idx, weight=w)

    # header row
    for c, col_name in enumerate(cols):
        CTkLabel(table, text=col_name, font=("Arial", 12, "bold")) \
            .grid(row=0, column=c, padx=5, pady=1, sticky="nsew")

    # load place data once
    place_map = {
        pl["Name"]: pl
        for pl in GenericModelWrapper("places").load_items()
    }

    # populate rows
    for r, name in enumerate(place_names, start=1):
        data     = place_map.get(name, {}) or {}
        portrait = data.get("Portrait", "")
        desc     = format_longtext(data.get("Description", ""))
        secrets  = format_longtext(data.get("Secrets", ""))
        npcs     = data.get("NPCs") or []
        values   = [portrait, name, desc, npcs, secrets]

        for c, val in enumerate(values):
            # scrollable for Description & Secrets
            if c in text_heights:
                cell = CTkTextbox(table, wrap="word", height=text_heights[c])
                cell.insert = cell._textbox.insert
                cell.insert("1.0", val)
                cell.configure(state="disabled")

            # Portrait thumbnail
            elif c == 0:
                if portrait and os.path.exists(portrait):
                    img   = Image.open(portrait).resize((40, 40), Image.Resampling.LANCZOS)
                    photo = CTkImage(light_image=img, size=(40, 40))
                    cell  = CTkLabel(table, image=photo, text="", anchor="center")
                    cell.image = photo
                    cell.bind(
                        "<Button-1>",
                        lambda e, p=portrait, n=name: show_portrait(p, n)
                    )
                else:
                    cell = CTkLabel(table, text="–", font=("Arial", 12), anchor="center")

            # clickable Name
            elif c == 1:
                cell = CTkLabel(
                    table, text=val,
                    text_color="#00BFFF", font=("Arial", 12, "underline"),
                    cursor="hand2", anchor="center",
                    height=60
                )
                if open_entity_callback:
                    cell.bind(
                        "<Button-1>",
                        lambda e, nm=val: open_entity_callback("Places", nm)
                    )

            # NPCs list as individual links
            elif c == 3:
                cell = ctk.CTkFrame(table, height=60)
                for i, npc_name in enumerate(val):
                    link = CTkLabel(
                        cell, text=npc_name,
                        text_color="#00BFFF", font=("Arial", 12, "underline"),
                        cursor="hand2",
                        height=60
                    )
                    if open_entity_callback:
                        link.bind(
                            "<Button-1>",
                            lambda e, nm=npc_name: open_entity_callback("NPCs", nm)
                        )
                    link.grid(row=0, column=i, padx=(0, 5))

            # default simple label
            else:
                cell = CTkLabel(
                    table, text=val,
                    font=("Arial", 12),
                    wraplength=wrap_lengths[c],
                    justify="left", anchor="w",
                    height=60
                )

            cell.grid(row=r, column=c, padx=5, pady=5, sticky="nsew")

        # match NPC row heights
        table.grid_rowconfigure(r, weight=1)

def create_scenario_detail_frame(entity_type, scenario_item, master, open_entity_callback=None):
    """
    Build a scrollable detail view for a scenario with:
    1) A header zone (Title, Summary, Secrets)
    2) Then the rest of the fields, but NPCs always before Places.
    """
    frame = ctk.CTkFrame(master)
    frame.pack(fill="both", expand=True, padx=20, pady=10)
    ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=1)
    # ——— HEADER ———
    CTkLabel(
        frame,
        text=format_longtext(scenario_item.get("Summary", "")),
        font=("Arial", 14),
        wraplength=1620,
        justify="left"
    ).pack(fill="x", pady=(0, 15))
    ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)

    # ——— BODY — prepare fields in the custom order ———
    tpl = load_template(entity_type.lower())
    # remove header fields
    body_fields = [
        f for f in tpl["fields"]
        if f["name"] not in ("Title", "Summary", "Secrets")
    ]
    # group them
    npc_fields   = [f for f in body_fields if f.get("linked_type") == "NPCs"]
    creature_fields = [f for f in body_fields if f.get("linked_type") == "Creatures"]
    place_fields = [f for f in body_fields if f.get("linked_type") == "Places"]
    other_fields = [f for f in body_fields if f not in npc_fields + place_fields + creature_fields]
    ordered_fields = npc_fields + creature_fields + place_fields + other_fields

    # render in that order
    for field in ordered_fields:
        name  = field["name"]
        ftype = field["type"]
        value = scenario_item.get(name) or ""

        if ftype == "text":
            insert_text(frame, name, value)
        elif ftype == "longtext":
            insert_longtext(frame, name, value)
        elif ftype == "list":
            linked = field.get("linked_type")
            items  = value if isinstance(value, list) else []
            if linked == "NPCs":
                insert_npc_table(frame, "NPCs", items, open_entity_callback)
            elif linked == "Creatures":
                insert_creature_table(frame, "Creatures", items, open_entity_callback)
            elif linked == "Places":
                insert_places_table(frame, "Places", items, open_entity_callback)
            else:
                insert_links(frame, name, items, linked, open_entity_callback)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=1)
    CTkLabel(frame, text="Secrets", font=("Arial", 18))\
    .pack(anchor="w", pady=(0, 5))
    CTkLabel(
        frame,
        text=format_longtext(scenario_item.get("Secrets", "")),
        font=("Arial", 14),
        wraplength=1620,
        justify="left"
    ).pack(fill="x", pady=(0, 15))
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
            portrait_label.bind(
                "<Button-1>",
                lambda e, p=portrait_path, n=portrait_label.entity_name: show_portrait(p, n)
            )
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
