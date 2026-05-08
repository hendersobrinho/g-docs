from __future__ import annotations

import tkinter as tk
from tkinter import ttk


PALETTE = {
    "window": "#EEF3F8",
    "surface": "#FFFFFF",
    "surface_alt": "#F7FAFD",
    "border": "#D5DEE8",
    "border_strong": "#B8C7D8",
    "text": "#203040",
    "muted": "#617286",
    "accent": "#2F6FED",
    "accent_hover": "#255FD0",
    "accent_pressed": "#1E4FAA",
    "accent_soft": "#DCE9FF",
    "danger": "#C34747",
    "danger_hover": "#AE3737",
    "danger_pressed": "#8F2828",
    "danger_soft": "#F7DEDE",
    "disabled_bg": "#E8EEF5",
    "disabled_fg": "#8A99AA",
}


def configure_app_style(widget: tk.Misc) -> None:
    window = widget.winfo_toplevel()
    try:
        window.configure(background=PALETTE["window"])
    except tk.TclError:
        pass

    root = widget._root()
    if getattr(root, "_docflow_style_configured", False):
        return

    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    root.option_add("*TCombobox*Listbox.background", PALETTE["surface"])
    root.option_add("*TCombobox*Listbox.foreground", PALETTE["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", PALETTE["accent_soft"])
    root.option_add("*TCombobox*Listbox.selectForeground", PALETTE["text"])

    style.configure(
        ".",
        background=PALETTE["window"],
        foreground=PALETTE["text"],
    )
    style.configure("TFrame", background=PALETTE["window"])
    style.configure("TLabel", background=PALETTE["window"], foreground=PALETTE["text"])
    style.configure("Header.TLabel", background=PALETTE["window"], foreground=PALETTE["text"], font=("TkDefaultFont", 10, "bold"))
    style.configure("Subtle.TLabel", background=PALETTE["window"], foreground=PALETTE["muted"])

    style.configure(
        "TLabelframe",
        background=PALETTE["surface"],
        borderwidth=1,
        relief="solid",
        bordercolor=PALETTE["border"],
        lightcolor=PALETTE["border"],
        darkcolor=PALETTE["border"],
    )
    style.configure(
        "TLabelframe.Label",
        background=PALETTE["window"],
        foreground=PALETTE["text"],
        font=("TkDefaultFont", 10, "bold"),
    )

    style.configure(
        "TNotebook",
        background=PALETTE["window"],
        borderwidth=0,
        tabmargins=(0, 0, 0, 0),
    )
    style.configure(
        "TNotebook.Tab",
        padding=(16, 9),
        background="#E3EBF5",
        foreground="#506074",
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", PALETTE["surface"]), ("active", "#EDF3FB")],
        foreground=[("selected", PALETTE["text"]), ("active", "#344457")],
    )

    for input_style in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(
            input_style,
            fieldbackground=PALETTE["surface"],
            foreground=PALETTE["text"],
            bordercolor=PALETTE["border_strong"],
            lightcolor=PALETTE["surface"],
            darkcolor=PALETTE["border"],
            insertcolor=PALETTE["text"],
            padding=6,
        )
        style.map(
            input_style,
            fieldbackground=[("disabled", "#F2F5F8"), ("readonly", PALETTE["surface"]), ("!disabled", PALETTE["surface"])],
            foreground=[("disabled", PALETTE["disabled_fg"]), ("!disabled", PALETTE["text"])],
            bordercolor=[("focus", PALETTE["accent"]), ("!focus", PALETTE["border_strong"])],
        )

    style.configure(
        "Treeview",
        background=PALETTE["surface"],
        fieldbackground=PALETTE["surface"],
        foreground=PALETTE["text"],
        bordercolor=PALETTE["border"],
        lightcolor=PALETTE["border"],
        darkcolor=PALETTE["border"],
        rowheight=30,
    )
    style.map(
        "Treeview",
        background=[("selected", PALETTE["accent_soft"])],
        foreground=[("selected", PALETTE["text"])],
    )
    style.configure(
        "Treeview.Heading",
        background="#EAF0F7",
        foreground="#314153",
        borderwidth=1,
        relief="flat",
        padding=(10, 8),
        font=("TkDefaultFont", 9, "bold"),
    )
    style.map(
        "Treeview.Heading",
        background=[("active", "#E0E9F4")],
    )

    _configure_button_styles(style)
    _configure_menubutton_styles(style)
    root._docflow_style_configured = True


def _configure_button_styles(style: ttk.Style) -> None:
    base_layout = {
        "padding": (14, 9),
        "borderwidth": 1,
        "relief": "solid",
        "anchor": "center",
    }
    style.configure(
        "TButton",
        background=PALETTE["surface"],
        foreground=PALETTE["text"],
        bordercolor=PALETTE["border_strong"],
        lightcolor=PALETTE["surface"],
        darkcolor=PALETTE["border"],
        focuscolor=PALETTE["accent_soft"],
        **base_layout,
    )
    style.map(
        "TButton",
        background=[("disabled", PALETTE["disabled_bg"]), ("pressed", "#E7EEF8"), ("active", "#F7FAFD")],
        foreground=[("disabled", PALETTE["disabled_fg"]), ("!disabled", PALETTE["text"])],
        bordercolor=[("focus", PALETTE["accent"]), ("active", "#9FB4CC"), ("!disabled", PALETTE["border_strong"])],
        lightcolor=[("pressed", "#DDE7F4"), ("active", PALETTE["surface"]), ("!disabled", PALETTE["surface"])],
        darkcolor=[("pressed", "#B4C5DA"), ("!disabled", PALETTE["border"])],
    )

    style.configure(
        "Primary.TButton",
        background=PALETTE["accent"],
        foreground="#FFFFFF",
        bordercolor=PALETTE["accent_hover"],
        lightcolor="#5D8FF0",
        darkcolor=PALETTE["accent_hover"],
        focuscolor=PALETTE["accent_soft"],
        **base_layout,
    )
    style.map(
        "Primary.TButton",
        background=[("disabled", "#BFD0F6"), ("pressed", PALETTE["accent_pressed"]), ("active", PALETTE["accent_hover"])],
        foreground=[("disabled", "#F7FAFF"), ("!disabled", "#FFFFFF")],
        bordercolor=[("disabled", "#B0C3EF"), ("focus", PALETTE["accent_pressed"]), ("!disabled", PALETTE["accent_hover"])],
    )

    style.configure(
        "Secondary.TButton",
        background=PALETTE["surface"],
        foreground=PALETTE["text"],
        bordercolor="#AFC1D4",
        lightcolor=PALETTE["surface"],
        darkcolor=PALETTE["border"],
        focuscolor=PALETTE["accent_soft"],
        **base_layout,
    )
    style.map(
        "Secondary.TButton",
        background=[("disabled", PALETTE["disabled_bg"]), ("pressed", "#E3ECF8"), ("active", "#F2F7FD")],
        bordercolor=[("focus", PALETTE["accent"]), ("active", "#93B0D5"), ("!disabled", "#AFC1D4")],
    )

    style.configure(
        "Quiet.TButton",
        background="#F3F6FA",
        foreground="#435467",
        bordercolor=PALETTE["border"],
        lightcolor="#F7FAFD",
        darkcolor=PALETTE["border"],
        focuscolor=PALETTE["accent_soft"],
        **base_layout,
    )
    style.map(
        "Quiet.TButton",
        background=[("disabled", PALETTE["disabled_bg"]), ("pressed", "#E2E9F2"), ("active", "#F8FBFE")],
        bordercolor=[("focus", PALETTE["accent"]), ("!disabled", PALETTE["border"])],
    )

    style.configure(
        "Danger.TButton",
        background=PALETTE["danger_soft"],
        foreground="#7C2020",
        bordercolor="#D28C8C",
        lightcolor="#FAE9E9",
        darkcolor="#D28C8C",
        focuscolor="#F4C9C9",
        **base_layout,
    )
    style.map(
        "Danger.TButton",
        background=[("disabled", "#F3E5E5"), ("pressed", PALETTE["danger_pressed"]), ("active", PALETTE["danger_hover"])],
        foreground=[("disabled", "#BA9292"), ("pressed", "#FFFFFF"), ("active", "#FFFFFF"), ("!disabled", "#7C2020")],
        bordercolor=[("disabled", "#E2C8C8"), ("focus", PALETTE["danger_pressed"]), ("!disabled", "#D28C8C")],
    )

    style.configure(
        "Toolbar.TButton",
        padding=(8, 6),
        borderwidth=1,
        relief="solid",
    )


def _configure_menubutton_styles(style: ttk.Style) -> None:
    style.configure(
        "TMenubutton",
        background=PALETTE["surface"],
        foreground=PALETTE["text"],
        bordercolor=PALETTE["border_strong"],
        lightcolor=PALETTE["surface"],
        darkcolor=PALETTE["border"],
        padding=(12, 8),
        relief="solid",
    )
    style.map(
        "TMenubutton",
        background=[("disabled", PALETTE["disabled_bg"]), ("pressed", "#E7EEF8"), ("active", "#F7FAFD")],
        foreground=[("disabled", PALETTE["disabled_fg"]), ("!disabled", PALETTE["text"])],
        bordercolor=[("focus", PALETTE["accent"]), ("!disabled", PALETTE["border_strong"])],
    )
    style.configure(
        "Secondary.TMenubutton",
        background=PALETTE["surface"],
        foreground=PALETTE["text"],
        bordercolor="#AFC1D4",
        lightcolor=PALETTE["surface"],
        darkcolor=PALETTE["border"],
        padding=(12, 8),
        relief="solid",
    )

