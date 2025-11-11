# Path: ocrtoodt/i2_ocr/ocr_engine.py
# Purpose: Perform OCR using Tesseract (via pytesseract). Produces per-page TSVs.

import os
import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np
import pandas as pd
import pytesseract
from pytesseract.pytesseract import TesseractNotFoundError

from ocrtoodt.i0_core.types_definitions import LineAnnotation


class OCREngine:
    """
    High-level OCR engine wrapper for Tesseract.

    ⚙️ All file system paths (tesseract binary, tessdata folder, OCR cache, etc.)
    are read directly from config.yaml — no runtime guessing or fallbacks.
    """

    def __init__(self, config: dict):
        """
        Initialize OCR engine strictly from config.yaml.

        Expected keys under config["ocr"]:
          - enabled_engines: ["tesseract"]
          - languages: ["rus", "eng"]
          - dpi: 300
          - tesseract_psm: 4
          - ocr_engine_path: absolute path to tesseract binary
          - tessdata_dir: absolute path to tessdata folder
        """
        self.config = config or {}
        ocr_cfg = self.config.get("ocr", {}) or {}

        # --- Core parameters ---
        self.enabled_engines = ocr_cfg.get("enabled_engines", ["tesseract"])
        if "tesseract" not in self.enabled_engines:
            raise ValueError("Tesseract must be listed in 'ocr.enabled_engines'.")

        self.languages = list(ocr_cfg.get("languages", ["rus", "eng"]))
        self.dpi = int(ocr_cfg.get("dpi", 300))
        self.psm = int(ocr_cfg.get("tesseract_psm", 6))

        # --- Paths from config (no fallback logic) ---
        self.tesseract_path = ocr_cfg.get("ocr_engine_path")
        self.tessdata_dir = ocr_cfg.get("tessdata_dir")

        # --- Validate paths explicitly ---
        if not self.tesseract_path or not os.path.isfile(self.tesseract_path):
            raise FileNotFoundError(
                f"Tesseract binary not found at:\n  {self.tesseract_path}\n"
                "Please verify 'ocr_engine_path' in config.yaml."
            )

        if not os.access(self.tesseract_path, os.X_OK):
            raise PermissionError(
                f"Tesseract binary is not executable:\n  {self.tesseract_path}"
            )

        if not self.tessdata_dir or not os.path.isdir(self.tessdata_dir):
            raise FileNotFoundError(
                f"Tessdata directory not found at:\n  {self.tessdata_dir}\n"
                "Please verify 'tessdata_dir' in config.yaml."
            )

        # --- Tell pytesseract which binary to use (no PATH dependency) ---
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_path

        logging.info(
            f"Tesseract initialized successfully.\n"
            f"  • Binary:   {self.tesseract_path}\n"
            f"  • Tessdata: {self.tessdata_dir}\n"
            f"  • Langs:    {self.languages}\n"
            f"  • PSM:      {self.psm}\n"
            f"  • DPI:      {self.dpi}"
        )

    # ------------------------------------------------------------------
    # Main public OCR method
    # ------------------------------------------------------------------

    def process_image(self, image: np.ndarray, output_dir: str, page_num: int) -> List[LineAnnotation]:
        """
        Run OCR on a single image using Tesseract and return structured lines.

        Args:
            image: np.ndarray — input image (RGB or grayscale)
            output_dir: path to directory for TSV output (from config["ocr_dir"])
            page_num: page index (1-based)
        """
        if not os.path.isdir(output_dir):
            raise FileNotFoundError(f"OCR output directory not found: {output_dir}")

        base_name = f"page_{page_num:04d}"
        tsv_output = os.path.join(output_dir, f"{base_name}.tsv")

        image = self._ensure_rgb_uint8(image)

        # Build tesseract CLI configuration strictly from config
        lang_arg = "+".join(self.languages) if self.languages else "eng"
        tess_cfg = f"--psm {self.psm} --dpi {self.dpi} -l {lang_arg} --tessdata-dir {self.tessdata_dir}"

        try:
            data = pytesseract.image_to_data(
                image,
                config=tess_cfg,
                output_type=pytesseract.Output.DICT,
            )
            logging.info("Tesseract processed page %s: %s words", page_num, len(data.get("text", [])))
        except TesseractNotFoundError as e:
            logging.error("Tesseract not callable: %s (%s)", self.tesseract_path, e)
            raise FileNotFoundError(
                f"Tesseract executable not found or not executable: {self.tesseract_path}"
            ) from e
        except Exception as e:
            logging.error("Tesseract error on page %s: %s", page_num, e)
            raise

        lines = self._group_words_into_lines(data, page_num)
        self._write_lines_tsv(lines, tsv_output)

        logging.info("Saved TSV for page %s → %s", page_num, tsv_output)
        return [
            LineAnnotation(page=l["page"], line_no=l["line_no"], text=l["text"], bbox=l["bbox"])
            for l in lines
        ]

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_rgb_uint8(image: np.ndarray) -> np.ndarray:
        """Ensure the input is an RGB uint8 OpenCV-compatible image."""
        if not isinstance(image, np.ndarray):
            raise TypeError(f"Expected numpy.ndarray, got {type(image)}")
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)
        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        if image.ndim == 3:
            if image.shape[2] == 3:
                return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            if image.shape[2] == 4:
                bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
                return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        raise ValueError(f"Unsupported image shape: {image.shape}")

    @staticmethod
    def _group_words_into_lines(tsv_dict: dict, page_num: int) -> List[dict]:
        """Group Tesseract word-level results into lines by (block, par, line)."""
        text_list = tsv_dict.get("text", [])
        width_list = tsv_dict.get("width", [])
        height_list = tsv_dict.get("height", [])
        left_list = tsv_dict.get("left", [])
        top_list = tsv_dict.get("top", [])
        block_list = tsv_dict.get("block_num", [])
        par_list = tsv_dict.get("par_num", [])
        line_list = tsv_dict.get("line_num", [])

        lines: List[dict] = []
        current_line: List[Tuple[str, int]] = []
        current_bbox: Optional[List[int]] = None
        prev_key: Optional[Tuple[int, int, int]] = None
        line_no = 0

        n = len(text_list)
        for i in range(n):
            try:
                txt = (text_list[i] or "").strip()
                if not txt:
                    continue
                if width_list[i] <= 0 or height_list[i] <= 0:
                    continue

                x1, y1 = int(left_list[i]), int(top_list[i])
                x2, y2 = x1 + int(width_list[i]), y1 + int(height_list[i])
                key = (int(block_list[i]), int(par_list[i]), int(line_list[i]))

                if prev_key is None or key == prev_key:
                    current_line.append((txt, x1))
                    if current_bbox is None:
                        current_bbox = [x1, y1, x2, y2]
                    else:
                        current_bbox[0] = min(current_bbox[0], x1)
                        current_bbox[1] = min(current_bbox[1], y1)
                        current_bbox[2] = max(current_bbox[2], x2)
                        current_bbox[3] = max(current_bbox[3], y2)
                else:
                    if current_line:
                        current_line.sort(key=lambda t: t[1])
                        text = " ".join(w for w, _ in current_line).strip()
                        lines.append({
                            "page": page_num,
                            "line_no": line_no,
                            "text": text,
                            "bbox": current_bbox,
                        })
                        line_no += 1
                    current_line = [(txt, x1)]
                    current_bbox = [x1, y1, x2, y2]
                prev_key = key
            except Exception as e:
                logging.warning("Word #%s grouping error on page %s: %s", i, page_num, e)
                continue

        if current_line:
            current_line.sort(key=lambda t: t[1])
            text = " ".join(w for w, _ in current_line).strip()
            lines.append({
                "page": page_num,
                "line_no": line_no,
                "text": text,
                "bbox": current_bbox,
            })
        return lines

    @staticmethod
    def _write_lines_tsv(lines: List[dict], path: str) -> None:
        """Save extracted lines into TSV: page, line_no, text, bbox."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        rows = [
            {
                "page": ln["page"],
                "line_no": ln["line_no"],
                "text": ln["text"],
                "bbox": str(ln["bbox"]),
            }
            for ln in lines
            if ln.get("text", "").strip()
        ]
        df = pd.DataFrame(rows, columns=["page", "line_no", "text", "bbox"])
        df.to_csv(path, sep="\t", index=False, encoding="utf-8")
