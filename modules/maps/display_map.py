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
# Now tracking each token’s original PIL for zooming:
_tokens           = []  # each: { "id", "orig_pil", "pil", "tk", "path", "x", "y" }
_current_drag     = None             # holds token being dragged
map_canvas        = None
map_base_tk       = None
map_mask_img      = None             # painted mask (scaled for GM)
map_mask_draw     = None
map_mask_tk       = None
map_mask_pil      = None             # fit-to-screen unpainted mask
map_mask_orig     = None             # pristine full-res mask
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
_base_id          = None             # canvas item ID for the base map image

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
        (icons["clear"], "Clear Mask", lambda: _clear_mask()),
        (icons["reset"], "Reset Mask", lambda: _reset_mask()),
        (icons["save"],  "Save Mask",  lambda: _save_fog_mask(item)),
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

    # canvas + scrollbars
    scroll_f = ctk.CTkFrame(container)
    scroll_f.pack(fill="both", expand=True)
    v_scroll = tk.Scrollbar(scroll_f, orient="vertical")
    h_scroll = tk.Scrollbar(scroll_f, orient="horizontal")
    v_scroll.pack(side="right", fill="y")
    h_scroll.pack(side="bottom", fill="x")

    canvas = tk.Canvas(scroll_f, width=w, height=h,
                       xscrollcommand=h_scroll.set,
                       yscrollcommand=v_scroll.set)
    h_scroll.config(command=canvas.xview)
    v_scroll.config(command=canvas.yview)
    canvas.pack(side="left", fill="both", expand=True)

    # draw base & mask, keep their IDs
    map_base_tk = ImageTk.PhotoImage(base)
    _base_id    = canvas.create_image(0, 0, anchor=tk.NW, image=map_base_tk)

    map_mask_img  = mask_scaled
    map_mask_draw = ImageDraw.Draw(map_mask_img)
    map_mask_tk   = ImageTk.PhotoImage(map_mask_img)
    _mask_id      = canvas.create_image(0, 0, anchor=tk.NW, image=map_mask_tk)

    map_canvas = canvas

    # token bindings
    canvas.tag_bind("token", "<ButtonPress-1>",    on_token_press)
    canvas.tag_bind("token", "<B1-Motion>",       on_token_move)
    canvas.tag_bind("token", "<ButtonRelease-1>", on_token_release)
    canvas.tag_bind("token", "<ButtonRelease-3>", on_token_right_click)
    # zoom with Ctrl+wheel
    canvas.bind("<Control-MouseWheel>", _on_zoom)
    canvas.bind("<Control-Button-4>",   _on_zoom)
    canvas.bind("<Control-Button-5>",   _on_zoom)

    # painting bindings
    canvas.bind("<Button-1>",    _on_paint)
    canvas.bind("<B1-Motion>",   _on_paint)

    canvas.config(scrollregion=(0, 0, w, h))

    # spawn saved tokens
    _tokens.clear()
    for rec in item["Tokens"]:
        add_token_to_canvas(rec["path"], rec["x"], rec["y"], persist=False)

    global _token_menu
    _token_menu = tk.Menu(map_canvas, tearoff=0)
    _token_menu.add_command(label="Show Portrait", command=lambda: show_token_portrait(_menu_token_id))
    _token_menu.add_separator()
    _token_menu.add_command(label="Delete Token", command=lambda: delete_token(_menu_token_id))


def _on_zoom(event):
    """
    True zoom: resize the base map & the CURRENT mask (map_mask_img),
    reposition tokens (both position & size), update canvas & mirror on second screen.
    """
    global map_zoom, map_base_tk, map_mask_tk

    # 1) Determine wheel direction
    delta = getattr(event, "delta", None)
    if delta is None:
        delta = 1 if event.num == 4 else -1
    factor = 1.1 if delta > 0 else 0.9
    map_zoom *= factor

    # 2) Compute new GM‐view size
    w0, h0 = gm_view_size
    wz, hz = int(w0 * map_zoom), int(h0 * map_zoom)

    # 3) RESAMPLE
    #    - map from pristine full-res original
    new_base = map_base_orig.resize((wz, hz), Image.LANCZOS)
    #    - mask from the CURRENT painted mask (so reveals persist)
    new_mask = map_mask_img.resize((wz, hz), Image.NEAREST)

    # 4) Update your PhotoImages
    map_base_tk = ImageTk.PhotoImage(new_base)
    map_mask_tk = ImageTk.PhotoImage(new_mask)
    map_canvas.itemconfig(_base_id, image=map_base_tk)
    map_canvas.itemconfig(_mask_id, image=map_mask_tk)

    # 5) Move each token to its scaled coord
    for t in _tokens:
        x0, y0 = t["x"], t["y"]
        map_canvas.coords(t["id"], x0 * map_zoom, y0 * map_zoom)

    # 6) ALSO rescale each token image
    for t in _tokens:
        orig = t["orig_pil"]
        w0, h0 = orig.size
        w1, h1 = max(1, int(w0 * map_zoom)), max(1, int(h0 * map_zoom))
        resized = orig.resize((w1, h1), Image.LANCZOS)
        tk_new = ImageTk.PhotoImage(resized)
        t["pil"] = resized
        t["tk"]  = tk_new
        map_canvas.itemconfig(t["id"], image=tk_new)

    # 7) Expand scrollregion for panning
    map_canvas.config(scrollregion=(0, 0, wz, hz))

    # 8) Mirror to fullscreen if active
    if _current_map:
        _update_fullscreen_map(_current_map)

    return "break"


def show_token_portrait(token_id):
    """
    Look up the token’s image path and pop up a full‐screen portrait.
    """
    tok = next((t for t in _tokens if t["id"] == token_id), None)
    if not tok:
        messagebox.showerror("Error", "Token not found.")
        return
    show_portrait(tok["path"])


def on_token_right_click(evt):
    """
    Show context menu when right-clicking a token.
    """
    global _menu_token_id
    clicked = map_canvas.find_closest(evt.x, evt.y)
    if clicked and "token" in map_canvas.gettags(clicked[0]):
        _menu_token_id = clicked[0]
        _token_menu.tk_popup(evt.x_root, evt.y_root)


def delete_token(token_id):
    """
    Remove a token from both the canvas and the map data.
    """
    global _tokens, _current_map
    tok = next((t for t in _tokens if t["id"] == token_id), None)
    if not tok:
        return
    map_canvas.delete(token_id)
    _tokens.remove(tok)
    recs = _current_map.get("Tokens", [])
    match = next((r for r in recs
                  if r["path"] == tok["path"]
                     and r["x"]    == tok["x"]
                     and r["y"]    == tok["y"]), None)
    if match:
        recs.remove(match)


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


def _on_paint(event):
    global map_mask_img, map_mask_draw, map_mask_tk, map_canvas, _mask_id
    mode = getattr(_self, "map_mode", None)
    if mode not in ("add", "remove"):
        return
    x = map_canvas.canvasx(event.x)
    y = map_canvas.canvasy(event.y)
    for item in map_canvas.find_overlapping(x, y, x, y):
        if "token" in map_canvas.gettags(item):
            return "break"
    r = map_brush_size
    c = (0,0,0,128) if mode=="add" else (0,0,0,0)
    if map_brush_shape == "Circle":
        map_mask_draw.ellipse([(x-r, y-r), (x+r, y+r)], fill=c)
    else:
        map_mask_draw.rectangle([(x-r, y-r), (x+r, y+r)], fill=c)
    map_mask_tk = ImageTk.PhotoImage(map_mask_img)
    map_canvas.itemconfig(_mask_id, image=map_mask_tk)
    return "break"


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
    1) Composite map, tokens, and fog at the map’s original resolution.
    2) Then zoom/crop to fill the second monitor.
    """
    global _fullscreen_win, _fullscreen_label, _fullscreen_photo

    # 1. Prepare original-resolution layers
    base_orig = Image.open(item["Image"]).convert("RGBA")
    mask_orig = Image.open(item["FogMaskPath"]).convert("RGBA")

    # Build token layer at ORIGINAL size (use orig_pil, not the zoomed one)
    token_layer = Image.new("RGBA", base_orig.size, (0,0,0,0))
    gm_w, gm_h   = map_mask_img.size
    ow, oh       = base_orig.size
    sx, sy       = ow / gm_w, oh / gm_h
    for t in _tokens:
        orig = t["orig_pil"]
        w0, h0 = orig.size
        x_o = int(t["x"] * sx - w0/2)
        y_o = int(t["y"] * sy - h0/2)
        token_layer.paste(orig, (x_o, y_o), orig)

    comp1 = Image.alpha_composite(base_orig, token_layer)

    # Build fully-opaque fog mask at ORIGINAL size
    mask0  = mask_orig.resize(base_orig.size, Image.NEAREST)
    alpha0 = mask0.split()[3].point(lambda p: 255 if p>0 else 0)
    mask_full = Image.new("RGBA", base_orig.size, (0,0,0,255))
    mask_full.putalpha(alpha0)

    final_orig = Image.alpha_composite(comp1, mask_full).convert("RGB")

    # 2. Zoom & crop/letterbox
    sx_mon, sy_mon, sw, sh = (_get_monitors()[1] if len(_get_monitors())>1 else _get_monitors()[0])
    if map_zoom != 1.0:
        swz, shz = int(sw * map_zoom), int(sh * map_zoom)
        zoomed   = final_orig.resize((swz, shz), Image.LANCZOS)
        if map_zoom > 1.0:
            left = (swz - sw)//2
            top  = (shz - sh)//2
            final = zoomed.crop((left, top, left+sw, top+sh))
        else:
            canvas_img = Image.new("RGB", (sw, sh), (0,0,0))
            px, py     = (sw - swz)//2, (sh - shz)//2
            canvas_img.paste(zoomed, (px, py))
            final = canvas_img
    else:
        final = final_orig.resize((sw, sh), Image.LANCZOS)

    # Display
    photo = ImageTk.PhotoImage(final)
    win   = ctk.CTkToplevel(); win.overrideredirect(True)
    win.geometry(f"{sw}x{sh}+{sx_mon}+{sy_mon}")

    _fullscreen_photo = photo
    _fullscreen_label = tk.Label(win, image=photo, bg="black")
    _fullscreen_label.image = photo
    _fullscreen_label.pack(fill="both", expand=True)
    win.bind("<Button-1>", lambda e: win.destroy())
    _fullscreen_win = win


def _update_fullscreen_map(item):
    """
    Exactly the same pipeline as _show_fullscreen_map,
    but swaps in a new PhotoImage on the existing window.
    """
    if not (_fullscreen_win and _fullscreen_win.winfo_exists()):
        return

    # 1. Build composite at original resolution
    base_orig = Image.open(item["Image"]).convert("RGBA")
    mask_orig = Image.open(item["FogMaskPath"]).convert("RGBA")

    token_layer = Image.new("RGBA", base_orig.size, (0,0,0,0))
    gm_w, gm_h   = map_mask_img.size
    ow, oh       = base_orig.size
    sx, sy       = ow / gm_w, oh / gm_h
    for t in _tokens:
        orig = t["orig_pil"]
        w0, h0 = orig.size
        x_o = int(t["x"] * sx - w0/2)
        y_o = int(t["y"] * sy - h0/2)
        token_layer.paste(orig, (x_o, y_o), orig)

    comp1 = Image.alpha_composite(base_orig, token_layer)

    mask0  = mask_orig.resize(base_orig.size, Image.NEAREST)
    alpha0 = mask0.split()[3].point(lambda p: 255 if p>0 else 0)
    mask_full = Image.new("RGBA", base_orig.size, (0,0,0,255))
    mask_full.putalpha(alpha0)
    final_orig = Image.alpha_composite(comp1, mask_full).convert("RGB")

    # 2. Zoom & crop/letterbox
    sx_mon, sy_mon, sw, sh = (_get_monitors()[1] if len(_get_monitors())>1 else _get_monitors()[0])
    if map_zoom != 1.0:
        swz, shz = int(sw * map_zoom), int(sh * map_zoom)
        zoomed   = final_orig.resize((swz, shz), Image.LANCZOS)
        if map_zoom > 1.0:
            left, top = (swz-sw)//2, (shz-sh)//2
            final = zoomed.crop((left, top, left+sw, top+sh))
        else:
            canvas_img = Image.new("RGB", (sw, sh), (0,0,0))
            px, py     = (sw-swz)//2, (sh-shz)//2
            canvas_img.paste(zoomed, (px, py))
            final = canvas_img
    else:
        final = final_orig.resize((sw, sh), Image.LANCZOS)

    # Swap in the new image
    new_photo = ImageTk.PhotoImage(final)
    _fullscreen_photo = new_photo
    _fullscreen_label.config(image=new_photo)
    _fullscreen_label.image = new_photo
