# Путь: ocrtoodt/i0_core/cli_entrypoint.py
# Назначение: Точка входа для CLI.

import argparse
from ocrtoodt.i0_core.pipeline_orchestrator import run_pipeline

def main():
    parser = argparse.ArgumentParser(description="OCR to ODT pipeline")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--input-image", help="Path to input image")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    args = parser.parse_args()
    run_pipeline(args)

if __name__ == "__main__":
    main()
