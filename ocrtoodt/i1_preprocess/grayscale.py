# Путь: ocrtoodt/i1_preprocess/grayscale.py
# Назначение: Преобразование изображения в оттенки серого.

import cv2

def apply_grayscale(img):
    """Преобразует изображение в оттенки серого."""
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)