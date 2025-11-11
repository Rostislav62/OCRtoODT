# gui/widgets/preview.py
"""
PreviewView — компонент предпросмотра изображения (ABBYY-style).
Поддерживает масштабирование колёсиком, перетаскивание и автоматическую подгонку.
"""

from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtGui import QPixmap, QWheelEvent, QPainter
from PySide6.QtCore import Qt


class PreviewView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        # применяем сглаживание через QPainter
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self._scale_factor = 1.0
        self.scene = QGraphicsScene()
        self.setScene(self.scene)


    # === загрузка изображения ===
    def set_image(self, path: str):
        self.scene.clear()
        pix = QPixmap(path)
        self.scene.addPixmap(pix)
        self.scene.setSceneRect(pix.rect())
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self._scale_factor = 1.0

    # === управление зумом ===
    def zoom_in(self):
        self._scale(1.25)

    def zoom_out(self):
        self._scale(0.8)

    def zoom_reset(self):
        self.resetTransform()
        self._scale_factor = 1.0
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def zoom_100(self):
        self.resetTransform()
        self._scale_factor = 1.0

    def _scale(self, factor):
        self.scale(factor, factor)
        self._scale_factor *= factor

    # === поддержка колесика мыши ===
    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier:
            self._scale(1.25 if event.angleDelta().y() > 0 else 0.8)
        else:
            super().wheelEvent(event)
