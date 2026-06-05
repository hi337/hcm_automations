# Human-in-the-loop cardiac MRI extraction

This project extracts only strongly supported values from cardiac MRI PDF reports, preserves evidence in per-report JSON, routes PDFs by HCM status, and writes high-confidence values to Excel.

## Setup

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Set `OPENAI_API_KEY` in `.env`.

If Windows blocks package installation into your user site-packages, this project also works with a local package target:

```bash
python -m pip install --target vendor pymupdf
python -m pip install openai pydantic pandas openpyxl python-dotenv
```

## Run

Put PDFs in `input_reports/`, then run:

```bash
python -m src.main
```

Name each PDF with the study accession number, for example `AHS8391094.pdf` or `102520586.pdf`. The pipeline treats the filename stem as the authoritative accession number and uses it in Excel even if the report text omits or disagrees with the accession.

Outputs are written to:

- `output/dataset.xlsx`
- `output/master_list_rows.xlsx`
- `output/review_json/*.json`
- `output/extracted_text/*.txt`
- `output/hcm/`
- `output/not_hcm/`
- `output/unsure_hcm/`
- `output/logs/`

Only fields with `confidence == "high"` are written to Excel. Medium, low, and absent values remain blank in Excel, with evidence retained in the review JSON.

`dataset.xlsx` is the audit workbook. `master_list_rows.xlsx` is formatted in the same column order as your master list screenshots so you can copy/paste rows across.

## Configuration

Default `.env`:

```text
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-5.4-mini
OPENAI_API_KEY=...
```

`azure_openai` and `local_llm` are kept as provider boundaries, but this build defaults to OpenAI and fails loudly if OpenAI credentials are missing.

## Optional Docling fallback

The default text extractor uses PyMuPDF. Install Docling only if table/layout misses become a real issue:

```bash
python -m pip install -r requirements-docling.txt
```
