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
_current_map = None
_self = None
_token_menu = None
_menu_token_id = None
_maps = {}
_tokens = []               # each: { "id", "pil", "tk", "path", "x", "y" }
_current_drag = None       # holds token being dragged
map_canvas = None
map_base_tk = None
map_mask_img = None        # holds the SCALED mask for GM editing
map_mask_draw = None
map_mask_tk = None
map_brush_size = 30
map_brush_shape = "Square" # "Circle" or "Square"
_mask_id = None
_fullscreen_win   = None
_fullscreen_label = None
_fullscreen_photo = None
_model_wrappers = {}
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
    Place a new 24×24 token at (x,y) or center if None.
    Records into both _tokens (live) and _current_map['Tokens'] (persistent).
    """
    global map_canvas, _mask_id, _tokens, _current_map

    # default coords = center
    w, h = map_canvas.winfo_width(), map_canvas.winfo_height()
    x = x if x is not None else w // 2
    y = y if y is not None else h // 2

    # load & border
    pil_img, tk_img = load_token_image(path)
    item_id = map_canvas.create_image(x, y, image=tk_img, tags=("token",))
    map_canvas.tag_raise(item_id, _mask_id)

    # record live
    _tokens.append({
        "id":   item_id,
        "pil":  pil_img,
        "tk":   tk_img,
        "path": path,
        "x":    x,
        "y":    y
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
    global _self, map_canvas, map_base_tk, map_mask_img, map_mask_draw, map_mask_tk, _mask_id, _current_map, _tokens

    setattr(_self, "map_mode", "remove")
    item = _maps.get(entity_name)
    if not item:
        messagebox.showwarning("Not Found", f"Map '{entity_name}' not found.")
        return

    # Persistence init
    _current_map = item
    # ensure Tokens is always a list, never None
    item["Tokens"] = item.get("Tokens") or []

    mask_path = _ensure_fog_mask(item)

    # clear UI
    container = _self.get_content_container()
    for w in container.winfo_children():
        w.destroy()

    # GM view size
    _self.update_idletasks()
    w, h = _self.winfo_width(), _self.winfo_height()

    # load & scale
    base = Image.open(item["Image"]).resize((w, h), Image.LANCZOS)
    mask_scaled = Image.open(mask_path).convert("RGBA").resize((w, h), Image.NEAREST)

    map_base_tk   = ImageTk.PhotoImage(base)
    map_mask_img  = mask_scaled
    map_mask_draw = ImageDraw.Draw(map_mask_img)
    map_mask_tk   = ImageTk.PhotoImage(map_mask_img)

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

    canvas.create_image(0, 0, anchor=tk.NW, image=map_base_tk)
    _mask_id = canvas.create_image(0, 0, anchor=tk.NW, image=map_mask_tk)
    map_canvas = canvas

    # token bindings
    canvas.tag_bind("token", "<ButtonPress-1>",    on_token_press)
    canvas.tag_bind("token", "<B1-Motion>",       on_token_move)
    canvas.tag_bind("token", "<ButtonRelease-1>", on_token_release)
    canvas.tag_bind("token", "<ButtonRelease-3>", on_token_right_click)

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
def show_token_portrait(token_id):
    """
    Look up the token’s image path and pop up a full‐screen portrait.
    """
    # find the token record
    tok = next((t for t in _tokens if t["id"] == token_id), None)
    if not tok:
        messagebox.showerror("Error", "Token not found.")
        return

    path = tok["path"]
    # Use the same full‐screen viewer as NPCGraphEditor does :contentReference[oaicite:2]{index=2}:contentReference[oaicite:3]{index=3}
    show_portrait(path)
    
def on_token_right_click(evt):
    """
    Show context menu when right-clicking a token.
    """
    global _menu_token_id
    clicked = map_canvas.find_closest(evt.x, evt.y)
    if clicked and "token" in map_canvas.gettags(clicked[0]):
        _menu_token_id = clicked[0]
        # popup at mouse position
        _token_menu.tk_popup(evt.x_root, evt.y_root)

def delete_token(token_id):
    """
    Remove a token from both the canvas and the map data.
    """
    global _tokens, _current_map

    # find the token entry
    tok = next((t for t in _tokens if t["id"] == token_id), None)
    if not tok:
        return

    # remove from canvas
    map_canvas.delete(token_id)
    # remove from live list
    _tokens.remove(tok)
    # remove from persistent map data
    recs = _current_map.get("Tokens", [])
    # find a matching record by path & coords
    match = next((r for r in recs
                  if r["path"] == tok["path"]
                     and r["x"] == tok["x"]
                     and r["y"] == tok["y"]), None)
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
    img = item.get("Image", "")
    mask = item.get("FogMaskPath", "")
    if not mask or not os.path.isfile(mask):
        base = Image.open(img)
        m = Image.new("RGBA", base.size, (0,0,0,128))
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
    # skip tokens
    for item in map_canvas.find_overlapping(x, y, x, y):
        if "token" in map_canvas.gettags(item):
            return "break"

    r = map_brush_size
    c = (0,0,0,128) if mode=="add" else (0,0,0,0)
    if map_brush_shape=="Circle":
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
    orig = Image.open(item["Image"])
    tosave = map_mask_img.resize(orig.size, Image.NEAREST)
    tosave.save(item["FogMaskPath"])
    _self.maps_wrapper.save_items(list(_maps.values()))
    _update_fullscreen_map(item)
    if _fullscreen_win and _fullscreen_win.winfo_exists():
        _fullscreen_win.update_idletasks()


def _show_fullscreen_map(item):
    """
    Scale map & original fog, draw tokens, then fog for players.
    """
    global _fullscreen_win, _fullscreen_label, _fullscreen_photo

    mons = _get_monitors()
    sx, sy, sw, sh = mons[1] if len(mons)>1 else mons[0]

    base_orig = Image.open(item["Image"]).convert("RGBA")
    mask_orig = Image.open(item["FogMaskPath"]).convert("RGBA")

    base_screen = base_orig.resize((sw, sh), Image.LANCZOS)
    mask_screen = mask_orig.resize((sw, sh), Image.NEAREST)

    token_layer = Image.new("RGBA", (sw, sh), (0,0,0,0))
    gm_w, gm_h = map_mask_img.size
    for t in _tokens:
        tx = int(t["x"]/gm_w * sw)
        ty = int(t["y"]/gm_h * sh)
        token_layer.paste(
            t["pil"],
            (tx - t["pil"].width//2, ty - t["pil"].height//2),
            t["pil"]
        )

    comp  = Image.alpha_composite(base_screen, token_layer)
    alpha = mask_screen.split()[3].point(lambda p:255 if p>0 else 0)
    fog   = Image.new("RGBA", (sw, sh), (0,0,0,255))
    fog.putalpha(alpha)
    final = Image.alpha_composite(comp, fog).convert("RGB")

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
    Refresh fullscreen view with updated fog and tokens.
    """
    if not (_fullscreen_win and _fullscreen_win.winfo_exists()):
        return

    mons = _get_monitors()
    sx, sy, sw, sh = mons[1] if len(mons)>1 else mons[0]

    base_orig = Image.open(item["Image"]).convert("RGBA")
    mask_orig = Image.open(item["FogMaskPath"]).convert("RGBA")

    base_screen = base_orig.resize((sw, sh), Image.LANCZOS)
    mask_screen = mask_orig.resize((sw, sh), Image.NEAREST)

    token_layer = Image.new("RGBA", (sw, sh), (0,0,0,0))
    gm_w, gm_h = map_mask_img.size
    for t in _tokens:
        tx = int(t["x"]/gm_w * sw)
        ty = int(t["y"]/gm_h * sh)
        token_layer.paste(
            t["pil"],
            (tx - t["pil"].width//2, ty - t["pil"].height//2),
            t["pil"]
        )

    comp  = Image.alpha_composite(base_screen, token_layer)
    alpha = mask_screen.split()[3].point(lambda p:255 if p>0 else 0)
    fog   = Image.new("RGBA", (sw, sh), (0,0,0,255))
    fog.putalpha(alpha)
    final = Image.alpha_composite(comp, fog).convert("RGB")

    new_photo = ImageTk.PhotoImage(final)
    _fullscreen_photo = new_photo
    _fullscreen_label.config(image=new_photo)
    _fullscreen_label.image = new_photo
