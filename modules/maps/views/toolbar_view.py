import tkinter as tk
import customtkinter as ctk
from modules.ui.icon_button import create_icon_button

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
        "pc":    self.load_icon("assets/icons/pc.png",       (48,48)),
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
    create_icon_button(toolbar, icons["pc"], "Add PC", command=lambda: self.open_entity_picker("PC")) \
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

    # Token‐size control
    size_label = ctk.CTkLabel(toolbar, text="Token Size:")
    size_label.pack(side="left", padx=(10,2), pady=8)

    self.token_slider = ctk.CTkSlider(
        toolbar, from_=16, to=128,
        command=self._on_token_size_change
    )
    self.token_slider.set(self.token_size)
    self.token_slider.pack(side="left", padx=5, pady=8)

    # ← NEW: show current value
    self.token_size_value_label = ctk.CTkLabel(
        toolbar,
        text=str(self.token_size),
        width=32
    )
    self.token_size_value_label.pack(side="left", padx=(2,10), pady=8)

def _on_brush_size_change(self, val):
    try:
        self.brush_size = int(val)
    except ValueError:
        pass

def _on_brush_shape_change(self, val):
    # normalize to lowercase for comparisons
    self.brush_shape = val.lower()

def _change_brush(self, delta):
    new = max(4, min(128, self.brush_size + delta))
    self.brush_size = new
    self.brush_slider.set(new)

def _on_token_size_change(self, val):
    try:
        self.token_size = int(val)
        self.token_size_value_label.configure(text=str(self.token_size))
    except ValueError:
        pass

