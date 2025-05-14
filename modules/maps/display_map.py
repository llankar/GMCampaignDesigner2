import os
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw, ImageOps

from modules.generic.generic_list_selection_view import GenericListSelectionView
from modules.ui.icon_button import create_icon_button
from modules.helpers.template_loader import load_template
from modules.generic.generic_model_wrapper import GenericModelWrapper
from modules.ui.image_viewer import _get_monitors, show_portrait


# ─ Module‐level state ───────────────────────────────────────────
_current_map      = None
_self             = None
_token_menu       = None
_menu_token_id    = None
_maps             = {}
_tokens           = []  # each: { "id", "orig_pil", "pil", "tk", "path", "x", "y" }
_current_drag     = None
map_canvas        = None
map_base_tk       = None
map_mask_img      = None
map_mask_draw     = None
map_mask_tk       = None
map_mask_pil      = None
map_mask_orig     = None
map_brush_size    = 30
map_brush_shape   = "Square"         # "Circle" or "Square"
_mask_id          = None
_fullscreen_win   = None
_fullscreen_label = None
_fullscreen_photo = None
_model_wrappers   = {}
map_zoom          = 1.0              # current zoom factor
map_base_pil      = None             # fit-to-screen copy of map
map_base_orig     = None             # pristine full-res map
gm_view_size      = (0, 0)           # (w, h) of the GM canvas at 100%
_base_id          = None   
_marker_pos = None   # holds (wx, wy) while the marker is active# canvas item ID for the base map image
# ── after your other module-globals ─────────────────────────
_marker_after_id = None     # ID of the .after() call
_marker_id       = None     # canvas ID of the red circle on main canvas
_templates = {
    "NPC":      load_template("npcs"),
    "Creature": load_template("creatures")
}

def select_map(self, maps_wrapper, map_template):
    """
    Entry point: show list of maps.
    """
    global _self, _maps, _model_wrappers
    _self = self
    _model_wrappers = {
        "NPC":      _self.npc_wrapper,
        "Creature": _self.creature_wrapper,
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
    
def _show_marker():
    """"Actually draw the red circle at _marker_pos on both canvases."""
    global _marker_id
    if not _marker_pos:
        return
    wx, wy = _marker_pos
    r = 20
    # draw on GM canvas
    _marker_id = map_canvas.create_oval(
        wx-r, wy-r, wx+r, wy+r,
        outline="red", width=3
    )
    # redraw fullscreen (pass the world‐pos)
    if _fullscreen_win and _fullscreen_win.winfo_exists():
        _update_fullscreen_map(_current_map, marker_world=_marker_pos)

def _end_marker(evt):
    """On release: cancel or remove the marker everywhere."""
    global _marker_after_id, _marker_id, _marker_pos
    # cancel pending long‐press
    if _marker_after_id:
        map_canvas.after_cancel(_marker_after_id)
        _marker_after_id = None

    # remove from GM canvas
    if _marker_id:
        map_canvas.delete(_marker_id)
        _marker_id = None

    # clear stored pos and update fullscreen to erase it
    _marker_pos = None
    if _fullscreen_win and _fullscreen_win.winfo_exists():
        _update_fullscreen_map(_current_map, marker_world=None)
        
def on_entity_selected(entity_type, entity_name, picker_frame):
    """
    Called when user picks an NPC or Creature in the selection dialog.
    """
    items = _model_wrappers[entity_type].load_items()
    selected = next(item for item in items if item.get("Name") == entity_name)
    portrait = selected.get("Portrait")
    if isinstance(portrait, dict):
        path = portrait.get("path") or portrait.get("text")
    else:
        path = portrait

    add_token_to_canvas(path)
    picker_frame.destroy()

def load_token_image(path, size=48, border=4, border_color=(0, 120, 215, 255)):
    """
    Returns a PIL.Image and PhotoImage of exactly `size`×`size` px,
    with a `border`-px solid outline in `border_color`.
    """
    orig = Image.open(path).convert("RGBA")
    inner = max(size - border * 2, 1)
    orig = orig.resize((inner, inner), Image.LANCZOS)
    bordered = ImageOps.expand(orig, border=border, fill=border_color)
    final = bordered.resize((size, size), Image.LANCZOS)
    return final, ImageTk.PhotoImage(final)

def open_entity_picker(entity_type):
    """
    Show a GenericListSelectionView for NPCs or Creatures.
    """
    picker = tk.Toplevel(_self)
    picker.title(f"Select {entity_type}")
    view = GenericListSelectionView(
        master=picker,
        entity_type=entity_type,
        model_wrapper=_model_wrappers[entity_type],
        template=_templates[entity_type],
        on_select_callback=lambda et, name: on_entity_selected(et, name, picker)
    )
    view.pack(fill="both", expand=True)

def add_token_to_canvas(path, x=None, y=None, persist=True):
    """
    Place a new token at (x,y) or center if None.
    Records into both _tokens (live) and _current_map['Tokens'] (persistent).
    """
    global map_canvas, _mask_id, _tokens, _current_map

    # default coords = center
    w, h = map_canvas.winfo_width(), map_canvas.winfo_height()
    x = x if x is not None else w // 2
    y = y if y is not None else h // 2

    # load & bordered token image
    pil_img, tk_img = load_token_image(path)
    item_id = map_canvas.create_image(x, y, image=tk_img, tags=("token",))
    map_canvas.tag_raise(item_id, _mask_id)

    # record live, storing original PIL for zoom
    _tokens.append({
        "id":       item_id,
        "orig_pil": pil_img.copy(),
        "pil":      pil_img,
        "tk":       tk_img,
        "path":     path,
        "x":        x,
        "y":        y
    })

    # record persistent
    if persist:
        _current_map["Tokens"].append({"path": path, "x": x, "y": y})

def on_token_press(evt):
    """
    Begin dragging a token.
    """
    global _current_drag
    clicked = map_canvas.find_closest(evt.x, evt.y)
    if clicked and "token" in map_canvas.gettags(clicked[0]):
        _current_drag = clicked[0]
        return "break"

def on_token_move(evt):
    """
    Move the token under the mouse, update live and persistent coords.
    """
    global _current_drag, _tokens, _current_map
    if not _current_drag:
        return

    x = map_canvas.canvasx(evt.x)
    y = map_canvas.canvasy(evt.y)
    map_canvas.coords(_current_drag, x, y)

    # update live
    tok = next(t for t in _tokens if t["id"] == _current_drag)
    old_x, old_y = tok["x"], tok["y"]
    tok["x"], tok["y"] = x, y

    # update persistent
    rec = next(r for r in _current_map["Tokens"]
               if r["path"] == tok["path"] and r["x"] == old_x and r["y"] == old_y)
    rec["x"], rec["y"] = x, y

    return "break"

def on_token_release(evt):
    """
    End dragging.
    """
    global _current_drag
    if _current_drag:
        _current_drag = None
        return "break"

def _set_brush_size(v):
    global map_brush_size
    map_brush_size = int(float(v))

def _set_brush_shape(shape):
    global map_brush_shape
    map_brush_shape = shape

def _ensure_fog_mask(item):
    """
    Ensure the fog-mask file exists; if not, create a blank one.
    """
    mask_dir = os.path.join(os.path.dirname(item["Image"]), "masks")
    os.makedirs(mask_dir, exist_ok=True)
    mask_path = os.path.join(mask_dir, f"{item['Name']}.png")
    if not os.path.isfile(mask_path):
        orig = Image.open(item["Image"])
        mask = Image.new("RGBA", orig.size, (0, 0, 0, 255))
        mask.save(mask_path)
    return mask_path

def _clear_mask():
    """
    Clear the current fog mask to opaque.
    """
    global map_mask_img, map_mask_draw, map_mask_tk
    w, h = map_mask_img.size
    map_mask_img = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    map_mask_draw = ImageDraw.Draw(map_mask_img)
    map_canvas.itemconfig(_mask_id, image=ImageTk.PhotoImage(map_mask_img))

def _reset_mask():
    """
    Reset the mask to the last-saved state.
    """
    global map_mask_img, map_mask_draw, map_mask_pil, map_mask_orig, map_mask_tk
    map_mask_img = map_mask_pil.copy()
    map_mask_draw = ImageDraw.Draw(map_mask_img)
    map_canvas.itemconfig(_mask_id, image=ImageTk.PhotoImage(map_mask_img))

def _save_fog_mask(item):
    """
    Save the current fog-mask image to disk.
    """
    global map_mask_img
    mask_path = _ensure_fog_mask(item)
    map_mask_img.save(mask_path)
    messagebox.showinfo("Saved", f"Fog mask saved to {mask_path}")

def _show_fullscreen_map(item):
    """
    Display a mirror of the GM map on a second monitor (if available).
    """
    global _fullscreen_win, _fullscreen_label, _fullscreen_photo
    if _fullscreen_win is not None:
        return
    monitors = _get_monitors()
    if len(monitors) < 2:
        messagebox.showwarning("No second monitor", "Cannot find a second display")
        return
    # Create fullscreen window on second monitor
    _fullscreen_win = tk.Toplevel(_self)
    _fullscreen_win.overrideredirect(True)
    m = monitors[1]
    _fullscreen_win.geometry(f"{m.width}x{m.height}+{m.x}+{m.y}")
    _fullscreen_label = tk.Label(_fullscreen_win)
    _fullscreen_label.pack(fill="both", expand=True)
    _update_fullscreen_map(item)

def _update_fullscreen_map(item):
    """
    Update the fullscreen mirror with the current zoom & mask state.
    """
    global _fullscreen_photo
    sw, sh = _fullscreen_label.winfo_width(), _fullscreen_label.winfo_height()
    if sw == 0 or sh == 0:
        return

    # Zoom & composite base+mask
    zoomed = map_base_orig.resize((int(gm_view_size[0]*map_zoom), int(gm_view_size[1]*map_zoom)), Image.LANCZOS)
    maskz  = map_mask_img.resize((int(gm_view_size[0]*map_zoom), int(gm_view_size[1]*map_zoom)), Image.NEAREST)
    final_orig = Image.alpha_composite(zoomed.convert("RGBA"), maskz.convert("RGBA"))

    # Fit to fullscreen window
    if sw/sh > final_orig.width/final_orig.height:
        ratio = sw/final_orig.width
    else:
        ratio = sh/final_orig.height
    swz, shz = int(final_orig.width*ratio), int(final_orig.height*ratio)
    final = final_orig.resize((swz, shz), Image.LANCZOS)

    # Center if smaller
    if swz < sw or shz < sh:
        px = (sw - swz) // 2 if swz < sw else 0
        py = (sh - shz) // 2 if shz < sh else 0
        canvas_img = Image.new("RGB", (sw, sh), (0, 0, 0))
        canvas_img.paste(final, (px, py))
        final = canvas_img

    # Swap in the new image
    new_photo = ImageTk.PhotoImage(final)
    _fullscreen_photo = new_photo
    _fullscreen_label.config(image=new_photo)
    _fullscreen_label.image = new_photo

def _on_display_map(entity_type, entity_name):
    """
    Show the GM map editor:
      - load/create fog mask
      - setup canvas + toolbar
      - re-spawn saved tokens
    """
    global _self, map_canvas, map_base_tk, map_mask_img, map_mask_draw, map_mask_tk
    global _base_id, _mask_id, _current_map, _tokens
    global map_base_pil, map_base_orig, map_mask_pil, map_mask_orig, gm_view_size

    setattr(_self, "map_mode", "remove")
    item = _maps.get(entity_name)
    if not item:
        messagebox.showwarning("Not Found", f"Map '{entity_name}' not found.")
        return

    # Persistence init
    _current_map = item
    item["Tokens"] = item.get("Tokens") or []

    mask_path = _ensure_fog_mask(item)

    # clear UI
    container = _self.get_content_container()
    for w in container.winfo_children():
        w.destroy()

    # GM view size
    _self.update_idletasks()
    w, h = _self.winfo_width(), _self.winfo_height()

    # load & scale base map + mask at 100%
    base        = Image.open(item["Image"]).resize((w, h), Image.LANCZOS)
    mask_scaled = Image.open(mask_path).convert("RGBA").resize((w, h), Image.NEAREST)

    # ── store originals for zooming ───────────────────────────
    map_base_pil   = base.copy()
    map_base_orig  = Image.open(item["Image"]).convert("RGBA")
    map_mask_img   = mask_scaled.copy()
    map_mask_draw  = ImageDraw.Draw(map_mask_img)
    map_mask_pil   = mask_scaled.copy()
    map_mask_orig  = Image.open(mask_path).convert("RGBA")
    gm_view_size   = (w, h)

    # toolbar
    toolbar = ctk.CTkFrame(container)
    toolbar.pack(fill="x", pady=5)

    icons = {
        "add":    _self.load_icon("icons/brush.png",  size=(48,48)),
        "rem":    _self.load_icon("icons/eraser.png", size=(48,48)),
        "clear":  _self.load_icon("icons/empty.png",  size=(48,48)),
        "reset":  _self.load_icon("icons/full.png",   size=(48,48)),
        "save":   _self.load_icon("icons/save.png",   size=(48,48)),
        "fs":     _self.load_icon("icons/expand.png", size=(48,48)),
        "npc":    _self.load_icon("icons/npc.png",    size=(48,48)),
        "creat":  _self.load_icon("icons/creature.png", size=(48,48))
    }
    for icon, tip, cmd in [
        (icons["add"],   "Add Fog",    lambda: setattr(_self, "map_mode", "add")),
        (icons["rem"],   "Remove Fog", lambda: setattr(_self, "map_mode", "remove")),
        (icons["clear"], "Clear Fog", lambda: _clear_mask()),
        (icons["reset"], "Reset Fog", lambda: _reset_mask()),
        (icons["save"],  "Save Image",  lambda: _save_fog_mask(item)),
        (icons["npc"],   "Add NPC",    lambda: open_entity_picker("NPC")),
        (icons["creat"], "Add Creature", lambda: open_entity_picker("Creature")),
        (icons["fs"],    "Fullscreen", lambda: _show_fullscreen_map(item)),
    ]:
        btn = create_icon_button(toolbar, icon, tip, cmd)
        btn.pack(side="left", padx=5)

    ctk.CTkLabel(toolbar, text="Size:").pack(side="left", padx=(20,2))
    slider = ctk.CTkSlider(toolbar, from_=5, to=200, command=_set_brush_size, width=120)
    slider.set(map_brush_size)
    slider.pack(side="left", padx=2)

    ctk.CTkLabel(toolbar, text="Shape:").pack(side="left", padx=(20,2))
    opt = ctk.CTkOptionMenu(toolbar, values=["Circle","Square"], command=_set_brush_shape)
    opt.set(map_brush_shape)
    opt.pack(side="left", padx=2)

    # full-window canvas (no scrollbars)
    map_canvas = tk.Canvas(container, width=w, height=h)
    map_canvas.pack(fill="both", expand=True)
    map_canvas.config(scrollregion=(0, 0, w, h))

    # draw base & mask, keep their IDs
    map_base_tk = ImageTk.PhotoImage(base)
    _base_id    = map_canvas.create_image(0, 0, anchor=tk.NW, image=map_base_tk)

    map_mask_tk = ImageTk.PhotoImage(map_mask_img)
    _mask_id    = map_canvas.create_image(0, 0, anchor=tk.NW, image=map_mask_tk)

    # token bindings
    map_canvas.tag_bind("token", "<ButtonPress-1>",    on_token_press)
    map_canvas.tag_bind("token", "<B1-Motion>",       on_token_move)
    map_canvas.tag_bind("token", "<ButtonRelease-1>", on_token_release)
    map_canvas.tag_bind("token", "<ButtonRelease-3>", on_token_right_click)
    map_canvas.bind("<Button-2>", _center_view_on_click)
    # long-press marker bindings
    map_canvas.bind("<ButtonPress-1>", _begin_marker, add="+")
    map_canvas.bind("<ButtonRelease-1>", _end_marker, add="+")
    
    # zoom with Ctrl+wheel
    map_canvas.bind("<MouseWheel>", _on_zoom)
    map_canvas.bind("<Control-Button-4>",   _on_zoom)
    map_canvas.bind("<Control-Button-5>",   _on_zoom)

    # painting bindings
    map_canvas.bind("<Button-1>",    _on_paint, add="+")
    map_canvas.bind("<B1-Motion>",   _on_paint)

    # spawn saved tokens
    _tokens.clear()
    for rec in item["Tokens"]:
        add_token_to_canvas(rec["path"], rec["x"], rec["y"], persist=False)

    global _token_menu
    _token_menu = tk.Menu(map_canvas, tearoff=0)
    _token_menu.add_command(label="Show Portrait", command=lambda: show_portrait(_menu_token_id))
    _token_menu.add_separator()
    _token_menu.add_command(label="Delete Token", command=lambda: delete_token(_menu_token_id))

def _center_view_on_click(event):
    """
    Recenters the view so that the point you middle‐click (or long‐press)
    ends up in the exact center of the canvas.
    """
    # 1) Canvas size in pixels
    canvas_w = map_canvas.winfo_width()
    canvas_h = map_canvas.winfo_height()

    # 2) Full map size *after* zoom
    zoomed_w = int(gm_view_size[0] * map_zoom)
    zoomed_h = int(gm_view_size[1] * map_zoom)

    # 3) Figure out how much you *can* scroll
    scrollable_w = max(0, zoomed_w - canvas_w)
    scrollable_h = max(0, zoomed_h - canvas_h)

    # 4) World‐coords under the mouse
    world_x = map_canvas.canvasx(event.x)
    world_y = map_canvas.canvasy(event.y)

    # 5) Desired top‐left so that world_x/world_y is centered
    target_x = world_x - canvas_w // 2
    target_y = world_y - canvas_h // 2

    # 6) Clamp to [0 … scrollable]
    target_x = min(max(target_x, 0), scrollable_w)
    target_y = min(max(target_y, 0), scrollable_h)

    # 7) Convert to “fractions” of the *entire* scrollregion
    fx = target_x / float(zoomed_w) if zoomed_w else 0.0
    fy = target_y / float(zoomed_h) if zoomed_h else 0.0

    # 8) Scroll!
    map_canvas.xview_moveto(fx)
    map_canvas.yview_moveto(fy)

    # 9) Finally, reposition your base & mask so they stay aligned
    off_x = map_canvas.canvasx(0)
    off_y = map_canvas.canvasy(0)
    map_canvas.coords(_base_id, -off_x, -off_y)
    map_canvas.coords(_mask_id, -off_x, -off_y)

    print(f"[CENTER] mouse_world=({world_x:.1f}, {world_y:.1f})")
    print(f"[CENTER] scrollable=({scrollable_w},{scrollable_h}), "
        f"target=({target_x:.1f},{target_y:.1f}), fx={fx:.4f}, fy={fy:.4f}")

def _on_zoom(event):
    global map_zoom, map_base_tk, map_mask_tk

    delta = getattr(event, "delta", None)
    if delta is None:
        delta = 1 if event.num == 4 else -1
    factor = 1.1 if delta > 0 else 0.9
    new_zoom = map_zoom * factor

    # Canvas and image dimensions
    canvas_w = map_canvas.winfo_width()
    canvas_h = map_canvas.winfo_height()
    base_w, base_h = gm_view_size
    zoomed_w, zoomed_h = int(base_w * new_zoom), int(base_h * new_zoom)

    # Get world coords under mouse BEFORE zoom
    mouse_world_x = map_canvas.canvasx(event.x) / map_zoom
    mouse_world_y = map_canvas.canvasy(event.y) / map_zoom

    # Resize map and mask
    map_base_tk = ImageTk.PhotoImage(map_base_orig.resize((zoomed_w, zoomed_h), Image.LANCZOS))
    map_mask_tk = ImageTk.PhotoImage(map_mask_orig.resize((zoomed_w, zoomed_h), Image.NEAREST))
    map_canvas.itemconfig(_base_id, image=map_base_tk)
    map_canvas.itemconfig(_mask_id, image=map_mask_tk)

    # Resize/move tokens
    for t in _tokens:
        x, y = t["x"], t["y"]
        map_canvas.coords(t["id"], x * new_zoom, y * new_zoom)
        resized = t["orig_pil"].resize(
            (int(t["orig_pil"].width * new_zoom), int(t["orig_pil"].height * new_zoom)),
            Image.LANCZOS
        )
        t["pil"] = resized
        t["tk"] = ImageTk.PhotoImage(resized)
        map_canvas.itemconfig(t["id"], image=t["tk"])

    # Update scroll region
    map_canvas.config(scrollregion=(0, 0, zoomed_w, zoomed_h))

    # New target: center the zoomed image on mouse_world_x/y
    center_x = (mouse_world_x * new_zoom) - (canvas_w // 2)
    center_y = (mouse_world_y * new_zoom) - (canvas_h // 2)

    # Clamp scroll to valid range
    max_x = max(0, zoomed_w - canvas_w)
    max_y = max(0, zoomed_h - canvas_h)
    scroll_x = min(max(center_x, 0), max_x)
    scroll_y = min(max(center_y, 0), max_y)

    fx = scroll_x / zoomed_w
    fy = scroll_y / zoomed_h
    map_canvas.xview_moveto(fx)
    map_canvas.yview_moveto(fy)

    # Update image position
    offset_x = map_canvas.canvasx(0)
    offset_y = map_canvas.canvasy(0)
    map_canvas.coords(_base_id, offset_x, offset_y)
    map_canvas.coords(_mask_id, offset_x, offset_y)

    map_zoom = new_zoom

    if _current_map:
        _update_fullscreen_map(_current_map, marker_world=_marker_pos)

    print(f"[ZOOM] zoom={map_zoom:.3f}, mouse_world=({mouse_world_x:.1f}, {mouse_world_y:.1f})")
    print(f"[ZOOM] center_on=({center_x:.1f}, {center_y:.1f}) → fx={fx:.4f}, fy={fy:.4f}")
    print(f"[ZOOM] canvas offset = ({offset_x:.1f}, {offset_y:.1f})")
    

def _on_paint(evt):
    """
    Paint (add/remove fog) at the mouse position.
    """
    global map_mask_draw, map_mask_tk
    x = map_canvas.canvasx(evt.x)
    y = map_canvas.canvasy(evt.y)
    r = map_brush_size
    if _self.map_mode == "add":
        xy = [x - r/2, y - r/2, x + r/2, y + r/2]
        if map_brush_shape == "Circle":
            map_mask_draw.ellipse(xy, fill=(0,0,0,0))
        else:
            map_mask_draw.rectangle(xy, fill=(0,0,0,0))
    else:
        xy = [x - r/2, y - r/2, x + r/2, y + r/2]
        if map_brush_shape == "Circle":
            map_mask_draw.ellipse(xy, fill=(0,0,0,255))
        else:
            map_mask_draw.rectangle(xy, fill=(0,0,0,255))
    map_mask_tk = ImageTk.PhotoImage(map_mask_img)
    map_canvas.itemconfig(_mask_id, image=map_mask_tk)

def on_token_right_click(evt):
    """
    Show context menu for tokens.
    """
    global _menu_token_id
    clicked = map_canvas.find_closest(evt.x, evt.y)
    if clicked and "token" in map_canvas.gettags(clicked[0]):
        _menu_token_id = clicked[0]
        _token_menu.post(evt.x_root, evt.y_root)

def delete_token(token_id):
    """
    Remove a token image and its record.
    """
    global _tokens, _current_map
    tok = next(t for t in _tokens if t["id"] == token_id)
    map_canvas.delete(token_id)
    _tokens = [t for t in _tokens if t["id"] != token_id]
    _current_map["Tokens"] = [r for r in _current_map["Tokens"]
                              if not (r["path"] == tok["path"]
                                      and r["x"] == tok["x"]
                                      and r["y"] == tok["y"])]

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


def _ensure_fog_mask(item):
    """
    Ensure the FogMaskPath exists; create and save if missing.
    """
    global _self, _maps
    img  = item.get("Image", "")
    mask = item.get("FogMaskPath", "")
    if not mask or not os.path.isfile(mask):
        base = Image.open(img)
        m    = Image.new("RGBA", base.size, (0,0,0,128))
        os.makedirs("masks", exist_ok=True)
        safe = item["Name"].replace(" ", "_")
        mask = os.path.join("masks", f"{safe}_mask.png")
        m.save(mask)
        item["FogMaskPath"] = mask
        _self.maps_wrapper.save_items(list(_maps.values()))
    return mask

def _begin_marker(evt):
    """
    On press: schedule a long-press after 500 ms,
    storing the click in world-coords into the global.
    """
    global _marker_pos, _marker_after_id

    # record the world-coords immediately
    _marker_pos = (
        map_canvas.canvasx(evt.x),
        map_canvas.canvasy(evt.y)
    )
    # schedule the marker to appear in half a second
    _marker_after_id = map_canvas.after(500, _show_marker)
    
def _save_fog_mask(item):
    """
    Save fog mask and persist map (including Tokens).
    """
    global map_mask_img
    if map_mask_img is None:
        messagebox.showerror("Error", "No mask to save.")
        return
    orig    = Image.open(item["Image"])
    tosave  = map_mask_img.resize(orig.size, Image.NEAREST)
    tosave.save(item["FogMaskPath"])
    _self.maps_wrapper.save_items(list(_maps.values()))
    _update_fullscreen_map(item)
    if _fullscreen_win and _fullscreen_win.winfo_exists():
        _fullscreen_win.update_idletasks()


def _show_fullscreen_map(item):
    """
    Open (or reposition) a fullscreen mirror window on the 2nd monitor,
    then draw it once by calling _update_fullscreen_map().
    """
    global _fullscreen_win, _fullscreen_label, _fullscreen_photo

    # if it already exists, just refresh
    if _fullscreen_win and _fullscreen_win.winfo_exists():
        _update_fullscreen_map(item)
        return

    # pick monitor tuple (x_off,y_off,width,height)
    mons = _get_monitors()
    mon = mons[1] if len(mons) > 1 else mons[0]
    x_off, y_off, sw, sh = mon

    # create borderless fullscreen window
    _fullscreen_win = tk.Toplevel(_self)
    _fullscreen_win.overrideredirect(True)
    _fullscreen_win.geometry(f"{sw}x{sh}+{x_off}+{y_off}")
    _fullscreen_label = tk.Label(_fullscreen_win, bg="black")
    _fullscreen_label.pack(fill="both", expand=True)

    # initial draw
    _update_fullscreen_map(item)


def _update_fullscreen_map(item, marker_world=None):
    """
    Rebuild the fullscreen image by:
      1) compositing base + tokens at zoomed “world” size,
      2) overlaying the current fog mask as fully opaque,
      3) cropping a sw×sh rectangle centered at the GM‐canvas center,
      4) letterboxing that crop into a sw×sh black canvas,
      5) drawing an optional red marker at marker_world.
    """
    global _fullscreen_photo, _marker_pos

    # If caller didn’t pass a marker, fall back to the last one
    if marker_world is None:
        marker_world = _marker_pos

    # Bail if the fullscreen window is closed
    if not (_fullscreen_win and _fullscreen_win.winfo_exists()):
        return

    # 1) Build the zoomed “world” at GM‐canvas resolution
    gm_w, gm_h = gm_view_size
    wz, hz     = int(gm_w * map_zoom), int(gm_h * map_zoom)

    # resize base map
    base_z = map_base_orig.resize((wz, hz), Image.LANCZOS)

    # draw tokens onto transparent layer
    token_layer = Image.new("RGBA", (wz, hz), (0, 0, 0, 0))
    for t in _tokens:
        ox = int(t["x"] * map_zoom)
        oy = int(t["y"] * map_zoom)
        img_z = t["orig_pil"].resize(
            (int(t["orig_pil"].width  * map_zoom),
             int(t["orig_pil"].height * map_zoom)),
            Image.LANCZOS
        )
        token_layer.paste(img_z,
                          (ox - img_z.width//2, oy - img_z.height//2),
                          img_z)

    comp = Image.alpha_composite(base_z.convert("RGBA"), token_layer)

    # 2) Overlay the current fog mask as fully opaque
    mask_resized = map_mask_img.resize((wz, hz), Image.NEAREST)
    alpha = mask_resized.split()[3].point(lambda p: 255 if p > 0 else 0)
    opaque_mask = Image.new("RGBA", (wz, hz), (0, 0, 0, 255))
    opaque_mask.putalpha(alpha)
    full = Image.alpha_composite(comp, opaque_mask).convert("RGB")

    # 3) Crop a sw×sh rectangle around the GM‐canvas center
    cw, ch = map_canvas.winfo_width(), map_canvas.winfo_height()
    cx = map_canvas.canvasx(cw / 2)
    cy = map_canvas.canvasy(ch / 2)

    mons = _get_monitors()
    mon  = mons[1] if len(mons) > 1 else mons[0]
    sw, sh = mon[2], mon[3]

    left = int(cx - sw / 2)
    top  = int(cy - sh / 2)
    left = max(0, min(left, wz - sw))
    top  = max(0, min(top, hz - sh))

    viewport = full.crop((left, top, left + sw, top + sh))

    # 4) Letterbox into a sw×sh black canvas
    canvas_img = Image.new("RGB", (sw, sh), (0, 0, 0))
    pw, ph = viewport.size
    px, py = (sw - pw) // 2, (sh - ph) // 2
    canvas_img.paste(viewport, (px, py))

    # 5) Draw optional red marker
    if marker_world:
        wx, wy = marker_world
        # compute marker position in the cropped image:
        mx = int((wx ) - left) + px
        my = int((wy ) - top)  + py
        r  = int(20 * map_zoom)
        print(f"Marker at {marker_world} -> {mx},{my} ({r})")
        print(f"Zomm factor: {map_zoom}")
        draw = ImageDraw.Draw(canvas_img)
        draw.ellipse([mx - r, my - r, mx + r, my + r], outline="red", width=4)

    # Swap in the new image
    photo = ImageTk.PhotoImage(canvas_img)
    _fullscreen_photo = photo
    _fullscreen_label.config(image=photo)
    _fullscreen_label.image = photo




