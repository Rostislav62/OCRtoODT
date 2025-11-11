# Путь: tests/i1_preprocess/test_image_preprocessor.py
# Назначение: Тест для проверки предобработки реального изображения 2.jpg с использованием конфигурации из config.yaml, проверяет результат после всех методов.

import pytest
import numpy as np
import cv2
import os
import yaml
from ocrtoodt.i1_preprocess.image_preprocessor import ImagePreprocessor


def test_preprocess_image():
    # Загружаем конфигурацию из config.yaml
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    # Путь к реальному изображению
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    test_image_path = os.path.join(BASE_DIR, "input", "2.jpg")

    preprocessor = ImagePreprocessor(config)
    output_dir = os.path.join(BASE_DIR, "cache", "preproc")

    # Проверяем существование входного изображения
    assert os.path.exists(test_image_path), f"Входное изображение {test_image_path} не найдено"

    # Запускаем предобработку
    results = preprocessor.preprocess(test_image_path, output_dir)

    # Проверяем, что результат — список путей к изображениям (промежуточные + финальное)
    assert isinstance(results, list)
    assert len(results) > 0, "Должны быть сохранены промежуточные и финальное изображения"

    # Загружаем финальное обработанное изображение
    final_image = results[-1]
    assert final_image.endswith("processed_2.jpg")
    processed_img = cv2.imread(final_image, cv2.IMREAD_GRAYSCALE)

    # Проверяем, что изображение серое (2D) и значения пикселей в допустимом диапазоне
    assert len(processed_img.shape) == 2
    assert processed_img.max() <= 255
    assert processed_img.min() >= 0

    # Проверяем, что resize_dpi увеличил размер, если включён
    original_img = cv2.imread(test_image_path, cv2.IMREAD_GRAYSCALE)
    if config.get("preprocess", {}).get("resize_dpi", False):
        assert processed_img.shape[0] >= original_img.shape[
            0] * 2, "Изображение должно быть увеличено (DPI <= 150 -> 300)"
    else:
        assert processed_img.shape[0] == original_img.shape[
            0], "Изображение не должно быть увеличено (resize_dpi: false)"

    # Проверяем горизонтальность текста, если deskew_hough включён
    if config.get("preprocess", {}).get("deskew_hough", False):
        edges = cv2.Canny(processed_img, 30, 100, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 150)
        if lines is not None:
            angles = [abs((line[0][1] * 180 / np.pi) - 90) for line in lines[:10]]
            mean_angle = np.mean(angles)
            assert mean_angle < 15, f"Текст не выровнен, средний угол: {mean_angle} градусов"

    # Проверяем, что crop_to_text_contour уменьшил размер изображения, если включён
    if config.get("preprocess", {}).get("crop_to_text_contour", False):
        assert processed_img.shape[0] <= original_img.shape[0], "Изображение должно быть обрезано по высоте"
        assert processed_img.shape[1] <= original_img.shape[1], "Изображение должно быть обрезано по ширине"