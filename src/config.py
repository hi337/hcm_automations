from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT_DIR / "input_reports"
OUTPUT_DIR = ROOT_DIR / "output"
EXCEL_PATH = OUTPUT_DIR / "dataset.xlsx"
MASTER_ROWS_PATH = OUTPUT_DIR / "master_list_rows.xlsx"

HCM_DIR = OUTPUT_DIR / "hcm"
NOT_HCM_DIR = OUTPUT_DIR / "not_hcm"
UNSURE_DIR = OUTPUT_DIR / "unsure_hcm"
TEXT_DIR = OUTPUT_DIR / "extracted_text"
JSON_DIR = OUTPUT_DIR / "review_json"
LOG_DIR = OUTPUT_DIR / "logs"

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "").strip().lower()
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

EXCEL_COLUMNS = [
    "accession_number",
    "source_pdf",
    "hcm_classification",
    "hcm_classification_confidence",
    "hcm_classification_evidence",
    "DOB",
    "SVCC_ID",
    "sex",
    "height_cm",
    "weight_kg",
    "BSA",
    "family_history_HCM",
    "family_history_sudden_death",
    "LGE",
    "AICD",
    "AICD_shocks",
    "hospitalization_for_HF",
    "aneurysm",
    "max_LV_wall_thickness_mm",
    "LVOT_gradient_mmHg",
    "syncope",
    "non_sustained_VT",
    "prior_arrhythmia",
    "study_date",
    "LVEF",
    "LVSV_indexed_BSA",
    "LVEDV_indexed_BSA",
    "LVESV_indexed_BSA",
    "LV_mass_indexed_BSA",
    "HCM_since",
    "extraction_status",
    "fields_blank_due_to_uncertainty",
    "review_required",
    "notes",
    "processed_timestamp",
]

MASTER_COLUMNS = [
    "SVCC ID",
    "Accession #",
    "age",
    "sex",
    "height (cm)",
    "weight (kg)",
    "BSA (m2)",
    "HCM since",
    "family history?",
    "SD?",
    "LGE?",
    "AICD?",
    "AICD shocks?",
    "hospitalization for HF?",
    "aneurysm?",
    "Max LV wall thickness (mm)",
    "LVOT Gradient (mmHg)",
    "unexplained syncope?",
    "non-sustained VT?",
    "prior arrhythmia?",
    "study date",
    "LVEF (%)",
    "LVSV (mL/m2)",
    "LVEDV (mL/m2)",
    "LVESV (mL/m2)",
    "LV mass (g/m2)",
    "Notes",
    "DICOM Transferred?",
    "Previous Studies?",
]


def ensure_output_dirs() -> None:
    for directory in [OUTPUT_DIR, HCM_DIR, NOT_HCM_DIR, UNSURE_DIR, TEXT_DIR, JSON_DIR, LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
