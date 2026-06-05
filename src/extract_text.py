from __future__ import annotations

import sys
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parents[1] / "vendor"
if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))

import fitz


def extract_text_from_pdf(pdf_path: Path) -> str:
    pages: list[str] = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            text = page.get_text("text")
            pages.append(f"\n\n--- PAGE {i + 1} ---\n{text}")
    return "\n".join(pages).strip()


def extract_text_with_docling(pdf_path: Path) -> str:
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    return result.document.export_to_markdown()
