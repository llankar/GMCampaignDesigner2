import re
import time
import os, ctypes
from ctypes import wintypes
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from modules.generic.generic_editor_window import GenericEditorWindow
from modules.ui.image_viewer import show_portrait

PORTRAIT_FOLDER = "assets/portraits"
MAX_PORTRAIT_SIZE = (1024, 1024)
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


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

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.on_right_click)
        self._tooltip = _ToolTip(self.tree)

        self.refresh_list()
    
    def show_portrait_window(self, iid):
        item = next((it for it in self.filtered_items
                    if sanitize_id(str(it.get(self.unique_field, ""))) == iid),
                    None)
        if not item:
            messagebox.showerror("Error", "Item not found.")
            return
        path = item.get("Portrait", "")
        title = str(item.get(self.unique_field, ""))
        # Delegate to our new helper
        show_portrait(path, title)

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
        # only show portrait if the item actually has one
        item = next((it for it in self.filtered_items
                    if sanitize_id(str(it.get(self.unique_field, ""))) == iid),
                    None)
        portrait_path = item.get("Portrait", "") if item else ""
        has_portrait = bool(portrait_path and os.path.exists(portrait_path))

        menu = tk.Menu(self, tearoff=0)
        if has_portrait:
            menu.add_command(label="Show Portrait",
                            command=lambda: self.show_portrait_window(iid))
        menu.add_command(label="Delete",
                        command=lambda: self.delete_item(iid))
        menu.post(event.x_root, event.y_root)
    
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
            if not any(sanitize_id(str(i.get(self.unique_field, ""))) == nid
                    for i in self.items):
                self.items.append(itm)
                added += 1
        if added:
            self.model_wrapper.save_items(self.items)
            self.filter_items(self.search_var.get())