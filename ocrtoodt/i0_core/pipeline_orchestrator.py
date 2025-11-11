# ocrtoodt/i0_core/pipeline_orchestrator.py
"""
Main orchestrator for OCRtoODT.
Handles image preprocessing, OCR, and ODT document assembly.
All paths are taken from config.yaml — no hardcoded values.
"""

import os, sys, logging, argparse, yaml, glob, re, multiprocessing, copy, time
import numpy as np
import cv2
from logging.handlers import QueueHandler, QueueListener
from multiprocessing import Queue
from ocrtoodt.i0_core.pdf_splitter import pdf_to_images
from ocrtoodt.i1_preprocess.image_preprocessor import ImagePreprocessor
from ocrtoodt.i2_ocr.ocr_engine import OCREngine
from ocrtoodt.i4_document_builder.odt_assembler import ODTAssembler


def setup_logging(log_level, log_file):
    """Set up multiprocessing-safe logging (QueueHandler + QueueListener)."""
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

    logger = logging.getLogger()
    if not logger.hasHandlers():
        fmt = logging.Formatter("%(asctime)s - %(levelname)s - [PID %(process)d] - %(message)s")
        handler = logging.StreamHandler()
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, config.get("log_level", "INFO")))

    start_time = time.perf_counter()
    logging.info(f"Processing {input_image} as page {page_num}")

    preprocessor = ImagePreprocessor(config)
    preproc_results = preprocessor.preprocess(input_image)
    image = preproc_results["final_image"]

    if isinstance(image, str):
        image = cv2.imread(image)
        if image is None:
            raise ValueError(f"Cannot read image file: {image}")
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    elif isinstance(image, np.ndarray):
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    else:
        raise ValueError(f"Unexpected image type: {type(image)}")

    logging.info("Preprocessing complete")

    # --- OCR ---
    ocr_engine = OCREngine(config)
    ocr_dir = config.get("ocr_dir")
    os.makedirs(ocr_dir, exist_ok=True)
    lines = ocr_engine.process_image(image, ocr_dir, page_num)
    output_file = os.path.join(ocr_dir, f"page_{page_num:04d}.tsv")
    logging.info(f"OCR complete: {len(lines)} lines, saved to {output_file}")

    elapsed = time.perf_counter() - start_time
    logging.info(f"Page {page_num} processed in {elapsed:.2f}s")

    return output_file


def run_pipeline(args):
    """Main pipeline: preprocess → OCR → ODT assembly."""
    start_time = time.perf_counter()

    # --- Load config and resolve paths ---
    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # --- Logging setup ---
    log_file = config.get("log_file")
    if not log_file:
        raise ValueError("Missing 'log_file' in config.yaml")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    log_level = getattr(logging, config.get("log_level", "INFO"))
    listener = setup_logging(log_level, log_file)
    logging.info("Pipeline started")

    # --- Input directory and patterns ---
    input_dir = config.get("input_dir")
    if not input_dir or not os.path.isdir(input_dir):
        listener.stop()
        raise FileNotFoundError(f"Input directory not found or invalid: {input_dir}")

    input_pattern = config.get("input_files_pattern", "*.jpg *.jpeg *.tif *.tiff *.png *.pdf")

    # Collect files matching patterns
    input_files = []
    for pattern in input_pattern.split():
        input_files.extend(glob.glob(os.path.join(input_dir, pattern)))

    input_files = sorted(set(input_files), key=natural_key)

    # --- PDF expansion (if any) ---
    expanded_files = []
    for f in input_files:
        if f.lower().endswith(".pdf"):
            logging.info(f"Converting PDF to images: {f}")
            pdf_images = pdf_to_images(f, input_dir, dpi=config.get("pdf_dpi", 300))
            expanded_files.extend(pdf_images)
        else:
            expanded_files.append(f)

    input_files = sorted(set(expanded_files), key=natural_key)
    if not input_files:
        listener.stop()
        raise FileNotFoundError(f"No input files found in {input_dir}")

    logging.info(f"Total images for OCR: {len(input_files)}")

    # --- Parallel processing ---
    par_cfg = config.get("parallel", {})
    parallel_enabled = bool(par_cfg.get("enabled", True))
    num_proc = par_cfg.get("num_processes", 1)
    num_proc = multiprocessing.cpu_count() - 1 if num_proc == "auto" else int(num_proc)

    params = [(img, copy.deepcopy(config), natural_key(img)) for img in input_files]

    tsv_files = []
    if not parallel_enabled or num_proc == 1:
        for p in params:
            tsv_files.append(process_single_image(p))
    else:
        with multiprocessing.Pool(processes=num_proc) as pool:
            for tsv_file in pool.imap(process_single_image, params):
                tsv_files.append(tsv_file)

    # --- Assemble ODT ---
    odt_assembler = ODTAssembler(config)
    odt_file = odt_assembler.assemble_odt(tsv_files)
    logging.info(f"ODT document assembled: {odt_file}")

    total_time = time.perf_counter() - start_time
    logging.info(f"Pipeline finished in {total_time:.2f}s")

    listener.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR to ODT pipeline")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML configuration file")
    args = parser.parse_args()
    run_pipeline(args)
