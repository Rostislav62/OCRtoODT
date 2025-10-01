import pytest
import numpy as np
import cv2
import os
from ocrtoodt.i1_preprocess.image_preprocessor import ImagePreprocessor


def test_preprocess_deskew_perspective():
    config = {
        "preprocess": {
            "methods": ["grayscale", "binarize_otsu", "denoise_median", "contrast_clahe", "deskew_hough",
                        "perspective_correction", "sharpen_edges"],
            "variants": ["no_deskew_perspective", "full"],
            "log_level": "INFO"
        }
    }
    preprocessor = ImagePreprocessor(config)
    input_image = "input/page.jpg"
    output_dir = "cache/preproc"

    assert os.path.exists(input_image), f"Входное изображение {input_image} не найдено"

    results = preprocessor.preprocess(input_image, output_dir)
    assert isinstance(results, list)
    assert len(results) == 2
    assert results[0].endswith("no_deskew_perspective_page.jpg")
    assert results[1].endswith("full_page.jpg")

    # Проверка no_deskew_perspective
    img_no_deskew = cv2.imread(results[0], cv2.IMREAD_GRAYSCALE)
    assert len(img_no_deskew.shape) == 2
    assert img_no_deskew.max() <= 255
    assert img_no_deskew.min() >= 0

    # Проверка full (с deskew_hough и perspective_correction)
    img_full = cv2.imread(results[1], cv2.IMREAD_GRAYSCALE)
    assert len(img_full.shape) == 2
    assert img_full.max() <= 255
    assert img_full.min() >= 0

    # Проверка горизонтальности текста (для full)
    edges = cv2.Canny(img_full, 30, 100, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 150)
    if lines is not None:
        angles = [abs((line[0][1] * 180 / np.pi) - 90) for line in lines[:10]]
        mean_angle = np.mean(angles)
        assert mean_angle < 15, f"Текст не выровнен, средний угол: {mean_angle} градусов"