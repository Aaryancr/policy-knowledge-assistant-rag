"""Document chunking and text-splitting service.

Note on Character Counts vs Token Counts:
We split text based on character length as a deterministic, lightweight proxy
(~4 characters per token in standard English text). This avoids tying the ingestion
pipeline to a specific tokenizer runtime (such as tiktoken or HuggingFace tokenizers),
enabling flexible downstream LLM provider swapping without re-chunking dependencies.
"""

from dataclasses import dataclass, field
import uuid
from typing import Any

from app.config import get_settings
from app.services.extractor import ExtractedSection

settings = get_settings()


@dataclass
class ProcessedChunk:
    """Represents a text chunk ready for vector embedding and persistence."""
    document_id: uuid.UUID
    chunk_index: int
    content: str
    page_number: int | None
    section_title: str | None
    metadata_json: dict[str, Any] = field(default_factory=dict)


def _split_text_recursively(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: list[str] | None = None,
) -> list[str]:
    """Recursively splits a string into chunks of max `chunk_size` with `chunk_overlap`."""
    if separators is None:
        separators = ["\n\n", "\n", ". ", "? ", "! ", "; ", " ", ""]

    if len(text) <= chunk_size:
        cleaned = text.strip()
        return [cleaned] if cleaned else []

    # Find the first separator present in text
    separator = separators[-1]
    new_separators = []
    for i, sep in enumerate(separators):
        if sep == "":
            separator = ""
            break
        if sep in text:
            separator = sep
            new_separators = separators[i + 1:]
            break

    splits = text.split(separator) if separator else list(text)

    # Recombine splits up to chunk_size with overlap
    good_chunks: list[str] = []
    current_chunk: list[str] = []
    current_len = 0

    for s in splits:
        s_len = len(s) + (len(separator) if current_chunk else 0)
        if current_len + s_len > chunk_size and current_chunk:
            combined = separator.join(current_chunk).strip()
            if combined:
                good_chunks.append(combined)

            # Keep overlap by retaining tail items
            overlap_len = 0
            overlap_chunk: list[str] = []
            for item in reversed(current_chunk):
                item_len = len(item) + len(separator)
                if overlap_len + item_len <= chunk_overlap:
                    overlap_chunk.insert(0, item)
                    overlap_len += item_len
                else:
                    break
            current_chunk = overlap_chunk
            current_len = sum(len(x) for x in current_chunk) + (len(separator) * max(0, len(current_chunk) - 1))

        if len(s) > chunk_size and new_separators:
            # Sub-split oversized segment with finer separators
            sub_chunks = _split_text_recursively(s, chunk_size, chunk_overlap, new_separators)
            good_chunks.extend(sub_chunks)
        else:
            current_chunk.append(s)
            current_len += len(s) + (len(separator) if len(current_chunk) > 1 else 0)

    if current_chunk:
        combined = separator.join(current_chunk).strip()
        if combined:
            good_chunks.append(combined)

    return good_chunks


def chunk_sections(
    sections: list[ExtractedSection],
    document_id: uuid.UUID,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[ProcessedChunk]:
    """Splits extracted document sections into indexed chunks with preserved metadata."""
    effective_chunk_size = chunk_size or settings.CHUNK_SIZE
    effective_chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    if effective_chunk_overlap >= effective_chunk_size:
        effective_chunk_overlap = max(0, effective_chunk_size // 4)

    processed_chunks: list[ProcessedChunk] = []
    chunk_index = 0

    for section in sections:
        if not section.content.strip():
            continue

        raw_chunks = _split_text_recursively(
            text=section.content,
            chunk_size=effective_chunk_size,
            chunk_overlap=effective_chunk_overlap,
        )

        for text_chunk in raw_chunks:
            cleaned = text_chunk.strip()
            if not cleaned:
                continue

            metadata = dict(section.metadata)
            metadata.update({
                "chunk_index": chunk_index,
                "char_length": len(cleaned),
            })
            if section.page_number is not None:
                metadata["page_number"] = section.page_number
            if section.section_title:
                metadata["section_title"] = section.section_title

            processed_chunks.append(
                ProcessedChunk(
                    document_id=document_id,
                    chunk_index=chunk_index,
                    content=cleaned,
                    page_number=section.page_number,
                    section_title=section.section_title,
                    metadata_json=metadata,
                )
            )
            chunk_index += 1

    return processed_chunks
