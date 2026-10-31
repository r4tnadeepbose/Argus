"""Results table showing live hosts, tech and takeover verdicts."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Mapping
from tkinter import ttk
from typing import Any

_COLUMNS = ("status", "host", "title", "tech", "takeover")
_WIDTHS = {"status": 60, "host": 280, "title": 380, "tech": 240, "takeover": 90}


class ResultsTable(ttk.LabelFrame):
    def __init__(self, master: tk.Misc,
                 on_open: Callable[[str], None] | None = None,
                 **kwargs):
        super().__init__(master, text="Results", padding=6, **kwargs)
        self._on_open = on_open
        self.tree = ttk.Treeview(self, columns=_COLUMNS, show="headings", height=10)
        for column in _COLUMNS:
            self.tree.heading(column, text=column.capitalize())
            self.tree.column(column, width=_WIDTHS[column], anchor=tk.W,
                             stretch=column in ("title", "tech"))
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.tag_configure("to", foreground="#c0392b")
        self.tree.bind("<Double-1>", self._handle_open)

    def render(self, results: Mapping[str, dict[str, Any]]) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        snapshot = dict(results)
        ordered = sorted(snapshot,
                         key=lambda host: (snapshot[host].get("status") or 0, host),
                         reverse=True)
        for host in ordered:
            row = snapshot[host]
            tech = ", ".join(row.get("tech") or [])[:80]
            self.tree.insert(
                "", tk.END, iid=host,
                values=(row.get("status") or "-", host,
                        (row.get("title") or "")[:100], tech,
                        row.get("takeover") or ""),
                tags=("to",) if row.get("takeover") else (),
            )

    def selected_hosts(self) -> list[str]:
        return list(self.tree.selection())

    def _handle_open(self, _event: tk.Event) -> None:
        selection = self.selected_hosts()
        if selection and self._on_open:
            self._on_open(selection[0])
