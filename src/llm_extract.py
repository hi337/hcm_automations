from __future__ import annotations

import os

from openai import AzureOpenAI, OpenAI

from schemas.cardiac_mri_schema import ReportExtraction
from src.config import AZURE_OPENAI_DEPLOYMENT, LLM_PROVIDER, OPENAI_MODEL


PROMPT_RULES = """
You are extracting data from a cardiac MRI radiology report.

Rules:
1. Extract only values explicitly supported by the report text.
2. Do not infer missing values.
3. If a value is ambiguous, set confidence to low or medium.
4. Only use confidence high when the report directly supports the value.
5. For Y/N fields:
   - Y means directly present.
   - N means directly negated.
   - If not mentioned, value must be null and confidence absent.
6. For LGE, possible synonyms include late gadolinium enhancement, delayed enhancement, myocardial scar, fibrosis, and enhancement pattern.
7. For HCM classification:
   - hcm if report clearly diagnoses or supports HCM.
   - not_hcm if report clearly excludes HCM.
   - unsure if report is equivocal.
8. Include evidence snippets for every non-null value.
9. Do not include information not present in the report.
10. Preserve uncertainty. Never guess.
11. Treat sudden death family history separately from HCM family history.
12. Extract prior_arrhythmia as a Y/N field when mentioned, including atrial fibrillation, atrial flutter, ventricular tachycardia, non-sustained VT/NSVT, SVT, frequent PVCs, or prior clinically important rhythm disease.
13. non_sustained_VT is Y only for directly mentioned NSVT/non-sustained VT, N only for directly negated NSVT/non-sustained VT, and null when not mentioned.
14. prior_arrhythmia is separate from non_sustained_VT. If NSVT is the arrhythmia mentioned, both prior_arrhythmia and non_sustained_VT can be Y when directly supported.
"""


def _prompt(report_text: str, accession: str, regex_data: dict) -> str:
    return f"""
{PROMPT_RULES}

Accession number: {accession}

The accession number comes from the PDF filename and is authoritative. Do not replace it with a different accession number from the report text.

Regex pre-extraction:
{regex_data}

Report text:
{report_text}
"""


def _openai_extract(report_text: str, accession: str, regex_data: dict) -> dict:
    client = OpenAI()
    response = client.responses.parse(
        model=OPENAI_MODEL,
        input=_prompt(report_text, accession, regex_data),
        text_format=ReportExtraction,
    )
    return response.output_parsed.model_dump()


def _azure_openai_extract(report_text: str, accession: str, regex_data: dict) -> dict:
    if not AZURE_OPENAI_DEPLOYMENT:
        raise RuntimeError("AZURE_OPENAI_DEPLOYMENT must be set for azure_openai provider.")
    client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-03-01-preview"),
    )
    response = client.responses.parse(
        model=AZURE_OPENAI_DEPLOYMENT,
        input=_prompt(report_text, accession, regex_data),
        text_format=ReportExtraction,
    )
    return response.output_parsed.model_dump()


def llm_extract(report_text: str, accession: str, regex_data: dict) -> dict:
    if LLM_PROVIDER == "openai":
        return _openai_extract(report_text, accession, regex_data)
    if LLM_PROVIDER == "azure_openai":
        return _azure_openai_extract(report_text, accession, regex_data)
    if LLM_PROVIDER == "local_llm":
        raise NotImplementedError("local_llm provider hook is reserved for institution-approved local deployment.")
    raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")
