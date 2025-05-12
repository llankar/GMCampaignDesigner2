import os
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw

from modules.generic.generic_list_selection_view import GenericListSelectionView
from modules.ui.icon_button import create_icon_button
from modules.ui.image_viewer import _get_monitors
from modules.helpers.template_loader import load_template
from PIL import ImageOps

# ─ Module‐level state ───────────────────────────────────────────

_self = None
_maps = {}
_tokens = []   # maps canvas item IDs → { "tkimg": PhotoImage }
_current_drag = None  # holds token being dragged
map_canvas = None
map_base_tk = None
map_mask_img = None       # holds the SCALED mask for GM editing
map_mask_draw = None
map_mask_tk = None
map_brush_size = 30
map_brush_shape = "Square"  # "Circle" or "Square"
_mask_id = None
# keep fullscreen window & widgets around so we can update later
_fullscreen_win   = None
_fullscreen_label = None
_fullscreen_photo = None
_model_wrappers = {}
_templates = {
    "NPC":        load_template("npcs"),
    "Creature":  load_template("creatures")
}

def add_npc_portrait(image_path, x, y, size=(64,64), border=3):
    """
    Loads image, draws a blue border, places it on the map_canvas at (x,y)
    *below* the fog mask so it’s hidden until that area is cleared.
    """
    # load & resize
    img = Image.open(image_path).convert("RGBA").resize(size, Image.LANCZOS)

    # draw border
    bw, bh = size[0] + 2*border, size[1] + 2*border
    bg  = Image.new("RGBA", (bw, bh), (0, 0, 255, 255))
    bg.paste(img, (border, border), img)

    tkimg = ImageTk.PhotoImage(bg)
    item  = map_canvas.create_image(x, y, image=tkimg, tags=("npc",))
    _npcs[item] = {"tkimg": tkimg}
    # ensure it sits under the fog overlay:
    map_canvas.tag_lower(item, _mask_id)
    return item

def on_entity_selected(entity_type, entity_name, picker_frame):
    # find the item in that model
    items = _model_wrappers[entity_type].load_items()
    selected = next(item for item in items if item.get("Name")==entity_name)
    # extract the portrait path (adjust if Portrait is stored differently)
    portrait = selected.get("Portrait")
    if isinstance(portrait, dict):
        portrait_path = portrait.get("path") or portrait.get("text")
    else:
        portrait_path = portrait

    # add it to the map
    add_token_to_canvas(portrait_path)
    # close the picker
    picker_frame.destroy()
    
def load_token_image(path, size=64, border=4, border_color=(0, 120, 215, 255)):
    """
    Returns a PIL.Image and an ImageTk.PhotoImage of exactly `size`×`size` pixels,
    with `border`-pixel-wide border in `border_color`.
    """
    # 1. Load and convert
    orig = Image.open(path).convert("RGBA")

    # 2. Compute how big the inner image must be to allow for the border
    inner_size = max(size - border * 2, 1)

    # 3. Resize the portrait into the inner area
    orig = orig.resize((inner_size, inner_size), Image.LANCZOS)

    # 4. Expand with the colored border
    bordered = ImageOps.expand(orig, border=border, fill=border_color)

    # 5. Finally, ensure exact dimensions (in case rounding issues arise)
    final_img = bordered.resize((size, size), Image.LANCZOS)

    return final_img, ImageTk.PhotoImage(final_img)

def add_token_to_canvas(path):
    global map_canvas, _mask_id, _tokens
    # load & border as before
    pil_img, tk_img = load_token_image(path)
    # start in center of the *full* canvas coordinate space
    w, h = map_canvas.winfo_width(), map_canvas.winfo_height()
    x, y = w // 2, h // 2

    # create the token image and tag it
    item_id = map_canvas.create_image(x, y, image=tk_img, tags=("token",))

    # **lift** it above the fog mask so you can still click/drag it
    map_canvas.tag_raise(item_id, _mask_id)

    # record both its PIL image (for full-res compositing) and its coords
    _tokens.append({
    "id":   item_id,
    "pil":  pil_img,
    "tk":   tk_img,
    "x":    x,
    "y":    y
})


# ─── function to open the selection view ───
def open_entity_picker(entity_type):
    picker_win = tk.Toplevel(_self)   # or whatever your main window var is
    picker_win.title(f"Select {entity_type}")
    view = GenericListSelectionView(
        master=picker_win,
        entity_type=entity_type,
        model_wrapper=_model_wrappers[entity_type],
        template=_templates[entity_type],
        on_select_callback=lambda et, name: on_entity_selected(et, name, picker_win)
    )
    view.pack(fill="both", expand=True)


# ─ Brush helpers ─────────────────────────────────────────────────
def _set_brush_size(v):
    global map_brush_size
    map_brush_size = int(float(v))

def _set_brush_shape(shape):
    global map_brush_shape
    map_brush_shape = shape

# ─ Entry point from MainWindow ──────────────────────────────────
def select_map(self, maps_wrapper, map_template):
    global _self, _maps, _model_wrappers
    _self = self
    _model_wrappers = {
        "NPC":        _self.npc_wrapper,
        "Creature":  _self.creature_wrapper,
    }
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
    npc_icon   = _self.load_icon("icons/npc.png",   size=(48,48))
    creature_icon   = _self.load_icon("icons/creature.png",   size=(48,48))
    # build UI
    frame   = ctk.CTkFrame(container); frame.pack(fill="both", expand=True)
    toolbar = ctk.CTkFrame(frame);       toolbar.pack(fill="x", pady=5)
    # in toolbar setup:
   
    # icon buttons
    for icon, tip, cmd in [
        (add_icon,  "Add Fog",    lambda: setattr(_self, "map_mode", "add")),
        (rem_icon,  "Remove Fog", lambda: setattr(_self, "map_mode", "remove")),
        (clear_icon, "Clear Mask",  lambda: _clear_mask()),
        (reset_icon, "Reset Mask",  lambda: _reset_mask()),
        (save_icon, "Save Mask",  lambda: _save_fog_mask(item)),
        (npc_icon, "add NPC",  lambda: open_entity_picker("NPC")),
        (creature_icon, "add Creature",  lambda: open_entity_picker("Creature")),
        (fs_icon,   "Fullscreen", lambda: _show_fullscreen_map(item)),
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
    # ── NPC drag bindings ─────────────────────────
    canvas.tag_bind("token", "<ButtonPress-1>",    on_token_press)
    canvas.tag_bind("token", "<B1-Motion>",       on_token_move)
    canvas.tag_bind("token", "<ButtonRelease-1>", on_token_release)
    
    # set scrollable region to full image size
    canvas.config(scrollregion=(0, 0, w, h))

    # painting bindings
    canvas.bind("<Button-1>",  _on_paint)
    canvas.bind("<B1-Motion>", _on_paint)

def on_token_press(evt):
    global _current_drag
    # pick the top token under the cursor
    items = map_canvas.find_withtag("token")
    clicked = map_canvas.find_closest(evt.x, evt.y)
    if clicked and clicked[0] in items:
        _current_drag = clicked[0]
        return "break"   # ← stop further fog‐editing handlers

def on_token_move(evt):
    global _current_drag, _tokens
    if _current_drag:
        # translate mouse → canvas coords
        x = map_canvas.canvasx(evt.x)
        y = map_canvas.canvasy(evt.y)

        # move the token on the GM canvas
        map_canvas.coords(_current_drag, x, y)

        # **update its position in our state** so the full-screen composer knows where it is
        for tok in _tokens:
            if tok["id"] == _current_drag:
                tok["x"], tok["y"] = x, y
                break

        # don’t let this event fall through to your fog-painting code
        return "break"

def on_token_release(evt):
    global _current_drag
    if _current_drag:
        # (we’ve already been updating .x/.y in on_token_move, so nothing more to do here)
        _current_drag = None
        return "break"
        
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

    # translate to canvas coords
    x = map_canvas.canvasx(event.x)
    y = map_canvas.canvasy(event.y)

    # **1) If there's a token here, do nothing and stop propagation**
    overlapping = map_canvas.find_overlapping(x, y, x, y)
    for item in overlapping:
        if "token" in map_canvas.gettags(item):
            return "break"

    # 2) Otherwise, paint or erase fog as before
    r = map_brush_size
    color = (0, 0, 0, 128) if mode == "add" else (0, 0, 0, 0)

    if map_brush_shape == "Circle":
        map_mask_draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=color)
    else:
        map_mask_draw.rectangle([(x - r, y - r), (x + r, y + r)], fill=color)

    # 3) Update the Tk image
    map_mask_tk = ImageTk.PhotoImage(map_mask_img)
    map_canvas.itemconfig(_mask_id, image=map_mask_tk)

    # Stop any other bindings from running
    return "break"

def _save_fog_mask(item):
    if map_mask_img is None:
        messagebox.showerror("Error", "No mask to save.")
        return
    orig = Image.open(item["Image"])
    mask_to_save = map_mask_img.resize(orig.size, Image.NEAREST)
    mask_to_save.save(item["FogMaskPath"])
    _self.maps_wrapper.save_items(list(_maps.values()))
    # First update the second‐screen view…
    _update_fullscreen_map(item)
    if _fullscreen_win and _fullscreen_win.winfo_exists():
        # force a redraw
        _fullscreen_win.update_idletasks()

def _show_fullscreen_map(item):
    """
    1) Scale the original map & fog to the second monitor
    2) Paste each 24×24 token at its SCREEN-coordinate
    3) Finally apply that fog on top so tokens only show in cleared areas
    """
    global _fullscreen_win, _fullscreen_label, _fullscreen_photo

    # 1. Which monitor & what size?
    mons = _get_monitors()
    sx, sy, sw, sh = mons[1] if len(mons) > 1 else mons[0]

    # 2. Load original assets
    base_orig = Image.open(item["Image"]).convert("RGBA")
    mask_orig = Image.open(item["FogMaskPath"]).convert("RGBA")

    # 3. Scale them to screen resolution
    base_screen = base_orig.resize((sw, sh), Image.LANCZOS)
    mask_screen = mask_orig.resize((sw, sh), Image.NEAREST)

    # 4. Build a transparent layer for tokens
    token_layer = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    gm_w, gm_h = map_mask_img.size   # GM-view mask is at GM size

    for t in _tokens:
        # Compute the token’s position on screen
        tx = int(t["x"] / gm_w * sw)
        ty = int(t["y"] / gm_h * sh)
        # Center a 24×24 token there
        token_layer.paste(
            t["pil"],
            (tx - t["pil"].width // 2, ty - t["pil"].height // 2),
            t["pil"]
        )

    # 5. Composite in order: map → tokens → fog
    comp = Image.alpha_composite(base_screen, token_layer)
    alpha = mask_screen.split()[3].point(lambda p: 255 if p > 0 else 0)
    fog   = Image.new("RGBA", (sw, sh), (0, 0, 0, 255))
    fog.putalpha(alpha)
    final = Image.alpha_composite(comp, fog).convert("RGB")

    # 6. Show as a borderless window on that monitor
    photo = ImageTk.PhotoImage(final)
    win   = ctk.CTkToplevel(); win.overrideredirect(True)
    win.geometry(f"{sw}x{sh}+{sx}+{sy}")

    _fullscreen_photo = photo
    _fullscreen_label = tk.Label(win, image=photo, bg="black")
    _fullscreen_label.image = photo
    _fullscreen_label.pack(fill="both", expand=True)
    win.bind("<Button-1>", lambda e: win.destroy())
    _fullscreen_win = win

def _update_fullscreen_map(item):
    """
    Exactly the same pipeline as _show_fullscreen_map,
    but just swaps in a new PhotoImage on the existing window.
    """
    if not (_fullscreen_win and _fullscreen_win.winfo_exists()):
        return

    mons = _get_monitors()
    sx, sy, sw, sh = mons[1] if len(mons) > 1 else mons[0]

    base_orig = Image.open(item["Image"]).convert("RGBA")
    mask_orig = Image.open(item["FogMaskPath"]).convert("RGBA")

    base_screen = base_orig.resize((sw, sh), Image.LANCZOS)
    mask_screen = mask_orig.resize((sw, sh), Image.NEAREST)

    token_layer = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    gm_w, gm_h = map_mask_img.size

    for t in _tokens:
        tx = int(t["x"] / gm_w * sw)
        ty = int(t["y"] / gm_h * sh)
        token_layer.paste(
            t["pil"],
            (tx - t["pil"].width // 2, ty - t["pil"].height // 2),
            t["pil"]
        )

    comp = Image.alpha_composite(base_screen, token_layer)
    alpha = mask_screen.split()[3].point(lambda p: 255 if p > 0 else 0)
    fog   = Image.new("RGBA", (sw, sh), (0, 0, 0, 255))
    fog.putalpha(alpha)
    final = Image.alpha_composite(comp, fog).convert("RGB")

    new_photo = ImageTk.PhotoImage(final)
    _fullscreen_photo = new_photo
    _fullscreen_label.config(image=new_photo)
    _fullscreen_label.image = new_photo