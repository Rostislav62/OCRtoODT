# Путь: ocrtoodt/i1_preprocess/contrast_clahe.py
# Назначение: Усиление контраста с помощью адаптивной гистограммной эквализации.

import cv2

def apply_contrast_clahe(img):
    """Усиливает контраст с помощью CLAHE."""
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(img)