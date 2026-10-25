"""Unit tests for document text extraction (PDF, DOCX, TXT)."""

import pytest
from app.services.extractor import DocumentExtractionError, extract_text
from tests.helpers import create_test_docx, create_test_pdf, create_test_txt


def test_pdf_extraction_page_numbers_and_metadata(tmp_path):
    pdf_path = create_test_pdf(
        str(tmp_path),
        filename="leave_policy.pdf",
        text_pages=["Employees receive 20 days PTO.", "Maternity leave is 16 weeks paid."],
    )

    sections = extract_text(pdf_path, "application/pdf")
    assert len(sections) == 2

    # Verify 1-indexed page numbering
    assert sections[0].page_number == 1
    assert "20 days PTO" in sections[0].content
    assert sections[0].metadata["page"] == 1
    assert sections[0].metadata["total_pages"] == 2
    assert sections[0].metadata["is_scanned_or_empty"] is False

    assert sections[1].page_number == 2
    assert "16 weeks paid" in sections[1].content
    assert sections[1].metadata["page"] == 2


def test_pdf_scanned_or_blank_page_detection(tmp_path):
    # Blank/scanned PDF without OCR text
    pdf_path = create_test_pdf(
        str(tmp_path),
        filename="scanned_handbook.pdf",
        blank_pages=2,
    )

    sections = extract_text(pdf_path, "application/pdf")
    assert len(sections) == 2
    for s in sections:
        assert s.content == ""
        assert s.metadata["is_scanned_or_empty"] is True


def test_docx_extraction_headings_and_sections(tmp_path):
    docx_path = create_test_docx(
        str(tmp_path),
        sections=[
            ("Security Policy", ["All passwords must be 12 characters minimum."]),
            ("Remote Work", ["Employees may work from home with manager consent."]),
        ],
    )

    sections = extract_text(docx_path)
    assert len(sections) == 2

    # DOCX does not invent fixed page numbers
    assert sections[0].page_number is None
    assert sections[0].section_title == "Security Policy"
    assert "12 characters minimum" in sections[0].content

    assert sections[1].page_number is None
    assert sections[1].section_title == "Remote Work"
    assert "manager consent" in sections[1].content


def test_txt_extraction_paragraphs_and_offsets(tmp_path):
    txt_path = create_test_txt(
        str(tmp_path),
        content="First paragraph regarding IT assets.\n\nSecond paragraph regarding NDA agreements.",
    )

    sections = extract_text(txt_path)
    assert len(sections) == 2

    assert sections[0].page_number is None
    assert "First paragraph regarding IT assets." in sections[0].content
    assert sections[0].metadata["line_start"] == 1

    assert sections[1].page_number is None
    assert "Second paragraph regarding NDA agreements." in sections[1].content
    assert sections[1].metadata["line_start"] > 1


def test_unsupported_document_format(tmp_path):
    dummy_path = tmp_path / "script.sh"
    dummy_path.write_text("#!/bin/bash\necho hello")

    with pytest.raises(DocumentExtractionError) as exc_info:
        extract_text(str(dummy_path), content_type="application/x-sh")

    assert "Unsupported document format" in str(exc_info.value)
