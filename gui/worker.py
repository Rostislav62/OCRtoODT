# gui/worker.py
"""
OCRWorker — background thread for running the OCRtoODT pipeline.
It launches the CLI subprocess, streams live logs and progress updates to the GUI,
supports safe cancellation, and gracefully handles errors.
"""

import subprocess
import threading
import sys
import os
import tempfile
import time
import yaml
import logging
from pathlib import Path
from PySide6.QtCore import QThread, Signal


class OCRWorker(QThread):
    # === Signals emitted to the GUI ===
    sig_progress = Signal(str)      # emits log line text
    sig_percent = Signal(int)       # emits progress percentage (0–100)
    sig_finished = Signal(str)      # emits status message on completion
    sig_error = Signal(str)         # emits error message
    sig_cancelled = Signal()        # emitted when user cancels OCR

    def __init__(self, config_path="config.yaml", parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self._cancelled = threading.Event()
        self.proc = None

    # ---------------------------------------------------------------
    # Environment helper
    # ---------------------------------------------------------------
    def _fix_runtime_env(self):
        """
        Ensure system environment is valid even when running
        inside a frozen (onefile) Nuitka binary.
        - Adds /usr/bin and /usr/local/bin to PATH (for tesseract)
        - Ensures HOME and TMPDIR exist (some libs need them)
        """
        env = os.environ.copy()
        path = env.get("PATH", "")
        essentials = ["/usr/bin", "/usr/local/bin"]
        for p in essentials:
            if p not in path:
                path = f"{p}:{path}"
        env["PATH"] = path
        env.setdefault("HOME", str(Path.home()))
        env.setdefault("TMPDIR", tempfile.gettempdir())
        return env

    # ---------------------------------------------------------------
    # Main OCR thread routine
    # ---------------------------------------------------------------
    def run(self):
        """
        Launches OCR pipeline as a subprocess and updates progress bar
        in real time based on log lines received from stdout.
        """
        try:
            # --- Load config to estimate number of pages ---
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                input_dir = cfg.get("input_dir", "input")
                num_pages = len([
                    f for f in os.listdir(input_dir)
                    if f.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff"))
                ])
            else:
                num_pages = 1

            expected_logs = max(1, num_pages * 25 + 10)
            coeff = 100.0 / expected_logs
            progress_value = 0.0

            cli_script = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "ocrtoodt", "i0_core", "cli_entrypoint.py")
            )

            if not os.path.isfile(cli_script):
                self.sig_error.emit(f"❌ CLI script not found at expected location:\n{cli_script}")
                return

            # --- Build command ---
            cmd = [sys.executable, cli_script, "--config", self.config_path]

            env = self._fix_runtime_env()

            # Log the start
            self.sig_progress.emit(f"🚀 Starting OCR pipeline...\n{' '.join(cmd)}\n")

            # --- Launch subprocess ---
            self.proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env,
            )

            # --- Stream output lines in real time ---
            for line in self.proc.stdout:
                if self._cancelled.is_set():
                    self._terminate_process()
                    self.sig_cancelled.emit()
                    self.sig_progress.emit("🛑 OCR cancelled by user\n")
                    return

                line = line.strip()
                if not line:
                    continue

                # Send log to GUI
                self.sig_progress.emit(line)

                # Increment progress smoothly
                progress_value += coeff
                if progress_value > 100:
                    progress_value = 100
                self.sig_percent.emit(int(progress_value))

            # Wait for subprocess to finish
            self.proc.wait()
            code = self.proc.returncode

            if code == -15:
                self.sig_progress.emit("🛑 OCR stopped by user.\n")
                self.sig_cancelled.emit()
                return

            if code == 0:
                # Smooth finalization animation
                self.sig_progress.emit("✅ OCR finished successfully.\n")
                remaining = max(0, 100 - int(progress_value))
                if remaining > 0:
                    step_value = remaining / 5
                    for i in range(5):
                        progress_value += step_value
                        self.sig_percent.emit(int(progress_value))
                        time.sleep(0.1)
                else:
                    self.sig_percent.emit(100)
                self.sig_finished.emit("success")

            else:
                # Non-zero exit code → show captured error
                self.sig_error.emit(f"❌ Process exited with code {code}")
                # Optionally log tail of stderr if available
                if self.proc.stdout:
                    tail = "".join(list(self.proc.stdout)[-5:])
                    self.sig_progress.emit(f"⚠️  Last log lines:\n{tail}")

        except FileNotFoundError:
            # If cli_entrypoint or tesseract is missing
            self.sig_error.emit("❌ OCR engine not found (Tesseract missing in PATH).")
        except Exception as e:
            # Unexpected Python-level exception
            self.sig_error.emit(f"❌ Exception: {e}")
        finally:
            self.proc = None

    # ---------------------------------------------------------------
    # Graceful process termination
    # ---------------------------------------------------------------
    def _terminate_process(self):
        """Terminate subprocess safely if running."""
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
        except Exception:
            pass

    # ---------------------------------------------------------------
    # Helper to extract percentage from logs (optional)
    # ---------------------------------------------------------------
    @staticmethod
    def _extract_percent(line: str):
        """
        Try to extract a numeric percentage from OCR log line, e.g. "Progress: 42%".
        Returns integer 0–100 or None.
        """
        import re
        match = re.search(r"(\d{1,3})\s*%?", line)
        if match:
            try:
                val = int(match.group(1))
                return max(0, min(val, 100))
            except ValueError:
                return None
        return None

    # ---------------------------------------------------------------
    # Public API: cancel the running OCR process
    # ---------------------------------------------------------------
    def cancel(self):
        """
        Request cancellation of the running OCR process.

        This sets the internal event flag checked by run(),
        and also terminates any subprocess if currently active.
        """
        if not self.isRunning():
            return  # nothing to cancel

        self._cancelled.set()  # signal the run() loop to stop

        # If a subprocess is active, terminate it gracefully
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
                logging.info("🛑 OCR subprocess terminated by user.")
        except Exception as e:
            logging.warning(f"Failed to terminate subprocess: {e}")

        # emit signal for GUI update
        self.sig_cancelled.emit()
