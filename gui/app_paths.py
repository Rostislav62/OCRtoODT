# gui/app_paths.py
"""
Unified path resolver for OCRtoODT GUI.
Works correctly in:
 - source run (python gui/main.py)
 - module run  (python -m gui.main)
 - Nuitka/Onefile binary (unpacked under /tmp/onefile_XXXX)
"""

import os, sys, tempfile

def _detect_base_dir() -> str:
    """Detect the directory containing bundled resources."""
    # Case 1 — Nuitka/PyInstaller onefile
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        # Nuitka onefile: real files extracted to /tmp/onefile_xxxxxx
        if not os.path.exists(os.path.join(base, "config.yaml")):
            tmp = tempfile.gettempdir()
            for name in os.listdir(tmp):
                if name.startswith("onefile_"):
                    cand = os.path.join(tmp, name)
                    if os.path.exists(os.path.join(cand, "config.yaml")):
                        return cand
        return base

    # Case 2 — running from source tree
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = _detect_base_dir()
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, os.pardir))

# Ensure imports work for both GUI and pipeline
for p in (PROJECT_ROOT, BASE_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")

def resource_path(*parts: str) -> str:
    """
    Return absolute path to a bundled resource inside gui/.
    Example: resource_path("resources", "icons", "app_icon.svg")
    """
    path = os.path.join(BASE_DIR, *parts)
    if not os.path.exists(path):
        # Fallback: try same relative path from temp onefile folder
        tmp = tempfile.gettempdir()
        for name in os.listdir(tmp):
            if name.startswith("onefile_"):
                cand = os.path.join(tmp, name, *parts)
                if os.path.exists(cand):
                    return cand
    return path
