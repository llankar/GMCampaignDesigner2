import re
import time
import os, ctypes
from ctypes import wintypes
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from screeninfo import get_monitors
from modules.generic.generic_editor_window import GenericEditorWindow

PORTRAIT_FOLDER = "assets/portraits"
MAX_PORTRAIT_SIZE = (1024, 1024)
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Helper function to get monitor information using ctypes and Windows API.
def get_monitors():
    monitors = []
    def monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
        rect = lprcMonitor.contents
        monitors.append((rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top))
        return True
    MonitorEnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL,
                                        wintypes.HMONITOR,
                                        wintypes.HDC,
                                        ctypes.POINTER(wintypes.RECT),
                                        wintypes.LPARAM)
    ctypes.windll.user32.EnumDisplayMonitors(0, 0, MonitorEnumProc(monitor_enum_proc), 0)
    return monitors

def sanitize_id(s):
    return re.sub(r'[^a-zA-Z0-9]+', '_', str(s)).strip('_')


class _ToolTip:
    """Simple tooltip for a Treeview showing full cell text on hover."""
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.text = ""
        widget.bind("<Motion>", self._on_motion)
        widget.bind("<Leave>", self._on_leave)

    def _on_motion(self, event):
        rowid = self.widget.identify_row(event.y)
        colid = self.widget.identify_column(event.x)
        if rowid and colid:
            if colid == "#0":
                txt = self.widget.item(rowid, "text")
            else:
                txt = self.widget.set(rowid, colid)
        else:
            txt = ""
        if txt and txt != self.text:
            self.text = txt
            self._show(event.x_root + 20, event.y_root + 10, txt)
        elif not txt:
            self._hide()

    def _on_leave(self, _):
        self._hide()

    def _show(self, x, y, text):
        self._hide()
        tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text=text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            wraplength=400
        )
        label.pack(ipadx=1)
        self.tipwindow = tw

    def _hide(self):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None
            self.text = ""


class GenericListView(ctk.CTkFrame):
    def __init__(self, master, model_wrapper, template, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.model_wrapper = model_wrapper
        self.template = template
        os.makedirs(PORTRAIT_FOLDER, exist_ok=True)

        self.items = self.model_wrapper.load_items()
        self.filtered_items = list(self.items)

        # Unique field and extra columns
        self.unique_field = next(
            (f["name"] for f in self.template["fields"] if f["name"] != "Portrait"),
            None
        )
        self.columns = [
            f["name"] for f in self.template["fields"]
            if f["name"] not in ("Portrait", self.unique_field)
        ]

        # --- Search bar ---
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=(5,45), pady=5)
        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        search_entry.bind("<Return>", lambda e: self.filter_items(self.search_var.get()))
        ctk.CTkButton(search_frame, text="Filter",
                    command=lambda: self.filter_items(self.search_var.get()))\
        .pack(side="left", padx=5)
        ctk.CTkButton(search_frame, text="Add",
                    command=self.add_item)\
        .pack(side="left", padx=5)

        # --- Treeview setup ---
        tree_frame = ctk.CTkFrame(self, fg_color="#2B2B2B")
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Custom.Treeview",
                        background="#2B2B2B",
                        fieldbackground="#2B2B2B",
                        foreground="white",
                        rowheight=25,
                        font=("Segoe UI", 10, "bold"))
        style.configure("Custom.Treeview.Heading",
                        background="#2B2B2B",
                        foreground="white",
                        font=("Segoe UI", 10, "bold"))
        style.map("Custom.Treeview",
                background=[("selected", "#2B2B2B")])

        self.tree = ttk.Treeview(
            tree_frame,
            columns=self.columns,
            show="tree headings",
            selectmode="browse",
            style="Custom.Treeview"
        )
        # Unique field column
        self.tree.heading("#0", text=self.unique_field,
                        command=lambda: self.sort_column(self.unique_field))
        self.tree.column("#0", width=180, anchor="w")
        # Other columns
        for col in self.columns:
            self.tree.heading(col, text=col,
                            command=lambda c=col: self.sort_column(c))
            self.tree.column(col, width=150, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # Bind events
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.on_right_click)
        # Tooltip for full text on hover
        self._tooltip = _ToolTip(self.tree)

        # Populate
        self.refresh_list()

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        self.batch_index = 0
        self.batch_size = 50
        self.insert_next_batch()

    def insert_next_batch(self):
        end = min(self.batch_index + self.batch_size, len(self.filtered_items))
        for i in range(self.batch_index, end):
            item = self.filtered_items[i]
            raw = item.get(self.unique_field, "")
            if isinstance(raw, dict):
                raw = raw.get("text", "")
            iid = sanitize_id(raw or f"item_{int(time.time()*1000)}")
            name_text = self.clean_value(item.get(self.unique_field, ""))
            vals = tuple(self.clean_value(item.get(c, "")) for c in self.columns)
            try:
                self.tree.insert("", "end", iid=iid, text=name_text, values=vals)
            except Exception as e:
                print("[ERROR] inserting item:", e, iid, vals)
        self.batch_index = end
        if end < len(self.filtered_items):
            self.after(50, self.insert_next_batch)

    def clean_value(self, val):
        if val is None:
            return ""
        if isinstance(val, dict):
            return self.clean_value(val.get("text", ""))
        if isinstance(val, list):
            return ", ".join(self.clean_value(v) for v in val if v is not None)
        return str(val).replace("{", "").replace("}", "").strip()

    def sort_column(self, column_name):
        if not hasattr(self, "sort_directions"):
            self.sort_directions = {}
        asc = self.sort_directions.get(column_name, True)
        self.sort_directions[column_name] = not asc
        self.filtered_items.sort(
            key=lambda x: str(x.get(column_name, "")),
            reverse=not asc
        )
        self.refresh_list()

    def on_double_click(self, event):
        iid = self.tree.focus()
        if not iid:
            return
        item = next((it for it in self.filtered_items
                    if sanitize_id(str(it.get(self.unique_field, ""))) == iid),
                    None)
        if item:
            editor = GenericEditorWindow(
                self.master, item, self.template,
                self.model_wrapper, creation_mode=False
            )
            self.master.wait_window(editor)
            if getattr(editor, "saved", False):
                self.model_wrapper.save_items(self.items)
                self.refresh_list()

    def on_right_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        self.tree.selection_set(iid)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Show Portrait",
                        command=lambda: self.show_portrait_window(iid))
        menu.add_command(label="Delete",
                        command=lambda: self.delete_item(iid))
        menu.post(event.x_root, event.y_root)

    def show_portrait_window(self, iid):
        # find the item data
        item = next((it for it in self.filtered_items
                    if sanitize_id(str(it.get(self.unique_field, ""))) == iid),
                    None)
        if not item:
            messagebox.showerror("Error", "Item not found.")
            return
        path = item.get("Portrait", "")
        if not path or not os.path.exists(path):
            messagebox.showerror("Error", "No valid portrait available.")
            return

        try:
            img = Image.open(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}")
            return

        # scale to fit MAX_PORTRAIT_SIZE
        ow, oh = img.size
        mw, mh = MAX_PORTRAIT_SIZE
        scale = min(mw/ow, mh/oh, 1)
        if scale < 1:
            img = img.resize((int(ow*scale), int(oh*scale)), Image.Resampling.LANCZOS)

        photo = ImageTk.PhotoImage(img)
        # keep reference
        if not hasattr(self, "_portrait_refs"):
            self._portrait_refs = {}
        self._portrait_refs[iid] = photo

        # Obtain monitor information using ctypes.
        monitors = get_monitors()
    #logging.debug("Detected monitors: " + str(monitors))

        # Choose the second monitor if available; otherwise, use the primary monitor.
        if len(monitors) > 1:
            target_monitor = monitors[1]
        #logging.debug(f"Using second monitor: {target_monitor}")
        else:
            target_monitor = monitors[0]
        #logging.debug("Only one monitor available; using primary monitor.")

        screen_x, screen_y, screen_width, screen_height = target_monitor
    #logging.debug(f"Target screen: ({screen_x}, {screen_y}, {screen_width}, {screen_height})")

        # Scale the image if it's larger than the monitor dimensions (without upscaling).
        img_width, img_height = img.size
        scale = min(screen_width / img_width, screen_height / img_height, 1)
        new_size = (int(img_width * scale), int(img_height * scale))
    #logging.debug(f"Scaling factor: {scale}, new image size: {new_size}")
        if scale < 1:
            resample_method = getattr(Image, "Resampling", Image).LANCZOS
            img = img.resize(new_size, resample_method)
        #logging.debug("Image resized.")

        portrait_img = ImageTk.PhotoImage(img)
        # Persist the image reference to prevent garbage collection.
        
        # Create a normal Toplevel window (with standard window decorations).
        win = ctk.CTkToplevel(self)
        win.title(item["Name"])
        # Set the window geometry to match the target monitor's dimensions and position.
        win.geometry(f"{screen_width}x{screen_height}+{screen_x}+{screen_y}")
        win.update_idletasks()
    #logging.debug("Window created on target monitor with screen size.")

        # Create a frame with a black background to hold the content.
        content_frame = tk.Frame(win, bg="white")
        content_frame.pack(fill="both", expand=True)

        # Add a label to display the NPC name.
        name_label = tk.Label(content_frame, text=item["Name"],
                            font=("Arial", 40, "bold"),
                            fg="white", bg="white")
        name_label.pack(pady=20)
    #logging.debug("NPC name label created.")

        # Add a label to display the portrait image.
        image_label = tk.Label(content_frame, image=portrait_img, bg="white")
        image_label.image = portrait_img  # persist reference
        image_label.pack(expand=True)
    #logging.debug("Portrait image label created.")
        new_x = screen_x + 0 #1920
        win.geometry(f"{screen_width}x{screen_height}+{new_x}+{screen_y}")
    #logging.debug(f"Window moved 1920 pixels to the right: new x-coordinate is {new_x}")
        # Bind a click event to close the window.
        win.bind("<Button-1>", lambda e: win.destroy())
    #logging.debug("Window displayed; waiting for click to close.")

    def delete_item(self, iid):
        self.items = [it for it in self.items
                    if sanitize_id(str(it.get(self.unique_field, ""))) != iid]
        self.model_wrapper.save_items(self.items)
        self.filter_items(self.search_var.get())

    def add_item(self):
        new = {}
        if self.open_editor(new, True):
            self.items.append(new)
            self.model_wrapper.save_items(self.items)
            self.filter_items(self.search_var.get())

    def open_editor(self, item, creation_mode=False):
        ed = GenericEditorWindow(
            self.master, item, self.template,
            self.model_wrapper, creation_mode
        )
        self.master.wait_window(ed)
        return getattr(ed, "saved", False)

    def filter_items(self, query):
        q = query.strip().lower()
        if q:
            self.filtered_items = [
                it for it in self.items
                if any(q in self.clean_value(v).lower() for v in it.values())
            ]
        else:
            self.filtered_items = list(self.items)
        self.refresh_list()

    def add_items(self, items):
        added = 0
        for itm in items:
            nid = sanitize_id(str(itm.get(self.unique_field, "")))
            if not any(sanitize_id(str(i.get(self.unique_field, ""))) == nid for i in self.items):
                self.items.append(itm)
                added += 1
        if added:
            self.model_wrapper.save_items(self.items)
            self.filter_items(self.search_var.get())