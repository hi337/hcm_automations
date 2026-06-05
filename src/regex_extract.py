from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MatchValue:
    value: str | float | int
    evidence: str
    source_text_location: str | None = None


def _page_for_index(text: str, index: int) -> str | None:
    page = 1
    for match in re.finditer(r"--- PAGE\s+(\d+)\s+---", text):
        if match.start() > index:
            break
        page = int(match.group(1))
    return f"page {page}"


def _first(patterns: list[str], text: str, flags: int = re.IGNORECASE) -> MatchValue | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            value = match.group("value") if "value" in match.groupdict() else match.group(1)
            evidence = match.group(0).strip()
            return MatchValue(value=value.strip(), evidence=evidence, source_text_location=_page_for_index(text, match.start()))
    return None


def _number(value: str) -> float | int | None:
    cleaned = value.replace(",", "").strip()
    try:
        parsed = float(cleaned)
    except ValueError:
        return None
    if parsed.is_integer():
        return int(parsed)
    return parsed


def deterministic_extract(text: str) -> dict:
    results: dict[str, dict] = {}

    field_patterns = {
        "DOB": [
            r"\bDOB\s*[:\-]\s*(?P<value>\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
            r"\bDate of Birth\s*[:\-]\s*(?P<value>\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
            r"\bDOB\s*[:\-]\s*(?P<value>\d{4}-\d{1,2}-\d{1,2})\b",
        ],
        "sex": [
            r"\bSex\s*[:\-]\s*(?P<value>Male|Female|M|F)\b",
            r"\bGender\s*[:\-]\s*(?P<value>Male|Female|M|F)\b",
        ],
        "study_date": [
            r"\bStudy Date\s*[:\-]\s*(?P<value>\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
            r"\bExam Date\s*[:\-]\s*(?P<value>\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
            r"\bDate of Service\s*[:\-]\s*(?P<value>\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
        ],
        "height_cm": [
            r"\bHeight\s*[:\-]?\s*(?P<value>\d{2,3}(?:\.\d+)?)\s*cm\b",
            r"\bHt\s*[:\-]?\s*(?P<value>\d{2,3}(?:\.\d+)?)\s*cm\b",
        ],
        "weight_kg": [
            r"\bWeight\s*[:\-]?\s*(?P<value>\d{2,3}(?:\.\d+)?)\s*kg\b",
            r"\bWt\s*[:\-]?\s*(?P<value>\d{2,3}(?:\.\d+)?)\s*kg\b",
        ],
        "BSA": [
            r"\bBSA\s*[:=\-]?\s*(?P<value>\d(?:\.\d{1,2})?)\s*(?:m2|m\^2|m²)?\b",
        ],
        "LVEF": [
            r"\bLVEF\s*[:=\-]?\s*(?P<value>\d{1,2}(?:\.\d+)?)\s*%",
            r"\bLV ejection fraction\s*[:=\-]?\s*(?P<value>\d{1,2}(?:\.\d+)?)\s*%",
        ],
        "max_LV_wall_thickness_mm": [
            r"\bmax(?:imum)?(?:\s+LV)?\s+wall thickness\s*[:=\-]?\s*(?P<value>\d{1,2}(?:\.\d+)?)\s*mm\b",
            r"\bmax(?:imum)?\s+septal thickness\s*[:=\-]?\s*(?P<value>\d{1,2}(?:\.\d+)?)\s*mm\b",
        ],
        "LVSV_indexed_BSA": [
            r"\bLVSV(?:i| index(?:ed)?)?\s*[:=\-]?\s*(?P<value>\d{1,3}(?:\.\d+)?)\s*(?:mL/m2|ml/m²|mL/m²)\b",
        ],
        "LVEDV_indexed_BSA": [
            r"\bLVEDV(?:i| index(?:ed)?)?\s*[:=\-]?\s*(?P<value>\d{1,3}(?:\.\d+)?)\s*(?:mL/m2|ml/m²|mL/m²)\b",
        ],
        "LVESV_indexed_BSA": [
            r"\bLVESV(?:i| index(?:ed)?)?\s*[:=\-]?\s*(?P<value>\d{1,3}(?:\.\d+)?)\s*(?:mL/m2|ml/m²|mL/m²)\b",
        ],
        "LV_mass_indexed_BSA": [
            r"\bLV mass(?:i| index(?:ed)?)?\s*[:=\-]?\s*(?P<value>\d{1,3}(?:\.\d+)?)\s*(?:g/m2|g/m²)\b",
        ],
        "LVSV_absolute": [
            r"\bLVSV\s*[:=\-]?\s*(?P<value>\d{1,3}(?:\.\d+)?)\s*mL\b",
        ],
        "LVEDV_absolute": [
            r"\bLVEDV\s*[:=\-]?\s*(?P<value>\d{1,3}(?:\.\d+)?)\s*mL\b",
        ],
        "LVESV_absolute": [
            r"\bLVESV\s*[:=\-]?\s*(?P<value>\d{1,3}(?:\.\d+)?)\s*mL\b",
        ],
        "LV_mass_absolute": [
            r"\bLV mass\s*[:=\-]?\s*(?P<value>\d{1,3}(?:\.\d+)?)\s*g\b",
        ],
    }

    for field, patterns in field_patterns.items():
        found = _first(patterns, text)
        if found:
            value: str | float | int = found.value
            if field not in {"DOB", "sex", "study_date"}:
                numeric = _number(str(value))
                if numeric is not None:
                    value = numeric
            results[field] = {
                "value": value,
                "confidence": "high",
                "evidence": found.evidence,
                "source_text_location": found.source_text_location,
                "reason": "Deterministic regex match.",
            }

    return results
