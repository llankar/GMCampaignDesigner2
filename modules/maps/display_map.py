import os
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw

from modules.generic.generic_list_selection_view import GenericListSelectionView
from modules.ui.icon_button import create_icon_button
from modules.ui.image_viewer import _get_monitors

# ─ Module‐level state ───────────────────────────────────────────
_self = None
_maps = {}
map_canvas = None
map_base_tk = None
map_mask_img = None       # holds the SCALED mask for GM editing
map_mask_draw = None
map_mask_tk = None
map_brush_size = 30
map_brush_shape = "Square"  # "Circle" or "Square"
_mask_id = None

# ─ Brush helpers ─────────────────────────────────────────────────
def _set_brush_size(v):
    global map_brush_size
    map_brush_size = int(float(v))

def _set_brush_shape(shape):
    global map_brush_shape
    map_brush_shape = shape

# ─ Entry point from MainWindow ──────────────────────────────────
def select_map(self, maps_wrapper, map_template):
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

# ─ Main GM view renderer ────────────────────────────────────────
def _on_display_map(entity_type, entity_name):
    global map_canvas, map_base_tk, map_mask_img, map_mask_draw, map_mask_tk, _mask_id
    setattr(_self, "map_mode", "remove")
    item = _maps.get(entity_name)
    if not item:
        messagebox.showwarning("Not Found", f"Map '{entity_name}' not found.")
        return

    # ensure the mask file exists on disk
    mask_path = _ensure_fog_mask(item)

    # clear old content
    container = _self.get_content_container()
    for w in container.winfo_children():
        w.destroy()

    # determine GM-view size
    _self.update_idletasks()
    w, h = _self.winfo_width(), _self.winfo_height()

    # load & scale base map + mask
    base = Image.open(item["Image"]).resize((w, h), Image.LANCZOS)
    mask_scaled = Image.open(mask_path).convert("RGBA").resize((w, h), Image.NEAREST)

    # keep the scaled mask in memory for painting
    map_base_tk   = ImageTk.PhotoImage(base)
    map_mask_img  = mask_scaled
    map_mask_draw = ImageDraw.Draw(map_mask_img)
    map_mask_tk   = ImageTk.PhotoImage(map_mask_img)

    # load icons at runtime
    add_icon   = _self.load_icon("icons/brush.png",  size=(48,48))
    rem_icon   = _self.load_icon("icons/eraser.png", size=(48,48))
    save_icon  = _self.load_icon("icons/save.png",   size=(48,48))
    fs_icon    = _self.load_icon("icons/expand.png", size=(48,48))
    reset_icon    = _self.load_icon("icons/full.png", size=(48,48))
    clear_icon    = _self.load_icon("icons/empty.png", size=(48,48))

    # build UI
    frame   = ctk.CTkFrame(container); frame.pack(fill="both", expand=True)
    toolbar = ctk.CTkFrame(frame);       toolbar.pack(fill="x", pady=5)

    # icon buttons
    for icon, tip, cmd in [
        (add_icon,  "Add Fog",    lambda: setattr(_self, "map_mode", "add")),
        (rem_icon,  "Remove Fog", lambda: setattr(_self, "map_mode", "remove")),
        (clear_icon, "Clear Mask",  lambda: _clear_mask()),
        (reset_icon, "Reset Mask",  lambda: _reset_mask()),
        (save_icon, "Save Mask",  lambda: _save_fog_mask(item)),
        (fs_icon,   "Fullscreen", lambda: _show_fullscreen_map(item))
    ]:
        btn = create_icon_button(toolbar, icon, tip, cmd)
        btn.pack(side="left", padx=5)

     # brush size slider
    ctk.CTkLabel(toolbar, text="Size:").pack(side="left", padx=(20,2))
    slider = ctk.CTkSlider(toolbar, from_=5, to=200, command=_set_brush_size, width=120)
    slider.set(map_brush_size)
    slider.pack(side="left", padx=2)

    # brush shape dropdown
    ctk.CTkLabel(toolbar, text="Shape:").pack(side="left", padx=(20,2))
    opt = ctk.CTkOptionMenu(toolbar, values=["Circle","Square"], command=_set_brush_shape)
    opt.set(map_brush_shape)
    opt.pack(side="left", padx=2)

    # ─ Scrollable canvas container ────────────────────────────────
    scroll_frame = ctk.CTkFrame(frame)
    scroll_frame.pack(fill="both", expand=True)

    v_scroll = tk.Scrollbar(scroll_frame, orient="vertical")
    h_scroll = tk.Scrollbar(scroll_frame, orient="horizontal")
    v_scroll.pack(side="right", fill="y")
    h_scroll.pack(side="bottom", fill="x")

    canvas = tk.Canvas(
        scroll_frame,
        width=w, height=h,
        xscrollcommand=h_scroll.set,
        yscrollcommand=v_scroll.set
    )
    h_scroll.config(command=canvas.xview)
    v_scroll.config(command=canvas.yview)
    canvas.pack(side="left", fill="both", expand=True)

    canvas.create_image(0, 0, anchor=tk.NW, image=map_base_tk)
    _mask_id = canvas.create_image(0, 0, anchor=tk.NW, image=map_mask_tk)
    map_canvas = canvas

    # set scrollable region to full image size
    canvas.config(scrollregion=(0, 0, w, h))

    # painting bindings
    canvas.bind("<Button-1>",  _on_paint)
    canvas.bind("<B1-Motion>", _on_paint)

# ─ Clear / Reset helpers ─────────────────────────────────────────
def _clear_mask():
    global map_mask_img, map_mask_tk, map_canvas, _mask_id, map_mask_draw
    w, h = map_mask_img.size
    map_mask_draw.rectangle([(0, 0), (w, h)], fill=(0, 0, 0, 0))
    map_mask_tk = ImageTk.PhotoImage(map_mask_img)
    map_canvas.itemconfig(_mask_id, image=map_mask_tk)

def _reset_mask():
    global map_mask_img, map_mask_tk, map_canvas, _mask_id, map_mask_draw
    w, h = map_mask_img.size
    map_mask_draw.rectangle([(0, 0), (w, h)], fill=(0, 0, 0, 128))
    map_mask_tk = ImageTk.PhotoImage(map_mask_img)
    map_canvas.itemconfig(_mask_id, image=map_mask_tk)

# ─ Helpers ──────────────────────────────────────────────────────
def _ensure_fog_mask(item):
    global _maps
    img_path  = item.get("Image", "")
    mask_path = item.get("FogMaskPath", "")

    if not mask_path or not os.path.isfile(mask_path):
        base = Image.open(img_path)
        mask = Image.new("RGBA", base.size, (0, 0, 0, 128))
        os.makedirs("masks", exist_ok=True)
        safe = item["Name"].replace(" ", "_")
        mask_path = os.path.join("masks", f"{safe}_mask.png")
        mask.save(mask_path)
        item["FogMaskPath"] = mask_path
        _self.maps_wrapper.save_items(list(_maps.values()))

    return mask_path

def _on_paint(event):
    global map_mask_img, map_mask_draw, map_mask_tk, map_canvas, _mask_id

    mode = getattr(_self, "map_mode", None)
    if mode not in ("add", "remove"):
        return

    # translate canvas coordinates to mask coordinates
    x = map_canvas.canvasx(event.x)
    y = map_canvas.canvasy(event.y)
    r = map_brush_size
    color = (0, 0, 0, 128) if mode == "add" else (0, 0, 0, 0)

    if map_brush_shape == "Circle":
        map_mask_draw.ellipse([(x-r, y-r), (x+r, y+r)], fill=color)
    else:
        map_mask_draw.rectangle([(x-r, y-r), (x+r, y+r)], fill=color)

    # update the overlay image
    map_mask_tk = ImageTk.PhotoImage(map_mask_img)
    map_canvas.itemconfig(_mask_id, image=map_mask_tk)

def _save_fog_mask(item):
    if map_mask_img is None:
        messagebox.showerror("Error", "No mask to save.")
        return
    orig = Image.open(item["Image"])
    mask_to_save = map_mask_img.resize(orig.size, Image.NEAREST)
    mask_to_save.save(item["FogMaskPath"])
    _self.maps_wrapper.save_items(list(_maps.values()))
    messagebox.showinfo("Saved", f"Mask saved to:\n{item['FogMaskPath']}")

def _show_fullscreen_map(item):
    """
    Display the map on the second monitor with a FULLY-OPAQUE fog
    everywhere the GM hasn’t cleared it, stretched to fill the screen.
    """
    base_orig = Image.open(item["Image"]).convert("RGBA")
    mask0     = map_mask_img.resize(base_orig.size, Image.NEAREST).convert("RGBA")

    alpha     = mask0.split()[3]
    bin_alpha = alpha.point(lambda p: 255 if p > 0 else 0)
    mask_full = Image.new("RGBA", base_orig.size, (0,0,0,255))
    mask_full.putalpha(bin_alpha)

    comp = Image.alpha_composite(base_orig, mask_full).convert("RGB")

    mons = _get_monitors()
    sx, sy, sw, sh = mons[1] if len(mons) > 1 else mons[0]
    comp = comp.resize((sw, sh), Image.LANCZOS)

    photo = ImageTk.PhotoImage(comp)
    win   = ctk.CTkToplevel()
    win.overrideredirect(True)
    win.geometry(f"{sw}x{sh}+{sx}+{sy}")

    lbl = tk.Label(win, image=photo, bg="black")
    lbl.image = photo
    lbl.pack(fill="both", expand=True)

    win.bind("<Button-1>", lambda e: win.destroy())
