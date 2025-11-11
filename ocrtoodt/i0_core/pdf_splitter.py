# Path: ocrtoodt/i0_core/pdf_splitter.py
# Purpose: Convert a multi-page PDF into individual PNG images.
# All output paths (input/output/cache) are defined in config.yaml,
# this module only performs conversion logic — no path guessing.

import os
import fitz  # PyMuPDF
import cv2
import numpy as np
import logging
import yaml


def pdf_to_images(pdf_path: str, config_path: str, dpi: int = None):
    """
    Converts a multi-page PDF into individual PNG images.
    Uses output directory strictly from config.yaml (key: input_dir).

    Args:
        pdf_path (str): Absolute path to the input PDF.
        config_path (str): Path to the YAML configuration file.
        dpi (int): Optional override for rendering DPI.

    Returns:
        list[str]: Absolute paths to all created PNG files.
    """
    # --- Load configuration ---
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # Get target directory for generated images
    output_dir = cfg.get("input_dir")
    if not output_dir or not os.path.isdir(output_dir):
        raise FileNotFoundError(
            f"Configured input_dir not found or invalid:\n  {output_dir}\n"
            "Please fix 'input_dir' in config.yaml."
        )

    # Determine rendering DPI
    pdf_dpi = dpi or cfg.get("ocr", {}).get("dpi", 300)

    # --- Conversion process ---
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    image_paths = []

    logging.info(f"Converting PDF → images: {pdf_path} ({doc.page_count} pages, {pdf_dpi} DPI)")

    for i, page in enumerate(doc, start=1):
        zoom = pdf_dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # Convert to numpy array
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        out_name = f"{i:03d}.png"
        out_path = os.path.join(output_dir, out_name)
        cv2.imwrite(out_path, img)
        image_paths.append(out_path)

        logging.info(f"🖼 Saved: {out_name}")

    doc.close()

    logging.info(f"✅ PDF converted successfully ({len(image_paths)} pages).")
    return image_paths
