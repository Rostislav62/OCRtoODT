# gui/utils_open.py
"""
Cross-platform "open with default application" helper.
Replaces webbrowser.open for local documents to avoid browser dialogs.
"""

import os
import platform
import subprocess

def open_with_default_app(path: str):
    """
    Open a file using the OS default application:
    - Windows: os.startfile
    - macOS:   open <path>
    - Linux:   xdg-open <path>
    """
    if not path or not os.path.exists(path):
        raise FileNotFoundError(path)
    system = platform.system()
    if system == "Windows":
        os.startfile(path)  # type: ignore[attr-defined]
    elif system == "Darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)
