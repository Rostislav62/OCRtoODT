# gui/dialogs/about_dialog.py
"""
AboutDialog:
- Small static dialog with icon/title/version/link
"""

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice
from PySide6.QtGui import QIcon
from ..theme import apply_parent_theme
from ..app_paths import resource_path

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        loader = QUiLoader()
        ui_path = resource_path("ui", "about_dialog.ui")

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

        button_box = widget.findChild(QDialogButtonBox, "buttonBox")
        if button_box:
            button_box.accepted.connect(self.accept)

        self.setWindowTitle("About OCRtoODT")
        self.setWindowIcon(QIcon(resource_path("resources", "icons", "about.svg")))
        self.setFixedSize(420, 320)
