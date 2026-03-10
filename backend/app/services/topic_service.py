from __future__ import annotations

from typing import Any, Dict, List

from app.services.llm_service import LLMService


def extract_paper_topics(chunks: List[Dict[str, Any]]) -> List[str]:
    """Extract 5–8 short research topics / keywords for a paper using Gemini.

    Args:
        chunks: List of chunk dicts (e.g. from get_chunks_for_paper).
    """
    if not chunks:
        return []

    MAX_CHUNKS = 8
    MAX_CHARS_PER_CHUNK = 400

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
        return []

    context_block = "\n\n".join(f"- {t}" for t in excerpt_texts)

    prompt = (
        "You are a research assistant. Based on the following excerpts from a "
        "research paper, list 5–8 short topics or keywords that best describe "
        "the core ideas. Respond with a simple comma-separated list, with no "
        "explanations.\n\n"
        f"{context_block}\n\n"
        "Topics:"
    )

    llm = LLMService()
    raw = llm.generate_text(prompt)

    # Parse a comma-separated or line-separated response into a clean list
    topics: List[str] = []
    for part in raw.replace("\n", ",").split(","):
        t = part.strip(" -•\t\r ")
        if t:
            topics.append(t)

    # De-duplicate while preserving order
    seen = set()
    unique_topics: List[str] = []
    for t in topics:
        if t.lower() in seen:
            continue
        seen.add(t.lower())
        unique_topics.append(t)

    return unique_topics[:8]

