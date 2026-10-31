#!/usr/bin/env python3
"""Launcher for the recon GUI.

The implementation lives in the ``recon`` package; this file exists so the
tool can still be started with ``python recon_gui.py``.
"""

from recon.app import main

if __name__ == "__main__":
    main()
