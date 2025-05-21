import os
import json
import tkinter as tk
import customtkinter as ctk
from modules.maps.views.map_selector import select_map, _on_display_map
from modules.maps.views.toolbar_view import _build_toolbar, _on_brush_size_change, _on_brush_shape_change, _change_brush, _on_token_size_change
from modules.maps.views.canvas_view import _build_canvas, _on_delete_key, on_paint
from modules.maps.services.fog_manager import _set_fog, clear_fog, reset_fog, on_paint
from modules.maps.services.token_manager import add_token, _on_token_press, _on_token_move, _on_token_release, _copy_token, _paste_token, _show_token_menu, _resize_token_dialog, _change_token_border_color, _delete_token, _persist_tokens
from modules.maps.views.fullscreen_view import open_fullscreen, _update_fullscreen_map
from modules.maps.services.entity_picker_service import open_entity_picker, on_entity_selected
from modules.maps.utils.icon_loader import load_icon
from PIL import Image, ImageTk, ImageDraw
from modules.generic.generic_model_wrapper import GenericModelWrapper
from modules.helpers.template_loader import load_template
from modules.helpers.text_helpers import format_longtext

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
        self.selected_token  = None    # last clicked token
        self.clipboard_token = None    # copied token data
    
        self.brush_size  = DEFAULT_BRUSH_SIZE
        self.token_size  = 48
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
        self.selected_token  = None    # last clicked token
        self.clipboard_token = None    # copied token data
    
        self.brush_size  = DEFAULT_BRUSH_SIZE
        self.token_size  = 48
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

    def _create_marker(self):
        x0, y0 = self._marker_start
        xw = (x0 - self.pan_x) / self.zoom
        yw = (y0 - self.pan_y) / self.zoom
        sx, sy = int(xw*self.zoom + self.pan_x), int(yw*self.zoom + self.pan_y)
        r = 10
        self._marker_id = self.canvas.create_oval(sx-r,sy-r,sx+r,sy+r, outline='red', width=2)
        if self.fs_canvas:
            self._fs_marker_id = self.fs_canvas.create_oval(sx-r,sy-r,sx+r,sy+r, outline='red', width=2)

    def _on_middle_click(self, event):
        # Recenter click → canvas center
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        xw = (event.x - self.pan_x) / self.zoom
        yw = (event.y - self.pan_y) / self.zoom
        self.pan_x = (cw/2) - xw*self.zoom
        self.pan_y = (ch/2) - yw*self.zoom
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

    def _perform_zoom(self, final: bool):
        """Actually do the heavy redraw. If final==True, you could switch to LANCZOS."""
        # choose resample filter
        resample = Image.LANCZOS if final else self._fast_resample
        # redraw base, mask, tokens using `resample` instead of hardcoded LANCZOS:
        self._update_canvas_images(resample=resample)

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
                # ─── HP circle update ───
                hp = token.get("hp", 10)
                max_hp = token.get("max_hp", 10)
                ratio = hp / max_hp if max_hp > 0 else 1.0
                color = "#ff3333" if ratio < 0.10 else "#33cc33"
    
                circle_diam = max(18, int(nw * 0.25))
                cx = sx + nw - circle_diam + 4
                cy = sy + nh - circle_diam + 4
    
                if "hp_canvas_ids" in token:
                    cid, tid = token["hp_canvas_ids"]
                    self.canvas.coords(cid, cx, cy, cx + circle_diam, cy + circle_diam)
                    self.canvas.itemconfig(cid, fill=color)
                    self.canvas.coords(tid, cx + circle_diam // 2, cy + circle_diam // 2)
                    self.canvas.itemconfig(tid, text=str(hp))
                # update name text below the token
                name_id = token.get('name_id')
                if name_id:
                    # center text under the token
                    tx = sx + nw/2
                    ty = sy + nh + 2
                    self.canvas.coords(name_id, tx, ty)
                    self.canvas.itemconfig(name_id, text=token['entity_id'])
                if token.get('info_widget_id'):
                    # place it just to the right of the token
                    ix = sx + nw + 10
                    iy = sy + nh/2
                    self.canvas.coords(token['info_widget_id'], ix, iy)
                    # refresh its contents from the record
                    rec = token.get('entity_record', {})
                    new_text = format_longtext( rec.get("Stats", "") if token['entity_type']=="Creature" else rec.get("Traits", ""))
                    tb = token['info_widget']
                    # refresh entire contents from the start of the tk.Text
                    tb._textbox.delete("1.0", "end")
                    tb._textbox.insert("1.0", new_text)
            else:
                b_id = self.canvas.create_rectangle(
                    sx-3, sy-3, sx+nw+3, sy+nh+3,
                    outline=token.get('border_color','#0000ff'),
                    width=3)
                i_id = self.canvas.create_image(sx, sy, image=tkimg, anchor='nw')
                # then the name label
                tx = sx + nw/2
                ty = sy + nh + 2
                name_id = self.canvas.create_text(
                    tx, ty,
                    text=token['entity_id'],
                    fill='white',
                    anchor='n'
                )
                token['name_id'] = name_id
                hp = token.get("hp", 10)
                max_hp = token.get("max_hp", 10)  # You can later make this configurable
                ratio = hp / max_hp if max_hp > 0 else 1.0
                color = "#ff3333" if ratio < 0.10 else "#33cc33"  # red or green
                nw, nh = int(tw*self.zoom), int(th*self.zoom)  # token size
                circle_diam = max(18, int(nw * 0.25))
                cx = sx + nw - circle_diam + 4
                cy = sy + nh - circle_diam + 4
                if "hp_canvas_ids" in token:
                    cid, tid = token["hp_canvas_ids"]
                    self.canvas.coords(cid, cx, cy,cx + circle_diam, cy + circle_diam)
                    self.canvas.itemconfig(cid, fill=color)
                    self.canvas.coords(tid, cx + circle_diam//2, cy + circle_diam//2)
                    self.canvas.itemconfig(tid, text=str(hp))
                else:
                    cid = self.canvas.create_oval(
                        cx, cy, cx + circle_diam, cy + circle_diam,
                        fill=color,
                        outline="black",
                        width=1
                    )
                    tid = self.canvas.create_text(
                        cx + circle_diam//2,
                        cy + circle_diam//2,
                        text=str(hp),
                        font=("Arial", max(10, circle_diam // 2), "bold"),
                        fill="white"
                    )
                    token["hp_canvas_ids"] = (cid, tid)
                    self.canvas.tag_bind(
                        tid,
                        "<Double-1>",
                        lambda e, t=token: self._on_hp_double_click(e, t)
                    )
                    self.canvas.tag_bind(
                        tid, 
                        "<Button-3>",
                        lambda e, t=token: self._on_max_hp_menu_click(e, t))
                # ─────────────── NEW: add right‐of‐token multi‐line textbox ───────────────
                rec = token.get('entity_record', {})
                # — coerce to a single string before inserting, and clear old text
                raw = rec.get("Stats", "") if token['entity_type']=="Creature" else rec.get("Traits", "")
                if isinstance(raw, (list, tuple)):
                     display = "\n".join(map(str, raw))
                else:
                        display = str(raw)
                height = token.get("size", self.token_size) *2
                entry = token.get("info_widget")
                if not entry:
                    entry = ctk.CTkTextbox(self.canvas, width=100, height=height, wrap="word")
                    entry._textbox.insert("1.0", display)
                    token["info_widget"] = entry
    
                entry._textbox.delete("1.0", "end")
                entry._textbox.insert("1.0", display)
    
                ix = sx + nw + 10
                iy = sy + nh/2
                info_id = self.canvas.create_window(ix, iy, anchor='w', window=entry)
                self.canvas.itemconfigure(info_id, state='hidden')  # ← start hidden
    
                # ✅ Set first, THEN bind
                token.update({
                    'canvas_ids':     (b_id, i_id),
                    'name_id':        name_id,
                    'info_widget_id': info_id,
                    'info_widget':    entry,
                })
    
                # ✅ Now bind using correct info_id
                for cid in (b_id, i_id):
                    self.canvas.tag_bind(cid, "<Enter>",
                        lambda e, iid=info_id: self.canvas.itemconfigure(iid, state='normal'))
                    self.canvas.tag_bind(cid, "<Leave>",
                        lambda e, iid=info_id: self.canvas.itemconfigure(iid, state='hidden'))
    
                entry.bind("<Enter>", lambda e, iid=info_id: self.canvas.itemconfigure(iid, state='normal'))
                entry.bind("<Leave>", lambda e, iid=info_id: self.canvas.itemconfigure(iid, state='hidden'))
                # keep it hidden if you mouse off the box itself
                widget = token['info_widget']
                widget.bind("<Enter>",
                    lambda e, iid=info_id:
                    self.canvas.itemconfigure(iid, state='normal'))
                widget.bind("<Leave>",
                    lambda e, iid=info_id:
                    self.canvas.itemconfigure(iid, state='hidden'))
    
                token.update({
                    'canvas_ids':     (b_id, i_id),
                    'name_id':        name_id,
                    'info_widget_id': info_id,
                    'info_widget':    entry,
                })
                # ─────────── BIND DRAG HANDLERS ONCE ───────────
    
                # bind all token events right after creation:
                self._bind_token(token)
    
    def _on_max_hp_menu_click(self, event, token):
        """
        Handler for middle‐click on the HP text to edit max_hp inline.
        Spawns a CTkEntry prefilled with token['max_hp'], commits on Enter.
        """
        # If a previous max_hp entry exists, clean it up first
        if "max_hp_entry_widget" in token:
            self.canvas.delete(token["max_hp_entry_widget_id"])
            token["max_hp_entry_widget"].destroy()
            del token["max_hp_entry_widget"], token["max_hp_entry_widget_id"]

        # Hide the HP text so it doesn’t clash with the entry
        cid, tid = token["hp_canvas_ids"]
        self.canvas.itemconfigure(tid, state="hidden")

        # Compute where to place the entry (centered on the HP text)
        x, y = self.canvas.coords(tid)

        # Create the inline entry, pre-fill with the current max_hp
        entry = ctk.CTkEntry(self.canvas, width=50)
        entry.insert(0, str(token.get("max_hp", 0)))

        # Embed it into the canvas and store references for cleanup
        entry_id = self.canvas.create_window(x, y, window=entry, anchor="center")
        token["max_hp_entry_widget"]    = entry
        token["max_hp_entry_widget_id"] = entry_id

        # Give focus and select all so typing immediately replaces the value
        entry.focus_set()
        entry.select_range(0, tk.END)

        # Bind Enter to commit the new max_hp
        entry.bind("<Return>", lambda e: self._on_max_hp_entry_commit(e, token))
    def _on_max_hp_entry_commit(self, event, token):
        """
        Handler for pressing <Return> in the inline max-HP entry.
        Parses the input, updates token['max_hp'], clamps current HP if needed,
        and updates the on-canvas text to show "current/max".
        """
        entry    = token.get("max_hp_entry_widget")
        entry_id = token.get("max_hp_entry_widget_id")
        if not entry:
            return

        raw = entry.get().strip()
        # Parse absolute new max_hp
        try:
            new_max = int(raw)
        except ValueError:
            # Invalid input — leave old max_hp
            new_max = token.get("max_hp", 1)

        # Enforce a minimum of 1
        new_max = max(1, new_max)

        # Optionally clamp current HP so it never exceeds new max
        cur_hp = token.get("hp", 0)
        cur_hp = min(cur_hp, new_max)
        token["hp"]     = new_max
        token["max_hp"] = new_max

        # Clean up the entry widget
        self.canvas.delete(entry_id)
        entry.destroy()
        del token["max_hp_entry_widget"], token["max_hp_entry_widget_id"]

        # Restore and update the HP text to "cur/max"
        cid, tid = token["hp_canvas_ids"]
        self.canvas.itemconfigure(
            tid,
            state="normal",
            text=f"{new_max}"
        )
        
    def _on_hp_double_click(self, event, token):
        """
        Handler for double-click on the HP text. Swaps the text with an inline CTkEntry
        so the GM can type a new HP (absolute or relative) directly.
        """
        # If an edit entry already exists, remove it first
        if "hp_entry_widget" in token:
            self.canvas.delete(token["hp_entry_widget_id"])
            token["hp_entry_widget"].destroy()
            del token["hp_entry_widget"], token["hp_entry_widget_id"]

        # Hide the text item
        cid, tid = token["hp_canvas_ids"]
        self.canvas.itemconfigure(tid, state="hidden")

        # Get the on-screen coords of the HP text
        x, y = self.canvas.coords(tid)

        # Create the inline entry pre-filled with the current HP
        entry = ctk.CTkEntry(self.canvas, width=50)
        entry.insert(0, str(token.get("hp", 0)))

        # Embed the entry into the canvas
        entry_id = self.canvas.create_window(x, y, window=entry, anchor="center")
        token["hp_entry_widget"]    = entry
        token["hp_entry_widget_id"] = entry_id

        # Focus & select all text so the GM can immediately type
        entry.focus_set()
        entry.select_range(0, tk.END)

        # Commit on Enter
        entry.bind("<Return>", lambda e: self._on_hp_entry_commit(e, token))


    def _on_hp_entry_commit(self, event, token):
        """
        Handler for pressing <Return> in the inline HP entry.
        Parses absolute or relative input, updates token.hp, and
        restores the text display.
        """
        entry   = token.get("hp_entry_widget")
        entry_id = token.get("hp_entry_widget_id")
        if not entry:
            return  # nothing to do

        raw = entry.get().strip()
        # Determine new HP (absolute or relative)
        try:
            if raw.startswith(("+", "-")):
                delta = int(raw)
                new_hp = token["hp"] + delta
            else:
                new_hp = int(raw)
        except ValueError:
            # invalid input — leave HP unchanged
            new_hp = token["hp"]

        # Clamp between 0 and max_hp
        max_hp = token.get("max_hp", new_hp)
        new_hp = max(0, min(new_hp, max_hp))
        token["hp"] = new_hp

        # Clean up the entry widget
        self.canvas.delete(entry_id)
        entry.destroy()
        del token["hp_entry_widget"], token["hp_entry_widget_id"]

        # Restore and update the HP text item
        cid, tid = token["hp_canvas_ids"]
        self.canvas.itemconfigure(tid, state="normal", text=str(new_hp))

        fill = 'red' if new_hp/max_hp < 0.25 else 'green'
        self.canvas.itemconfig(cid, fill=fill)
        
    def on_resize(self):
        # just redraw at new canvas size
        self._update_canvas_images()

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
        self.current_map["token_size"] = self.token_size
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

    _build_canvas = _build_canvas
    _build_toolbar = _build_toolbar
    _change_brush = _change_brush
    _change_token_border_color = _change_token_border_color
    _copy_token = _copy_token
    _delete_token = _delete_token
    _on_brush_shape_change = _on_brush_shape_change
    _on_brush_size_change = _on_brush_size_change
    _on_delete_key = _on_delete_key
    _on_display_map = _on_display_map
    _on_token_move = _on_token_move
    _on_token_press = _on_token_press
    _on_token_release = _on_token_release
    _on_token_size_change = _on_token_size_change
    _paste_token = _paste_token
    _persist_tokens = _persist_tokens
    _resize_token_dialog = _resize_token_dialog
    _set_fog = _set_fog
    _show_token_menu = _show_token_menu
    _update_fullscreen_map = _update_fullscreen_map
    add_token = add_token
    clear_fog = clear_fog
    load_icon = load_icon
    on_entity_selected = on_entity_selected
    on_paint = on_paint
    open_entity_picker = open_entity_picker
    open_fullscreen = open_fullscreen
    reset_fog = reset_fog
    select_map = select_map
