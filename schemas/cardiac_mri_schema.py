from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


Confidence = Literal["high", "medium", "low", "absent"]
HcmClassification = Literal["hcm", "not_hcm", "unsure"]


class ExtractedField(BaseModel):
    value: str | float | int | None = None
    confidence: Confidence = "absent"
    evidence: str | None = None
    reason: str | None = None
    source_text_location: str | None = None

    @field_validator("evidence", "reason", "source_text_location", mode="before")
    @classmethod
    def blank_strings_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class ReportExtraction(BaseModel):
    accession_number: str

    hcm_classification: HcmClassification = "unsure"
    hcm_classification_confidence: Confidence = "absent"
    hcm_classification_evidence: str | None = None

    patient_name: ExtractedField = Field(default_factory=ExtractedField)
    DOB: ExtractedField = Field(default_factory=ExtractedField)
    SVCC_ID: ExtractedField = Field(default_factory=ExtractedField)
    sex: ExtractedField = Field(default_factory=ExtractedField)

    height_cm: ExtractedField = Field(default_factory=ExtractedField)
    weight_kg: ExtractedField = Field(default_factory=ExtractedField)
    BSA: ExtractedField = Field(default_factory=ExtractedField)

    family_history_HCM: ExtractedField = Field(default_factory=ExtractedField)
    family_history_sudden_death: ExtractedField = Field(default_factory=ExtractedField)
    LGE: ExtractedField = Field(default_factory=ExtractedField)
    AICD: ExtractedField = Field(default_factory=ExtractedField)
    AICD_shocks: ExtractedField = Field(default_factory=ExtractedField)
    hospitalization_for_HF: ExtractedField = Field(default_factory=ExtractedField)
    aneurysm: ExtractedField = Field(default_factory=ExtractedField)
    max_LV_wall_thickness_mm: ExtractedField = Field(default_factory=ExtractedField)
    LVOT_gradient_mmHg: ExtractedField = Field(default_factory=ExtractedField)
    syncope: ExtractedField = Field(default_factory=ExtractedField)
    non_sustained_VT: ExtractedField = Field(default_factory=ExtractedField)
    prior_arrhythmia: ExtractedField = Field(default_factory=ExtractedField)

    study_date: ExtractedField = Field(default_factory=ExtractedField)
    LVEF: ExtractedField = Field(default_factory=ExtractedField)
    LVSV_indexed_BSA: ExtractedField = Field(default_factory=ExtractedField)
    LVEDV_indexed_BSA: ExtractedField = Field(default_factory=ExtractedField)
    LVESV_indexed_BSA: ExtractedField = Field(default_factory=ExtractedField)
    LV_mass_indexed_BSA: ExtractedField = Field(default_factory=ExtractedField)
    HCM_since: ExtractedField = Field(default_factory=ExtractedField)

    LVSV_absolute: ExtractedField = Field(default_factory=ExtractedField)
    LVEDV_absolute: ExtractedField = Field(default_factory=ExtractedField)
    LVESV_absolute: ExtractedField = Field(default_factory=ExtractedField)
    LV_mass_absolute: ExtractedField = Field(default_factory=ExtractedField)

    fields_blank_due_to_uncertainty: list[str] = Field(default_factory=list)
    review_required: bool = True
    notes: str | None = None


def empty_extraction(accession_number: str) -> ReportExtraction:
    return ReportExtraction(accession_number=accession_number)
