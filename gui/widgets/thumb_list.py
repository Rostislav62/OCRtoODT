# gui/widgets/thumb_list.py
"""
ThumbList — список файлов (миниатюр изображений).
Поддерживает Drag & Drop из проводника и выбор файлов из GUI.
"""

import os
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QListView
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, Signal, QSize


class ThumbList(QListWidget):
    filesDropped = Signal(list)     # список всех путей, которые перетащили
    fileSelected = Signal(str)      # путь выбранного файла

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListView.IconMode)
        self.setIconSize(QSize(96, 96))
        self.setResizeMode(QListWidget.Adjust)
        self.setSpacing(6)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)
        self.itemSelectionChanged.connect(self._on_selection_changed)

    # === загрузка изображений ===
    def load_files(self, file_paths):
        self.clear()
        for path in file_paths:
            if not os.path.exists(path):
                continue
            name = os.path.basename(path)
            item = QListWidgetItem(name)
            pix = QPixmap(path)
            if not pix.isNull():
                icon = QIcon(pix.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                item.setIcon(icon)
            item.setData(Qt.UserRole, path)
            self.addItem(item)
        if file_paths:
            self.setCurrentRow(0)
            self.fileSelected.emit(file_paths[0])

    # === drag & drop ===
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                p = url.toLocalFile()
                if p.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".pdf")):
                    paths.append(p)
        if paths:
            self.filesDropped.emit(paths)
            self.load_files(paths)

    # === выбор элемента ===
    def _on_selection_changed(self):
        item = self.currentItem()
        if item:
            path = item.data(Qt.UserRole)
            if path:
                self.fileSelected.emit(path)
