"""Thread-safe log widget: workers enqueue, the main loop drains."""

from __future__ import annotations

import queue
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk


class LogPanel(ttk.Frame):
    def __init__(self, master: tk.Misc, height: int = 12,
                 on_clear: Callable[[], None] | None = None, **kwargs):
        super().__init__(master, **kwargs)
        self._queue: queue.Queue[str] = queue.Queue()

        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(6, 6))
        ttk.Label(header, text="LOG", style="Section.TLabel").pack(side=tk.LEFT)
        if on_clear:
            ttk.Button(header, text="clear", style="Ghost.TButton",
                       command=on_clear).pack(side=tk.RIGHT)

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)
        self.text = tk.Text(
            body, state=tk.DISABLED, height=height, wrap="none",
            relief="flat", borderwidth=0, highlightthickness=0,
            padx=14, pady=12)
        scrollbar = ttk.Scrollbar(body, orient=tk.VERTICAL, command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))

    def apply_palette(self, palette, fonts) -> None:
        self.text.configure(
            bg=palette.surface,
            fg=palette.text,
            insertbackground=palette.text,
            selectbackground=palette.select_bg,
            selectforeground=palette.select_fg,
            font=fonts["mono"],
        )

    def append(self, message: str) -> None:
        """Called from any thread."""
        self._queue.put(message)

    def drain(self) -> None:
        """Called from the Tk main thread."""
        try:
            while True:
                message = self._queue.get_nowait()
                self.text.config(state=tk.NORMAL)
                self.text.insert(tk.END, message + "\n")
                self.text.see(tk.END)
                self.text.config(state=tk.DISABLED)
        except queue.Empty:
            pass

    def clear(self) -> None:
        self.text.config(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.config(state=tk.DISABLED)
