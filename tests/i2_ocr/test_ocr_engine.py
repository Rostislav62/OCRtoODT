# Путь: tests/i2_ocr/test_ocr_engine.py
# Назначение: Тест для проверки работы OCR-движка.

import pytest
import os
import cv2
import numpy as np
from ocrtoodt.i2_ocr.ocr_engine import OCREngine
from ocrtoodt.i0_core.types_definitions import LineAnnotation

@pytest.fixture
def config():
    """Фикстура для конфигурации."""
    return {
        "ocr": {
            "enabled_engines": ["tesseract"],
            "languages": ["rus", "eng"],
            "dpi": 75,
            "tesseract_psm": 4
        }
    }

@pytest.fixture
def sample_image(tmp_path):
    """Создаёт тестовое изображение."""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img_path = str(tmp_path / "test_image.jpg")
    cv2.imwrite(img_path, img)
    return img_path

def test_ocr_engine(config, sample_image, tmp_path):
    """Тестирует OCR-движок."""
    ocr_engine = OCREngine(config)
    image = cv2.imread(sample_image)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    output_dir = str(tmp_path / "ocr")
    lines = ocr_engine.process_image(image, output_dir)

    assert isinstance(lines, list), "Результат должен быть списком"
    assert all(isinstance(line, LineAnnotation) for line in lines), "Все элементы должны быть LineAnnotation"
    assert os.path.exists(os.path.join(output_dir, "page_0002_tesseract.txt")), "Текстовый файл должен быть создан"
    assert os.path.exists(os.path.join(output_dir, "page_0002_tesseract.tsv")), "TSV-файл должен быть создан"