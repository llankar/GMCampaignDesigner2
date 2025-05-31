from PIL import ImageDraw, Image, ImageTk

def _set_fog(self, mode):
    self.fog_mode = mode

def clear_fog(self):
    self.mask_img = Image.new("RGBA", self.base_img.size, (0,0,0,0))
    self._update_canvas_images()

def reset_fog(self):
    self.mask_img = Image.new("RGBA", self.base_img.size, (0, 0, 0, 128))
    self._update_canvas_images()

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
    # actually paint or erase on the mask_img
    if self.fog_mode == "add":
        if self.brush_shape == "circle":
            draw.ellipse((left, top, right, bottom), fill=(0, 0, 0, 128))
        else:
            draw.rectangle((left, top, right, bottom), fill=(0, 0, 0, 128))
    else:  # "rem"
        # clear that area (make it fully transparent)
        draw.rectangle((left, top, right, bottom), fill=(0, 0, 0,   0))    # 1) compute brush in screen coords
    half = self.brush_size/2
    size      = int(self.brush_size * self.zoom)
    half_size = size // 2
    size      = int(self.brush_size * self.zoom)
    half_size = size // 2

    # Directly center on the mouse‐pointer (event.x/event.y):
    px = event.x - half_size
    py = event.y - half_size

    if self.fog_mode == "add":
        if self.brush_shape == "circle":
            self.canvas.create_oval(
                px, py, px + size, py + size,
                fill="black", stipple="gray50", width=0,
                tags="fog_preview"
            )
        else:
            self.canvas.create_rectangle(
                px, py, px + size, py + size,
                fill="black", stipple="gray50", width=0,
                tags="fog_preview"
            )
    else:
        # in “erase” mode we just delete the old preview if any
        self.canvas.delete("fog_preview")
    # Directly center on the mouse‐pointer (event.x/event.y):
    px = event.x - half_size
    py = event.y - half_size

    if self.fog_mode == "add":
        if self.brush_shape == "circle":
            self.canvas.create_oval(
                px, py, px + size, py + size,
                fill="black", stipple="gray50", width=0,
                tags="fog_preview"
            )
        else:
            self.canvas.create_rectangle(
                px, py, px + size, py + size,
                fill="black", stipple="gray50", width=0,
                tags="fog_preview"
            )
    else:
        # in “erase” mode we just delete the old preview if any
        self.canvas.delete("fog_preview")
    
    
    # —— only resize & blit the mask ——
    w, h = self.base_img.size
    sw, sh = int(w * self.zoom), int(h * self.zoom)

    # use the interactive (fast) filter
    mask_resized = self.mask_img.resize((sw, sh), resample=self._fast_resample)
    self.mask_tk = ImageTk.PhotoImage(mask_resized)

    # update the existing canvas image item
    self.canvas.itemconfig(self.mask_id, image=self.mask_tk)
    self.canvas.coords(self.mask_id, self.pan_x, self.pan_y)

