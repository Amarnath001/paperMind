from __future__ import annotations

from typing import Any, Dict, List

from app.services.llm_service import LLMService


def generate_paper_summary(chunks: List[Dict[str, Any]]) -> str:
    """Generate a concise summary for a paper using Gemini.

    Args:
        chunks: List of chunk dicts (e.g. from get_chunks_for_paper), each
                containing at least a ``text`` field.
    """
    if not chunks:
        return ""

    # Take a subset of chunks to keep the prompt size reasonable.
    MAX_CHUNKS = 8
    MAX_CHARS_PER_CHUNK = 500

    selected = chunks[:MAX_CHUNKS]
    excerpt_texts: List[str] = []
    for c in selected:
        text = (c.get("text") or "").strip()
        if not text:
            continue
        if len(text) > MAX_CHARS_PER_CHUNK:
            text = text[:MAX_CHARS_PER_CHUNK] + "..."
        excerpt_texts.append(text)

    if not excerpt_texts:
        return ""

    context_block = "\n\n".join(f"- {t}" for t in excerpt_texts)

    prompt = (
        "You are a research assistant. Summarize the key ideas of the "
        "following research paper excerpts in 3–5 sentences. The summary "
        "should be clear, factual, and suitable for a technical reader.\n\n"
        f"{context_block}\n\n"
        "Summary:"
    )

    llm = LLMService()
    summary = llm.generate_text(prompt)
    return summary.strip()

