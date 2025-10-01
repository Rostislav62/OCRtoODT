import pytest
import numpy as np
import cv2
import os
from ocrtoodt.i1_preprocess.image_preprocessor import ImagePreprocessor


def test_preprocess_all_methods():
    config = {
        "preprocess": {
            "methods": ["grayscale", "binarize_otsu", "denoise_median", "contrast_clahe", "deskew_hough",
                        "perspective_correction", "sharpen_edges"],
            "variants": ["default"],
            "log_level": "INFO"
        }
    }
    preprocessor = ImagePreprocessor(config)
    # Используем реальное изображение
    input_image = "input/page.jpg"
    output_dir = "cache/preproc"

    # Проверяем, что входное изображение существует
    assert os.path.exists(input_image), f"Входное изображение {input_image} не найдено"

    # Тест
    results = preprocessor.preprocess(input_image, output_dir)
    assert isinstance(results, list)  # Проверяем, что результат — список
    assert len(results) == 1  # Один вариант ("default")
    assert results[0].endswith("default_page.jpg")  # Проверяем имя файла

    # Проверяем результат
    processed_img = cv2.imread(results[0], cv2.IMREAD_GRAYSCALE)
    assert len(processed_img.shape) == 2  # Grayscale
    assert processed_img.max() <= 255  # Бинаризация
    assert processed_img.min() >= 0  # Бинаризация
    assert np.var(processed_img) >= 0  # Проверка резкости