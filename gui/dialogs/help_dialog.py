# gui/dialogs/help_dialog.py
"""
HelpDialog:
- Load help_dialog.ui
- Render README.md as HTML with basic styling
- Incremental search (Ctrl+F)
"""

import os, markdown
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QTextBrowser, QLineEdit, QPushButton
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice, QEvent, Qt
from PySide6.QtGui import QTextCursor, QTextDocument
from ..theme import apply_parent_theme
from ..app_paths import resource_path, PROJECT_ROOT

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        loader = QUiLoader()
        ui_path = resource_path("ui", "help_dialog.ui")

        ui_file = QFile(ui_path)
        if not ui_file.open(QIODevice.ReadOnly):
            raise IOError(f"Cannot open: {ui_path}")
        widget = loader.load(ui_file)
        ui_file.close()
        if not widget:
            raise RuntimeError(f"Failed to load {ui_path}")

        apply_parent_theme(self, parent)
        layout = QVBoxLayout(self)
        layout.addWidget(widget)

        self.setWindowTitle("Help — OCRtoODT")
        self.resize(750, 640)

        self.text_browser = widget.findChild(QTextBrowser, "textBrowser")
        self.edit_find    = widget.findChild(QLineEdit, "editFind")
        self.btn_prev     = widget.findChild(QPushButton, "btnPrev")
        self.btn_next     = widget.findChild(QPushButton, "btnNext")

        button_box = widget.findChild(QDialogButtonBox, "buttonBox")
        if button_box:
            button_box.rejected.connect(self.reject)

        self._load_markdown()

        self.edit_find.textChanged.connect(self.find_first)
        self.btn_next.clicked.connect(self.find_next)
        self.btn_prev.clicked.connect(self.find_prev)
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
            self.edit_find.setFocus()
            return True
        return super().eventFilter(obj, event)

    def _load_markdown(self):
        readme_path = os.path.join(PROJECT_ROOT, "README.md")
        if not os.path.exists(readme_path):
            self.text_browser.setText("README.md not found.")
            return
        with open(readme_path, "r", encoding="utf-8") as f:
            md = f.read()
        html = markdown.markdown(md, extensions=["fenced_code", "tables", "sane_lists"])
        styled = f"""
        <html><head><style>
        body {{ font-family: 'DejaVu Sans', sans-serif; color:#2e3440; background:#f8f9fc; padding:10px; }}
        h1, h2, h3 {{ color:#4a90e2; margin-top:10px; }}
        code, pre {{ background:#e6ebf5; border-radius:4px; padding:2px 4px; font-family:'DejaVu Sans Mono', monospace; }}
        a {{ color:#4a90e2; text-decoration:none; }}
        a:hover {{ text-decoration:underline; }}
        </style></head><body>{html}</body></html>"""
        self.text_browser.setHtml(styled)

    # --- search helpers ---
    def find_first(self):
        self.search_term = self.edit_find.text()
        if self.search_term:
            self._find(self.search_term, forward=True)

    def find_next(self):
        self._find(getattr(self, "search_term", self.edit_find.text()), forward=True)

    def find_prev(self):
        self._find(getattr(self, "search_term", self.edit_find.text()), forward=False)

    def _find(self, text, forward=True):
        flags = QTextDocument.FindFlag(0)
        if not forward:
            flags |= QTextDocument.FindBackward
        found = self.text_browser.find(text, flags)
        if not found:
            cursor = self.text_browser.textCursor()
            cursor.movePosition(QTextCursor.Start if forward else QTextCursor.End)
            self.text_browser.setTextCursor(cursor)
            self.text_browser.find(text, flags)
