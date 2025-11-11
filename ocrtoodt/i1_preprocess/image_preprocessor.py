# Path: ocrtoodt/i1_preprocess/image_preprocessor.py
import os
import cv2
import numpy as np
import logging
from PIL import Image

class ImagePreprocessor:
    """
    Единый модуль предобработки изображений.
    Каждый шаг включается/выключается по флагам из config.yaml.
    """

    def __init__(self, config):
        self.config = config
        self.pre_cfg = config.get("preprocess", {})
        self.preproc_dir = config.get("preproc_dir", "cache/preproc")

    # ------------------------------------------------------------
    def preprocess(self, image_path: str, output_dir: str = None):
        """Основной конвейер предобработки (по флагам)."""
        os.makedirs(output_dir or self.preproc_dir, exist_ok=True)

        # 1. Загрузка (универсально JPG, PNG, TIFF, PDF)
        image = self.load_image(image_path)
        logging.info(f"Изображение загружено: {image_path} ({image.shape})")

        # 2. Преобразование в оттенки серого
        if self.pre_cfg.get("grayscale", False):
            image = self.to_grayscale(image)
            logging.info("Преобразование в оттенки серого")

        # 3. Удаление шума
        if self.pre_cfg.get("denoise_median", False):
            image = self.denoise_median(image)
            logging.info("Удаление шума (медианный фильтр)")

        # 4. Улучшение контраста CLAHE
        if self.pre_cfg.get("contrast_clahe", False):
            image = self.apply_contrast_clahe(image)
            logging.info("Улучшение контраста CLAHE")

        # 5. Бинаризация методом Оцу
        if self.pre_cfg.get("binarize_otsu", False):
            image = self.binarize_otsu(image)
            logging.info("Бинаризация Оцу")

        # 6. Усиление резкости краёв
        if self.pre_cfg.get("sharpen_edges", False):
            image = self.sharpen_edges(image)
            logging.info("Усиление резкости краёв")

        # 7. Работа полностью в RAM — не сохраняем на диск
        logging.info("Предобработка завершена (RAM only, без сохранения файлов)")
        return {"final_image": image}

    # ------------------------------------------------------------
    def load_image(self, image_path: str):
        """Поддержка JPG, PNG, TIFF, PDF (1-я страница PDF)."""
        _, ext = os.path.splitext(image_path.lower())
        if ext in [".tif", ".tiff"]:
            img = Image.open(image_path)
            if img.mode != "RGB":
                img = img.convert("RGB")
            image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        elif ext in [".png", ".jpg", ".jpeg"]:
            image = cv2.imread(image_path)
        elif ext == ".pdf":
            from pdf2image import convert_from_path
            pages = convert_from_path(image_path, dpi=300)
            if not pages:
                raise ValueError(f"Не удалось извлечь страницы из PDF: {image_path}")
            img = pages[0].convert("RGB")
            image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {ext}")
        if image is None:
            raise ValueError(f"Не удалось загрузить: {image_path}")
        return image

    # ------------------------------------------------------------
    def to_grayscale(self, image):
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def denoise_median(self, image, ksize: int = 3):
        return cv2.medianBlur(image, ksize)

    def apply_contrast_clahe(self, image):
        if len(image.shape) == 2:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(image)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l2 = clahe.apply(l)
        merged = cv2.merge((l2, a, b))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    def binarize_otsu(self, image):
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    def sharpen_edges(self, image):
        kernel = np.array([[0, -1, 0],
                           [-1, 5, -1],
                           [0, -1, 0]])
        return cv2.filter2D(image, -1, kernel)
