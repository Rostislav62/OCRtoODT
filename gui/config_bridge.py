# gui/config_bridge.py
"""
Configuration bridge between YAML config and GUI.

Key goals:
- Preserve YAML comments, key order, and formatting on save (ruamel.yaml).
- Auto-detect runtime mode:
    • Development (running from PyCharm / source tree)
    • Installed (app laid out under /usr/bin/ocrtoodt)
- Adjust only the necessary path fields in-memory (so users always see correct paths),
  but do NOT overwrite entire sections (otherwise comments would be lost).
- When GUI writes changes back, use ruamel.yaml so the original comments remain.

IMPORTANT:
- Never replace whole mappings like cfg["ocr"] = {...} — that would drop comments
  inside the 'ocr' section. Instead, mutate keys of the existing CommentedMap.
"""

import os
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap


# ------------------------- YAML helpers -------------------------

_yaml = YAML()
_yaml.preserve_quotes = True        # keep quotes if present
_yaml.width = 1000                  # do not re-break long lines
_yaml.indent(mapping=2, sequence=4) # pleasant default indentation


def _ensure_section(cfg: CommentedMap, key: str) -> CommentedMap:
    """
    Ensure cfg[key] exists and is a CommentedMap.
    We never replace a whole mapping unless it's missing. This preserves comments.
    """
    val = cfg.get(key)
    if isinstance(val, CommentedMap):
        return val
    # If it's a plain dict or missing, convert/create a CommentedMap in-place
    new = CommentedMap(val or {})
    cfg[key] = new
    return new


def _set_scalar(cfg: CommentedMap, key: str, value: Any) -> None:
    """
    Set a scalar value on the top-level mapping without disturbing comments.
    If the key exists, we overwrite just the scalar node.
    """
    cfg[key] = value


def load_config(path: str = "config.yaml") -> CommentedMap:
    """
    Load YAML config with ruamel.yaml preserving comments.
    All paths (input_dir, output_file, ocr_dir, log_file, tessdata, etc.)
    are read directly from config.yaml without any auto-calculation.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        cfg = _yaml.load(f) or CommentedMap()

    if not isinstance(cfg, CommentedMap):
        tmp = CommentedMap()
        tmp.update(cfg or {})
        cfg = tmp

    return cfg


def save_config(cfg: CommentedMap, path: str = "config.yaml") -> None:
    """
    Save YAML config back to disk while preserving comments and formatting.
    Assumes cfg is a CommentedMap (as returned by load_config).
    """
    # NOTE: Do NOT rebuild whole sub-maps before saving.
    # Just dump the CommentedMap as-is to keep comments intact.
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        _yaml.dump(cfg, f)


# ------------------------- GUI mappers -------------------------

def apply_cfg_to_gui(ui, cfg: CommentedMap) -> None:
    """
    Push config values into GUI widgets.
    Reading values does not affect comments.
    """

    # General
    ui.editInputDir.setText(cfg.get("input_dir", ""))
    par = _ensure_section(cfg, "parallel")
    ui.chkParallel.setChecked(bool(par.get("enabled", True)))

    np = str(par.get("num_processes", "auto"))
    if np.lower() == "auto":
        ui.comboProcesses.setCurrentText("auto")
    else:
        ui.comboProcesses.setCurrentText(np)

    # Preprocess
    pre = _ensure_section(cfg, "preprocess")
    ui.chkGrayscale.setChecked(bool(pre.get("grayscale", True)))
    ui.chkDenoise.setChecked(bool(pre.get("denoise_median", True)))
    ui.chkContrast.setChecked(bool(pre.get("contrast_clahe", True)))
    ui.chkBinarize.setChecked(bool(pre.get("binarize_otsu", True)))
    ui.chkSharpen.setChecked(bool(pre.get("sharpen_edges", True)))

    # OCR languages
    ocr = _ensure_section(cfg, "ocr")
    langs = "+".join(list(ocr.get("languages", [])))
    ui.comboLang.setCurrentText(langs)

    # ODT
    odt = _ensure_section(cfg, "odt")
    ui.spinIndentMin.setValue(float(odt.get("paragraph_indent_min", 2.0)))
    ui.spinIndentMax.setValue(float(odt.get("paragraph_indent_max", 10.0)))
    ui.comboFont.setCurrentText(str(odt.get("font_name", "Times New Roman")))
    ui.editMargins.setText(str(odt.get("margin_left", "0.5cm")))
    ui.comboAlign.setCurrentText({
        "justify": "По ширине",
        "left": "По левому краю",
        "center": "По центру"
    }.get(str(odt.get("text_align", "justify")), "По ширине"))
    ui.spinDefGap.setValue(float(odt.get("definition_gap_threshold", 1.2)))

    # UI section
    ui_sec = _ensure_section(cfg, "ui")
    ui.chkNotifyOnFinish.setChecked(bool(ui_sec.get("notify_on_finish", True)))
    ui.chkSoundOnFinish.setChecked(bool(ui_sec.get("play_sound_on_finish", True)))
    ui.spinFontSize.setValue(int(ui_sec.get("font_size", 12)))
    ui.comboTheme.setCurrentText("Тёмная" if str(ui_sec.get("theme", "light")) == "dark" else "Светлая")


def apply_gui_to_cfg(ui, cfg: CommentedMap) -> CommentedMap:
    """
    Read GUI values and write them into the same CommentedMap in-place.
    We never replace entire sections (so we keep existing comments).
    """
    # General
    _set_scalar(cfg, "input_dir", ui.editInputDir.text().strip())

    par = _ensure_section(cfg, "parallel")
    par["enabled"] = bool(ui.chkParallel.isChecked())
    val = ui.comboProcesses.currentText().strip().lower()
    if val == "auto":
        par["num_processes"] = "auto"
    else:
        try:
            par["num_processes"] = int(val)
        except ValueError:
            par["num_processes"] = "auto"

    # Preprocess
    pre = _ensure_section(cfg, "preprocess")
    pre["grayscale"] = bool(ui.chkGrayscale.isChecked())
    pre["denoise_median"] = bool(ui.chkDenoise.isChecked())
    pre["contrast_clahe"] = bool(ui.chkContrast.isChecked())
    pre["binarize_otsu"] = bool(ui.chkBinarize.isChecked())
    pre["sharpen_edges"] = bool(ui.chkSharpen.isChecked())

    # UI
    ui_sec = _ensure_section(cfg, "ui")
    ui_sec["notify_on_finish"] = bool(ui.chkNotifyOnFinish.isChecked())
    ui_sec["play_sound_on_finish"] = bool(ui.chkSoundOnFinish.isChecked())
    ui_sec["font_size"] = int(ui.spinFontSize.value())
    theme = ui.comboTheme.currentText()
    ui_sec["theme"] = "dark" if "тём" in theme.lower() else "light"

    # OCR languages
    ocr = _ensure_section(cfg, "ocr")
    langs = [l.strip() for l in ui.comboLang.currentText().split("+") if l.strip()]
    ocr["languages"] = langs

    # ODT
    odt = _ensure_section(cfg, "odt")
    odt["paragraph_indent_min"] = float(ui.spinIndentMin.value())
    odt["paragraph_indent_max"] = float(ui.spinIndentMax.value())
    odt["font_name"] = str(ui.comboFont.currentText())
    odt["margin_left"] = str(ui.editMargins.text().strip())
    align = ui.comboAlign.currentText()
    odt["text_align"] = {
        "По ширине": "justify",
        "По левому краю": "left",
        "По центру": "center"
    }.get(align, "justify")
    odt["definition_gap_threshold"] = float(ui.spinDefGap.value())

    return cfg
