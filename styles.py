import tkinter as tk
from tkinter import ttk


class AppStyles:
    COLORS = {
        "primary": "#2563eb",         # tailwind blue-600
        "primary_dark": "#1d4ed8",    # tailwind blue-700
        "primary_light": "#dbeafe",   # tailwind blue-100
        "secondary": "#64748b",       # tailwind slate-500
        "success": "#10b981",         # tailwind emerald-500
        "success_dark": "#059669",    # tailwind emerald-600
        "danger": "#e11d48",          # tailwind rose-600
        "danger_dark": "#be123c",     # tailwind rose-700
        "warning": "#f59e0b",         # tailwind amber-500
        "warning_dark": "#d97706",    # tailwind amber-600
        "info": "#0ea5e9",            # tailwind sky-500
        "dark": "#0f172a",            # tailwind slate-900
        "dark_secondary": "#334155",  # tailwind slate-700
        "light": "#f1f5f9",           # tailwind slate-100
        "white": "#ffffff",
        "border": "#cbd5e1",          # tailwind slate-300
        "text_primary": "#0f172a",    # tailwind slate-900
        "text_secondary": "#475569",  # tailwind slate-600
        "text_light": "#94a3b8",      # tailwind slate-400
        "hover": "#f8fafc",           # tailwind slate-50
        "selected": "#e2e8f0",        # tailwind slate-200
        "header_bg": "#f8fafc",       # tailwind slate-50
        "card_bg": "#ffffff",
        "shadow": "#00000010",
        "customer_name_bg": "#dbeafe",  # highlight for customer name rows
    }

    FONTS = {
        "title": ("Segoe UI", 16, "bold"),
        "subtitle": ("Segoe UI", 13, "bold"),
        "heading": ("Segoe UI", 11, "bold"),
        "body": ("Segoe UI", 10),
        "body_bold": ("Segoe UI", 10, "bold"),
        "small": ("Segoe UI", 9),
        "small_bold": ("Segoe UI", 9, "bold"),
        "button": ("Segoe UI", 10, "bold"),
        "entry": ("Segoe UI", 10),
    }

    PADDING = {
        "small": 5,
        "medium": 10,
        "large": 15,
        "xlarge": 20,
    }

    @classmethod
    def setup_theme(cls, root):
        style = ttk.Style(root)
        style.theme_use("clam")

        style.configure(".", background=cls.COLORS["light"])
        style.configure(".", foreground=cls.COLORS["text_primary"])
        style.configure(".", font=cls.FONTS["body"])

        style.configure(
            "Card.TFrame",
            background=cls.COLORS["white"],
            relief="solid",
            borderwidth=1,
        )

        style.configure(
            "Header.TFrame",
            background=cls.COLORS["primary"],
        )

        style.configure(
            "Title.TLabel",
            font=cls.FONTS["title"],
            foreground=cls.COLORS["text_primary"],
            background=cls.COLORS["light"],
        )

        style.configure(
            "Subtitle.TLabel",
            font=cls.FONTS["subtitle"],
            foreground=cls.COLORS["text_primary"],
            background=cls.COLORS["light"],
        )

        style.configure(
            "Section.TLabelframe",
            background=cls.COLORS["white"],
            foreground=cls.COLORS["text_primary"],
            font=cls.FONTS["heading"],
            relief="solid",
            borderwidth=1,
        )

        style.configure(
            "Section.TLabelframe.Label",
            font=cls.FONTS["heading"],
            foreground=cls.COLORS["primary"],
            background=cls.COLORS["white"],
            padding=8,
        )

        style.configure(
            "Treeview",
            background=cls.COLORS["white"],
            foreground=cls.COLORS["text_primary"],
            fieldbackground=cls.COLORS["white"],
            rowheight=26,
            font=cls.FONTS["body"],
        )

        style.configure(
            "Treeview.Heading",
            background=cls.COLORS["header_bg"],
            foreground=cls.COLORS["text_primary"],
            font=cls.FONTS["body_bold"],
            relief="flat",
            borderwidth=0,
            padding=[5, 8],
        )

        style.map(
            "Treeview",
            background=[
                ("selected", cls.COLORS["selected"]),
                ("hover", cls.COLORS["hover"]),
            ],
        )

        style.map(
            "Treeview.Heading",
            background=[
                ("pressed", cls.COLORS["border"]),
                ("active", cls.COLORS["border"]),
            ],
        )

        style.configure(
            "TEntry",
            font=cls.FONTS["entry"],
            fieldbackground=cls.COLORS["white"],
            insertcolor=cls.COLORS["primary"],
        )

        style.configure(
            "TCombobox",
            font=cls.FONTS["body"],
            fieldbackground=cls.COLORS["white"],
        )

        style.map(
            "TCombobox",
            fieldbackground=[
                ("readonly", cls.COLORS["white"]),
            ],
        )

        style.configure(
            "Primary.TButton",
            font=cls.FONTS["button"],
            background=cls.COLORS["primary"],
            foreground=cls.COLORS["white"],
            padding=(8, 4),
            relief="flat",
        )

        style.map(
            "Primary.TButton",
            background=[
                ("active", cls.COLORS["primary_dark"]),
                ("pressed", cls.COLORS["primary_dark"]),
            ],
        )

        style.configure(
            "Success.TButton",
            font=cls.FONTS["button"],
            background=cls.COLORS["success"],
            foreground=cls.COLORS["white"],
            padding=(8, 4),
            relief="flat",
        )

        style.map(
            "Success.TButton",
            background=[
                ("active", cls.COLORS["success_dark"]),
                ("pressed", cls.COLORS["success_dark"]),
            ],
        )

        style.configure(
            "Danger.TButton",
            font=cls.FONTS["button"],
            background=cls.COLORS["danger"],
            foreground=cls.COLORS["white"],
            padding=(8, 4),
            relief="flat",
        )

        style.map(
            "Danger.TButton",
            background=[
                ("active", cls.COLORS["danger_dark"]),
                ("pressed", cls.COLORS["danger_dark"]),
            ],
        )

        style.configure(
            "Warning.TButton",
            font=cls.FONTS["button"],
            background=cls.COLORS["warning"],
            foreground=cls.COLORS["dark"],
            padding=(8, 4),
            relief="flat",
        )

        style.map(
            "Warning.TButton",
            background=[
                ("active", cls.COLORS["warning_dark"]),
                ("pressed", cls.COLORS["warning_dark"]),
            ],
        )

        style.configure(
            "Secondary.TButton",
            font=cls.FONTS["button"],
            background=cls.COLORS["secondary"],
            foreground=cls.COLORS["white"],
            padding=(8, 4),
            relief="flat",
        )

        style.map(
            "Secondary.TButton",
            background=[
                ("active", cls.COLORS["dark_secondary"]),
                ("pressed", cls.COLORS["dark_secondary"]),
            ],
        )

        style.configure(
            "TNotebook",
            background=cls.COLORS["light"],
            tabmargins=[2, 5, 0, 0],
        )

        style.configure(
            "TNotebook.Tab",
            font=cls.FONTS["body_bold"],
            foreground=cls.COLORS["text_secondary"],
            background=cls.COLORS["light"],
            padding=[10, 5],
            relief="flat",
        )

        style.map(
            "TNotebook.Tab",
            background=[
                ("selected", cls.COLORS["white"]),
                ("active", cls.COLORS["hover"]),
            ],
            foreground=[
                ("selected", cls.COLORS["primary"]),
                ("active", cls.COLORS["text_primary"]),
            ],
        )

        style.configure(
            "TScrollbar",
            background=cls.COLORS["light"],
            troughcolor=cls.COLORS["white"],
            arrowcolor=cls.COLORS["secondary"],
            relief="flat",
        )

        root.configure(bg=cls.COLORS["light"])

        return style


def create_card(parent, **kwargs):
    frame = tk.Frame(
        parent,
        bg=AppStyles.COLORS["white"],
        highlightbackground=AppStyles.COLORS["border"],
        highlightthickness=1,
        **kwargs,
    )
    return frame


def create_section_label(parent, text, **kwargs):
    label = tk.Label(
        parent,
        text=text,
        font=AppStyles.FONTS["heading"],
        fg=AppStyles.COLORS["primary"],
        bg=AppStyles.COLORS["white"],
        **kwargs,
    )
    return label


def create_title_label(parent, text, **kwargs):
    label = tk.Label(
        parent,
        text=text,
        font=AppStyles.FONTS["title"],
        fg=AppStyles.COLORS["text_primary"],
        bg=AppStyles.COLORS["light"],
        **kwargs,
    )
    return label


def create_stat_card(parent, title, value, color=AppStyles.COLORS["primary"], **kwargs):
    card = create_card(parent, **kwargs)

    title_label = tk.Label(
        card,
        text=title,
        font=AppStyles.FONTS["small"],
        fg=AppStyles.COLORS["text_secondary"],
        bg=AppStyles.COLORS["white"],
    )
    title_label.pack(pady=(8, 2), padx=10)

    value_label = tk.Label(
        card,
        text=value,
        font=("Segoe UI", 18, "bold"),
        fg=color,
        bg=AppStyles.COLORS["white"],
    )
    value_label.pack(pady=(0, 10), padx=12)

    return card, value_label


def styled_button(parent, text, command, style="Primary", **kwargs):
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        font=AppStyles.FONTS["button"],
        cursor="hand2",
        **kwargs,
    )

    colors = {
        "Primary": (AppStyles.COLORS["primary"], AppStyles.COLORS["white"]),
        "Success": (AppStyles.COLORS["success"], AppStyles.COLORS["white"]),
        "Danger": (AppStyles.COLORS["danger"], AppStyles.COLORS["white"]),
        "Warning": (AppStyles.COLORS["warning"], AppStyles.COLORS["dark"]),
        "Secondary": (AppStyles.COLORS["secondary"], AppStyles.COLORS["white"]),
    }

    bg, fg = colors.get(style, colors["Primary"])

    btn.configure(
        bg=bg,
        fg=fg,
        activebackground=bg,
        activeforeground=fg,
        relief="flat",
        padx=10,
        pady=5,
        bd=0,
    )

    def on_enter(e):
        btn.configure(
            bg=AppStyles.COLORS.get(f"{style.lower()}_dark", bg)
            if style != "Warning"
            else AppStyles.COLORS["warning_dark"]
        )

    def on_leave(e):
        btn.configure(bg=bg)

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)

    return btn


def create_input_field(parent, label_text, row, col, width=20, span=1):
    label = tk.Label(
        parent,
        text=label_text,
        font=AppStyles.FONTS["small"],
        fg=AppStyles.COLORS["text_secondary"],
        bg=AppStyles.COLORS["white"],
        anchor="w",
    )
    label.grid(row=row, column=col, sticky="w", padx=5, pady=(5, 2))

    entry = tk.Entry(
        parent,
        font=AppStyles.FONTS["body"],
        width=width,
        relief="solid",
        bd=1,
        bg=AppStyles.COLORS["white"],
        insertbackground=AppStyles.COLORS["primary"],
    )
    entry.grid(
        row=row + 1, column=col, sticky="w", padx=5, pady=(0, 5), columnspan=span
    )

    return entry


def make_scrollable(parent):
    """Wrap a frame's content in a vertical scrollable canvas. Returns scrollable_frame."""
    bg = AppStyles.COLORS["light"]

    outer = tk.Frame(parent, bg=bg)
    outer.pack(fill="both", expand=True)

    scrollbar = ttk.Scrollbar(outer, orient="vertical")
    scrollbar.pack(side="right", fill="y")

    canvas = tk.Canvas(outer, bg=bg, highlightthickness=0, yscrollcommand=scrollbar.set)
    scrollbar.config(command=canvas.yview)
    canvas.pack(side="left", fill="both", expand=True)

    frame = tk.Frame(canvas, bg=bg)
    canvas.create_window((0, 0), window=frame, anchor="nw", tags="frame")

    frame.bind(
        "<Configure>",
        lambda e: canvas.after(10, lambda: canvas.configure(scrollregion=canvas.bbox("all")))
    )
    canvas.bind("<Configure>", lambda e: canvas.itemconfig("frame", width=e.width))
    canvas.bind(
        "<Enter>",
        lambda e: canvas.bind_all(
            "<MouseWheel>",
            lambda ev: canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units")
        )
    )
    canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    return frame
