import os
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw

from modules.generic.generic_list_selection_view import GenericListSelectionView
from modules.ui.image_viewer import _get_monitors  # monitor detection from image_viewer :contentReference[oaicite:2]{index=2}:contentReference[oaicite:3]{index=3}

# ─ Module‐level state so callbacks can share data ────────────────
_self = None
_maps = {}
map_canvas = None
map_base_tk = None
map_mask_img = None
map_mask_draw = None
map_mask_tk = None
map_brush_size = 30
_mask_id = None

def select_map(self, maps_wrapper, map_template):
    """
    Called by MainWindow.map_tool:
    - stores 'self' and loads all maps into a dict
    - clears the content area
    - shows a GenericListSelectionView that calls _on_display_map
    """
    global _self, _maps
    _self = self
    _maps = {m["Name"]: m for m in maps_wrapper.load_items()}
    _self.clear_current_content()

    selector = GenericListSelectionView(
        _self.get_content_container(),
        "maps",
        maps_wrapper,
        map_template,
        on_select_callback=_on_display_map
    )
    selector.pack(fill="both", expand=True)

def _on_display_map(entity_type, entity_name):
    """
    When a map is selected:
    - ensures a fog mask exists (semi-transparent in GM view)
    - resizes map + mask to fill the window
    - displays them on a canvas with control buttons
    """
    global map_canvas, map_base_tk, map_mask_img, map_mask_draw, map_mask_tk, _mask_id

    item = _maps.get(entity_name)
    if not item:
        messagebox.showwarning("Not Found", f"Map '{entity_name}' not found.")
        return

    # ensure we have a mask file (at whatever opacity the GM wants)
    mask_path = _ensure_fog_mask(item)

    # clear out the GM view area
    container = _self.get_content_container()
    for w in container.winfo_children():
        w.destroy()

    # determine container size
    _self.update_idletasks()
    win_w = _self.winfo_width()
    win_h = _self.winfo_height()

    # load & scale
    base = Image.open(item["Image"]).resize((win_w, win_h), Image.LANCZOS)
    mask = Image.open(mask_path).convert("RGBA").resize((win_w, win_h), Image.NEAREST)

    map_base_tk   = ImageTk.PhotoImage(base)
    map_mask_img  = mask
    map_mask_draw = ImageDraw.Draw(map_mask_img)
    map_mask_tk   = ImageTk.PhotoImage(map_mask_img)

    # build UI
    frame = ctk.CTkFrame(container)
    frame.pack(fill="both", expand=True)

    btn_frame = ctk.CTkFrame(frame)
    btn_frame.pack(fill="x", pady=5)

    # GM controls
    ctk.CTkButton(btn_frame, text="Add Fog",
                  command=lambda: setattr(_self, "map_mode", "add")
                 ).pack(side="left", padx=5)
    ctk.CTkButton(btn_frame, text="Remove Fog",
                  command=lambda: setattr(_self, "map_mode", "remove")
                 ).pack(side="left", padx=5)
    ctk.CTkButton(btn_frame, text="Save Mask",
                  command=lambda: _save_fog_mask(item)
                 ).pack(side="left", padx=5)

    # ★ New button to pop this map+mask full‐screen on the 2nd monitor
    ctk.CTkButton(btn_frame, text="Show Fullscreen",
                  command=lambda: _show_fullscreen_map(item)
                 ).pack(side="left", padx=5)

    # the canvas with base + mask
    canvas = tk.Canvas(frame, width=win_w, height=win_h)
    canvas.pack(fill="both", expand=True)
    canvas.create_image(0, 0, anchor=tk.NW, image=map_base_tk)
    _mask_id   = canvas.create_image(0, 0, anchor=tk.NW, image=map_mask_tk)
    map_canvas = canvas

    canvas.bind("<Button-1>",  _on_paint)
    canvas.bind("<B1-Motion>", _on_paint)

def _ensure_fog_mask(item):
    """
    Create a mask PNG if none exists;
    mask opacity is whatever the GM desires in the edit view.
    """
    global _maps
    img_path  = item.get("Image", "")
    mask_path = item.get("FogMaskPath", "")

    if not mask_path or not os.path.isfile(mask_path):
        base = Image.open(img_path)
        # default semi-transparent mask (GM edit view)
        mask = Image.new("RGBA", base.size, (0, 0, 0, 128))
        os.makedirs("masks", exist_ok=True)
        safe = item['Name'].replace(' ', '_')
        mask_path = os.path.join("masks", f"{safe}_mask.png")
        mask.save(mask_path)
        item["FogMaskPath"] = mask_path
        _self.maps_wrapper.save_items(list(_maps.values()))

    return mask_path

def _on_paint(event):
    """
    Draw or erase on the mask in GM view,
    then update the overlay.
    """
    global map_mask_img, map_mask_draw, map_mask_tk, map_canvas, _mask_id

    mode = getattr(_self, "map_mode", None)
    if mode not in ("add", "remove"):
        return

    x, y = event.x, event.y
    r    = map_brush_size
    color = (0, 0, 0, 128) if mode == "add" else (0, 0, 0, 0)

    map_mask_draw.ellipse([(x-r, y-r), (x+r, y+r)], fill=color)
    map_mask_tk = ImageTk.PhotoImage(map_mask_img)
    map_canvas.itemconfig(_mask_id, image=map_mask_tk)

def _save_fog_mask(item):
    """
    Save the GM‐edited mask to disk and DB.
    """
    if map_mask_img is None:
        messagebox.showerror("Error", "No mask to save.")
        return
    path = item.get("FogMaskPath", "")
    map_mask_img.save(path)
    _self.maps_wrapper.save_items(list(_maps.values()))
    messagebox.showinfo("Fog Saved", f"Mask saved to:\n{path}")

def _show_fullscreen_map(item):
    """
    Displays the map on the second monitor with a FULLY-OPAQUE fog
    everywhere the GM hasn’t cleared it, using the current in-memory mask.
    """
    import customtkinter as ctk
    import tkinter as tk
    from PIL import Image, ImageTk
    from modules.ui.image_viewer import _get_monitors

    global map_mask_img

    # 1) Load the base map and grab the current in-memory fog mask
    base_orig = Image.open(item["Image"]).convert("RGBA")
    mask_orig = map_mask_img.copy().convert("RGBA")

    # 2) Determine second monitor geometry
    monitors = _get_monitors()
    target   = monitors[1] if len(monitors) > 1 else monitors[0]
    sx, sy, sw, sh = target

    # 3) Resize both base and mask to fill that screen
    base = base_orig.resize((sw, sh), Image.LANCZOS)
    mask = mask_orig.resize((sw, sh), Image.NEAREST)

    # 4) Create a binary (fully-opaque) version of the mask:
    #    any pixel you haven’t erased → alpha = 255; erased → alpha = 0
    alpha = mask.split()[3]
    bin_alpha = alpha.point(lambda p: 255 if p > 0 else 0)
    mask_full = Image.new("RGBA", (sw, sh), (0, 0, 0, 255))
    mask_full.putalpha(bin_alpha)

    # 5) Composite the full-opacity mask over the base map
    comp = Image.alpha_composite(base, mask_full).convert("RGB")

    # 6) Show in a borderless CTkToplevel on the second screen
    photo = ImageTk.PhotoImage(comp)
    win = ctk.CTkToplevel()
    win.overrideredirect(True)
    win.geometry(f"{sw}x{sh}+{sx}+{sy}")

    lbl = tk.Label(win, image=photo, bg="black")
    lbl.image = photo
    lbl.pack(fill="both", expand=True)

    # 7) Close when clicked
    win.bind("<Button-1>", lambda e: win.destroy())

