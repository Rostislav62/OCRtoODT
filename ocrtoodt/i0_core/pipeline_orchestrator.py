# Path: ocrtoodt/i0_core/pipeline_orchestrator.py
# Purpose: Orchestrator for preprocessing, OCR, and document assembly (Tesseract only, parallelized).

import os
import logging
import argparse
import yaml
import cv2
import glob
import re
import time
import numpy as np
import multiprocessing
import copy
from logging.handlers import QueueHandler, QueueListener
from multiprocessing import Queue
from ocrtoodt.i1_preprocess.image_preprocessor import ImagePreprocessor
from ocrtoodt.i2_ocr.ocr_engine import OCREngine
from ocrtoodt.i4_document_builder.odt_assembler import ODTAssembler


def setup_logging(log_level, log_file):
    """Sets up multiprocessing-safe logging (QueueHandler + QueueListener)."""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    log_format = logging.Formatter("%(asctime)s - %(levelname)s - [PID %(process)d] - %(message)s")

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(log_format)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_format)

    log_queue = Queue()
    queue_handler = QueueHandler(log_queue)

    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addHandler(queue_handler)

    listener = QueueListener(log_queue, file_handler, stream_handler)
    listener.start()

    return listener


def natural_key(filename):
    """Natural sort by numeric prefix in filename."""
    base = os.path.basename(filename)
    match = re.match(r"(\d+)", base)
    return int(match.group(1)) if match else float("inf")


def process_single_image(params):
    """Process one image: preprocess → OCR → TSV output."""
    input_image, config, page_num = params

    # Local logging setup (safe inside multiprocessing)
    logger = logging.getLogger()
    if not logger.hasHandlers():
        fmt = logging.Formatter("%(asctime)s - %(levelname)s - [PID %(process)d] - %(message)s")
        handler = logging.StreamHandler()
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, config.get("log_level", "INFO")))

    start_time = time.perf_counter()
    logging.info(f"Обработка изображения {input_image} как страница {page_num}")

    # --- Предобработка ---
    preprocessor = ImagePreprocessor(config)
    preproc_results = preprocessor.preprocess(input_image)
    image = preproc_results["final_image"]

    if isinstance(image, str):  # fallback если вдруг путь
        image = cv2.imread(image)
        if image is None:
            raise ValueError(f"Ошибка чтения файла: {image}")
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    elif isinstance(image, np.ndarray):
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    else:
        raise ValueError(f"Некорректный тип результата предобработки: {type(image)}")

    logging.info("Предобработка завершена")

    # --- OCR (Tesseract only) ---
    ocr_engine = OCREngine(config)
    lines = ocr_engine.process_image(image, config.get("ocr_dir", "cache/ocr"), page_num)
    output_file = os.path.join(config.get("ocr_dir", "cache/ocr"), f"page_{page_num:04d}.tsv")
    logging.info(f"OCR завершён: {len(lines)} строк, сохранено в {output_file}")

    end_time = time.perf_counter()
    logging.info(f"Страница {page_num} обработана за {end_time - start_time:.2f} сек")

    return output_file


def run_pipeline(args):
    """Main orchestrator: preprocess → OCR (parallel) → ODT assembly."""
    start_time = time.perf_counter()

    # --- Настройка логирования ---
    with open(args.config, "r") as f:
        config = yaml.safe_load(f)
    log_file = config.get("log_file", "cache/logs/pipeline.log")
    log_level = getattr(logging, config.get("log_level", "INFO"))
    listener = setup_logging(log_level, log_file)
    logging.info("Пайплайн запущен")

    # --- Поиск изображений ---
    input_dir = config.get("input_dir", "input")
    input_pattern = config.get("input_files_pattern", "*.jpg *.jpeg *.tif *.tiff *.png *.pdf")
    input_files = []
    for pattern in input_pattern.split():
        input_files.extend(glob.glob(os.path.join(input_dir, pattern)))
    input_files = sorted(set(input_files), key=natural_key)

    if not input_files:
        logging.error(f"Не найдены изображения в {input_dir} по шаблону {input_pattern}")
        listener.stop()
        raise FileNotFoundError(f"Не найдены изображения в {input_dir}")

    logging.info(f"Найдено {len(input_files)} изображений: {input_files}")

    # --- Настройка параллельной обработки ---
    par_cfg = config.get("parallel", {})
    parallel_enabled = bool(par_cfg.get("enabled", True))
    num_processes = par_cfg.get("num_processes", "auto")

    if num_processes == "auto":
        num_processes = max(1, multiprocessing.cpu_count() - 1)
    else:
        num_processes = int(num_processes)

    logging.info(f"Параллельная обработка: {parallel_enabled}, процессов: {num_processes}")

    # --- Подготовка параметров ---
    params_list = []
    for input_image in input_files:
        page_num = natural_key(input_image)
        if page_num == float("inf"):
            logging.warning(f"Пропуск файла без номера: {input_image}")
            continue
        params_list.append((input_image, copy.deepcopy(config), page_num))

    # --- Параллельная предобработка + OCR ---
    tsv_files = []
    if not parallel_enabled or num_processes == 1:
        for params in params_list:
            tsv_file = process_single_image(params)
            tsv_files.append(tsv_file)
    else:
        logging.info(f"Запуск параллельной обработки ({num_processes} процессов)...")
        with multiprocessing.Pool(processes=num_processes) as pool:
            tsv_files = pool.map(process_single_image, params_list)

    # --- Сортировка по страницам ---
    tsv_files.sort(key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0]))

    # --- Сборка ODT ---
    odt_assembler = ODTAssembler(config)
    odt_file = odt_assembler.assemble_odt(tsv_files)
    logging.info(f"Собран ODT-документ: {odt_file}")

    end_time = time.perf_counter()
    logging.info(f"Пайплайн завершён за {end_time - start_time:.2f} секунд")

    listener.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR to ODT pipeline (Tesseract only, parallelized)")
    parser.add_argument("--config", default="config.yaml", help="Путь к YAML-конфигу")
    parser.add_argument("--log-level", default="INFO", help="Уровень логирования")
    args = parser.parse_args()
    run_pipeline(args)
