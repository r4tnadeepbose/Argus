"""Results table showing live hosts, tech and takeover verdicts."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Mapping
from tkinter import ttk
from typing import Any

_COLUMNS = ("status", "host", "title", "tech", "takeover")
_WIDTHS = {"status": 64, "host": 280, "title": 380, "tech": 230, "takeover": 96}


class ResultsTable(ttk.Frame):
    def __init__(self, master: tk.Misc,
                 on_open: Callable[[str], None] | None = None,
                 **kwargs):
        super().__init__(master, **kwargs)
        self._on_open = on_open
        self._palette = None

        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(header, text="RESULTS", style="Section.TLabel").pack(side=tk.LEFT)
        self.count_label = ttk.Label(header, text="no hosts yet", style="Muted.TLabel")
        self.count_label.pack(side=tk.RIGHT)

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(body, columns=_COLUMNS, show="headings")
        for column in _COLUMNS:
            self.tree.heading(column, text=column.upper())
            self.tree.column(column, width=_WIDTHS[column], anchor=tk.W,
                             stretch=column in ("title", "tech"))
        scrollbar = ttk.Scrollbar(body, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))
        self.tree.bind("<Double-1>", self._handle_open)

    def apply_palette(self, palette) -> None:
        self._palette = palette
        self.tree.tag_configure("to", foreground=palette.danger)
        self.tree.tag_configure("odd", background=palette.surface)
        self.tree.tag_configure("even", background=palette.surface_alt)

    def render(self, results: Mapping[str, dict[str, Any]]) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        snapshot = dict(results)
        ordered = sorted(snapshot,
                         key=lambda host: (snapshot[host].get("status") or 0, host),
                         reverse=True)
        for index, host in enumerate(ordered):
            row = snapshot[host]
            tech = ", ".join(row.get("tech") or [])[:80]
            tags = ["even" if index % 2 else "odd"]
            if row.get("takeover"):
                tags.append("to")
            self.tree.insert(
                "", tk.END, iid=host,
                values=(row.get("status") or "-", host,
                        (row.get("title") or "")[:100], tech,
                        row.get("takeover") or ""),
                tags=tuple(tags),
            )
        if ordered:
            self.count_label.config(text=f"{len(ordered)} hosts")
        else:
            self.count_label.config(text="no hosts yet")

    def selected_hosts(self) -> list[str]:
        return list(self.tree.selection())

    def _handle_open(self, _event: tk.Event) -> None:
        selection = self.selected_hosts()
        if selection and self._on_open:
            self._on_open(selection[0])
