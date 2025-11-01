# Путь: ocrtoodt/i1_preprocess/sharpen_edges.py
# Назначение: Усиление резкости по краям изображения.

import cv2

def apply_sharpen_edges(img):
    """Усиление резкости по краям."""
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(img, (5, 5), 0)
    img = cv2.addWeighted(img, 1.5, blurred, -0.5, 0)
    return img