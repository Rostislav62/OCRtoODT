# Путь: ocrtoodt/i1_preprocess/image_preprocessor.py
# Назначение: Оркестратор для последовательного вызова методов предобработки изображений с логированием каждого метода и времени выполнения в файл.

import cv2
import logging
import os
import time
from ocrtoodt.i1_preprocess.grayscale import apply_grayscale
from ocrtoodt.i1_preprocess.binarize_otsu import apply_binarize_otsu
from ocrtoodt.i1_preprocess.denoise_median import apply_denoise_median
from ocrtoodt.i1_preprocess.contrast_clahe import apply_contrast_clahe
from ocrtoodt.i1_preprocess.deskew_hough import apply_deskew_hough
from ocrtoodt.i1_preprocess.perspective_correction import apply_perspective_correction
from ocrtoodt.i1_preprocess.sharpen_edges import apply_sharpen_edges
from ocrtoodt.i1_preprocess.check_dpi import apply_check_dpi


class ImagePreprocessor:
    def __init__(self, config):
        self.config = config
        # Настройка логирования в файл
        log_dir = "cache/logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "preprocess.log")
        logging.basicConfig(
            level=config.get("log_level", "INFO"),
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

    def preprocess(self, image_path, output_dir):
        """Обрабатывает изображение с учётом методов из конфига."""
        img = cv2.imread(image_path)
        if img is None:
            logging.error(f"Не удалось загрузить изображение: {image_path}")
            return None

        results = []
        for variant in self.config["preprocess"]["variants"]:
            processed_img = img.copy()
            methods = self.config["preprocess"]["methods"]
            if variant == "no_deskew_perspective":
                methods = [m for m in methods if m not in ["deskew_hough", "perspective_correction"]]
            logging.info(f"Применяемые методы для варианта '{variant}': {', '.join(methods)}")

            start_time = time.time()
            processed_img = apply_check_dpi(processed_img, self.config)
            logging.info(f"Метод check_dpi выполнен за {time.time() - start_time:.3f} секунд")

            for method in methods:
                start_time = time.time()
                if method == "grayscale":
                    processed_img = apply_grayscale(processed_img)
                elif method == "binarize_otsu":
                    processed_img = apply_binarize_otsu(processed_img)
                elif method == "denoise_median":
                    processed_img = apply_denoise_median(processed_img)
                elif method == "contrast_clahe":
                    processed_img = apply_contrast_clahe(processed_img)
                elif method == "deskew_hough":
                    processed_img = apply_deskew_hough(processed_img)
                elif method == "perspective_correction":
                    processed_img = apply_perspective_correction(processed_img)
                elif method == "sharpen_edges":
                    processed_img = apply_sharpen_edges(processed_img)
                logging.info(f"Метод {method} выполнен за {time.time() - start_time:.3f} секунд")

            output_path = f"{output_dir}/{variant}_{os.path.basename(image_path)}"
            cv2.imwrite(output_path, processed_img)
            logging.info(f"Сохранено: {output_path}")
            results.append(output_path)

        return results