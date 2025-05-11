import os
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw
from modules.generic.generic_list_selection_view import GenericListSelectionView

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
    - remembers 'self' and loads all maps into a dict
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
    - ensures a 50%-opaque fog mask exists
    - resizes map + mask to fill the window
    - displays them on a canvas with Add/Remove Fog & Save Mask buttons
    """
    global map_canvas, map_base_tk, map_mask_img, map_mask_draw, map_mask_tk, _mask_id

    item = _maps.get(entity_name)
    if not item:
        messagebox.showwarning("Not Found", f"Map '{entity_name}' not found.")
        return

    # 1) Ensure the mask file exists (at 50% opacity)
    mask_path = _ensure_fog_mask(item)

    # 2) Figure out full window size
    _self.update_idletasks()
    win_w = _self.winfo_width()
    win_h = _self.winfo_height()

    # 3) Clear out the content area
    container = _self.get_content_container()
    for w in container.winfo_children():
        w.destroy()

    # 4) Load & resize images
    base = Image.open(item["Image"]).resize((win_w, win_h), Image.LANCZOS)
    mask = Image.open(mask_path).convert("RGBA").resize((win_w, win_h), Image.NEAREST)

    map_base_tk  = ImageTk.PhotoImage(base)
    map_mask_img = mask
    map_mask_draw = ImageDraw.Draw(map_mask_img)
    map_mask_tk  = ImageTk.PhotoImage(map_mask_img)

    # 5) Build UI: buttons + canvas
    frame = ctk.CTkFrame(container)
    frame.pack(fill="both", expand=True)

    btn_frame = ctk.CTkFrame(frame)
    btn_frame.pack(fill="x", pady=5)
    ctk.CTkButton(btn_frame, text="Add Fog",
                command=lambda: setattr(_self, "map_mode", "add")
            ).pack(side="left", padx=5)
    ctk.CTkButton(btn_frame, text="Remove Fog",
            command=lambda: setattr(_self, "map_mode", "remove")
        ).pack(side="left", padx=5)
    ctk.CTkButton(btn_frame, text="Save Mask",
    command=lambda: _save_fog_mask(item)
    ).pack(side="left", padx=5)

    canvas = tk.Canvas(frame, width=win_w, height=win_h)
    canvas.pack(fill="both", expand=True)
    canvas.create_image(0, 0, anchor=tk.NW, image=map_base_tk)
    _mask_id = canvas.create_image(0, 0, anchor=tk.NW, image=map_mask_tk)
    map_canvas = canvas

    canvas.bind("<Button-1>",  _on_paint)
    canvas.bind("<B1-Motion>", _on_paint)

def _ensure_fog_mask(item):
    """
    Create a 50%-opaque black mask PNG if none exists,
    otherwise reuse the existing one. Persist FogMaskPath back to DB.
    """
    global _maps
    img_path = item.get("Image", "")
    mask_path = item.get("FogMaskPath", "")

    if not mask_path or not os.path.isfile(mask_path):
        base = Image.open(img_path)
        # 50% opacity black
        mask = Image.new("RGBA", base.size, (0, 0, 0, 127))
        os.makedirs("masks", exist_ok=True)
        safe_name = item['Name'].replace(' ', '_')
        mask_path = os.path.join("masks", f"{safe_name}_mask.png")
        mask.save(mask_path)
        item["FogMaskPath"] = mask_path
        # Persist all maps back to the DB with updated paths
        _self.maps_wrapper.save_items(list(_maps.values()))

    return mask_path

def _on_paint(event):
    """
    Draw or erase a semi-transparent circle on the mask depending on map_mode,
    then update the canvas overlay in real time.
    """
    global map_mask_img, map_mask_draw, map_mask_tk, map_canvas, _mask_id

    mode = getattr(_self, "map_mode", None)
    if mode not in ("add", "remove"):
        return

    x, y = event.x, event.y
    r    = map_brush_size
    # semi-transparent black for add, full clear for remove
    color = (0, 0, 0, 128) if mode == "add" else (0, 0, 0, 0)

    map_mask_draw.ellipse([(x-r, y-r), (x+r, y+r)], fill=color)

    # Refresh the PhotoImage to show the change
    map_mask_tk = ImageTk.PhotoImage(map_mask_img)
    map_canvas.itemconfig(_mask_id, image=map_mask_tk)

def _save_fog_mask(item):
    """
    Write the edited mask back to disk and persist the model update.
    """
    path = item.get("FogMaskPath", "")
    if not path or map_mask_img is None:
        messagebox.showerror("Error", "No mask to save.")
        return

    map_mask_img.save(path)
    _self.maps_wrapper.save_items(list(_maps.values()))
    messagebox.showinfo("Fog Saved", f"Mask saved to:\n{path}")