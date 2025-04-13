import tkinter as tk
import customtkinter as ctk
from modules.ui.tooltip import ToolTip

def create_icon_button(parent, icon, tooltip_text, command):
    # Use a container with a background matching your dark theme.
    container = tk.Frame(parent, bg="#2B2B2B")
    btn = ctk.CTkButton(
        container,
        text="",
        image=icon,
        command=command,
        width=80,
        height=80,
        corner_radius=12,
        fg_color="#0077CC",
        hover_color="#005fa3",
        border_width=1,
        border_color="#005fa3"
    )
    btn.pack()
    ToolTip(container, tooltip_text)
    return container