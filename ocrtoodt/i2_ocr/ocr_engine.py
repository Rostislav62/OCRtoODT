# Путь: ocrtoodt/i2_ocr/ocr_engine.py
# Назначение: Класс для выполнения OCR с использованием Tesseract, создаёт TSV-файл для каждой страницы.

import os
import logging
import cv2
import pytesseract
import pandas as pd
import numpy as np
from ocrtoodt.i0_core.types_definitions import LineAnnotation
from typing import List

class OCREngine:
    """Класс для выполнения OCR с использованием Tesseract."""

    def __init__(self, config: dict):
        """
        Инициализирует OCR-движок.

        Args:
            config: Словарь конфигурации с настройками OCR.
        """
        self.config = config
        self.enabled_engines = config.get("ocr", {}).get("enabled_engines", ["tesseract"])
        self.languages = config.get("ocr", {}).get("languages", ["rus", "eng"])
        self.dpi = config.get("ocr", {}).get("dpi", 75)
        self.psm = config.get("ocr", {}).get("tesseract_psm", 6)
        if "tesseract" not in self.enabled_engines:
            raise ValueError("Tesseract должен быть включён в enabled_engines")
        logging.info(f"Tesseract инициализирован с языками: {self.languages}, psm: {self.psm}")

    def process_image(self, image: np.ndarray, output_dir: str, page_num: int) -> List[LineAnnotation]:
        """
        Выполняет OCR на изображении с использованием Tesseract.

        Args:
            image: Изображение (numpy array) для обработки.
            output_dir: Директория для сохранения результатов (cache/ocr).
            page_num: Номер страницы для имени TSV и поля page.

        Returns:
            List[LineAnnotation]: Список аннотаций строк.
        """
        os.makedirs(output_dir, exist_ok=True)
        base_name = f"page_{page_num:04d}"  # Например, page_0001
        tsv_output = os.path.join(output_dir, f"{base_name}.tsv")

        # Настраиваем Tesseract
        os.environ["TESSDATA_PREFIX"] = "/usr/share/tesseract-ocr/5/tessdata/"

        # Формируем конфигурацию Tesseract (без whitelist)
        config = f"--psm {self.psm} -l {'+'.join(self.languages)} --dpi {self.dpi}"

        # Выполняем OCR
        try:
            tsv_data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
            logging.info(f"Tesseract обработал изображение, найдено {len(tsv_data['text'])} элементов")
        except Exception as e:
            logging.error(f"Ошибка Tesseract для страницы {page_num}: {e}")
            raise

        # Группируем слова в строки на основе block_num, par_num, line_num
        lines = []
        current_line = []
        current_bbox = None
        line_no = 0
        prev_line_key = None

        for i in range(len(tsv_data["text"])):
            if tsv_data["text"][i].strip() and tsv_data["width"][i] > 0 and tsv_data["height"][i] > 0:
                try:
                    bbox = [
                        tsv_data["left"][i],
                        tsv_data["top"][i],
                        tsv_data["left"][i] + tsv_data["width"][i],
                        tsv_data["top"][i] + tsv_data["height"][i]
                    ]
                    line_key = (tsv_data["block_num"][i], tsv_data["par_num"][i], tsv_data["line_num"][i])

                    # Проверяем, принадлежит ли слово текущей строке
                    if prev_line_key is None or line_key == prev_line_key:
                        current_line.append((tsv_data["text"][i], bbox[0]))
                        if current_bbox is None:
                            current_bbox = bbox
                        else:
                            current_bbox[0] = min(current_bbox[0], bbox[0])
                            current_bbox[2] = max(current_bbox[2], bbox[2])
                            current_bbox[1] = min(current_bbox[1], bbox[1])
                            current_bbox[3] = max(current_bbox[3], bbox[3])
                    else:
                        # Завершаем текущую строку
                        if current_line:
                            current_line.sort(key=lambda x: x[1])  # Сортировка по x-координате
                            text = " ".join(word for word, _ in current_line)
                            lines.append({
                                "page": page_num,
                                "line_no": line_no,
                                "text": text,
                                "bbox": current_bbox
                            })
                            line_no += 1
                        current_line = [(tsv_data["text"][i], bbox[0])]
                        current_bbox = bbox

                    prev_line_key = line_key
                except Exception as e:
                    logging.warning(f"Ошибка обработки слова {i} на странице {page_num}: {e}")
                    continue

        # Добавляем последнюю строку
        if current_line:
            current_line.sort(key=lambda x: x[1])
            text = " ".join(word for word, _ in current_line)
            lines.append({
                "page": page_num,
                "line_no": line_no,
                "text": text,
                "bbox": current_bbox
            })

        # Сохраняем TSV только с текстовыми строками
        df = pd.DataFrame([
            {
                "page": line["page"],
                "line_no": line["line_no"],
                "text": line["text"],
                "bbox": str(line["bbox"]),
            }
            for line in lines if line["text"].strip()
        ])
        df.to_csv(tsv_output, sep="\t", index=False, encoding="utf-8")
        logging.info(f"Сохранён TSV-файл: {tsv_output}")

        # Формируем список LineAnnotation
        result = [
            LineAnnotation(
                page=line["page"],
                line_no=line["line_no"],
                text=line["text"],
                bbox=line["bbox"],
            )
            for line in lines
        ]

        logging.info(f"Извлечено {len(result)} строк с помощью Tesseract для страницы {page_num}")
        return result