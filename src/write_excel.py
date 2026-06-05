from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from src.config import EXCEL_COLUMNS, EXCEL_PATH, MASTER_COLUMNS, MASTER_ROWS_PATH
from src.validate import normalize_date_to_mdy


def writeable_value(field: dict | None):
    if not field:
        return None
    if field.get("confidence") == "high":
        return field.get("value")
    return None


def extraction_to_excel_row(extraction: dict, pdf_path: Path) -> dict:
    row = {col: None for col in EXCEL_COLUMNS}

    row["accession_number"] = pdf_path.stem
    row["source_pdf"] = pdf_path.name
    row["hcm_classification"] = extraction.get("hcm_classification")
    row["hcm_classification_confidence"] = extraction.get("hcm_classification_confidence")
    row["hcm_classification_evidence"] = extraction.get("hcm_classification_evidence")

    field_map = [
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
    ]

    for field in field_map:
        row[field] = writeable_value(extraction.get(field))

    row["fields_blank_due_to_uncertainty"] = ", ".join(extraction.get("fields_blank_due_to_uncertainty", []))
    row["review_required"] = extraction.get("review_required", True)
    row["notes"] = extraction.get("notes")
    row["extraction_status"] = "processed"
    row["processed_timestamp"] = datetime.now().isoformat(timespec="seconds")

    return row


def append_to_excel(row: dict) -> None:
    if EXCEL_PATH.exists():
        df = pd.read_excel(EXCEL_PATH)
    else:
        df = pd.DataFrame(columns=EXCEL_COLUMNS)

    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df = df.reindex(columns=EXCEL_COLUMNS)
    df.to_excel(EXCEL_PATH, index=False)


def extraction_to_master_row(extraction: dict, pdf_path: Path) -> dict:
    row = {col: None for col in MASTER_COLUMNS}

    row["SVCC ID"] = writeable_value(extraction.get("SVCC_ID"))
    row["Accession #"] = pdf_path.stem
    row["age"] = _age_from_extraction(extraction)
    row["sex"] = writeable_value(extraction.get("sex"))
    row["height (cm)"] = writeable_value(extraction.get("height_cm"))
    row["weight (kg)"] = writeable_value(extraction.get("weight_kg"))
    row["BSA (m2)"] = writeable_value(extraction.get("BSA"))
    row["HCM since"] = _year_from_field(extraction.get("HCM_since"))
    row["family history?"] = writeable_value(extraction.get("family_history_HCM"))
    row["SD?"] = writeable_value(extraction.get("family_history_sudden_death"))
    row["LGE?"] = writeable_value(extraction.get("LGE"))
    row["AICD?"] = writeable_value(extraction.get("AICD"))
    row["AICD shocks?"] = writeable_value(extraction.get("AICD_shocks"))
    row["hospitalization for HF?"] = writeable_value(extraction.get("hospitalization_for_HF"))
    row["aneurysm?"] = writeable_value(extraction.get("aneurysm"))
    row["Max LV wall thickness (mm)"] = writeable_value(extraction.get("max_LV_wall_thickness_mm"))
    row["LVOT Gradient (mmHg)"] = writeable_value(extraction.get("LVOT_gradient_mmHg"))
    row["unexplained syncope?"] = writeable_value(extraction.get("syncope"))
    row["non-sustained VT?"] = writeable_value(extraction.get("non_sustained_VT"))
    row["prior arrhythmia?"] = writeable_value(extraction.get("prior_arrhythmia"))
    row["study date"] = writeable_value(extraction.get("study_date"))
    row["LVEF (%)"] = writeable_value(extraction.get("LVEF"))
    row["LVSV (mL/m2)"] = writeable_value(extraction.get("LVSV_indexed_BSA"))
    row["LVEDV (mL/m2)"] = writeable_value(extraction.get("LVEDV_indexed_BSA"))
    row["LVESV (mL/m2)"] = writeable_value(extraction.get("LVESV_indexed_BSA"))
    row["LV mass (g/m2)"] = writeable_value(extraction.get("LV_mass_indexed_BSA"))
    row["Notes"] = _master_notes(extraction)
    return row


def append_to_master_excel(row: dict) -> None:
    if MASTER_ROWS_PATH.exists():
        df = pd.read_excel(MASTER_ROWS_PATH)
    else:
        df = pd.DataFrame(columns=MASTER_COLUMNS)

    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df = df.reindex(columns=MASTER_COLUMNS)
    with pd.ExcelWriter(MASTER_ROWS_PATH, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
        worksheet = writer.sheets["Sheet1"]
        for cell in worksheet[1]:
            cell.font = cell.font.copy(bold=False)
        worksheet.freeze_panes = "A2"


def _field_value(extraction: dict, field_name: str):
    field = extraction.get(field_name) or {}
    if field.get("confidence") == "high":
        return field.get("value")
    return None


def _age_from_extraction(extraction: dict) -> int | None:
    dob = _field_value(extraction, "DOB")
    study_date = _field_value(extraction, "study_date")
    if not dob or not study_date:
        return None
    dob_norm = normalize_date_to_mdy(str(dob))
    study_norm = normalize_date_to_mdy(str(study_date))
    if not dob_norm or not study_norm:
        return None
    dob_dt = pd.to_datetime(dob_norm)
    study_dt = pd.to_datetime(study_norm)
    age = study_dt.year - dob_dt.year - ((study_dt.month, study_dt.day) < (dob_dt.month, dob_dt.day))
    return int(age)


def _year_from_field(field: dict | None) -> int | str | None:
    value = writeable_value(field)
    if value is None:
        return None
    text = str(value)
    if text.isdigit() and len(text) == 4:
        return int(text)
    normalized = normalize_date_to_mdy(text)
    if not normalized:
        return value
    return int(pd.to_datetime(normalized).year)


def _master_notes(extraction: dict) -> str | None:
    notes = []
    prior_arrhythmia = extraction.get("prior_arrhythmia") or {}
    if prior_arrhythmia.get("confidence") == "high" and prior_arrhythmia.get("value"):
        evidence = prior_arrhythmia.get("evidence")
        notes.append(f"prior arrhythmia: {evidence or prior_arrhythmia.get('value')}")

    unsure = extraction.get("fields_blank_due_to_uncertainty") or []
    if unsure:
        notes.append(f"review uncertain fields: {', '.join(unsure)}")

    classification = extraction.get("hcm_classification")
    if classification == "unsure":
        notes.append("review HCM classification")

    return "; ".join(notes) if notes else None
