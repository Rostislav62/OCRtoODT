# 🧠 OCRtoODT — Smart OCR and ODT Converter

**OCRtoODT** is a modern, cross-platform OCR application that converts scanned PDFs and images into editable `.odt` documents (LibreOffice / OpenOffice). It’s designed as an open-source alternative to commercial tools like ABBYY FineReader — lightweight, efficient, and fully self-contained.

---

## 🚀 Key Features
- 📄 Convert scanned PDFs or images (JPEG, PNG, TIFF) into editable ODT files.
- 🧠 Text recognition powered by **Tesseract OCR**.
- ⚙️ Configurable preprocessing: grayscale, denoise, sharpen, contrast, etc.
- 🪶 Intelligent paragraph and layout reconstruction.
- 🌗 Light/Dark theme support.
- 🖱️ Full GUI (PySide6 / Qt6) — no terminal needed.
- 💾 Configurable via **config.yaml**, preserving comments.
- 🔄 Multi-core OCR processing (parallel pipelines).
- 💬 Multi-language OCR (Russian, English, etc.).

---

## 🧩 Project Architecture
The project follows a clean modular pipeline:

```
ocrtoodt/
 ├── i0_core/                # Core logic and pipeline orchestrator
 │   ├── cli_entrypoint.py   # CLI entrypoint
 │   ├── pipeline_orchestrator.py  # Coordinates the full OCR process
 │   ├── pdf_splitter.py     # Splits PDFs into images
 │   └── types_definitions.py # Data models
 │
 ├── i1_preprocess/          # Image preprocessing modules
 │   ├── grayscale.py, denoise_median.py, contrast_clahe.py, binarize_otsu.py
 │   └── image_preprocessor.py
 │
 ├── i2_ocr/                 # OCR stage (Tesseract engine)
 │   └── ocr_engine.py
 │
 ├── i3_lines_analysis/      # Line grouping and paragraph detection
 │   └── lines_classifier.py
 │
 ├── i4_document_builder/    # Builds the final ODT file
 │   └── odt_assembler.py
```

The GUI lives under `gui/` and is built with PySide6:
```
gui/
 ├── main.py                 # GUI entrypoint
 ├── dialogs/                # Settings, Help, About dialogs
 ├── resources/              # Icons, sounds, QSS themes
 ├── ui/                     # Qt Designer .ui files
 └── theme.py, worker.py     # Theme management and threading
```

---

## 🖥️ Graphical Interface
The GUI is designed for simplicity and productivity.

### 🔘 Main controls:
- **Open** — import PDF or images
- **Run OCR** — start the recognition process
- **Export** — save to ODT
- **Settings** — open configuration dialog
- **Progress bar & log** — display OCR progress and messages

### ⚙️ Settings dialog tabs:
1. **General** — input directory, parallel processing (auto/1–32 threads)
2. **Preprocessing** — noise reduction, grayscale, contrast, sharpening
3. **OCR** — Tesseract settings: languages, PSM, DPI, tessdata paths
4. **ODT** — text formatting, font, margins, paragraph detection
5. **UI** — theme (light/dark), font size, sound/notification options

---

## ⚙️ Configuration (config.yaml)
Settings are stored in `config.yaml` using `ruamel.yaml`, preserving formatting and comments.

Example:
```yaml
program_root: /home/user/OCRtoODT
input_dir: input
output_file: output/result.odt
ocr_engine_path: tesseract/tesseract
languages: [rus, eng]
psm: 4
parallel:
  enabled: true
  num_processes: auto
```

---

## 🔧 Installation & Launch
### From source
```bash
git clone https://github.com/Rostislav62/OCRtoODT.git
cd OCRtoODT
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python gui/main.py
```

---

## 🔍 Technical Details
- **Language**: Python 3.12
- **GUI**: PySide6 / Qt6
- **OCR**: Embedded Tesseract
- **ODT**: odfpy
- **PDF handling**: PyMuPDF (fitz), pdf2image
- **Image preprocessing**: OpenCV + NumPy
- **Config system**: ruamel.yaml

---

## 👨‍💻 Author & License
Author: **Rostislav Smigliuc**  
License: [MIT License](LICENSE)
