"""Document text extraction service supporting PDF, DOCX, and TXT files."""

from dataclasses import dataclass, field
import os
from typing import Any
import docx
import pypdf


@dataclass
class ExtractedSection:
    """Represents an extracted text block with source location metadata."""
    content: str
    page_number: int | None = None
    section_title: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class DocumentExtractionError(Exception):
    """Raised when text extraction fails due to corruption or invalid structure."""
    pass


def extract_from_pdf(file_path: str) -> list[ExtractedSection]:
    """Extracts text page-by-page from a PDF document.
    
    Preserves 1-indexed page numbers. Detects image-only/scanned pages without
    pretending optical character recognition (OCR) occurred.
    """
    try:
        reader = pypdf.PdfReader(file_path)
    except Exception as exc:
        raise DocumentExtractionError(f"Failed to parse PDF document: {exc}") from exc

    sections: list[ExtractedSection] = []
    total_pages = len(reader.pages)

    for page_idx, page in enumerate(reader.pages, start=1):
        try:
            raw_text = page.extract_text() or ""
        except Exception:
            raw_text = ""

        cleaned_text = raw_text.strip()
        is_empty_or_scanned = len(cleaned_text) == 0

        sections.append(
            ExtractedSection(
                content=cleaned_text,
                page_number=page_idx,
                section_title=f"Page {page_idx}",
                metadata={
                    "page": page_idx,
                    "total_pages": total_pages,
                    "is_scanned_or_empty": is_empty_or_scanned,
                },
            )
        )

    return sections


def extract_from_docx(file_path: str) -> list[ExtractedSection]:
    """Extracts text and hierarchical headings from a DOCX document.
    
    DOCX files do not have fixed page boundaries; page_number remains None.
    Heading paragraphs are preserved to provide contextual section titles.
    """
    try:
        doc = docx.Document(file_path)
    except Exception as exc:
        raise DocumentExtractionError(f"Failed to parse DOCX document: {exc}") from exc

    sections: list[ExtractedSection] = []
    current_heading: str | None = None
    current_paragraphs: list[str] = []

    def flush_section():
        nonlocal current_paragraphs, current_heading
        text_block = "\n".join(current_paragraphs).strip()
        if text_block:
            sections.append(
                ExtractedSection(
                    content=text_block,
                    page_number=None,
                    section_title=current_heading,
                    metadata={"section": current_heading} if current_heading else {},
                )
            )
        current_paragraphs = []

    for paragraph in doc.paragraphs:
        p_text = paragraph.text.strip()
        if not p_text:
            continue

        style_name = paragraph.style.name if paragraph.style else ""
        if "heading" in style_name.lower():
            # Flush existing section before starting a new heading block
            flush_section()
            current_heading = p_text
        else:
            current_paragraphs.append(p_text)

    # Flush any remaining paragraphs
    flush_section()

    return sections


def extract_from_txt(file_path: str) -> list[ExtractedSection]:
    """Extracts text from a TXT file with UTF-8 / latin-1 decoding.
    
    Splits content by paragraph blocks and records line offsets.
    Page numbers remain None as plaintext files do not have page pagination.
    """
    if not os.path.exists(file_path):
        raise DocumentExtractionError(f"File not found: {file_path}")

    try:
        with open(file_path, "rb") as f:
            raw_bytes = f.read()

        try:
            full_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            full_text = raw_bytes.decode("latin-1")
    except Exception as exc:
        raise DocumentExtractionError(f"Failed to read TXT file: {exc}") from exc

    # Split by double line breaks to form coherent paragraph sections
    paragraphs = full_text.split("\n\n")
    sections: list[ExtractedSection] = []
    line_offset = 1

    for p in paragraphs:
        cleaned = p.strip()
        lines_count = p.count("\n") + 1
        if cleaned:
            sections.append(
                ExtractedSection(
                    content=cleaned,
                    page_number=None,
                    section_title=None,
                    metadata={"line_start": line_offset, "line_end": line_offset + lines_count - 1},
                )
            )
        line_offset += lines_count + 1

    return sections


def extract_text(file_path: str, content_type: str | None = None) -> list[ExtractedSection]:
    """Routes document to appropriate extractor based on extension and content type."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return extract_from_pdf(file_path)
    elif ext == ".docx":
        return extract_from_docx(file_path)
    elif ext in [".txt", ".text", ".md"]:
        return extract_from_txt(file_path)
    elif content_type == "application/pdf":
        return extract_from_pdf(file_path)
    elif content_type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ]:
        return extract_from_docx(file_path)
    elif content_type and content_type.startswith("text/"):
        return extract_from_txt(file_path)
    else:
        raise DocumentExtractionError(f"Unsupported document format: '{ext}' (content_type='{content_type}')")

