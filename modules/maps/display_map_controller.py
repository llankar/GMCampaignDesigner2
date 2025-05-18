# display_map_controller.py

import os
import ast
import json
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, colorchooser
from PIL import Image, ImageTk, ImageDraw
from modules.ui.image_viewer import show_portrait
from modules.generic.generic_list_selection_view import GenericListSelectionView
from modules.generic.generic_model_wrapper import GenericModelWrapper
from modules.ui.icon_button import create_icon_button
from screeninfo import get_monitors
from modules.helpers.template_loader import load_template

DEFAULT_BRUSH_SIZE = 32  # px
MASKS_DIR = os.path.join(os.getcwd(), "masks")
MAX_ZOOM = 3.0
MIN_ZOOM = 0.1
ZOOM_STEP = 0.1  # 10% per wheel notch
ctk.set_appearance_mode("dark")

class DisplayMapController:
    def __init__(self, parent, maps_wrapper, map_template):
        self.parent = parent
        self.maps = maps_wrapper
        self.map_template = map_template
        
        self._model_wrappers = {
            "NPC":      GenericModelWrapper("npcs"),
            "Creature": GenericModelWrapper("creatures"),
        }
        self._templates = {
            "NPC":      load_template("npcs"),
            "Creature": load_template("creatures")
        }
        # --- State ---
        self.current_map = None
        self.base_img    = None
        self.mask_img    = None
        self.base_tk     = None
        self.mask_tk     = None
        self.base_id     = None
        self.mask_id     = None
        self._zoom_after_id = None
        self._fast_resample = Image.BILINEAR   # interactive filter
        self.zoom        = 1.0
        self.pan_x       = 0
        self.pan_y       = 0

        self.brush_size  = DEFAULT_BRUSH_SIZE
        self.brush_shape = "rectangle"  # new: "rectangle" or "circle"
        self.fog_mode    = "add"    # "add" or "rem"
        self.tokens      = []       # list of token dicts

        # Panning state
        self._panning      = False
        self._last_mouse   = (0, 0)
        self._orig_pan     = (0, 0)

        # Long‐press marker
        self._marker_after_id = None
        self._marker_start    = None
        self._marker_id       = None
        self._fs_marker_id    = None

        # Fullscreen mirror
        self.fs            = None
        self.fs_canvas     = None
        self.fs_base_id    = None
        self.fs_mask_id    = None

        # Build a name→map record dict for quick lookup
        self._maps = {m["Name"]: m for m in maps_wrapper.load_items()}

        # Begin by selecting a map
        self.select_map()

    def select_map(self):
        """Show the full‐frame map selector, replacing any existing UI."""
        for w in self.parent.winfo_children():
            w.destroy()

        selector = GenericListSelectionView(
            self.parent,
            "maps",
            self.maps,
            self.map_template,
            on_select_callback=self._on_display_map
        )
        selector.pack(fill="both", expand=True)

    def _on_display_map(self, entity_type, map_name):
        """Callback from selector: build editor UI and load the chosen map."""
        # Lookup the chosen map record
        item = self._maps.get(map_name)
        if not item:
            messagebox.showwarning("Not Found", f"Map '{map_name}' not found.")
            return
        self.current_map = item

        # Clear selector
        for w in self.parent.winfo_children():
            w.destroy()

        # Build toolbar + canvas
        self._build_toolbar()
        self._build_canvas()

        # Load images
        img_path = item["Image"]
        self.base_img = Image.open(img_path).convert("RGBA")

        mask_path = item.get("FogMaskPath", "")
        if mask_path and os.path.exists(mask_path):
            self.mask_img = Image.open(mask_path).convert("RGBA")
        else:
            self.mask_img = Image.new("RGBA", self.base_img.size, (0,0,0,128))

        # Reset view
        self.zoom  = 1.0
        self.pan_x = 0
        self.pan_y = 0

        # Clear any existing tokens
        for t in self.tokens:
            for cid in t.get("canvas_ids", []):
                self.canvas.delete(cid)
            if self.fs_canvas and "fs_canvas_ids" in t:
                for cid in t["fs_canvas_ids"]:
                    self.fs_canvas.delete(cid)
        self.tokens = []

        # Load persisted tokens (Python‐repr list of dicts)
        raw = item.get("Tokens", [])
        # Normalize into a Python list of dicts
        if isinstance(raw, str):
            # old-style single-quoted repr or JSON
            raw = raw.strip()
            if raw:
                    try:
                            token_list = ast.literal_eval(raw)
                    except (SyntaxError, ValueError):
                            try:
                                    token_list = json.loads(raw)
                            except Exception:
                                    token_list = []
            else:
                token_list = []
        elif isinstance(raw, list):
            token_list = raw
        else:
            token_list = []
        for rec in token_list:
            path = rec.get("image_path") or rec.get("path")
            try:
                pil_img = Image.open(path).convert("RGBA")
                # resize to 48×48
                pil_img = pil_img.resize((48, 48), resample=Image.LANCZOS)
            except Exception:
                continue
            # Position may be under rec["position"] or rec["x"],rec["y"]
            pos = rec.get("position")
            if isinstance(pos, (list, tuple)) and len(pos) >= 2:
                xw, yw = pos[0], pos[1]
            else:
                xw, yw = rec.get("x", 0), rec.get("y", 0)
            
            token = {
                "entity_type": rec.get("entity_type", "NPC"),
                "entity_id":   rec.get("entity_id"),
                "image_path":  path,
                "pil_image":   pil_img,
                "position":    (xw, yw),
                "border_color": rec.get("border_color", "#0000ff")
            }
            self.tokens.append(token)

        # Initial draw
        self._update_canvas_images()

    def _build_toolbar(self):    
        # use a dark‐mode CTkFrame for the toolbar
        toolbar = ctk.CTkFrame(self.parent) 
        toolbar.pack(side="top", fill="x")

        # Load icons
        icons = {
            "add":   self.load_icon("assets/icons/brush.png",    (48,48)),
            "rem":   self.load_icon("assets/icons/eraser.png",   (48,48)),
            "clear": self.load_icon("assets/icons/empty.png",    (48,48)),
            "reset": self.load_icon("assets/icons/full.png",     (48,48)),
            "save":  self.load_icon("assets/icons/save.png",     (48,48)),
            "fs":    self.load_icon("assets/icons/expand.png",   (48,48)),
            "npc":   self.load_icon("assets/icons/npc.png",      (48,48)),
            "creat": self.load_icon("assets/icons/creature.png", (48,48)),
        }

        # Fog controls
        create_icon_button(toolbar, icons["add"],   "Add Fog",     command=lambda: self._set_fog("add")).pack(side="left")
        create_icon_button(toolbar, icons["rem"],   "Remove Fog",  command=lambda: self._set_fog("rem")).pack(side="left")
        create_icon_button(toolbar, icons["clear"], "Clear Fog",   command=self.clear_fog).pack(side="left")
        create_icon_button(toolbar, icons["reset"], "Reset Fog",   command=self.reset_fog).pack(side="left")
        create_icon_button(toolbar, icons["save"],  "Save Map",    command=self.save_map).pack(side="left")

        # Token controls and fullscreen before the brush size
        create_icon_button(toolbar, icons["creat"], "Add Creature", command=lambda: self.open_entity_picker("Creature"))\
            .pack(side="left", padx=2)
        create_icon_button(toolbar, icons["npc"],   "Add NPC",      command=lambda: self.open_entity_picker("NPC"))\
            .pack(side="left", padx=2)
        create_icon_button(toolbar, icons["fs"],    "Fullscreen",   command=self.open_fullscreen)\
            .pack(side="left", padx=2)

        # Brush shape selector
        shape_label = ctk.CTkLabel(toolbar, text="Shape:")
        shape_label.pack(side="left", padx=(10,2), pady=8)
        self.shape_menu = ctk.CTkOptionMenu(
            toolbar,
            values=["Rectangle", "Circle"],
            command=self._on_brush_shape_change
        )
        self.shape_menu.set("Rectangle")
        self.shape_menu.pack(side="left", padx=5, pady=8)
        
        # Brush‐size control in dark mode
        size_label = ctk.CTkLabel(toolbar, text="Brush Size:")
        size_label.pack(side="left", padx=(10,2), pady=8)
        self.brush_slider = ctk.CTkSlider(
            toolbar, from_=4, to=128,
            command=self._on_brush_size_change
        )
        self.brush_slider.set(self.brush_size)
        self.brush_slider.pack(side="left", padx=5, pady=8)

        # Key bindings for bracket adjustments
        self.parent.bind("[", lambda e: self._change_brush(-4))
        self.parent.bind("]", lambda e: self._change_brush(+4))
        
    def _on_brush_shape_change(self, val):
        # normalize to lowercase for comparisons
        self.brush_shape = val.lower()
        
    def _build_canvas(self):
        self.canvas = tk.Canvas(self.parent, bg="black")
        self.canvas.pack(fill="both", expand=True)

        # Painting, panning, markers
        self.canvas.bind("<ButtonPress-1>",    self._on_mouse_down)
        self.canvas.bind("<B1-Motion>",        self._on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>",  self._on_mouse_up)
        self.canvas.bind("<ButtonPress-2>",    self._on_middle_click)
        # Zoom & resize
        self.canvas.bind("<MouseWheel>",       self.on_zoom)
        self.parent.bind("<Configure>",        lambda e: self._update_canvas_images())

    def load_icon(self, path, size=(32,32)):
        #Load & resize with PIL
        pil_img = Image.open(path).resize(size, resample=Image.LANCZOS)
        # Wrap in a CTkImage so CustomTkinter buttons get the right type
        return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)

    def _set_fog(self, mode):
        self.fog_mode = mode

    def clear_fog(self):
        self.mask_img = Image.new("RGBA", self.base_img.size, (0,0,0,0))
        self._update_canvas_images()

    def reset_fog(self):
        self.mask_img = Image.new("RGBA", self.base_img.size, (0, 0, 0, 128))
        self._update_canvas_images()

    def save_map(self):
        """Save the current fog mask to disk and persist the path."""
        os.makedirs(MASKS_DIR, exist_ok=True)
        fname     = os.path.basename(self.current_map["Image"])
        mask_path = os.path.join(MASKS_DIR, fname)
        # ensure we’re using a .png so we can preserve alpha
        base, ext = os.path.splitext(mask_path or "")
        if not ext.lower() in (".png",):
            # if no path or wrong ext, switch to PNG
            base = base or os.path.splitext(self.current_map["ImagePath"])[0]
            mask_path = base + "_mask.png"
            self.current_map["FogMaskPath"] = mask_path

        os.makedirs(os.path.dirname(mask_path), exist_ok=True)
        # save with explicit PNG format to keep RGBA channel
        self.mask_img.save(mask_path, format="PNG")

        # Update in-memory record
        self.current_map["FogMaskPath"] = mask_path

        # Persist *all* maps via save_items
        all_maps = list(self._maps.values())
        self.maps.save_items(all_maps)
        # Now that fog (and any moved tokens) are final, refresh the second‐screen view
        # only if that window (and its canvas) still exist:
        try:
            if getattr(self, 'fs', None) and self.fs.winfo_exists() \
                and getattr(self, 'fs_canvas', None) and self.fs_canvas.winfo_exists():
                self._update_fullscreen_map()
        except tk.TclError:
            # second‐screen has been closed or destroyed—ignore
            pass

    def _on_brush_size_change(self, val):
        try:
            self.brush_size = int(val)
        except ValueError:
            pass

    def _change_brush(self, delta):
        new = max(4, min(128, self.brush_size + delta))
        self.brush_size = new
        self.brush_slider.set(new)

    def on_paint(self, event):
        """Paint or erase fog using a square brush of size self.brush_size,
           with semi-transparent black (alpha=128) for fog."""
        if any('drag_data' in t for t in self.tokens):
            return
        if not self.mask_img:
            return

        # Convert screen → world coords
        xw = (event.x - self.pan_x) / self.zoom
        yw = (event.y - self.pan_y) / self.zoom

        half = self.brush_size / 2
        left   = int(xw - half)
        top    = int(yw - half)
        right  = int(xw + half)
        bottom = int(yw + half)

        draw = ImageDraw.Draw(self.mask_img)
        if self.fog_mode == "add":
            # Paint semi-transparent black
            if self.brush_shape == "circle":
                draw.ellipse([left, top, right, bottom], fill=(0, 0, 0, 128))
            else:
                draw.rectangle([left, top, right, bottom], fill=(0, 0, 0, 128))
        else:
            # Erase (make fully transparent)
            if self.brush_shape == "circle":
                draw.ellipse([left, top, right, bottom], fill=(0, 0, 0,   0))
            else:
                draw.rectangle([left, top, right, bottom], fill=(0, 0, 0,   0))

        self._update_canvas_images()

    def _on_mouse_down(self, event):
        # If you clicked on a token, let its handlers take over:
        current = set(self.canvas.find_withtag("current"))
        token_ids = {cid for t in self.tokens for cid in t["canvas_ids"]}
        if current & token_ids:
            return

        # Always schedule the long-press marker, but no panning:
        self._marker_start = (event.x, event.y)
        self._marker_after_id = self.canvas.after(500, self._create_marker)

    def _on_mouse_move(self, event):
        # If the user has moved since the press, cancel the long-press marker
        if self._marker_after_id and self._marker_start:
            dx = event.x - self._marker_start[0]
            dy = event.y - self._marker_start[1]
            # 5 px threshold; tweak to taste
            if abs(dx) > 5 or abs(dy) > 5:
                self.canvas.after_cancel(self._marker_after_id)
                self._marker_after_id = None

        # Now do the normal paint (or whatever else) on drag
        self.on_paint(event)

    def _on_mouse_up(self, event):
       # Cancel marker if not fired
        if self._marker_after_id:
            self.canvas.after_cancel(self._marker_after_id)
            self._marker_after_id = None

        # Remove any existing marker
        if self._marker_id:
            self.canvas.delete(self._marker_id)
            self._marker_id = None
        if self.fs_canvas and self._fs_marker_id:
            self.fs_canvas.delete(self._fs_marker_id)
            self._fs_marker_id = None

    def _on_middle_click(self, event):
        # Recenter click → canvas center
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        xw = (event.x - self.pan_x) / self.zoom
        yw = (event.y - self.pan_y) / self.zoom
        self.pan_x = (cw/2) - xw*self.zoom
        self.pan_y = (ch/2) - yw*self.zoom
        self._update_canvas_images()

    def _create_marker(self):
        x0, y0 = self._marker_start
        xw = (x0 - self.pan_x) / self.zoom
        yw = (y0 - self.pan_y) / self.zoom
        sx, sy = int(xw*self.zoom + self.pan_x), int(yw*self.zoom + self.pan_y)
        r = 10
        self._marker_id = self.canvas.create_oval(sx-r,sy-r,sx+r,sy+r, outline='red', width=2)
        if self.fs_canvas:
            self._fs_marker_id = self.fs_canvas.create_oval(sx-r,sy-r,sx+r,sy+r, outline='red', width=2)

    def on_zoom(self, event):
        # keep cursor world‐point fixed
        xw = (event.x - self.pan_x) / self.zoom
        yw = (event.y - self.pan_y) / self.zoom
        delta = event.delta / 120
        self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, self.zoom * (1 + ZOOM_STEP*delta)))
        self.pan_x = event.x - xw*self.zoom
        self.pan_y = event.y - yw*self.zoom
        # Debounce the full redraw
        if self._zoom_after_id:
            self.canvas.after_cancel(self._zoom_after_id)
        self._zoom_after_id = self.canvas.after(
            50,                            # wait 50ms after last wheel event
            lambda: self._perform_zoom(final=False)
    )

    def _perform_zoom(self, final: bool):
        """Actually do the heavy redraw. If final==True, you could switch to LANCZOS."""
        # choose resample filter
        resample = Image.LANCZOS if final else self._fast_resample
        # redraw base, mask, tokens using `resample` instead of hardcoded LANCZOS:
        self._update_canvas_images(resample=resample)

    def on_resize(self):
        # just redraw at new canvas size
        self._update_canvas_images()

    def _update_canvas_images(self, resample=Image.LANCZOS):
        """Redraw GM canvas then mirror to fullscreen."""
        if not self.base_img:
            return
        w, h = self.base_img.size
        sw, sh = int(w*self.zoom), int(h*self.zoom)
        x0, y0 = self.pan_x, self.pan_y

        # Base
        base_resized = self.base_img.resize((sw,sh), resample=self._fast_resample)
        self.base_tk = ImageTk.PhotoImage(base_resized)
        if self.base_id:
            self.canvas.itemconfig(self.base_id, image=self.base_tk)
            self.canvas.coords(self.base_id, x0, y0)
        else:
            self.base_id = self.canvas.create_image(x0, y0, image=self.base_tk, anchor='nw')

        # Mask
        mask_resized = self.mask_img.resize((sw,sh), resample=Image.LANCZOS)
        self.mask_tk = ImageTk.PhotoImage(mask_resized)
        if self.mask_id:
            self.canvas.itemconfig(self.mask_id, image=self.mask_tk)
            self.canvas.coords(self.mask_id, x0, y0)
        else:
            self.mask_id = self.canvas.create_image(x0, y0, image=self.mask_tk, anchor='nw')

        # Tokens
        for token in self.tokens:
            pil = token['pil_image']
            tw, th = pil.size
            nw, nh = int(tw*self.zoom), int(th*self.zoom)
            img_r = pil.resize((nw,nh), resample=Image.LANCZOS)
            tkimg = ImageTk.PhotoImage(img_r)
            token['tk_image'] = tkimg

            xw, yw = token['position']
            sx, sy = int(xw*self.zoom + self.pan_x), int(yw*self.zoom + self.pan_y)

            if 'canvas_ids' in token:
                b_id, i_id = token['canvas_ids']
                # update border color in case it changed
                self.canvas.itemconfig(b_id, outline=token.get('border_color','#0000ff'))
                self.canvas.coords(b_id, sx-3, sy-3, sx+nw+3, sy+nh+3)
                self.canvas.coords(i_id, sx, sy)
                self.canvas.itemconfig(i_id, image=tkimg)
            else:
                b_id = self.canvas.create_rectangle(
                    sx-3, sy-3, sx+nw+3, sy+nh+3,
                    outline=token.get('border_color','#0000ff'),
                    width=3)
                i_id = self.canvas.create_image(sx, sy, image=tkimg, anchor='nw')
                token['canvas_ids'] = (b_id, i_id)
                # bind all token events right after creation:
                self._bind_token(token)

    
    def _bind_token(self, token):
        """Attach drag & right-click handlers to both border & image."""
        b_id, i_id = token['canvas_ids']
        for cid in (b_id, i_id):
            # press → start drag
            self.canvas.tag_bind(cid, "<ButtonPress-1>",
                                 lambda e, t=token: self._on_token_press(e, t))
            # drag → move token, then break so on_paint doesn't run
            self.canvas.tag_bind(cid, "<B1-Motion>",
                                 lambda e, t=token: (self._on_token_move(e, t), "break"))
            # release → end drag
            self.canvas.tag_bind(cid, "<ButtonRelease-1>",
                                 lambda e, t=token: self._on_token_release(e, t))
            # right-click → context menu
            self.canvas.tag_bind(cid, "<Button-3>",
                                 lambda e, t=token: self._show_token_menu(e, t))
    
    def open_fullscreen(self):
        monitors = get_monitors()
        if len(monitors) < 2:
            return
        m = monitors[1]
        self.fs = tk.Toplevel(self.parent)
        self.fs.title("Players Map")
        self.fs.resizable(True, True)
        self.fs.geometry(f"{m.width}x{m.height}+{m.x}+{m.y}")
        self.fs_canvas = tk.Canvas(self.fs, bg="black")
        self.fs_canvas.pack(fill="both", expand=True)
        self.fs_base_id = None
        self.fs_mask_id = None
        self._update_fullscreen_map()

    def _update_fullscreen_map(self):
        """Mirror the GM canvas into the fullscreen window."""
        if not self.fs_canvas or not self.base_img:
            return

        # Same logic as above but on fs_canvas
        w, h = self.base_img.size
        sw, sh = int(w*self.zoom), int(h*self.zoom)
        x0, y0 = self.pan_x, self.pan_y

        base_resized = self.base_img.resize((sw,sh), resample=Image.LANCZOS)
        self.fs_base_tk = ImageTk.PhotoImage(base_resized)
        if self.fs_base_id:
            self.fs_canvas.itemconfig(self.fs_base_id, image=self.fs_base_tk)
            self.fs_canvas.coords(self.fs_base_id, x0, y0)
        else:
            self.fs_base_id = self.fs_canvas.create_image(x0, y0,
                                                          image=self.fs_base_tk,
                                                          anchor='nw')
        for token in self.tokens:
            pil = token['pil_image']
            tw, th = pil.size
            nw, nh = int(tw*self.zoom), int(th*self.zoom)
            img_r = pil.resize((nw,nh), resample=Image.LANCZOS)
            fsimg = ImageTk.PhotoImage(img_r)
            token['fs_tk'] = fsimg

            xw, yw = token['position']
            sx, sy = int(xw*self.zoom + self.pan_x), int(yw*self.zoom + self.pan_y)

            if 'fs_canvas_ids' in token:
                b_id, i_id = token['fs_canvas_ids']
                self.fs_canvas.coords(b_id, sx-3, sy-3, sx+nw+3, sy+nh+3)
                # also update fullscreen border color
                self.fs_canvas.itemconfig(b_id, outline=token.get('border_color','#0000ff'))
                self.fs_canvas.coords(i_id, sx, sy)
                self.fs_canvas.itemconfig(i_id, image=fsimg)
            else:
                b_id = self.fs_canvas.create_rectangle(
                    sx-3, sy-3, sx+nw+3, sy+nh+3,
                    outline=token.get('border_color','#0000ff'),
                    width=3
                    )
                i_id = self.fs_canvas.create_image(sx, sy, image=fsimg, anchor='nw')
                token['fs_canvas_ids'] = (b_id, i_id)
        
        # create a copy of the mask where any non-zero alpha becomes 255 (fully opaque)
        mask_copy = self.mask_img.copy()
        # split out alpha channel
        _, _, _, alpha = mask_copy.split()
        # map any alpha>0 to 255, leave 0 as 0
        alpha = alpha.point(lambda a: 255 if a>0 else 0)
        mask_copy.putalpha(alpha)
        mask_resized = mask_copy.resize((sw, sh), resample=Image.LANCZOS)
        self.fs_mask_tk = ImageTk.PhotoImage(mask_resized)
        if self.fs_mask_id:
            self.fs_canvas.itemconfig(self.fs_mask_id, image=self.fs_mask_tk)
            self.fs_canvas.coords(self.fs_mask_id, x0, y0)
        else:
            self.fs_mask_id = self.fs_canvas.create_image(x0, y0,
                                                        image=self.fs_mask_tk,
                                                        anchor='nw')
    
    def open_entity_picker(self, entity_type):
        """
        Show a GenericListSelectionView for NPCs or Creatures.
        """
        picker = tk.Toplevel(self.parent)
        picker.title(f"Select {entity_type}")
        picker.geometry("1300x600")
        view = GenericListSelectionView(
            master=picker,
            entity_type=entity_type,
            model_wrapper=self._model_wrappers[entity_type],
            template=self._templates[entity_type],
            on_select_callback=lambda et, name: self.on_entity_selected(et, name, picker)
        )
        
        view.pack(fill="both", expand=True)
    
    def on_entity_selected(self, entity_type, entity_name, picker_frame):
        """
        Called when user picks an NPC or Creature in the selection dialog.
        """
        items = self._model_wrappers[entity_type].load_items()
        selected = next(item for item in items if item.get("Name") == entity_name)
        portrait = selected.get("Portrait")
        if isinstance(portrait, dict):
            path = portrait.get("path") or portrait.get("text")
        else:
            path = portrait

        self.add_token(path, entity_type, entity_name)
        picker_frame.destroy()
        
    # --- Token management ---
    def add_token(self, path, entity_type, entity_name):
        img_path = path
        pil_img  = Image.open(img_path).convert("RGBA")
        pil_img = pil_img.resize((48, 48), resample=Image.LANCZOS)
        token = {
            "entity_type": entity_type,
            "entity_id":  entity_name,
            "image_path":  img_path,
            "pil_image":   pil_img,
            "position":    (0, 0),
            "border_color": "#0000ff",
        }
        self.tokens.append(token)
        self._update_canvas_images()

        # Bind drag & menu
        b_id, i_id = token["canvas_ids"]
        for tag in (b_id, i_id):
            self.canvas.tag_bind(tag, "<ButtonPress-1>",
                                 lambda e, t=token: self._on_token_press(e, t))
            self.canvas.tag_bind(tag, "<B1-Motion>",
                                 lambda e, t=token: self._on_token_move(e, t))
            self.canvas.tag_bind(tag, "<ButtonRelease-1>",
                                 lambda e, t=token: self._on_token_release(e, t))
            self.canvas.tag_bind(tag, "<Button-3>",
                                 lambda e, t=token: self._show_token_menu(e, t))
        self._persist_tokens()

    def _on_token_press(self, event, token):
        token["drag_data"] = {"x": event.x, "y": event.y}

    def _on_token_move(self, event, token):
        dx = event.x - token["drag_data"]["x"]
        dy = event.y - token["drag_data"]["y"]
        b_id, i_id = token["canvas_ids"]
        self.canvas.move(b_id, dx, dy)
        self.canvas.move(i_id, dx, dy)
        token["drag_data"] = {"x": event.x, "y": event.y}
        sx, sy = self.canvas.coords(i_id)
        token["position"] = ((sx - self.pan_x)/self.zoom, (sy - self.pan_y)/self.zoom)

    def _on_token_release(self, event, token):
        token.pop("drag_data", None)
        self._persist_tokens()

    def _show_token_menu(self, event, token):
        menu = tk.Menu(self.canvas, tearoff=0)
        menu.add_command(label="Show Portrait",
            command=lambda: show_portrait(token["image_path"], token.get("entity_type")))
        menu.add_command(label="Change Border Color",
            command=lambda t=token: self._change_token_border_color(t))
        menu.add_separator()
        menu.add_command(label="Delete Token",
            command=lambda t=token: self._delete_token(t))
        menu.tk_popup(event.x_root, event.y_root)
    
    def _change_token_border_color(self, token):
        """Open a color chooser and update the token’s border."""
        result = colorchooser.askcolor(
            color=token.get("border_color", "#0000ff"),
            title="Choose token border color"
        )
        # result == ( (r,g,b), "#rrggbb" ) or (None, None) if cancelled
        if result and result[1]:
            new_color = result[1]
            token["border_color"] = new_color
            # update GM canvas border
            b_id = token["canvas_ids"][0]
            self.canvas.itemconfig(b_id, outline=new_color)
            # update fullscreen border if open
            if getattr(self, "fs_canvas", None) and "fs_canvas_ids" in token:
                fs_b_id = token["fs_canvas_ids"][0]
                self.fs_canvas.itemconfig(fs_b_id, outline=new_color)
            # persist the choice
            self._persist_tokens()
    def _delete_token(self, token):
        for cid in token.get("canvas_ids", []):
            self.canvas.delete(cid)
        if self.fs_canvas and "fs_canvas_ids" in token:
            for cid in token["fs_canvas_ids"]:
                self.fs_canvas.delete(cid)
        self.tokens.remove(token)
        self._persist_tokens()

    def _persist_tokens(self):
        """Serialize tokens into current_map and save all maps."""
        # Build the JSON/AST-safe list
        data = []
        # build one entry per token
        for t in self.tokens:
            x, y = t["position"]
            entry = {
                "entity_type": t["entity_type"],
                "entity_id":   t["entity_id"],
                "image_path":  t["image_path"],
                "x":           x,
                "y":           y,
                "border_color": t.get("border_color", "#0000ff")
            }
            data.append(entry)
        # serialize all tokens back into the map record
        self.current_map["Tokens"] = json.dumps(data)

        # Persist all maps
        all_maps = list(self._maps.values())
        self.maps.save_items(all_maps)

