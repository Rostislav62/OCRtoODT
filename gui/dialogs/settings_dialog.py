# gui/dialogs/settings_dialog.py
"""
SettingsDialog:
- Loads .ui via QUiLoader
- Provides sound test button
- Applies parent theme for visual consistency
"""

import os
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from ..theme import apply_parent_theme
from ..app_paths import resource_path

class SettingsDialog(QDialog):
    """Application settings window loaded from settings_dialog.ui."""

    def __init__(self, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        ui_path = resource_path("ui", "settings_dialog.ui")

        ui_file = QFile(ui_path)
        if not ui_file.exists():
            raise FileNotFoundError(f"UI file not found: {ui_path}")
        if not ui_file.open(QIODevice.ReadOnly):
            raise IOError(f"Unable to open: {ui_path}")

        ui = loader.load(ui_file, self)
        ui_file.close()
        if not ui:
            raise RuntimeError("Failed to load settings_dialog.ui")

        self.ui = ui
        self.setLayout(ui.layout())
        self.setMinimumSize(720, 500)
        self.setWindowTitle("Settings — OCRtoODT")

        # Buttons
        try:
            self.ui.btnOK.clicked.connect(self.accept)
            self.ui.btnCancel.clicked.connect(self.reject)
        except Exception:
            pass

        # Theme
        apply_parent_theme(self, parent)

        # Optional sound test
        if hasattr(self.ui, "btnTestSound"):
            self.ui.btnTestSound.clicked.connect(self.play_test_sound)

    def play_test_sound(self):
        """Play a simple WAV to confirm audio output works."""
        sound_path = resource_path("resources", "sounds", "done.wav")
        if not os.path.exists(sound_path):
            # handled by GUI with QMessageBox in Main if needed
            return
        self._audio_output = QAudioOutput()
        self._audio_output.setVolume(0.8)
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio_output)
        self._player.setSource(QUrl.fromLocalFile(sound_path))
        self._player.play()
