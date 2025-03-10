import customtkinter as ctk
from tkinter import ttk
import logging
from PIL import Image, ImageTk
import os

class NPCGraphCanvas(ctk.CTkCanvas):
    def __init__(self, master, editor):
        super().__init__(master, bg="#ffffff", highlightthickness=0)
        self.editor = editor

        self.bind("<Button-1>", self.on_canvas_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<MouseWheel>", self._on_mousewheel_y)
        self.bind("<Shift-MouseWheel>", self._on_mousewheel_x)
        self.bind("<Button-4>", self._on_mousewheel_y)
        self.bind("<Button-5>", self._on_mousewheel_y)
        self.bind("<Shift-Button-4>", self._on_mousewheel_x)
        self.bind("<Shift-Button-5>", self._on_mousewheel_x)

    def _on_mousewheel_y(self, event):
        if event.num == 4 or event.delta > 0:
            self.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.yview_scroll(1, "units")

    def _on_mousewheel_x(self, event):
        if event.num == 4 or event.delta > 0:
            self.xview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.xview_scroll(1, "units")

    def on_canvas_click(self, event):
        item = self.find_closest(event.x, event.y)
        if not item:
            return
        item_id = item[0]
        tags = self.gettags(item_id)
        logging.debug(f"Clicked item ID: {item_id}, tags: {tags}")

        if "object" in tags:
            self.editor.select_object(item_id)
        else:
            self.editor.start_drag(event)

    def on_drag(self, event):
        if not self.editor.selected_node or not self.editor.drag_start:
            return

        dx = event.x - self.editor.drag_start[0]
        dy = event.y - self.editor.drag_start[1]

        for item in self.editor.selected_items:
            self.move(item, dx, dy)

        x, y = self.editor.node_positions[self.editor.selected_node]
        self.editor.node_positions[self.editor.selected_node] = (x + dx, y + dy)

        self.editor.drag_start = (event.x, event.y)

        bbox = self.bbox("all")
        if bbox:
            padding = 50
            scroll_region = (bbox[0]-padding, bbox[1]-padding, bbox[2]+padding, bbox[3]+padding)
            self.configure(scrollregion=scroll_region)

        self.editor.draw_graph()

    def draw_graph(self):
        self.delete("all")
        self.editor.node_images.clear()

        NODE_WIDTH = 100
        TEXT_LINE_HEIGHT = 14
        TEXT_TOTAL_HEIGHT = 2 * TEXT_LINE_HEIGHT + 4
        TEXT_PADDING = 5

        for link in self.editor.graph["links"]:
            npc_name1 = link["npc_name1"]
            npc_name2 = link["npc_name2"]
            link_text = link["text"]

            tag1 = f"npc_{npc_name1.replace(' ', '_')}"
            tag2 = f"npc_{npc_name2.replace(' ', '_')}"

            x1, y1 = self.editor.node_positions.get(tag1, (0, 0))
            x2, y2 = self.editor.node_positions.get(tag2, (0, 0))

            self.create_line(x1, y1, x2, y2, fill="black", tags=("link",))

            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2

            self.create_text(mid_x, mid_y, text=link_text, fill="red", font=("Arial", 10, "bold"), tags=("link_text",))

        for node in self.editor.graph["nodes"]:
            npc_name = node["npc_name"]
            tag = f"npc_{npc_name.replace(' ', '_')}"
            x, y = self.editor.node_positions.get(tag, (node["x"], node["y"]))

            portrait_path = self.editor.npcs.get(npc_name, {}).get("Portrait", "")
            has_portrait = portrait_path and os.path.exists(portrait_path)

            portrait_height = 0
            portrait_width = 0

            if has_portrait:
                img = Image.open(portrait_path)
                original_width, original_height = img.size

                max_portrait_width = NODE_WIDTH - 4
                max_portrait_height = 80

                ratio = min(max_portrait_width / original_width, max_portrait_height / original_height)
                portrait_width = int(original_width * ratio)
                portrait_height = int(original_height * ratio)

                img = img.resize((portrait_width, portrait_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)

                self.editor.node_images[npc_name] = photo

            node_height = portrait_height + TEXT_TOTAL_HEIGHT + (TEXT_PADDING if has_portrait else 0)

            self.create_rectangle(
                x - NODE_WIDTH // 2, y - node_height // 2,
                x + NODE_WIDTH // 2, y + node_height // 2,
                fill="lightblue", tags=(tag,)
            )

            if has_portrait:
                self.create_image(
                    x, y - node_height // 2 + portrait_height // 2,
                    image=self.editor.node_images[npc_name], tags=(tag,)
                )

            words = npc_name.split()
            if len(words) >= 2:
                wrapped_name = f"{words[0]}\n{' '.join(words[1:])}"
            else:
                wrapped_name = npc_name

            if has_portrait:
                text_y = y - node_height // 2 + portrait_height + TEXT_PADDING + TEXT_LINE_HEIGHT // 2 + 2
            else:
                text_y = y

            self.create_text(
                x, text_y,
                text=wrapped_name,
                fill="black",
                font=("Arial", 9, "bold"),
                width=NODE_WIDTH - 4,
                justify="center",
                tags=(tag,)
            )

        for obj in self.editor.graph["objects"]:
            if obj["type"] == "rectangle":
                rect_id = self.create_rectangle(obj["x1"], obj["y1"], obj["x2"], obj["y2"], fill="green", tags="object")
                if obj["id"] == self.editor.selected_object:
                    self.editor.selected_object = rect_id
                    self.editor.select_object(rect_id)

        self.update_idletasks()
        bbox = self.bbox("all")
        if bbox:
            padding = 50
            scroll_region = (bbox[0]-padding, bbox[1]-padding, bbox[2]+padding, bbox[3]+padding)
            self.configure(scrollregion=scroll_region)
