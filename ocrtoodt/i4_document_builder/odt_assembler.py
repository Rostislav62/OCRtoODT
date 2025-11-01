# Path: ocrtoodt/i4_document_builder/odt_assembler.py
# Purpose: Assembles an ODT document from a list of TSV files with formatting and structural analysis.

import os
import logging
import pandas as pd
import numpy as np
from odf.opendocument import OpenDocumentText
from odf.style import Style, TextProperties, ParagraphProperties
from odf.text import P
from typing import List


class ODTAssembler:
    """Class for assembling an ODT document from TSV files."""

    def __init__(self, config: dict):
        self.config = config
        self.output_dir = config.get("output_dir", "output")
        odt_cfg = config.get("odt", {})

        self.font_name = odt_cfg.get("font_name", "Times New Roman")
        self.font_size = odt_cfg.get("font_size", "12pt")
        self.margin_left = odt_cfg.get("margin_left", "0.5cm")
        self.image_width = odt_cfg.get("image_width", 2534)

        # управление пустыми строками
        self.insert_empty_lines = bool(odt_cfg.get("insert_empty_lines", False))
        self.gap_empty_threshold = float(odt_cfg.get("gap_empty_threshold", 1.9))
        self.max_empty_lines = int(odt_cfg.get("max_empty_lines", 1))

        # структура абзацев
        self.par_indent_min = int(odt_cfg.get("paragraph_indent_min", 290))
        self.par_indent_max = int(odt_cfg.get("paragraph_indent_max", 335))
        self.par_continue_max = int(odt_cfg.get("paragraph_continue_max", 125))
        self.par_indent_spaces = int(odt_cfg.get("paragraph_indent_spaces", 4))

        # выравнивание текста
        self.text_align = odt_cfg.get("text_align", "justify")

        # параметры “врезок” (definition blocks)
        self.def_left_min = int(odt_cfg.get("definition_left_min", 500))
        self.def_left_max = int(odt_cfg.get("definition_left_max", 600))
        self.def_right_min = int(odt_cfg.get("definition_right_min", 3900))
        self.def_right_max = int(odt_cfg.get("definition_right_max", 3960))
        self.def_gap_threshold = float(odt_cfg.get("definition_gap_threshold", 1.2))
        self.def_gap_min = int(odt_cfg.get("definition_gap_min", 40))

        logging.info(
            f"ODTAssembler initialized: font={self.font_name}, size={self.font_size}, "
            f"text_align={self.text_align}, insert_empty_lines={self.insert_empty_lines}, "
            f"gap_thr={self.gap_empty_threshold}, def_gap_thr={self.def_gap_threshold}, "
            f"x1: cont<{self.par_continue_max}, new∈[{self.par_indent_min},{self.par_indent_max}], "
            f"def: L∈[{self.def_left_min},{self.def_left_max}], R∈[{self.def_right_min},{self.def_right_max}]"
        )

    # ------------------------------------------------------------------
    def _ensure_styles(self, doc: OpenDocumentText):
        """Create and register paragraph styles."""
        # Paragraph (justify)
        p_style = Style(name="Paragraph", family="paragraph")
        p_style.addElement(ParagraphProperties(marginleft=self.margin_left, textalign=self.text_align))
        p_style.addElement(TextProperties(fontname=self.font_name, fontsize=self.font_size))
        doc.styles.addElement(p_style)

        # Heading
        h_style = Style(name="Heading", family="paragraph")
        h_style.addElement(ParagraphProperties(textalign="center"))
        h_style.addElement(TextProperties(fontname=self.font_name, fontsize=self.font_size, fontweight="bold"))
        doc.styles.addElement(h_style)

        # Footnote
        fn_style = Style(name="Footnote", family="paragraph")
        fn_style.addElement(ParagraphProperties(marginleft="1cm"))
        fn_style.addElement(TextProperties(fontname=self.font_name, fontsize="10pt", fontstyle="italic"))
        doc.styles.addElement(fn_style)

        # Divider
        line_style = Style(name="Divider", family="paragraph")
        line_style.addElement(ParagraphProperties(borderbottom="0.1pt solid #000000"))
        doc.styles.addElement(line_style)

        # Definition (врезка)
        def_style = Style(name="Definition", family="paragraph")
        def_style.addElement(ParagraphProperties(marginleft="1cm", marginright="1cm", textalign="justify"))
        def_style.addElement(TextProperties(fontname=self.font_name, fontsize=self.font_size))
        doc.styles.addElement(def_style)

        # Page break
        pb_style = Style(name="PageBreakParagraph", family="paragraph")
        pb_style.addElement(ParagraphProperties(breakbefore="page"))
        doc.styles.addElement(pb_style)

    # ------------------------------------------------------------------
    def assemble_odt(self, tsv_files: List[str]) -> str:
        """Creates an ODT document from a list of TSV files."""
        for tsv_file in tsv_files:
            if not os.path.exists(tsv_file):
                raise FileNotFoundError(f"TSV file {tsv_file} not found")

        doc = OpenDocumentText()
        self._ensure_styles(doc)

        for idx, tsv_file in enumerate(sorted(tsv_files)):
            logging.info(f"Processing TSV: {tsv_file}")
            if idx > 0:
                doc.text.addElement(P(stylename="PageBreakParagraph"))

            prev_ends_with_hyphen = False
            current_text, current_style = [], "Paragraph"
            in_definition = False
            def_text = []

            df = pd.read_csv(tsv_file, sep="\t")
            lines = [row.to_dict() for _, row in df.iterrows()]

            parsed, heights = [], []
            for line in lines:
                bbox = eval(line["bbox"])
                line["bbox"] = bbox
                parsed.append(line)
                heights.append(bbox[3] - bbox[1])
            lines = parsed
            avg_line_height = float(np.mean(heights)) if heights else 1.0

            for i, line in enumerate(lines):
                text_val = str(line["text"]).strip()
                if not text_val:
                    continue

                bbox = line["bbox"]
                x1, y1, x2, y2 = bbox
                is_upper = text_val.isupper() and len(text_val) > 10
                is_footnote = text_val.startswith("*")
                ends_with_hyphen = text_val.endswith("-") and not text_val.endswith("--")

                # базовый стиль
                if is_footnote:
                    style = "Footnote"
                elif is_upper:
                    style = "Heading"
                else:
                    style = "Paragraph"

                # ---------- определяем “врезку” ----------
                is_def_line = (self.def_left_min <= x1 <= self.def_left_max) and \
                              (self.def_right_min <= x2 <= self.def_right_max)

                if is_def_line or in_definition:
                    if is_def_line and not in_definition:
                        # перед врезкой — сброс текущего абзаца
                        if current_text:
                            p = P(stylename=current_style, text="".join(current_text))
                            doc.text.addElement(p)
                            current_text = []
                        # воздух над врезкой
                        if i > 0:
                            prev_y2 = lines[i - 1]["bbox"][3]
                            gap_before = max(0, y1 - prev_y2)
                            if gap_before > max(self.def_gap_min, self.def_gap_threshold * avg_line_height):
                                doc.text.addElement(P(text=""))
                        in_definition, def_text = True, []

                    # переносы внутри врезки
                    if def_text and prev_ends_with_hyphen:
                        def_text[-1] = def_text[-1].rstrip("-") + text_val.lstrip()
                    else:
                        def_text.append(text_val)

                    prev_ends_with_hyphen = ends_with_hyphen

                    # следующая строка — проверка, не продолжается ли врезка
                    next_is_def = False
                    if i + 1 < len(lines):
                        nx1, nx2 = lines[i + 1]["bbox"][0], lines[i + 1]["bbox"][2]
                        next_is_def = (self.def_left_min - 50 <= nx1 <= self.def_left_max + 50) and \
                                      (self.def_right_min - 50 <= nx2 <= self.def_right_max + 50)

                    if not next_is_def:
                        # закрываем врезку
                        if def_text:
                            p = P(stylename="Definition", text=" ".join(def_text))
                            doc.text.addElement(p)
                            def_text = []
                        in_definition = False

                        # воздух под врезкой
                        if i + 1 < len(lines):
                            next_y1 = lines[i + 1]["bbox"][1]
                            nx1, nx2 = lines[i + 1]["bbox"][0], lines[i + 1]["bbox"][2]
                            gap_after = max(0, next_y1 - y2)
                            if (gap_after > max(self.def_gap_min, self.def_gap_threshold * avg_line_height)) or \
                               (self.par_indent_min <= nx1 <= self.par_indent_max):
                                doc.text.addElement(P(text=""))
                        prev_ends_with_hyphen = False
                    continue  # обработали врезку

                # ---------- обычная структура абзацев ----------
                if x1 < self.par_continue_max and current_text:
                    # продолжение абзаца
                    if prev_ends_with_hyphen:
                        current_text[-1] = current_text[-1].rstrip("-") + text_val.lstrip()
                    else:
                        current_text[-1] += " " + text_val
                    prev_ends_with_hyphen = ends_with_hyphen
                    continue

                if self.par_indent_min <= x1 <= self.par_indent_max:
                    # новый абзац
                    if current_text:
                        p = P(stylename=current_style, text="".join(current_text))
                        doc.text.addElement(p)
                    indent = " " * self.par_indent_spaces
                    current_text = [indent + text_val]
                    current_style = style
                    prev_ends_with_hyphen = ends_with_hyphen
                    continue

                # переносы между строками
                if prev_ends_with_hyphen and current_text:
                    current_text[-1] = current_text[-1].rstrip("-") + text_val.lstrip()
                else:
                    if current_text:
                        p = P(stylename=current_style, text="".join(current_text))
                        doc.text.addElement(p)
                    current_text = [text_val]
                    current_style = style

                # сноски
                if is_footnote:
                    doc.text.addElement(P(stylename="Divider", text="_" * 65))
                    p = P(stylename="Footnote", text=text_val)
                    doc.text.addElement(p)
                    current_text = []
                    current_style = "Paragraph"
                    prev_ends_with_hyphen = False
                else:
                    prev_ends_with_hyphen = ends_with_hyphen

            # -------- сброс последнего блока --------
            if in_definition and def_text:
                p = P(stylename="Definition", text=" ".join(def_text))
                doc.text.addElement(p)
                in_definition, def_text = False, []

            if current_text:
                p = P(stylename=current_style, text="".join(current_text))
                doc.text.addElement(p)

        # -------- сохранение --------
        os.makedirs(self.output_dir, exist_ok=True)
        odt_output = os.path.join(self.output_dir, "result.odt")
        doc.save(odt_output)
        logging.info(f"Saved ODT file: {odt_output}")
        return odt_output
