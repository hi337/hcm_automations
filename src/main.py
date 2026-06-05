from __future__ import annotations

import json
import traceback
from pathlib import Path

from src.config import INPUT_DIR, JSON_DIR, LOG_DIR, TEXT_DIR, ensure_output_dirs
from src.extract_text import extract_text_from_pdf
from src.llm_extract import llm_extract
from src.regex_extract import deterministic_extract
from src.route import route_pdf
from src.validate import validate_and_postprocess
from src.write_excel import append_to_excel, append_to_master_excel, extraction_to_excel_row, extraction_to_master_row


def process_pdf(pdf_path: Path) -> None:
    accession = pdf_path.stem

    text = extract_text_from_pdf(pdf_path)
    if len(text.strip()) < 100:
        raise RuntimeError("PDF text extraction returned very little text; OCR or Docling fallback review is needed.")

    (TEXT_DIR / f"{accession}.txt").write_text(text, encoding="utf-8")

    regex_data = deterministic_extract(text)
    llm_data = llm_extract(text, accession, regex_data)
    validated = validate_and_postprocess(llm_data, text, regex_data)

    json_path = JSON_DIR / f"{accession}.json"
    json_path.write_text(json.dumps(validated, indent=2, ensure_ascii=False), encoding="utf-8")

    row = extraction_to_excel_row(validated, pdf_path)
    append_to_excel(row)
    master_row = extraction_to_master_row(validated, pdf_path)
    append_to_master_excel(master_row)
    route_pdf(pdf_path, validated)


def main() -> None:
    ensure_output_dirs()
    pdfs = sorted(INPUT_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {INPUT_DIR}")
        return

    failures: list[str] = []
    for pdf_path in pdfs:
        try:
            process_pdf(pdf_path)
            print(f"Processed: {pdf_path.name}")
        except Exception as exc:
            failures.append(pdf_path.name)
            message = f"Failed: {pdf_path.name}: {exc}\n{traceback.format_exc()}"
            print(message)
            (LOG_DIR / f"{pdf_path.stem}.error.log").write_text(message, encoding="utf-8")

    print(f"Done. Processed {len(pdfs) - len(failures)} of {len(pdfs)} PDFs.")
    if failures:
        print(f"Failures: {', '.join(failures)}")


if __name__ == "__main__":
    main()
