# gui/main.py
"""
MainWindow for OCRtoODT (PySide6).
All helpers, dialogs, theme, and path logic are split into dedicated modules.
"""

import os, sys
from ruamel.yaml import YAML

# ================================================================
# 🧭 1. Определяем корневую папку программы (program_root)
# ================================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))  # ← корневая папка OCRtoODT

# Добавляем родительскую папку (OCRtoODT) в sys.path — чтобы работали импорты
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ================================================================
# 🗂️ 2. Функция обновления/добавления program_root в config.yaml
# ================================================================
def ensure_program_root(config_path: str, detected_root: str):
    """
    Ensures that config.yaml has a valid 'program_root' key set to the detected project root.
    Keeps all other paths as relative. Preserves YAML comments and formatting.
    """
    if not os.path.exists(config_path):
        print(f"[WARN] Config file not found: {config_path}")
        return

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 1000

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.load(f) or {}

    # --- Add or update program_root ---
    prev_root = cfg.get("program_root")
    if not prev_root or os.path.abspath(prev_root) != detected_root:
        cfg["program_root"] = detected_root
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f)
        print(f"🧭 Program root set to: {detected_root}")
        print(f"   Updated config: {config_path}\n")
    else:
        print(f"🧭 Program root already correct: {detected_root}")

# ================================================================
# ⚙️ 3. Вычисляем и записываем program_root при запуске
# ================================================================
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")
ensure_program_root(CONFIG_PATH, PROJECT_ROOT)


# 🟢 Явно указываем, что текущий модуль принадлежит пакету gui
if __package__ is None:
    __package__ = "gui"


from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, QDialog, QWidget
)
from PySide6.QtCore import QFile, Qt, QCoreApplication
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QIcon

# Project helpers
from gui.app_paths import CONFIG_PATH, resource_path
from gui.theme import apply_theme, auto_detect_theme
from gui.utils_open import open_with_default_app

# Internal packages
from gui.worker import OCRWorker
from gui.config_bridge import load_config, save_config, apply_gui_to_cfg, apply_cfg_to_gui

from gui.widgets.preview import PreviewView
from gui.widgets.thumb_list import ThumbList

# Dialogs
from gui.dialogs.settings_dialog import SettingsDialog
from gui.dialogs.help_dialog import HelpDialog
from gui.dialogs.about_dialog import AboutDialog

# Pipeline helper
from ocrtoodt.i0_core.pdf_splitter import pdf_to_images


# ===============================================================
# Main Window
# ===============================================================
class MainWindow(QMainWindow):
    """Main GUI window with preview, thumbnails, log and toolbar."""

    def __init__(self):
        super().__init__()
        self.ui = None
        self.worker = None

        # Load configuration
        self.cfg = load_config(CONFIG_PATH)

        # Load interface and connect signals
        self._load_ui()
        self._setup_connections()

        # Basic window settings
        self.setWindowTitle("OCRtoODT GUI")
        self.setWindowIcon(QIcon(resource_path("resources", "icons", "app_icon.svg")))
        self.resize(1200, 800)
        self.setMinimumWidth(1100)
        self.setMinimumHeight(700)

        # Apply theme (light/dark/auto)
        ui_theme = self.cfg.get("ui", {}).get("theme", "auto")
        if ui_theme == "auto":
            ui_theme = auto_detect_theme(default="light")
        apply_theme(self, ui_theme)

    def _load_ui(self):
        loader = QUiLoader()
        ui_file = QFile(resource_path("ui", "main_window.ui"))
        ui_file.open(QFile.ReadOnly)
        ui = loader.load(ui_file)
        ui_file.close()
        if not ui:
            raise RuntimeError("Failed to load main_window.ui")

        self.setCentralWidget(ui.centralwidget)

        if hasattr(ui, "toolBar"):
            self.addToolBar(ui.toolBar)
            ui.toolBar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        if hasattr(ui, "statusBar"):
            self.setStatusBar(ui.statusBar())

        try:
            with open(resource_path("resources", "style.qss"), "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            pass

        self.ui = ui

        # Replace placeholders with custom widgets
        self.thumb_list = ThumbList()
        self.preview_view = PreviewView()

        if hasattr(self.ui, "listFiles"):
            parent = self.ui.listFiles.parent()
            layout = parent.layout()
            idx = layout.indexOf(self.ui.listFiles)
            layout.takeAt(idx)
            layout.insertWidget(idx, self.thumb_list)
            self.ui.listFiles.deleteLater()

        if hasattr(self.ui, "viewPreview"):
            parent = self.ui.viewPreview.parent()
            layout = parent.layout()
            idx = layout.indexOf(self.ui.viewPreview)
            layout.takeAt(idx)
            layout.insertWidget(idx, self.preview_view)
            self.ui.viewPreview.deleteLater()

        self.thumb_list.fileSelected.connect(self.preview_view.set_image)

        try:
            self.ui.verticalLayoutCentral.setStretch(0, 4)
            self.ui.verticalLayoutCentral.setStretch(1, 1)
        except Exception:
            pass

        self.ui.actionExport.setEnabled(False)
        self.statusBar().addPermanentWidget(self.ui.lblStatus)
        self.statusBar().addPermanentWidget(self.ui.progressTotal)

        # Toolbar icons
        icon_path = resource_path("resources", "icons")
        self.ui.actionOpen.setIcon(QIcon(os.path.join(icon_path, "open.svg")))
        self.ui.actionSettings.setIcon(QIcon(os.path.join(icon_path, "settings.svg")))
        self.ui.actionRun.setIcon(QIcon(os.path.join(icon_path, "run.svg")))
        self.ui.actionStop.setIcon(QIcon(os.path.join(icon_path, "stop.svg")))
        self.ui.actionExport.setIcon(QIcon(os.path.join(icon_path, "export.svg")))
        self.ui.actionClear.setIcon(QIcon(os.path.join(icon_path, "clear.svg")))
        self.ui.actionAbout.setIcon(QIcon(os.path.join(icon_path, "about.svg")))
        self.ui.actionHelp.setIcon(QIcon(os.path.join(icon_path, "help.svg")))

        # Shortcuts / tooltips
        self.ui.actionOpen.setShortcut("Ctrl+O")
        self.ui.actionSettings.setShortcut("Ctrl+,")
        self.ui.actionRun.setShortcut("Ctrl+R")
        self.ui.actionStop.setShortcut("Ctrl+S")
        self.ui.actionExport.setShortcut("Ctrl+E")
        self.ui.actionClear.setShortcut("Ctrl+L")
        self.ui.actionAbout.setShortcut("F1")
        self.ui.actionHelp.setShortcut("F2")

        self.ui.actionOpen.setToolTip("Open files (Ctrl+O)")
        self.ui.actionSettings.setToolTip("Settings (Ctrl+,)")
        self.ui.actionRun.setToolTip("Start OCR (Ctrl+R)")
        self.ui.actionStop.setToolTip("Stop OCR (Ctrl+S)")
        self.ui.actionExport.setToolTip("Open ODT (Ctrl+E)")
        self.ui.actionClear.setToolTip("Clear workspace (Ctrl+L)")
        self.ui.actionAbout.setToolTip("About (F1)")
        self.ui.actionHelp.setToolTip("Help / Documentation (F2)")

        # Zoom buttons
        self.ui.btnZoomIn.clicked.connect(self.preview_view.zoom_in)
        self.ui.btnZoomOut.clicked.connect(self.preview_view.zoom_out)
        self.ui.btnZoomFit.clicked.connect(self.preview_view.zoom_reset)
        self.ui.btnZoom100.clicked.connect(self.preview_view.zoom_100)

    def _setup_connections(self):
        self.ui.actionOpen.triggered.connect(self.open_files)
        self.ui.actionRun.triggered.connect(self.start_ocr)
        self.ui.actionStop.triggered.connect(self.stop_ocr)
        self.ui.actionAbout.triggered.connect(self.show_about)
        self.ui.actionSettings.triggered.connect(self.open_settings)
        self.ui.actionExport.triggered.connect(self.open_odt)
        self.ui.actionClear.triggered.connect(self.clear_workspace)
        self.ui.actionHelp.triggered.connect(self.show_help)


    # ---------- small helpers ----------
    def log(self, text: str):
        self.ui.textLog.append(text)
        self.ui.textLog.ensureCursorVisible()

    # ---------- open/select files ----------
    def open_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Выбери изображения или PDF",
            "",
            "Изображения и PDF (*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.pdf)",
        )
        if not paths:
            return

        cfg = load_config(CONFIG_PATH)
        input_dir = cfg.get("input_dir")

        # Validate that the configured input_dir exists
        if not input_dir or not os.path.isdir(input_dir):
            QMessageBox.warning(
                self,
                "Invalid input path",
                f"❌ Input directory not found:\n{input_dir}\n\n"
                "Please make sure the path in config.yaml is correct."
            )
            return

        # Clean up input directory (if user wants to reuse previous session)
        for f in os.listdir(input_dir):
            f_path = os.path.join(input_dir, f)
            try:
                if os.path.isfile(f_path):
                    os.remove(f_path)
            except Exception as e:
                self.log(f"⚠️ Не удалось удалить {f}: {e}")

        copied_files, counter = [], 1

        for src in paths:
            ext = Path(src).suffix.lower()
            if ext == ".pdf":
                self.log(f"📄 Конвертация PDF → изображения: {Path(src).name}")
                try:
                    temp_images = pdf_to_images(src, CONFIG_PATH, dpi=300)
                    for img_path in temp_images:
                        new_name = f"{counter:03d}.png"
                        new_path = os.path.join(input_dir, new_name)
                        os.rename(img_path, new_path)
                        copied_files.append(new_path)
                        self.log(f"🖼 {Path(src).name} → {new_name}")
                        counter += 1
                except Exception as e:
                    self.log(f"❌ Ошибка при конвертации PDF: {e}")
            else:
                dst_name = f"{counter:03d}{ext}"
                dst_path = os.path.join(input_dir, dst_name)
                try:
                    from shutil import copy2
                    copy2(src, dst_path)
                    copied_files.append(dst_path)
                    self.log(f"📸 {Path(src).name} → {dst_name}")
                    counter += 1
                except Exception as e:
                    self.log(f"❌ Ошибка копирования {src}: {e}")

        if copied_files:
            self.thumb_list.load_files(copied_files)
            self.preview_view.set_image(copied_files[0])

        count = len(copied_files)
        self.log(f"✅ Загружено {count} файлов в {input_dir}")
        if hasattr(self.ui, "lblStatus"):
            self.ui.lblStatus.setText(f"Загружено {count} файлов")

    # ---------- settings / help / about ----------
    def open_settings(self):
        try:
            dlg = SettingsDialog(self)
            cfg = load_config(CONFIG_PATH)
            apply_cfg_to_gui(dlg.ui, cfg)

            if dlg.exec() == QDialog.Accepted:
                new_cfg = apply_gui_to_cfg(dlg.ui, cfg)
                save_config(new_cfg, CONFIG_PATH)

                ui_theme = new_cfg.get("ui", {}).get("theme", "light")
                apply_theme(self, ui_theme)
                self.log("⚙️ Settings updated and applied.")
        except Exception as e:
            QMessageBox.warning(self, "Settings Error", f"Failed to open settings dialog:\n{e}")

    def show_help(self):
        HelpDialog(self).exec()

    def show_about(self):
        AboutDialog(self).exec()

    # ---------- OCR worker ----------
    def start_ocr(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Busy", "OCR is already running.")
            return
        self.worker = OCRWorker(config_path=CONFIG_PATH)
        self.worker.sig_progress.connect(self.log)
        self.worker.sig_error.connect(self.on_ocr_error)
        self.worker.sig_percent.connect(lambda p: self.ui.progressTotal.setValue(p))
        self.worker.sig_finished.connect(self.on_ocr_finished)
        self.worker.sig_cancelled.connect(self.on_ocr_cancelled)

        self.ui.progressTotal.setValue(0)
        self.set_busy(True)
        self.worker.start()
        self.log("🚀 OCR process started...")
        self.ui.lblStatus.setText("Processing...")

    def stop_ocr(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.log("🛑 OCR cancelled by user.")
            self.ui.lblStatus.setText("Cancelled.")

    def on_ocr_error(self, message):
        self.log(f"❌ OCR Error: {message}")
        self.set_busy(False)
        self.ui.lblStatus.setText("Error.")

    def on_ocr_cancelled(self):
        self.log("🛑 OCR process aborted.")
        self.set_busy(False)
        self.ui.lblStatus.setText("Cancelled.")

    def on_ocr_finished(self, status):
        self.log("✅ OCR завершён успешно.")
        self.set_busy(False)
        self.ui.lblStatus.setText("Готово")
        self.ui.actionExport.setEnabled(True)

        # Звук/уведомление — как раньше (сокращено, можно оставить как было)
        try:
            cfg = load_config(CONFIG_PATH)
            ui_cfg = cfg.get("ui", {})
            # уведомление
            if ui_cfg.get("notify_on_finish", True):
                QMessageBox.information(self, "OCRtoODT", "✅ Распознавание завершено успешно!", QMessageBox.Ok)
        except Exception:
            pass

    def set_busy(self, busy: bool):
        self.ui.actionRun.setEnabled(not busy)
        self.ui.actionSettings.setEnabled(not busy)
        self.ui.actionOpen.setEnabled(not busy)
        self.ui.actionExport.setEnabled(not busy)
        self.ui.actionStop.setEnabled(busy)
        self.ui.lblStatus.setText("Processing..." if busy else "Ready.")

    # ---------- open produced ODT ----------
    def open_odt(self):
        try:
            cfg = load_config(CONFIG_PATH)
            odt_path = cfg.get("output_file", "")

            def try_open(path: str) -> bool:
                if path and os.path.exists(path):
                    open_with_default_app(path)  # ← без браузера
                    self.log(f"📄 Открыт файл: {path}")
                    if hasattr(self.ui, "lblStatus"):
                        self.ui.lblStatus.setText("Открыт ODT")
                    return True
                return False

            # 1) основной путь из конфига
            if try_open(odt_path):
                return

            # 2) fallback: последний .odt в output/
            out_dir = os.path.dirname(odt_path) or "output"
            candidates = [
                os.path.join(out_dir, name)
                for name in os.listdir(out_dir)
                if name.lower().endswith(".odt")
            ] if os.path.isdir(out_dir) else []

            if candidates:
                latest = max(candidates, key=lambda p: os.path.getmtime(p))
                if try_open(latest):
                    return

            QMessageBox.warning(self, "Файл не найден", f"ODT не найден.\nОжидался путь:\n{odt_path}")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть ODT:\n{e}")

    # ---------- clear workspace ----------
    def clear_workspace(self):
        self.ui.textLog.clear()
        try: self.thumb_list.clear()
        except Exception: pass
        try: self.preview_view.set_image(None)
        except Exception: pass

        try:
            cfg = load_config(CONFIG_PATH)
            input_dir = cfg.get("input_dir", "input")
            if os.path.isdir(input_dir):
                removed = 0
                for f in os.listdir(input_dir):
                    p = os.path.join(input_dir, f)
                    if os.path.isfile(p):
                        try: os.remove(p); removed += 1
                        except Exception as e: self.log(f"⚠️ Failed to remove {p}: {e}")
                self.log(f"🧹 Cleared input/: removed {removed} files")
        except Exception as e:
            self.log(f"❌ Input cleanup error: {e}")

        try:
            ocr_cache = os.path.join("cache", "ocr")
            if os.path.isdir(ocr_cache):
                removed = 0
                for f in os.listdir(ocr_cache):
                    p = os.path.join(ocr_cache, f)
                    if os.path.isfile(p):
                        try: os.remove(p); removed += 1
                        except Exception as e: self.log(f"⚠️ Failed to remove cached file {p}: {e}")
                self.log(f"🧹 Cleared cache/ocr/: removed {removed} files")
        except Exception as e:
            self.log(f"❌ OCR cache cleanup error: {e}")

        self.ui.progressTotal.setValue(0)
        self.ui.actionExport.setEnabled(False)
        if hasattr(self.ui, "lblStatus"):
            self.ui.lblStatus.setText("Ready")
        self.log("✅ Workspace fully cleared")


if __name__ == "__main__":
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication([])
    app.setWindowIcon(QIcon(resource_path("resources", "icons", "app_icon.svg")))

    win = MainWindow()
    win.show()
    raise SystemExit(app.exec())
