# Path: ocrtoodt/i4_document_builder/odt_assembler.py
# Purpose: Assemble final ODT document from OCR TSV files.
# All paths (input/output/cache) come strictly from config.yaml — no guessing.

import os
import logging
import yaml
from odf.opendocument import OpenDocumentText
from odf.text import P
from odf.style import Style, TextProperties, ParagraphProperties


class ODTAssembler:
    """
    Build a .odt document from recognized TSV lines.
    Reads all output paths (especially output_file) strictly from config.yaml.
    """

    def __init__(self, config: dict):
        self.config = config or {}
        self.odt_cfg = self.config.get("odt", {}) or {}
        self.output_file = self.config.get("output_file")

        if not self.output_file:
            raise ValueError("Missing 'output_file' in config.yaml.")

        # Ensure the parent folder exists (safe to create for output)
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

    # ------------------------------------------------------------------

    def assemble_odt(self, tsv_files: list[str]) -> str:
        """
        Assemble recognized TSV files into a single ODT document.

        Args:
            tsv_files (list[str]): list of TSV file paths (from OCR).
        Returns:
            str: path to the final ODT document.
        """
        if not tsv_files:
            raise ValueError("No TSV files provided for ODT assembly.")

        # --- Create ODT document ---
        doc = OpenDocumentText()
        self._define_styles(doc)

        font_name = self.odt_cfg.get("font_name", "Times New Roman")
        font_size = str(self.odt_cfg.get("font_size", "12pt"))
        text_align = self.odt_cfg.get("text_align", "justify")

        logging.info("Assembling ODT with %d TSV files...", len(tsv_files))

        for tsv_path in tsv_files:
            if not os.path.isfile(tsv_path):
                logging.warning(f"TSV not found: {tsv_path}")
                continue

            with open(tsv_path, "r", encoding="utf-8") as f:
                next(f)  # skip header
                for line in f:
                    parts = line.strip().split("\t")
                    if len(parts) < 3:
                        continue
                    text = parts[2].strip()
                    if not text:
                        continue
                    p = P(stylename=self.style_body, text=text)
                    doc.text.addElement(p)

            # Add page break between TSVs if configured
            if self.odt_cfg.get("page_break", True):
                doc.text.addElement(P(stylename=self.style_body, text="\n"))

        doc.save(self.output_file)
        logging.info("✅ ODT saved successfully: %s", self.output_file)
        return self.output_file

    # ------------------------------------------------------------------

    def _define_styles(self, doc: OpenDocumentText) -> None:
        """
        Define minimal paragraph styles for title and body text.
        """
        self.style_body = Style(name="TextBody", family="paragraph")
        self.style_body.addElement(TextProperties(attributes={
            "fontsize": self.odt_cfg.get("font_size", "12pt"),
            "fontname": self.odt_cfg.get("font_name", "Times New Roman"),
        }))
        self.style_body.addElement(ParagraphProperties(attributes={
            "textalign": self.odt_cfg.get("text_align", "justify"),
            "marginleft": self.odt_cfg.get("margin_left", "0.5cm"),
        }))

        self.style_title = Style(name="Title", family="paragraph")
        self.style_title.addElement(TextProperties(attributes={
            "fontsize": "16pt",
            "fontweight": "bold",
            "fontname": self.odt_cfg.get("font_name", "Times New Roman"),
        }))
        self.style_title.addElement(ParagraphProperties(attributes={
            "textalign": "center",
            "marginbottom": "0.3cm",
        }))

        doc.styles.addElement(self.style_body)
        doc.styles.addElement(self.style_title)
