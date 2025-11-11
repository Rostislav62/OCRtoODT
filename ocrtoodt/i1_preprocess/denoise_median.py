# Путь: ocrtoodt/i1_preprocess/denoise_median.py
# Назначение: Уменьшение шума с помощью медианного фильтра.

import cv2

def apply_denoise_median(img):
    """Уменьшает шум с помощью медианного фильтра."""
    return cv2.medianBlur(img, 3)