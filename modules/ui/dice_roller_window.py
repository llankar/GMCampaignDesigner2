import random
import tkinter as tk
from datetime import datetime
from math import ceil, sqrt

import customtkinter as ctk
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from tkinter import messagebox

from modules.helpers.window_helper import position_window_at_top


DICE_TYPES = ("d4", "d6", "d8", "d10", "d12", "d20", "d100")


class DiceRollerWindow(ctk.CTkToplevel):
    """Interactive dice roller window with a 3D visualisation panel."""

    def __init__(self, master, on_close=None):
        super().__init__(master)
        self.title("Dice Roller")
        self.geometry("960x640")
        self.minsize(880, 560)
        self.transient(master)
        self._on_close_callback = on_close

        self.dice_type = tk.StringVar(value="d20")
        self.quantity_var = tk.StringVar(value="1")
        self.modifier_var = tk.StringVar(value="0")

        # 3D rendering helpers
        self.figure = Figure(figsize=(6, 5), facecolor="#1a1a1a")
        self.ax = self.figure.add_subplot(111, projection="3d")
        self.ax.set_facecolor("#1a1a1a")
        self.ax.view_init(elev=28, azim=35)
        self._update_view_vectors()
        self.light_direction = np.array([0.35, 0.45, 0.82])
        self.light_direction /= np.linalg.norm(self.light_direction)

        self.roll_history = []
        self._dice_buttons = {}

        self._build_ui()
        position_window_at_top(self, width=960, height=640)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=12, pady=12)

        controls_frame = ctk.CTkFrame(main_frame, width=260)
        controls_frame.pack(side="left", fill="y", padx=(0, 12), pady=6)
        controls_frame.pack_propagate(False)

        display_frame = ctk.CTkFrame(main_frame)
        display_frame.pack(side="left", fill="both", expand=True, pady=6)

        # Dice selector grid -------------------------------------------------
        selector_label = ctk.CTkLabel(
            controls_frame, text="Select Dice", font=("Segoe UI", 16, "bold")
        )
        selector_label.pack(pady=(18, 6))

        selector_grid = ctk.CTkFrame(controls_frame)
        selector_grid.pack(pady=(0, 18))

        for index, dice in enumerate(DICE_TYPES):
            button = ctk.CTkButton(
                selector_grid,
                text=dice.upper(),
                width=80,
                corner_radius=8,
                command=lambda d=dice: self._set_dice_type(d),
            )
            row, col = divmod(index, 2)
            button.grid(row=row, column=col, padx=6, pady=6, sticky="ew")
            self._dice_buttons[dice] = button

        self._highlight_selected_dice()

        # Quantity -----------------------------------------------------------
        quantity_label = ctk.CTkLabel(
            controls_frame, text="Number of Dice", font=("Segoe UI", 14)
        )
        quantity_label.pack()
        quantity_entry = ctk.CTkEntry(
            controls_frame, textvariable=self.quantity_var, justify="center"
        )
        quantity_entry.pack(pady=(4, 16))

        quick_row = ctk.CTkFrame(controls_frame)
        quick_row.pack(pady=(0, 16))
        for qty in (1, 2, 3, 4, 6, 8):
            btn = ctk.CTkButton(
                quick_row,
                text=str(qty),
                width=36,
                command=lambda q=qty: self.quantity_var.set(str(q)),
            )
            btn.pack(side="left", padx=3)

        # Modifier -----------------------------------------------------------
        modifier_label = ctk.CTkLabel(
            controls_frame, text="Modifier", font=("Segoe UI", 14)
        )
        modifier_label.pack()
        modifier_entry = ctk.CTkEntry(
            controls_frame, textvariable=self.modifier_var, justify="center"
        )
        modifier_entry.pack(pady=(4, 18))

        # Buttons ------------------------------------------------------------
        roll_button = ctk.CTkButton(
            controls_frame, text="Roll", font=("Segoe UI", 16, "bold"), command=self.roll_dice
        )
        roll_button.pack(pady=(0, 10), fill="x", padx=10)

        clear_button = ctk.CTkButton(
            controls_frame, text="Clear History", command=self.clear_history
        )
        clear_button.pack(fill="x", padx=10)

        # Results box --------------------------------------------------------
        history_label = ctk.CTkLabel(
            controls_frame, text="Roll History", font=("Segoe UI", 14, "bold")
        )
        history_label.pack(pady=(18, 6))

        self.results_box = ctk.CTkTextbox(controls_frame, height=220)
        self.results_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.results_box.configure(state="disabled")

        # Matplotlib canvas --------------------------------------------------
        canvas = FigureCanvasTkAgg(self.figure, master=display_frame)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.pack(fill="both", expand=True, padx=10, pady=10)
        self.canvas = canvas

        self._reset_axes()

    # ------------------------------------------------------------------
    # Dice Rolling Logic
    # ------------------------------------------------------------------
    def _set_dice_type(self, dice: str):
        self.dice_type.set(dice)
        self._highlight_selected_dice()

    def _highlight_selected_dice(self):
        selected = self.dice_type.get()
        for dice, btn in self._dice_buttons.items():
            if dice == selected:
                btn.configure(fg_color="#0091ff", hover_color="#0077cc")
            else:
                btn.configure(fg_color="#2a2a2a", hover_color="#3a3a3a")

    def _parse_int(self, value: str, fallback: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    def roll_dice(self):
        dice = self.dice_type.get()
        if not dice:
            return
        sides = int(dice[1:])
        quantity = self._parse_int(self.quantity_var.get(), fallback=1)
        modifier = self._parse_int(self.modifier_var.get(), fallback=0)

        if quantity <= 0:
            messagebox.showerror("Invalid quantity", "Please roll at least one die.")
            return
        if quantity > 30:
            messagebox.showerror(
                "Too many dice",
                "For performance reasons, please roll 30 dice or fewer at a time.",
            )
            return

        rolls = [random.randint(1, sides) for _ in range(quantity)]
        total = sum(rolls) + modifier

        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "dice": dice,
            "quantity": quantity,
            "modifier": modifier,
            "rolls": rolls,
            "total": total,
        }
        self.roll_history.append(entry)
        self._append_history_entry(entry)
        self._render_rolls(rolls, sides)

    def _append_history_entry(self, entry):
        text = (
            f"[{entry['timestamp']}] Rolled {entry['quantity']}{entry['dice']}"
            f" {'+' if entry['modifier'] >= 0 else ''}{entry['modifier']}\n"
            f"    Results: {', '.join(str(r) for r in entry['rolls'])}"
            f"  → Total: {entry['total']}\n"
        )
        self.results_box.configure(state="normal")
        self.results_box.insert("end", text)
        self.results_box.see("end")
        self.results_box.configure(state="disabled")

    def clear_history(self):
        self.roll_history.clear()
        self.results_box.configure(state="normal")
        self.results_box.delete("1.0", "end")
        self.results_box.configure(state="disabled")
        self._reset_axes()

    # ------------------------------------------------------------------
    # 3D Rendering Helpers
    # ------------------------------------------------------------------
    def _reset_axes(self):
        self.ax.cla()
        self.ax.set_facecolor("#1a1a1a")
        self.ax.set_axis_off()
        self.ax.view_init(elev=28, azim=35)
        self._update_view_vectors()
        self.ax.text(
            0.5,
            0.5,
            0.5,
            "Roll dice to see them here",
            color="#cccccc",
            ha="center",
            va="center",
            transform=self.ax.transAxes,
            fontsize=14,
        )
        self.canvas.draw_idle()

    def _render_rolls(self, rolls, sides):
        self.ax.cla()
        self.ax.set_axis_off()
        count = len(rolls)
        grid_cols = max(1, ceil(sqrt(count)))
        grid_rows = ceil(count / grid_cols)
        spacing = 2.2
        die_size = 1.0

        colors = self._color_palette_for_die(sides)

        for idx, value in enumerate(rolls):
            row = idx // grid_cols
            col = idx % grid_cols
            center = np.array([
                (col - (grid_cols - 1) / 2) * spacing,
                ((grid_rows - 1) / 2 - row) * spacing,
                0,
            ])
            orientation = self._random_orientation()
            color = colors[idx % len(colors)]
            self._draw_die(center, die_size, value, orientation, color)

        limit = spacing * max(grid_cols, grid_rows) / 1.8
        self.ax.set_xlim(-limit, limit)
        self.ax.set_ylim(-limit, limit)
        self.ax.set_zlim(-limit, limit)
        self.ax.view_init(elev=28, azim=35)
        self._update_view_vectors()
        self.canvas.draw_idle()

    def _draw_die(self, center, size, value, orientation, base_color):
        half = size / 2.0
        vertices = np.array([
            [-half, -half, -half],
            [half, -half, -half],
            [half, half, -half],
            [-half, half, -half],
            [-half, -half, half],
            [half, -half, half],
            [half, half, half],
            [-half, half, half],
        ])

        rotated = vertices @ orientation.T + center
        faces = [
            [rotated[idx] for idx in face]
            for face in ([0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6], [1, 2, 6, 5], [0, 3, 7, 4])
        ]

        face_colors = []
        for face in faces:
            normal = np.cross(face[1] - face[0], face[2] - face[0])
            normal_length = np.linalg.norm(normal)
            if normal_length == 0:
                intensity = 0.8
            else:
                normal /= normal_length
                intensity = 0.35 + 0.65 * max(0, np.dot(normal, self.light_direction))
            face_color = tuple(min(1.0, max(0.0, c * intensity)) for c in base_color)
            face_colors.append(face_color)

        collection = Poly3DCollection(faces, facecolors=face_colors, edgecolors="#111111", linewidths=1.0)
        self.ax.add_collection3d(collection)

        text_pos = center + np.array([0, 0, size * 0.75])
        self.ax.text(
            text_pos[0],
            text_pos[1],
            text_pos[2],
            str(value),
            color="white",
            ha="center",
            va="center",
            fontsize=16,
            fontweight="bold",
        )

    def _random_orientation(self):
        angles = np.radians(np.random.uniform(0, 360, size=3))
        cx, cy, cz = np.cos(angles)
        sx, sy, sz = np.sin(angles)

        rotation = np.array(
            [
                [cy * cz, -cy * sz, sy],
                [sx * sy * cz + cx * sz, cx * cz - sx * sy * sz, -sx * cy],
                [-cx * sy * cz + sx * sz, sx * cz + cx * sy * sz, cx * cy],
            ]
        )
        return rotation

    def _color_palette_for_die(self, sides):
        palettes = {
            4: [(0.91, 0.36, 0.29), (0.92, 0.54, 0.32)],
            6: [(0.27, 0.54, 0.95), (0.33, 0.78, 0.97)],
            8: [(0.48, 0.31, 0.83), (0.62, 0.41, 0.93)],
            10: [(0.24, 0.71, 0.58), (0.35, 0.83, 0.68)],
            12: [(0.95, 0.77, 0.25), (0.98, 0.61, 0.21)],
            20: [(0.94, 0.24, 0.59), (0.97, 0.36, 0.74)],
            100: [(0.52, 0.56, 0.95), (0.68, 0.72, 0.97)],
        }
        return palettes.get(sides, [(0.4, 0.4, 0.95), (0.6, 0.6, 0.98)])

    def _update_view_vectors(self):
        elev = np.deg2rad(self.ax.elev)
        azim = np.deg2rad(self.ax.azim)
        self.view_vector = np.array(
            [
                np.cos(elev) * np.cos(azim),
                np.cos(elev) * np.sin(azim),
                np.sin(elev),
            ]
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def _on_close(self):
        if callable(self._on_close_callback):
            try:
                self._on_close_callback()
            finally:
                self._on_close_callback = None
        self.destroy()
