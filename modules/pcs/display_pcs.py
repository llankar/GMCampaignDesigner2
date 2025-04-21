import customtkinter as ctk

def display_pcs_in_banner(banner_frame, pcs_items):
    # Clear previous banner content
    for widget in banner_frame.winfo_children():
        widget.destroy()

    # Settings
    card_width = 300  # Wider card now
    visible_cards = 6  # 6 cards visible without scrolling
    banner_visible_width = card_width * visible_cards

    # Create scrollable canvas
    canvas = ctk.CTkCanvas(
        banner_frame,
        bg="#333",
        highlightthickness=0,
        width=banner_visible_width,
        height=300  # Match your banner height
    )
    scrollbar = ctk.CTkScrollbar(banner_frame, orientation="horizontal", command=canvas.xview)
    scrollable_frame = ctk.CTkFrame(canvas, fg_color="transparent")

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(xscrollcommand=scrollbar.set)

    canvas.pack(fill="both", expand=True)
    scrollbar.pack(fill="x", side="bottom")

    # Configure scrollable frame columns
    for idx in range(len(pcs_items)):
        scrollable_frame.grid_columnconfigure(idx, weight=0, minsize=card_width)

    col_idx = 0

    # Helper function to add compact labels
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
    # Populate all PCs into scrollable frame
    for pc_name, pc_data in pcs_items.items():
        pc_frame = ctk.CTkFrame(scrollable_frame, fg_color="#444", corner_radius=5)
        pc_frame.grid(row=0, column=col_idx, sticky="nsew", padx=5, pady=5)

        if pc_data.get("Name"):
            add_large_label(pc_frame, "Name", pc_data["Name"])

        if pc_data.get("Background"):
            add_label(pc_frame, "Background", pc_data["Background"])

        if pc_data.get("Secret"):
            add_label(pc_frame, "Secret", pc_data["Secret"])

        if pc_data.get("Traits"):
            add_label(pc_frame, "Traits", pc_data["Traits"])

        col_idx += 1