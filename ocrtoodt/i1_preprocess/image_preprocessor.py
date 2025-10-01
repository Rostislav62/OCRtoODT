import cv2
import numpy as np
import logging
import os

class ImagePreprocessor:
    def __init__(self, config):
        self.config = config
        logging.basicConfig(level=config.get("log_level", "INFO"))

    def preprocess(self, image_path, output_dir):
        """Обрабатывает изображение с учётом методов из конфига."""
        img = cv2.imread(image_path)
        if img is None:
            logging.error(f"Не удалось загрузить изображение: {image_path}")
            return None

        results = []
        for variant in self.config["preprocess"]["variants"]:
            processed_img = img.copy()
            for method in self.config["preprocess"]["methods"]:
                if method == "grayscale":
                    processed_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2GRAY)
                elif method == "binarize_otsu":
                    if len(processed_img.shape) == 3:
                        processed_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2GRAY)
                    _, processed_img = cv2.threshold(processed_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                elif method == "denoise_median":
                    processed_img = cv2.medianBlur(processed_img, 3)
                elif method == "contrast_clahe":
                    if len(processed_img.shape) == 3:
                        processed_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2GRAY)
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                    processed_img = clahe.apply(processed_img)
                elif method == "deskew_hough":
                    processed_img = self.deskew_hough(processed_img)
                elif method == "perspective_correction":
                    processed_img = self.perspective_correction(processed_img)
                elif method == "sharpen_edges":
                    processed_img = self.sharpen_edges(processed_img)

            # Сохранение варианта
            output_path = f"{output_dir}/{variant}_{os.path.basename(image_path)}"
            cv2.imwrite(output_path, processed_img)
            logging.info(f"Сохранено: {output_path}")
            results.append(output_path)

        return results

    def deskew_hough(self, img):
        """Выравнивание наклонных строк с помощью Hough Transform."""
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(img, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        if lines is not None:
            angle = 0
            for rho, theta in lines[0]:
                angle = (theta * 180 / np.pi) - 90
                break
            (h, w) = img.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            img = cv2.warpAffine(img, M, (w, h))
        return img

    def perspective_correction(self, img):
        """Коррекция перспективы для выпуклых страниц."""
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(img, 50, 150, apertureSize=3)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            logging.warning("Контуры страницы не найдены")
            return img

        contour = max(contours, key=cv2.contourArea)
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        if len(approx) == 4:
            pts = approx.reshape(4, 2)
            rect = np.zeros((4, 2), dtype="float32")
            s = pts.sum(axis=1)
            rect[0] = pts[np.argmin(s)]  # Верх-лево
            rect[2] = pts[np.argmax(s)]  # Низ-право
            diff = np.diff(pts, axis=1)
            rect[1] = pts[np.argmin(diff)]  # Верх-право
            rect[3] = pts[np.argmax(diff)]  # Низ-лево

            (h, w) = img.shape[:2]
            dst = np.array([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]], dtype="float32")
            M = cv2.getPerspectiveTransform(rect, dst)
            img = cv2.warpPerspective(img, M, (w, h))
        else:
            logging.warning("Недостаточно точек для коррекции перспективы")
        return img

    def sharpen_edges(self, img):
        """Усиление резкости по краям."""
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(img, (5, 5), 0)
        img = cv2.addWeighted(img, 1.5, blurred, -0.5, 0)
        return img