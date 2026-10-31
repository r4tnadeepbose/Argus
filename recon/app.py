"""Application entry point."""

from __future__ import annotations


def main() -> None:
    """Start the Tkinter application."""
    try:
        import tkinter as tk
        from tkinter import ttk
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on interpreter
        print(f"[!] {exc}. This Python build has no Tkinter.")
        print("    Install python3-tk, or use a python.org Windows build.")
        return

    from .ui.main_window import ReconApp

    try:
        root = tk.Tk()
    except tk.TclError as exc:  # pragma: no cover - no display available
        print(f"[!] Cannot open a window: {exc}")
        return
    try:
        ttk.Style().theme_use("clam")
    except Exception:  # noqa: BLE001 - theme availability is platform-specific
        pass
    ReconApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
