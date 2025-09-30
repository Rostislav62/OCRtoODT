import pytest
import numpy as np
import cv2
from ocrtoodt.i1_preprocess.image_preprocessor import ImagePreprocessor

def test_preprocess_grayscale(tmp_path):
    config = {"preprocess": {"methods": ["grayscale"], "variants": ["variant1"]}, "log_level": "INFO"}
    preprocessor = ImagePreprocessor(config)
    # Создаём тестовое изображение
    img = np.ones((100, 100, 3), dtype=np.uint8) * 255  # Белое RGB
    test_image = str(tmp_path / "test.jpg")
    cv2.imwrite(test_image, img)
    # Тест
    result = preprocessor.preprocess(test_image, str(tmp_path))
    assert result is not None
    processed_img = cv2.imread(result, cv2.IMREAD_GRAYSCALE)
    assert len(processed_img.shape) == 2  # Идеальный продукт: Grayscale изображение