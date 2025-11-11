# Path: ocrtoodt/i0_core/cli_entrypoint.py
# Purpose: Entry point for CLI pipeline (used by GUI worker and direct CLI runs).

import os
import sys
import yaml
import argparse
import tempfile

# --- Ensure root of project is in sys.path BEFORE any imports ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Now safe to import internal modules
from ocrtoodt.i0_core.pipeline_orchestrator import run_pipeline


def main():
    """
    Entry point for both direct CLI and GUI subprocess calls.
    Detects embedded Tesseract inside onefile/Nuitka temp dirs if present,
    adjusts config.yaml accordingly, then launches the OCR pipeline.
    """
    parser = argparse.ArgumentParser(description="OCRtoODT pipeline (Tesseract OCR + ODT builder)")
    parser.add_argument("--config", default="config.yaml", help="Path to configuration file (YAML)")
    parser.add_argument("--input-image", help="Optional single image path")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    args = parser.parse_args()

    try:
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        ocr_cfg = cfg.get("ocr", {})

        engine_path = ocr_cfg.get("ocr_engine_path")
        tessdata_dir = ocr_cfg.get("tessdata_dir")

        if not engine_path or not os.path.isfile(engine_path):
            print(f"[ERROR] Tesseract binary not found at {engine_path}")
            sys.exit(1)
        if not tessdata_dir or not os.path.isdir(tessdata_dir):
            print(f"[WARN] tessdata folder not found at {tessdata_dir}")
        print(f"[OK] Using Tesseract: {engine_path}")
        print(f"[OK] Using tessdata:  {tessdata_dir}")

    except Exception as e:
        print(f"[ERROR] Unable to read configuration: {e}")
        sys.exit(1)

    # --- Finally, run pipeline ---
    run_pipeline(args)


if __name__ == "__main__":
    main()
