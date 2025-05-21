import tkinter as tk
from PIL import ImageTk, Image
from screeninfo import get_monitors

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
    # reset IDs so base/mask/tokens all get re-created on the new canvas
    self.fs_base_id = None
    self.fs_mask_id = None
    # clear any stale fullscreen token IDs
    for token in self.tokens:
        token.pop('fs_canvas_ids', None)
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
            b_id, i_id, t_id = token['fs_canvas_ids']
            self.fs_canvas.coords(b_id, sx-3, sy-3, sx+nw+3, sy+nh+3)
            # also update fullscreen border color
            self.fs_canvas.itemconfig(b_id, outline=token.get('border_color','#0000ff'))
            self.fs_canvas.coords(i_id, sx, sy)
            self.fs_canvas.itemconfig(i_id, image=fsimg)
            # move the text label under the token
            self.fs_canvas.coords(
                t_id,
                sx + nw//2,
                sy + nh + 2
            )
        else:
            b_id = self.fs_canvas.create_rectangle(
                sx-3, sy-3, sx+nw+3, sy+nh+3,
                outline=token.get('border_color','#0000ff'),
                width=3
                )
            i_id = self.fs_canvas.create_image(sx, sy, image=fsimg, anchor='nw')
            # then draw the name centered under the token
            t_id = self.fs_canvas.create_text(
                sx + nw//2,
                sy + nh + 2,
                text=token['entity_id'],
                fill='white',
                anchor='n'
            )
            token['fs_canvas_ids'] = (b_id, i_id, t_id)
        hp = token.get("hp", 0)
        tw, th = token['pil_image'].size
        nw, nh = int(tw*self.zoom), int(th*self.zoom)
        sx = int(token['position'][0]*self.zoom + self.pan_x)
        sy = int(token['position'][1]*self.zoom + self.pan_y)

        if hp <= 0:
            # clean up any old fs-cross
            if 'fs_cross_ids' in token:
                for x_id in token['fs_cross_ids']:
                    self.fs_canvas.delete(x_id)

            tl = (sx,      sy)
            br = (sx+nw,   sy+nh)
            tr = (sx+nw,   sy)
            bl = (sx,      sy+nh)

            line1 = self.fs_canvas.create_line(*tl, *br, fill="red", width=3)
            line2 = self.fs_canvas.create_line(*tr, *bl, fill="red", width=3)
            token['fs_cross_ids'] = (line1, line2)
        else:
            # remove the fs-cross if they’ve been revived
            if 'fs_cross_ids' in token:
                for x_id in token['fs_cross_ids']:
                    self.fs_canvas.delete(x_id)
                del token['fs_cross_ids']
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
    # ensure the mask is on top of everything
    self.fs_canvas.tag_raise(self.fs_mask_id)

