# Путь: ocrtoodt/i1_preprocess/check_dpi.py
# Назначение: Проверка DPI изображения и увеличение до 300 DPI, если меньше, с выводом DPI в консоль.

import cv2
from PIL import Image
import logging

def apply_check_dpi(img, config):
    """Проверяет DPI и увеличивает до 300, если меньше."""
    if not config.get("preprocess", {}).get("dpi_adjust", True):
        return img

    # Читаем DPI через PIL
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    exif_data = pil_img.getexif()
    if exif_data:
        dpi = exif_data.get(282, (300, 1))[0] / exif_data.get(282, (300, 1))[1]
        logging.info(f"Оригинальное DPI: {dpi:.1f}")
        if dpi < 300:
            scale = 300 / dpi
            (h, w) = img.shape[:2]
            new_h, new_w = int(h * scale), int(w * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            logging.info(f"Изображение увеличено до 300 DPI (оригинал: {dpi:.1f})")
        else:
            logging.info("DPI уже 300 или выше, корректировка не требуется")
    else:
        logging.warning("DPI не найдено, используется оригинальное изображение")
    return img