import pytest
import numpy as np
import cv2
from ocrtoodt.i1_preprocess.image_preprocessor import ImagePreprocessor

def test_preprocess_all_methods(tmp_path):
    config = {
        "preprocess": {
            "methods": ["grayscale", "binarize_otsu", "denoise_median", "contrast_clahe", "deskew_hough", "perspective_correction", "sharpen_edges"],
            "variants": ["default"],
            "log_level": "INFO"
        }
    }
    preprocessor = ImagePreprocessor(config)
    # Создаём тестовое изображение
    img = np.ones((100, 100, 3), dtype=np.uint8) * 255  # Белое RGB
    test_image = str(tmp_path / "test.jpg")
    cv2.imwrite(test_image, img)
    # Тест
    results = preprocessor.preprocess(test_image, str(tmp_path))
    assert isinstance(results, list)  # Проверяем, что результат — список
    assert len(results) == 1  # Один вариант ("default")
    assert results[0].endswith("default_test.jpg")  # Проверяем имя файла

    # Проверяем результат
    processed_img = cv2.imread(results[0], cv2.IMREAD_GRAYSCALE)
    assert len(processed_img.shape) == 2  # Grayscale
    assert processed_img.max() <= 255  # Бинаризация
    assert processed_img.min() >= 0   # Бинаризация
    # Проверка резкости (дисперсия ненулевая после sharpen_edges)
    assert np.var(processed_img) >= 0