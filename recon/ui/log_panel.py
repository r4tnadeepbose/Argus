"""Thread-safe log widget: workers enqueue, the main loop drains."""

from __future__ import annotations

import queue
import tkinter as tk
from tkinter import scrolledtext, ttk


class LogPanel(ttk.LabelFrame):
    def __init__(self, master: tk.Misc, height: int = 14, **kwargs):
        super().__init__(master, text="Log", padding=6, **kwargs)
        self._queue: queue.Queue[str] = queue.Queue()
        self.text = scrolledtext.ScrolledText(
            self, state=tk.DISABLED, height=height, font=("Consolas", 9))
        self.text.pack(fill=tk.BOTH, expand=True)

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
