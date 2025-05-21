from tkinter import messagebox 
import ast
import json
import os
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
from modules.helpers.template_loader import load_template
from modules.generic.generic_list_selection_view import GenericListSelectionView

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
    # 1) Lookup the chosen map record
    item = self._maps.get(map_name)
    if not item:
        messagebox.showwarning("Not Found", f"Map '{map_name}' not found.")
        return
    self.current_map = item

    # Restore token size if set
    size = item.get("token_size")
    if isinstance(size, int):
        self.token_size = size

    # 2) Tear down any existing UI & build toolbar + canvas
    for w in self.parent.winfo_children():
        w.destroy()
    self._build_toolbar()
    self._build_canvas()

    # 3) Load base image + fog mask
    self.base_img = Image.open(item["Image"]).convert("RGBA")
    mask_path   = item.get("FogMaskPath", "")
    if mask_path and os.path.exists(mask_path):
        self.mask_img = Image.open(mask_path).convert("RGBA")
    else:
        self.mask_img = Image.new("RGBA", self.base_img.size, (0,0,0,128))

    # Reset pan/zoom
    self.zoom  = 1.0
    self.pan_x = 0
    self.pan_y = 0

    # 4) Clear out any old tokens from both canvases
    for t in self.tokens:
        for cid in t.get("canvas_ids", []):
            self.canvas.delete(cid)
        if self.fs_canvas and t.get("fs_canvas_ids"):
            for cid in t["fs_canvas_ids"]:
                self.fs_canvas.delete(cid)
    self.tokens = []

    # 5) Parse persisted token list
    print(f"[load_token item= {item}")
    raw = item.get("Tokens", [])
    print(f"[load_token] Raw tokens: {raw}")
    if isinstance(raw, str):
        try:
            token_list = ast.literal_eval(raw.strip() or "[]")
            print(f"[load_token] Loaded {len(token_list)} tokens")
        except Exception:
            try:
                token_list = json.loads(raw)
            except Exception:
                token_list = []
                print(f"[load_token] Failed to parse tokens: {raw}")
    elif isinstance(raw, list):
        token_list = raw
    else:
        token_list = []

    # 6) Pre-load all Creature & NPC records once
    creatures = {r.get("Name"): r for r in self._model_wrappers["Creature"].load_items()}
    npcs      = {r.get("Name"): r for r in self._model_wrappers["NPC"].load_items()}

    # 7) Build self.tokens in one pass (only image loading & metadata)
    for rec in token_list:
        path = rec.get("image_path") or rec.get("path")
        sz   = rec.get("size", self.token_size)
        try:
            pil = Image.open(path).convert("RGBA")
            pil = pil.resize((sz, sz), resample=Image.LANCZOS)
        except Exception as e:
            print(f"[load_token] Failed to load image '{path}': {e}")
            continue
        pos = rec.get("position")
        if isinstance(pos, (list, tuple)) and len(pos) >= 2:
            xw, yw = pos
        else:
            xw = rec.get("x", 0)
            yw = rec.get("y", 0)

        self.tokens.append({
            "entity_type":  rec.get("entity_type", entity_type),
            "entity_id":    rec.get("entity_id"),
            "image_path":   path,  # ✅ ← ADD THIS
            "pil_image":    pil,
            "position":     (xw, yw),
            "border_color": rec.get("border_color", "#0000ff"),
            "size":         sz,
            "hp":           rec.get("hp", 10),           
            "max_hp":       rec.get("total_hp", 10),
            "hp_label_id":  None,                        
            "hp_entry":     None,                        
            "hp_entry_id":  None                         
        })

    # 8) Hydrate each token & create its hidden, word-wrapped info box
    for token in self.tokens:
        if token["entity_type"] == "Creature":
            record = creatures.get(token["entity_id"], {})
            raw_txt = record.get("Stats", "")
        else:
            record = npcs.get(token["entity_id"], {})
            raw_txt = record.get("Traits", "")

        token["entity_record"] = record

        # Coerce list→newline string
        if isinstance(raw_txt, (list, tuple)):
            info = "\n".join(map(str, raw_txt))
        else:
            info = str(raw_txt or "")

        # Half-width, double-height, word-wrapped textbox
        height = token["size"] * 2
        tb = ctk.CTkTextbox(self.canvas, width=100, height=height, wrap="word")
        tb._textbox.delete("1.0", "end")
        tb._textbox.insert("1.0", info)

        token["info_widget"] = tb

    # 9) Finally draw everything onto the canvas
    self._update_canvas_images()

