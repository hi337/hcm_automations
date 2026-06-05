from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from schemas.cardiac_mri_schema import ExtractedField, ReportExtraction


OBJECTIVE_FIELDS = [
    "DOB",
    "sex",
    "height_cm",
    "weight_kg",
    "BSA",
    "study_date",
    "LVEF",
    "max_LV_wall_thickness_mm",
    "LVSV_indexed_BSA",
    "LVEDV_indexed_BSA",
    "LVESV_indexed_BSA",
    "LV_mass_indexed_BSA",
    "LVSV_absolute",
    "LVEDV_absolute",
    "LVESV_absolute",
    "LV_mass_absolute",
]

EXCEL_FIELD_NAMES = [
    "DOB",
    "SVCC_ID",
    "sex",
    "height_cm",
    "weight_kg",
    "BSA",
    "family_history_HCM",
    "LGE",
    "AICD",
    "max_LV_wall_thickness_mm",
    "syncope",
    "study_date",
    "LVEF",
    "LVSV_indexed_BSA",
    "LVEDV_indexed_BSA",
    "LVESV_indexed_BSA",
    "LV_mass_indexed_BSA",
    "HCM_since",
]

YES_NO_FIELDS = ["family_history_HCM", "LGE", "AICD", "syncope"]
YES_NO_FIELDS += [
    "family_history_sudden_death",
    "AICD_shocks",
    "hospitalization_for_HF",
    "aneurysm",
    "non_sustained_VT",
    "prior_arrhythmia",
]

HCM_POSITIVE_PATTERNS = [
    r"\bhypertrophic cardiomyopathy\b",
    r"\bknown\s+HCM\b",
    r"\bapical\s+HCM\b",
    r"\basymmetric septal hypertrophy consistent with HCM\b",
    r"\bfindings compatible with hypertrophic cardiomyopathy\b",
    r"\bconsistent with hypertrophic cardiomyopathy\b",
]

HCM_NEGATIVE_PATTERNS = [
    r"\bno evidence of hypertrophic cardiomyopathy\b",
    r"\bnot consistent with HCM\b",
    r"\bnot consistent with hypertrophic cardiomyopathy\b",
    r"\bnormal wall thickness\b",
    r"\bhypertrophy due to (?:hypertension|aortic stenosis)\b",
    r"\brather than HCM\b",
]

HCM_UNSURE_PATTERNS = [
    r"\bpossible\s+HCM\b",
    r"\bquery\s+HCM\b",
    r"\bborderline hypertrophy\b",
    r"\bdifferential includes HCM\b",
    r"\bphenotype not diagnostic\b",
    r"\bcannot exclude HCM\b",
    r"\bequivocal(?: for)? HCM\b",
]


def validate_and_postprocess(llm_data: dict, text: str, regex_data: dict) -> dict:
    extraction = ReportExtraction.model_validate(llm_data)
    extraction = _merge_regex_fields(extraction, regex_data)
    _normalize_fields(extraction)
    _apply_plausibility_rules(extraction)
    _apply_hcm_rules(extraction, text)
    _recalculate_svcc_id(extraction)
    _calculate_bsa_fallback(extraction)
    _track_uncertainty(extraction)
    return extraction.model_dump()


def _merge_regex_fields(extraction: ReportExtraction, regex_data: dict) -> ReportExtraction:
    for field_name in OBJECTIVE_FIELDS:
        regex_field = regex_data.get(field_name)
        if not regex_field:
            continue
        current = getattr(extraction, field_name)
        if current.confidence != "high":
            setattr(extraction, field_name, ExtractedField.model_validate(regex_field))
    return extraction


def _normalize_fields(extraction: ReportExtraction) -> None:
    for field_name in ["DOB", "study_date", "HCM_since"]:
        field = getattr(extraction, field_name)
        if field.value is not None:
            normalized = normalize_date_to_mdy(str(field.value))
            if normalized:
                field.value = normalized
            else:
                _downgrade(field, "Date format could not be normalized.")

    if extraction.sex.value is not None:
        normalized = normalize_sex(str(extraction.sex.value))
        if normalized:
            extraction.sex.value = normalized
        else:
            _downgrade(extraction.sex, "Sex value was not recognized.")

    for field_name in YES_NO_FIELDS:
        field = getattr(extraction, field_name)
        if field.value is not None:
            normalized = normalize_yes_no(field.value)
            if normalized:
                field.value = normalized
            else:
                _downgrade(field, "Y/N field contained an unsupported value.")

    numeric_fields = [
        "height_cm",
        "weight_kg",
        "BSA",
        "LVEF",
        "max_LV_wall_thickness_mm",
        "LVSV_indexed_BSA",
        "LVEDV_indexed_BSA",
        "LVESV_indexed_BSA",
        "LV_mass_indexed_BSA",
        "LVOT_gradient_mmHg",
        "LVSV_absolute",
        "LVEDV_absolute",
        "LVESV_absolute",
        "LV_mass_absolute",
    ]
    for field_name in numeric_fields:
        field = getattr(extraction, field_name)
        if field.value is not None:
            numeric = normalize_number(field.value)
            if numeric is None:
                _downgrade(field, "Numeric value could not be parsed.")
            else:
                field.value = numeric


def _apply_plausibility_rules(extraction: ReportExtraction) -> None:
    checks = {
        "height_cm": lambda value: 100 <= float(value) <= 230,
        "weight_kg": lambda value: 25 <= float(value) <= 250,
        "BSA": plausible_bsa,
        "LVEF": plausible_lvef,
        "max_LV_wall_thickness_mm": plausible_wall_thickness,
        "LVSV_indexed_BSA": lambda value: 10 <= float(value) <= 150,
        "LVEDV_indexed_BSA": lambda value: 20 <= float(value) <= 250,
        "LVESV_indexed_BSA": lambda value: 5 <= float(value) <= 200,
        "LV_mass_indexed_BSA": lambda value: 20 <= float(value) <= 250,
        "LVOT_gradient_mmHg": lambda value: 0 <= float(value) <= 250,
    }
    for field_name, check in checks.items():
        field = getattr(extraction, field_name)
        if field.value is None:
            continue
        try:
            ok = check(field.value)
        except (TypeError, ValueError):
            ok = False
        if not ok:
            _downgrade(field, f"{field_name} failed plausibility validation.")


def _apply_hcm_rules(extraction: ReportExtraction, text: str) -> None:
    unsure = _find_first(HCM_UNSURE_PATTERNS, text)
    negative = _find_first(HCM_NEGATIVE_PATTERNS, text)
    positive = _find_first(HCM_POSITIVE_PATTERNS, text)

    if unsure:
        extraction.hcm_classification = "unsure"
        extraction.hcm_classification_confidence = "medium"
        extraction.hcm_classification_evidence = unsure
    elif negative:
        extraction.hcm_classification = "not_hcm"
        extraction.hcm_classification_confidence = "high"
        extraction.hcm_classification_evidence = negative
    elif positive:
        if re.search(r"\b(no|without|denies|not)\b.{0,40}" + re.escape(positive), text, re.IGNORECASE | re.DOTALL):
            extraction.hcm_classification = "unsure"
            extraction.hcm_classification_confidence = "medium"
            extraction.hcm_classification_evidence = positive
        else:
            extraction.hcm_classification = "hcm"
            extraction.hcm_classification_confidence = "high"
            extraction.hcm_classification_evidence = positive
    elif extraction.hcm_classification_confidence != "high":
        extraction.hcm_classification = "unsure"
        extraction.hcm_classification_confidence = "absent"
        extraction.hcm_classification_evidence = None


def _recalculate_svcc_id(extraction: ReportExtraction) -> None:
    extraction.SVCC_ID = ExtractedField(confidence="absent", reason="SVCC_ID is calculated deterministically only.")
    name = extraction.patient_name
    dob = extraction.DOB
    if name.confidence != "high" or dob.confidence != "high" or not name.value or not dob.value:
        return

    initials = initials_from_name(str(name.value))
    dob_digits = dob_to_yyyymmdd(str(dob.value))
    if not initials or not dob_digits:
        return

    extraction.SVCC_ID = ExtractedField(
        value=f"{initials}_{dob_digits}",
        confidence="high",
        evidence=f"Name: {name.evidence}; DOB: {dob.evidence}",
        reason="Calculated from high-confidence patient name and DOB.",
        source_text_location=dob.source_text_location or name.source_text_location,
    )


def _calculate_bsa_fallback(extraction: ReportExtraction) -> None:
    if extraction.BSA.confidence == "high" and extraction.BSA.value is not None:
        return
    values = {
        "LVSV_absolute": extraction.LVSV_absolute.value,
        "LVSV_indexed": extraction.LVSV_indexed_BSA.value,
        "LVEDV_absolute": extraction.LVEDV_absolute.value,
        "LVEDV_indexed": extraction.LVEDV_indexed_BSA.value,
        "LVESV_absolute": extraction.LVESV_absolute.value,
        "LVESV_indexed": extraction.LVESV_indexed_BSA.value,
        "LV_mass_absolute": extraction.LV_mass_absolute.value,
        "LV_mass_indexed": extraction.LV_mass_indexed_BSA.value,
    }
    bsa, status = calculate_bsa_from_indexed_values(values)
    if bsa is not None:
        extraction.BSA = ExtractedField(
            value=bsa,
            confidence="high",
            evidence="Calculated from at least two concordant absolute/indexed LV measurements.",
            reason="Deterministic BSA fallback.",
        )
    elif status != "insufficient_candidates":
        extraction.BSA.reason = f"BSA fallback rejected: {status}."


def _track_uncertainty(extraction: ReportExtraction) -> None:
    blanked = set(extraction.fields_blank_due_to_uncertainty)
    for field_name in EXCEL_FIELD_NAMES:
        field = getattr(extraction, field_name)
        if field.value is not None and field.confidence != "high":
            blanked.add(field_name)

    extraction.fields_blank_due_to_uncertainty = sorted(blanked)
    extraction.review_required = bool(
        extraction.fields_blank_due_to_uncertainty
        or extraction.hcm_classification == "unsure"
        or extraction.hcm_classification_confidence != "high"
    )


def normalize_yes_no(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"y", "yes", "present", "true", "1"}:
        return "Y"
    if text in {"n", "no", "absent", "false", "0"}:
        return "N"
    return None


def normalize_sex(value: str) -> str | None:
    text = value.strip().lower()
    if text in {"m", "male"}:
        return "M"
    if text in {"f", "female"}:
        return "F"
    return None


def normalize_number(value: Any) -> float | int | None:
    if isinstance(value, int | float):
        return value
    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    if not match:
        return None
    parsed = float(match.group(0))
    return int(parsed) if parsed.is_integer() else parsed


def plausible_bsa(value: Any) -> bool:
    return value is not None and 1.2 <= float(value) <= 2.6


def plausible_lvef(value: Any) -> bool:
    return value is not None and 5 <= float(value) <= 90


def plausible_wall_thickness(value: Any) -> bool:
    return value is not None and 3 <= float(value) <= 50


def normalize_date_to_mdy(date_string: str) -> str | None:
    accepted_formats = [
        "%m/%d/%Y",
        "%m/%d/%y",
        "%m-%d-%Y",
        "%m-%d-%y",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d-%b-%Y",
    ]
    cleaned = date_string.strip()
    for fmt in accepted_formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return f"{dt.month}/{dt.day}/{dt.year}"
        except ValueError:
            continue
    return None


def dob_to_yyyymmdd(date_string: str) -> str | None:
    normalized = normalize_date_to_mdy(date_string)
    if not normalized:
        return None
    dt = datetime.strptime(normalized, "%m/%d/%Y")
    return dt.strftime("%Y%m%d")


def initials_from_name(name: str) -> str | None:
    cleaned = re.sub(r"[^A-Za-z,\s'-]", " ", name).strip()
    if not cleaned:
        return None

    if "," in cleaned:
        last, first = [part.strip() for part in cleaned.split(",", 1)]
        first_parts = first.split()
        last_parts = last.split()
    else:
        parts = cleaned.split()
        if len(parts) < 2:
            return None
        first_parts = [parts[0]]
        last_parts = [parts[-1]]

    if not first_parts or not last_parts:
        return None
    return f"{first_parts[0][0]}{last_parts[0][0]}".upper()


def calculate_bsa_from_indexed_values(values: dict) -> tuple[float | None, str]:
    pairs = [
        ("LVSV_absolute", "LVSV_indexed"),
        ("LVEDV_absolute", "LVEDV_indexed"),
        ("LVESV_absolute", "LVESV_indexed"),
        ("LV_mass_absolute", "LV_mass_indexed"),
    ]
    candidates: list[float] = []
    for absolute_key, indexed_key in pairs:
        absolute = values.get(absolute_key)
        indexed = values.get(indexed_key)
        if absolute is None or indexed in (None, 0):
            continue
        candidates.append(float(absolute) / float(indexed))

    if len(candidates) < 2:
        return None, "insufficient_candidates"

    mean_bsa = sum(candidates) / len(candidates)
    max_deviation = max(abs(candidate - mean_bsa) for candidate in candidates)
    if max_deviation <= 0.05 and plausible_bsa(mean_bsa):
        return round(mean_bsa, 2), "high"
    return None, "inconsistent_candidates"


def _find_first(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return re.sub(r"\s+", " ", match.group(0).strip())
    return None


def _downgrade(field: ExtractedField, reason: str) -> None:
    field.confidence = "low"
    field.reason = f"{field.reason or ''} {reason}".strip()
