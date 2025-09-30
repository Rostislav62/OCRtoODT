import argparse
from ocrtoodt.0_core.pipeline_orchestrator import run_pipeline

def main():
    parser = argparse.ArgumentParser(description="OCRtoODT: Умное распознавание текста для книг.")
    parser.add_argument("--config", default="config.yaml", help="Путь к конфиг-файлу")
    parser.add_argument("--input", help="Папка с входными изображениями")
    parser.add_argument("--output", help="Путь к выходному ODT")
    parser.add_argument("--force", action="store_true", help="Пересчитать все этапы")
    args = parser.parse_args()
    run_pipeline(args)  # Вызов пайплайна

if __name__ == "__main__":
    main()