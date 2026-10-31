"""Minimal retro-modern theme: palettes and ttk style configuration.

Two palettes are provided: ``SLATE`` (dark) and ``PAPER`` (warm light).
Importing this module does not require Tkinter; ``apply`` imports it lazily.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str
    surface: str
    surface_alt: str
    border: str
    text: str
    muted: str
    accent: str
    accent_text: str
    accent_soft: str
    accent_soft_text: str
    danger: str
    success: str
    select_bg: str
    select_fg: str


SLATE = Palette(
    name="Slate",
    bg="#16181b",
    surface="#1e2126",
    surface_alt="#23262c",
    border="#2f343b",
    text="#e8e4dc",
    muted="#8d887f",
    accent="#d99a5b",
    accent_text="#1b1611",
    accent_soft="#33291d",
    accent_soft_text="#e7c9a1",
    danger="#cf7b6d",
    success="#8fbf9f",
    select_bg="#343b44",
    select_fg="#f3efe8",
)

PAPER = Palette(
    name="Paper",
    bg="#f1eee8",
    surface="#fbf9f4",
    surface_alt="#f6f2ea",
    border="#ddd6ca",
    text="#24211c",
    muted="#8b8378",
    accent="#b4552d",
    accent_text="#fff8f1",
    accent_soft="#efdccb",
    accent_soft_text="#76351b",
    danger="#a8442f",
    success="#4f7d5a",
    select_bg="#ead8c3",
    select_fg="#24211c",
)

PALETTES = {"dark": SLATE, "light": PAPER}

_UI_FAMILIES = (
    "Segoe UI Variable Text", "Segoe UI", "Inter", "Cantarell", "Ubuntu",
    "Noto Sans", "DejaVu Sans", "Helvetica",
)
_MONO_FAMILIES = (
    "Cascadia Mono", "Cascadia Code", "JetBrains Mono", "Consolas",
    "Ubuntu Mono", "DejaVu Sans Mono", "Liberation Mono", "Courier New",
)


def _pick_family(root, families: tuple[str, ...]) -> str:
    from tkinter import font as tkfont

    available = set(tkfont.families(root))
    return next((family for family in families if family in available), families[-1])


def set_titlebar_dark(root, dark: bool) -> None:
    """Best-effort native dark title bar on Windows 10/11. No-op elsewhere."""
    import sys

    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        value = ctypes.c_int(1 if dark else 0)
        for attribute in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (new/old builds)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value))
        # Without a frame refresh Windows keeps the old caption until redraw.
        swp_flags = 0x0020 | 0x0001 | 0x0002 | 0x0004  # FRAMECHANGED|NOSIZE|NOMOVE|NOZORDER
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, swp_flags)
    except Exception:  # noqa: BLE001 - cosmetic only
        pass


def apply(root, style, palette: Palette) -> dict:
    """Configure every ttk style used by the app. Returns the font objects."""
    from tkinter import font as tkfont

    ui = _pick_family(root, _UI_FAMILIES)
    mono = _pick_family(root, _MONO_FAMILIES)
    fonts = {
        "ui": tkfont.Font(root=root, family=ui, size=10),
        "ui_bold": tkfont.Font(root=root, family=ui, size=10, weight="bold"),
        "small": tkfont.Font(root=root, family=ui, size=9),
        "section": tkfont.Font(root=root, family=ui, size=8, weight="bold"),
        "title": tkfont.Font(root=root, family=ui, size=19, weight="bold"),
        "table": tkfont.Font(root=root, family=ui, size=9),
        "mono": tkfont.Font(root=root, family=mono, size=9),
    }

    try:
        style.theme_use("clam")
    except Exception:  # noqa: BLE001 - exotic Tk builds may lack clam
        pass
    root.configure(bg=palette.bg)

    style.configure(
        ".",
        background=palette.bg,
        foreground=palette.text,
        fieldbackground=palette.surface,
        bordercolor=palette.border,
        lightcolor=palette.bg,
        darkcolor=palette.bg,
        troughcolor=palette.surface_alt,
        focuscolor=palette.accent,
        font=fonts["ui"],
        borderwidth=0,
    )

    # frames and labels
    style.configure("TFrame", background=palette.bg)
    style.configure("Surface.TFrame", background=palette.surface)
    style.configure("TLabel", background=palette.bg, foreground=palette.text,
                    font=fonts["ui"])
    style.configure("Muted.TLabel", background=palette.bg, foreground=palette.muted,
                    font=fonts["small"])
    style.configure("Section.TLabel", background=palette.bg, foreground=palette.muted,
                    font=fonts["section"])
    style.configure("Title.TLabel", background=palette.bg, foreground=palette.text,
                    font=fonts["title"])
    style.configure("Accent.TLabel", background=palette.bg, foreground=palette.accent,
                    font=fonts["section"])
    style.configure("TSeparator", background=palette.border)

    # buttons
    style.configure(
        "TButton",
        background=palette.surface,
        foreground=palette.text,
        padding=(14, 7),
        relief="flat",
        borderwidth=0,
        focusthickness=0,
        font=fonts["ui"],
    )
    style.map(
        "TButton",
        background=[("disabled", palette.bg), ("pressed", palette.border),
                    ("active", palette.surface_alt)],
        foreground=[("disabled", palette.muted)],
    )
    style.configure(
        "Accent.TButton",
        background=palette.accent,
        foreground=palette.accent_text,
        padding=(20, 7),
        font=fonts["ui_bold"],
    )
    style.map(
        "Accent.TButton",
        background=[("disabled", palette.surface_alt), ("pressed", palette.danger),
                    ("active", palette.accent)],
        foreground=[("disabled", palette.muted)],
    )
    style.configure(
        "Ghost.TButton",
        background=palette.bg,
        foreground=palette.muted,
        padding=(10, 6),
        font=fonts["small"],
    )
    style.map(
        "Ghost.TButton",
        background=[("pressed", palette.surface), ("active", palette.surface_alt)],
        foreground=[("active", palette.text)],
    )
    style.configure(
        "Danger.TButton",
        background=palette.bg,
        foreground=palette.danger,
        padding=(14, 7),
        font=fonts["ui"],
    )
    style.map(
        "Danger.TButton",
        background=[("disabled", palette.bg), ("active", palette.surface_alt),
                    ("pressed", palette.surface)],
        foreground=[("disabled", palette.muted)],
    )

    # inputs
    for entry_style in ("TEntry", "TSpinbox"):
        style.configure(
            entry_style,
            fieldbackground=palette.surface,
            foreground=palette.text,
            insertcolor=palette.text,
            bordercolor=palette.border,
            lightcolor=palette.surface,
            darkcolor=palette.surface,
            arrowcolor=palette.muted,
            padding=(9, 6),
            relief="flat",
            borderwidth=1,
        )
        style.map(
            entry_style,
            bordercolor=[("focus", palette.accent)],
            fieldbackground=[("disabled", palette.surface_alt)],
            foreground=[("disabled", palette.muted)],
        )

    style.configure(
        "TCheckbutton",
        background=palette.bg,
        foreground=palette.text,
        indicatorcolor=palette.surface,
        font=fonts["small"],
        padding=(0, 5),
    )
    style.map(
        "TCheckbutton",
        background=[("active", palette.bg)],
        indicatorcolor=[("selected", palette.accent), ("!selected", palette.surface)],
        foreground=[("disabled", palette.muted)],
    )

    # options render as toggle chips (no default indicator box)
    style.configure(
        "Toggle.Toolbutton",
        background=palette.bg,
        foreground=palette.muted,
        bordercolor=palette.border,
        lightcolor=palette.bg,
        darkcolor=palette.bg,
        padding=(12, 6),
        relief="flat",
        borderwidth=1,
        font=fonts["small"],
    )
    style.map(
        "Toggle.Toolbutton",
        background=[("selected", palette.accent_soft), ("active", palette.surface)],
        foreground=[("selected", palette.accent_soft_text), ("active", palette.text)],
        bordercolor=[("selected", palette.accent), ("!selected", palette.border),
                     ("active", palette.border)],
        lightcolor=[("selected", palette.accent_soft)],
        darkcolor=[("selected", palette.accent_soft)],
    )

    # results table
    style.configure(
        "Treeview",
        background=palette.surface,
        fieldbackground=palette.surface,
        foreground=palette.text,
        borderwidth=0,
        relief="flat",
        rowheight=29,
        font=fonts["table"],
    )
    style.map(
        "Treeview",
        background=[("selected", palette.select_bg)],
        foreground=[("selected", palette.select_fg)],
    )
    style.configure(
        "Treeview.Heading",
        background=palette.bg,
        foreground=palette.muted,
        relief="flat",
        borderwidth=0,
        padding=(8, 9),
        font=fonts["section"],
    )
    style.map("Treeview.Heading", background=[("active", palette.surface_alt)])

    # progress and scrollbars
    style.configure(
        "Accent.Horizontal.TProgressbar",
        troughcolor=palette.surface_alt,
        background=palette.accent,
        bordercolor=palette.surface_alt,
        lightcolor=palette.accent,
        darkcolor=palette.accent,
        thickness=4,
        borderwidth=0,
    )
    for orient in ("Vertical", "Horizontal"):
        style.configure(
            f"{orient}.TScrollbar",
            background=palette.border,
            troughcolor=palette.bg,
            bordercolor=palette.bg,
            arrowcolor=palette.muted,
            gripcount=0,
            relief="flat",
            width=10,
        )
        style.map(f"{orient}.TScrollbar",
                  background=[("active", palette.muted), ("pressed", palette.muted)])

    # paned window sashes
    style.configure("TPanedwindow", background=palette.bg)
    style.configure("Sash", background=palette.bg, sashthickness=10, gripcount=0,
                    lightcolor=palette.border, darkcolor=palette.border,
                    bordercolor=palette.border)

    return fonts
