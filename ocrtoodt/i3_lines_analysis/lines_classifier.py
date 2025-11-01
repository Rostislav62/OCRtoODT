# Путь: ocrtoodt/i3_lines_analysis/lines_classifier.py
# Назначение: Классификация строк текста в заголовки (TITLE) или абзацы (PARAGRAPH),
# сохранение результатов в cache/lines_annot.jsonl.

import os
import logging
import pandas as pd
import json
from ocrtoodt.i0_core.types_definitions import LineAnnotation
from typing import List

class LineClassifier:
    """Классификатор строк для определения заголовков и абзацев."""

    def __init__(self, config: dict):
        """
        Инициализирует классификатор.

        Args:
            config: Словарь конфигурации (classification.caps_ratio, center_tolerance_px).
        """
        self.config = config
        self.caps_ratio = config.get("classification", {}).get("caps_ratio", 0.7)
        self.center_tolerance_px = config.get("classification", {}).get("center_tolerance_px", 40)
        logging.info(f"LineClassifier инициализирован: caps_ratio={self.caps_ratio}, center_tolerance_px={self.center_tolerance_px}")

    def classify_lines(self, tsv_file: str, output_jsonl: str, image_width: int) -> List[LineAnnotation]:
        """
        Классифицирует строки из TSV-файла, сохраняет результаты в JSONL.

        Args:
            tsv_file: Путь к TSV-файлу (например, cache/ocr/page_0002_tesseract.tsv).
            output_jsonl: Путь к выходному JSONL-файлу (cache/lines_annot.jsonl).
            image_width: Ширина изображения для проверки центрирования.

        Returns:
            List[LineAnnotation]: Список аннотаций с классифицированными строками.
        """
        if not os.path.exists(tsv_file):
            logging.error(f"TSV-файл {tsv_file} не найден")
            raise FileNotFoundError(f"TSV-файл {tsv_file} не найден")

        # Читаем TSV
        df = pd.read_csv(tsv_file, sep="\t")
        lines = []

        for _, row in df.iterrows():
            try:
                text = str(row["text"])
                bbox = eval(row["bbox"])  # Предполагается, что bbox в формате [x1, y1, x2, y2]
                centered = row["centered"]
                ends_with_hyphen = row["ends_with_hyphen"]

                # Определяем тип строки
                cls = self._classify_line(text, bbox, image_width, centered)

                lines.append(
                    LineAnnotation(
                        page=row["page"],
                        line_no=row["line_no"],
                        text=text,
                        cls=cls,
                        bbox=bbox,
                        centered=centered,
                        ends_with_hyphen=ends_with_hyphen
                    )
                )
            except Exception as e:
                logging.warning(f"Ошибка обработки строки {row['line_no']}: {e}")
                continue

        # Сохраняем в JSONL
        os.makedirs(os.path.dirname(output_jsonl), exist_ok=True)
        with open(output_jsonl, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(json.dumps({
                    "page": line.page,
                    "line_no": line.line_no,
                    "text": line.text,
                    "cls": line.cls,
                    "bbox": line.bbox,
                    "centered": line.centered,
                    "ends_with_hyphen": line.ends_with_hyphen
                }, ensure_ascii=False) + "\n")
        logging.info(f"Сохранён JSONL-файл: {output_jsonl}")
        logging.info(f"Классифицировано {len(lines)} строк")

        return lines

    def _classify_line(self, text: str, bbox: list, image_width: int, centered: bool) -> str:
        """
        Определяет тип строки (TITLE или PARAGRAPH).

        Args:
            text: Текст строки.
            bbox: Координаты [x1, y1, x2, y2].
            image_width: Ширина изображения.
            centered: Флаг центрирования из TSV.

        Returns:
            str: Тип строки (TITLE или PARAGRAPH).
        """
        # Подсчёт доли заглавных букв
        if not text.strip():
            return "PARAGRAPH"
        letters = [c for c in text if c.isalpha()]
        if not letters:
            return "PARAGRAPH"
        caps_count = sum(1 for c in letters if c.isupper())
        caps_ratio = caps_count / len(letters)

        # Проверка центрирования (если не указано в TSV)
        if not isinstance(centered, bool):
            center_x = (bbox[0] + bbox[2]) / 2
            image_center = image_width / 2
            centered = abs(center_x - image_center) <= self.center_tolerance_px

        # Классификация: заголовок, если много заглавных букв или строка центрирована
        if caps_ratio >= self.caps_ratio or centered:
            return "TITLE"
        return "PARAGRAPH"