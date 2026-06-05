from __future__ import annotations

import shutil
from pathlib import Path

from src.config import HCM_DIR, NOT_HCM_DIR, UNSURE_DIR


def route_pdf(pdf_path: Path, extraction: dict) -> Path:
    classification = extraction.get("hcm_classification", "unsure")

    if classification == "hcm":
        target = HCM_DIR / pdf_path.name
    elif classification == "not_hcm":
        target = NOT_HCM_DIR / pdf_path.name
    else:
        target = UNSURE_DIR / pdf_path.name

    shutil.copy2(pdf_path, target)
    return target
