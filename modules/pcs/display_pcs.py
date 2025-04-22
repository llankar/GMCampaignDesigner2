import customtkinter as ctk
from modules.helpers.text_helpers import format_multiline_text
def display_pcs_in_banner(banner_frame, pcs_items):
    # Clear previous banner content
    for widget in banner_frame.winfo_children():
        widget.destroy()

    # Settings
    card_width = 300  # Width for each PC card
    visible_cards = 6  # 6 cards visible without scrolling
    banner_visible_width = card_width * visible_cards
    banner_visible_height = 260  # Adjusted compact height

    # Create scrollable canvas
    canvas = ctk.CTkCanvas(
        banner_frame,
        bg="#333",
        highlightthickness=0,
        width=banner_visible_width,
        height=banner_visible_height
    )

    h_scrollbar = ctk.CTkScrollbar(banner_frame, orientation="horizontal", command=canvas.xview)
    v_scrollbar = ctk.CTkScrollbar(banner_frame, orientation="vertical", command=canvas.yview)

    scrollable_frame = ctk.CTkFrame(canvas, fg_color="transparent")

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)

    # Pack the elements
    canvas.grid(row=0, column=0, sticky="nsew")
    v_scrollbar.grid(row=0, column=1, sticky="ns")
    h_scrollbar.grid(row=1, column=0, sticky="ew")

    banner_frame.grid_rowconfigure(0, weight=1)
    banner_frame.grid_columnconfigure(0, weight=1)

    # Enable mousewheel vertical scroll
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # Layout settings
    max_columns = visible_cards  # 6 cards per row
    row_idx = 0
    col_idx = 0

    # Helper functions to add labels
    def add_label(parent, title, content):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=2, padx=3)

        label_title = ctk.CTkLabel(frame, text=f"{title}:", font=("Segoe UI", 15, "bold"), anchor="w")
        label_title.pack(fill="x")

        label_content = ctk.CTkLabel(
            frame, text=content, font=("Segoe UI", 14),
            anchor="w", justify="left", wraplength=card_width - 20
        )
        label_content.pack(fill="x")

    def add_large_label(parent, title, content):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=2, padx=3)
        label_content = ctk.CTkLabel(
            frame, text=content, font=("Segoe UI", 15, "bold"),
            anchor="w", justify="left", wraplength=card_width - 20
        )
        label_content.pack(fill="x")

    # Populate all PCs
    for pc_name, pc_data in pcs_items.items():
        pc_frame = ctk.CTkFrame(scrollable_frame, fg_color="#444", corner_radius=5)
        pc_frame.grid(row=row_idx, column=col_idx, sticky="nsew", padx=5, pady=5)

        if pc_data.get("Name"):
            add_large_label(pc_frame, "Name", pc_data["Name"])

        if pc_data.get("Background"):
            add_label(pc_frame, "Background",format_multiline_text( pc_data["Background"]))

        if pc_data.get("Secret"):
            add_label(pc_frame, "Secret", format_multiline_text(pc_data["Secret"]))

        if pc_data.get("Traits"):
            add_label(pc_frame, "Traits", format_multiline_text(pc_data["Traits"]))

        # Move to next column/row
        col_idx += 1
        if col_idx >= max_columns:
            col_idx = 0
            row_idx += 1