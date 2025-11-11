# gui/theme.py
"""
Theme utilities for OCRtoODT GUI.
Simplified, stable, and guaranteed to reapply theme fully across all widgets.

Features:
- auto_detect_theme(): detects GNOME preference (dark/light)
- set_qt_palette(): installs readable palette for dark/light
- apply_theme(): applies palette + QSS + forces full widget re-polish
- apply_parent_theme(): makes dialogs match parent window

This version ensures that when you change theme in Settings,
the entire interface (all widgets, toolbars, menus, dialogs)
refreshes immediately and completely — no partial updates.
"""

import os
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor
from .app_paths import resource_path


# ---------------------------------------------------------
# Detect system theme (GNOME etc.)
# ---------------------------------------------------------
def auto_detect_theme(default: str = "light") -> str:
    """Detect GNOME color-scheme preference; fallback to 'light'."""
    try:
        import subprocess
        res = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
            capture_output=True, text=True
        )
        return "dark" if "dark" in res.stdout.lower() else "light"
    except Exception:
        return default


# ---------------------------------------------------------
# Set palette colors
# ---------------------------------------------------------
def set_qt_palette(theme: str):
    """Install a readable Qt palette for dark/light themes."""
    pal = QPalette()

    if theme == "dark":
        bg = QColor("#1e1e1e")
        base = QColor("#2b2b2b")
        text = QColor("#e0e0e0")
        button = QColor("#2c2c2c")
        btext = QColor("#eaeaea")
        hl = QColor("#4a90e2")
        hltxt = QColor("#ffffff")
    else:
        bg = QColor("#f8f9fb")
        base = QColor("#ffffff")
        text = QColor("#111111")
        button = QColor("#e6e9ef")
        btext = QColor("#111111")
        hl = QColor("#2563eb")
        hltxt = QColor("#ffffff")

    pal.setColor(QPalette.Window, bg)
    pal.setColor(QPalette.WindowText, text)
    pal.setColor(QPalette.Base, base)
    pal.setColor(QPalette.AlternateBase, bg if theme == "dark" else QColor("#f1f3f8"))
    pal.setColor(QPalette.Text, text)
    pal.setColor(QPalette.Button, button)
    pal.setColor(QPalette.ButtonText, btext)
    pal.setColor(QPalette.ToolTipBase, base)
    pal.setColor(QPalette.ToolTipText, text)
    pal.setColor(QPalette.Highlight, hl)
    pal.setColor(QPalette.HighlightedText, hltxt)

    QApplication.instance().setPalette(pal)


# ---------------------------------------------------------
# Internal recursive refresh helper
# ---------------------------------------------------------
def _refresh_all_widgets(widget: QWidget, theme: str):
    """Force full re-polish for widget and all its children."""
    if not widget:
        return
    widget.setProperty("theme", theme)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    for child in widget.findChildren(QWidget):
        child.setProperty("theme", theme)
        child.style().unpolish(child)
        child.style().polish(child)


# ---------------------------------------------------------
# Main entry point
# ---------------------------------------------------------
def apply_theme(app_or_widget: QWidget, theme: str):
    """
    Apply full theme update:
      - Fusion style
      - Palette for dark/light
      - Style.qss (if exists)
      - Force full widget re-polish for entire app
    """
    app = QApplication.instance()
    if not app:
        return

    # Use a stable base style
    QApplication.setStyle("Fusion")

    # 1️⃣ Palette for text/background contrast
    set_qt_palette(theme)

    # 2️⃣ QSS stylesheet (if exists)
    try:
        qss_path = resource_path("resources", "style.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                style = f.read()
            app.setStyleSheet(style)
        else:
            app.setStyleSheet("")  # clear old style if missing
    except Exception:
        pass

    # 3️⃣ Propagate theme to all widgets
    for top in app.topLevelWidgets():
        _refresh_all_widgets(top, theme)

    # 4️⃣ Refresh main widget explicitly (ensures toolbar, preview, etc.)
    _refresh_all_widgets(app_or_widget, theme)

    # 5️⃣ Update QApplication property (for future dialogs)
    app.setProperty("theme", theme)

    # --- log (for debugging only)
    print(f"🎨 Theme applied: {theme}")


# ---------------------------------------------------------
# Dialog theme sync helper
# ---------------------------------------------------------
def apply_parent_theme(dialog: QWidget, parent: QWidget):
    """
    Make a dialog visually consistent with its parent window.
    """
    if not parent or not dialog:
        return
    theme = parent.property("theme") or QApplication.instance().property("theme") or "light"
    _refresh_all_widgets(dialog, theme)
