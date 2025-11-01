# Путь: ocrtoodt/i1_preprocess/binarize_otsu.py
# Назначение: Бинаризация изображения методом Оцу.

import cv2

def apply_binarize_otsu(img):
    """Применяет бинаризацию по методу Оцу."""
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, processed_img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return processed_img