import tkinter as tk
from PIL import ImageDraw

def _build_canvas(self):
    self.canvas = tk.Canvas(self.parent, bg="black")
    self.canvas.pack(fill="both", expand=True)

    # Global Copy/Paste bindings
    # Must use bind_all so shortcuts work even if canvas isn't focused
    # Global Copy/Paste bindings on the real Tk root
    root = self.parent.winfo_toplevel()
    root.bind_all("<Control-c>", self._copy_token)
    root.bind_all("<Control-C>", self._copy_token)
    root.bind_all("<Control-v>", self._paste_token)
    root.bind_all("<Control-V>", self._paste_token)
    root.bind_all("<Delete>", self._on_delete_key)

    # Painting, panning, markers
    self.canvas.bind("<ButtonPress-1>",    self._on_mouse_down)
    self.canvas.bind("<B1-Motion>",        self._on_mouse_move)
    self.canvas.bind("<ButtonRelease-1>",  self._on_mouse_up)
    self.canvas.bind("<ButtonPress-2>",    self._on_middle_click)
    # Zoom & resize
    self.canvas.bind("<MouseWheel>",       self.on_zoom)
    self.parent.bind("<Configure>",        lambda e: self._update_canvas_images())

def _on_delete_key(self, event=None):
    """If a token is selected (via click), delete it on Delete key."""
    if not self.selected_token:
        return
    # remove it from both canvases and from the list
    self._delete_token(self.selected_token)
    # clear the selection so repeated deletes do nothing
    self.selected_token = None

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

