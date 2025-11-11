# Путь: tests/i3_lines_analysis/test_lines_classifier.py
# Назначение: Тест для проверки классификации строк в заголовки и абзацы.

import pytest
import os
import yaml
import json
import pandas as pd
from ocrtoodt.i3_lines_analysis.lines_classifier import LineClassifier

@pytest.fixture
def config():
    """Загружает конфигурацию из config.yaml."""
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

@pytest.fixture
def tsv_file(tmp_path):
    """Создаёт тестовый TSV-файл."""
    tsv_data = [
        {
            "page": 2,
            "line_no": 0,
            "text": "ДИАНЕТИКА - ТОЧНАЯ НАУКА",
            "bbox": [100, 50, 500, 100],
            "centered": True,
            "ends_with_hyphen": False
        },
        {
            "page": 2,
            "line_no": 1,
            "text": "Дианетика - это точная наука, и её применение сопоставимо с инженерным делом, только проще.",
            "bbox": [50, 150, 550, 200],
            "centered": False,
            "ends_with_hyphen": False
        }
    ]
    tsv_path = str(tmp_path / "test_tesseract.tsv")
    pd.DataFrame(tsv_data).to_csv(tsv_path, sep="\t", index=False, encoding="utf-8")
    return tsv_path

@pytest.fixture
def output_jsonl(tmp_path):
    """Путь для выходного JSONL-файла."""
    return str(tmp_path / "lines_annot.jsonl")

def test_lines_classifier(config, tsv_file, output_jsonl):
    """Тестирует классификацию строк."""
    classifier = LineClassifier(config)
    image_width = 600  # Примерная ширина изображения

    # Классификация
    lines = classifier.classify_lines(tsv_file, output_jsonl, image_width)

    # Проверяем результат
    assert len(lines) == 2, "Должно быть классифицировано 2 строки"
    assert lines[0].cls == "TITLE", "Первая строка должна быть заголовком (много заглавных букв и центрирована)"
    assert lines[1].cls == "PARAGRAPH", "Вторая строка должна быть абзацем"

    # Проверяем JSONL
    assert os.path.exists(output_jsonl), f"JSONL-файл {output_jsonl} не создан"
    with open(output_jsonl, "r", encoding="utf-8") as f:
        jsonl_lines = [json.loads(line) for line in f]
    assert len(jsonl_lines) == 2, "JSONL должен содержать 2 строки"
    assert jsonl_lines[0]["cls"] == "TITLE", "Первая строка в JSONL должна быть заголовком"
    assert jsonl_lines[1]["cls"] == "PARAGRAPH", "Вторая строка в JSONL должна быть абзацем"