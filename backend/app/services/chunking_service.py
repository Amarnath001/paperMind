from __future__ import annotations

import re
from typing import List, Tuple


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _split_into_paragraphs(text: str) -> list[str]:
    # Split on double newlines as a simple paragraph heuristic
    raw_paragraphs = re.split(r"\n{2,}", text)
    return [p.strip() for p in raw_paragraphs if p.strip()]


def estimate_token_count(chunk: str) -> int:
    """Rough token-count approximation based on word count."""
    # Very simple heuristic: assume ~0.75 tokens per character of a word.
    words = chunk.split()
    return int(len(words) * 1.3)


def chunk_text(
    text: str,
    min_chunk_size: int = 800,
    max_chunk_size: int = 1200,
) -> List[Tuple[int, str, int]]:
    """Split text into ordered chunks with approximate token counts.

    Returns a list of tuples: (chunk_index, chunk_text, token_count).
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = _split_into_paragraphs(normalized)

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_norm = _normalize_whitespace(para)
        para_len = len(para_norm)

        if para_len > max_chunk_size and not current:
            # Very long paragraph: hard-split it
            start = 0
            while start < para_len:
                end = min(start + max_chunk_size, para_len)
                part = para_norm[start:end]
                chunks.append(part)
                start = end
            continue

        if current_len + 1 + para_len <= max_chunk_size:
            current.append(para_norm)
            current_len += (1 if current_len else 0) + para_len
        else:
            if current:
                chunks.append(" ".join(current))
            current = [para_norm]
            current_len = para_len

    if current:
        chunks.append(" ".join(current))

    # Post-process small trailing chunks by merging if necessary
    merged: list[str] = []
    for chunk in chunks:
        if merged and len(chunk) < min_chunk_size and len(merged[-1]) + 1 + len(chunk) <= max_chunk_size:
            merged[-1] = f"{merged[-1]} {chunk}"
        else:
            merged.append(chunk)

    result: List[Tuple[int, str, int]] = []
    for idx, chunk in enumerate(merged):
        token_count = estimate_token_count(chunk)
        result.append((idx, chunk, token_count))

    return result

