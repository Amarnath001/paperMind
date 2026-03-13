"""LLM service abstraction for PaperMind.

This module introduces a thin service layer around LLM providers. For now,
only Gemini is supported and is used exclusively for *generation* tasks
(answering questions, summarisation, etc.). Embeddings continue to be handled
locally via Sentence Transformers and pgvector.
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any

import google.generativeai as genai

from app.config import Config


class LLMService:
    """High-level LLM interface.

    Usage:
        llm = LLMService()
        text = llm.generate_text("Hello, world")
    """

    def __init__(self, provider: Optional[str] = None) -> None:
        self.provider = (provider or Config.LLM_PROVIDER).lower()
        if self.provider == "gemini":
            _configure_gemini()
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider!r}")

    # --------------------------------------------------------------------- #
    # Core API
    # --------------------------------------------------------------------- #

    def generate_text(self, prompt: str) -> str:
        """Generate free-form text from a prompt using the configured LLM."""
        if not prompt.strip():
            raise ValueError("Prompt must not be empty.")

        if self.provider == "gemini":
            return _gemini_generate_text(prompt)

        raise ValueError(f"Unsupported LLM provider: {self.provider!r}")

    def generate_answer(self, question: str, context_chunks: List[str]) -> str:
        """Generate an answer using a RAG-style prompt over context chunks.

        This does not perform retrieval itself — it assumes the caller already
        retrieved relevant chunks (e.g. via pgvector semantic search).
        """
        if not question.strip():
            raise ValueError("Question must not be empty.")

        if not context_chunks:
            # Still allow the model to answer, but make it explicit.
            context_text = "No additional context chunks were provided."
        else:
            bullet_chunks = "\n\n".join(
                f"- {chunk.strip()}" for chunk in context_chunks if chunk.strip()
            )
            context_text = f"The following context excerpts come from research papers:\n\n{bullet_chunks}"

        prompt = (
            "You are a concise, accurate research assistant. "
            "Use ONLY the provided context excerpts to answer the question. "
            "If the context does not contain the answer, say that explicitly.\n\n"
            f"{context_text}\n\n"
            f"Question: {question.strip()}\n\n"
            "Answer:"
        )

        return self.generate_text(prompt)

    def generate_answer_with_citations(
        self,
        question: str,
        retrieved_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate an answer plus simple citations based on retrieved chunks.

        The citations are derived from the *order* of retrieved_chunks rather
        than parsing the model output. This is intentionally simple and robust:
        chunks are labelled [1], [2], ... in the same order they are sent to
        the model, and all of them are exposed as citation candidates.
        """
        if not question.strip():
            raise ValueError("Question must not be empty.")

        if not retrieved_chunks:
            # No context: respond with a guarded answer.
            answer = (
                "I do not have any relevant excerpts from the library to answer "
                "this question confidently."
            )
            return {"answer": answer, "citations": []}

        # Truncate very long chunks to avoid huge prompts
        MAX_CHARS_PER_CHUNK = 600
        formatted_chunks: List[str] = []
        citations: List[Dict[str, Any]] = []

        for idx, chunk in enumerate(retrieved_chunks, start=1):
            label = f"[{idx}]"
            text = (chunk.get("text") or "").strip()
            if len(text) > MAX_CHARS_PER_CHUNK:
                text = text[:MAX_CHARS_PER_CHUNK] + "..."

            paper_title = chunk.get("paper_title") or "Unknown paper"
            chunk_index = chunk.get("chunk_index")

            formatted_chunks.append(
                f"{label} Paper: {paper_title}\n"
                f"Chunk index: {chunk_index}\n"
                f"Excerpt: {text}"
            )

            citations.append(
                {
                    "chunk_id": str(chunk.get("chunk_id")),
                    "paper_id": str(chunk.get("paper_id")),
                    "paper_title": paper_title,
                    "chunk_index": chunk_index,
                    "label": label,
                }
            )

        context_block = "\n\n".join(formatted_chunks)

        prompt = (
            "You are a careful, concise research assistant.\n"
            "Use the numbered excerpts below as your primary evidence when answering.\n"
            "If the excerpts only partially cover the question, still give the best\n"
            "possible explanation you can, being explicit about what is grounded in\n"
            "the excerpts and what is a reasonable inference beyond them.\n"
            "Avoid claiming that you cannot answer at all unless there is truly no\n"
            "relevant information in the excerpts. When relevant, reference the\n"
            "excerpt numbers like [1], [2] in your answer.\n\n"
            "Context excerpts:\n"
            f"{context_block}\n\n"
            f"Question: {question.strip()}\n\n"
            "Answer (with references to [1], [2], etc where appropriate):"
        )

        answer_text = self.generate_text(prompt)
        return {
            "answer": answer_text,
            "citations": citations,
        }


# ------------------------------------------------------------------------- #
# Gemini implementation details
# ------------------------------------------------------------------------- #

_gemini_configured = False
_gemini_model = None


def _configure_gemini() -> None:
    """Configure the global Gemini client once per process."""
    global _gemini_configured
    if _gemini_configured:
        return

    api_key = Config.GEMINI_API_KEY
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Set it in your environment or .env file to use Gemini."
        )

    genai.configure(api_key=api_key)
    _gemini_configured = True


def _get_gemini_model():
    """Return a lazily initialised GenerativeModel instance."""
    global _gemini_model
    if _gemini_model is None:
        model_name = Config.GEMINI_MODEL
        _gemini_model = genai.GenerativeModel(model_name)
    return _gemini_model


def _gemini_generate_text(prompt: str) -> str:
    model = _get_gemini_model()
    # google-generativeai returns a GenerativeResponse object
    response = model.generate_content(prompt)
    # .text aggregates candidate parts; fall back defensively
    text = getattr(response, "text", "") or ""
    if not text and getattr(response, "candidates", None):
        # best-effort fallback if .text is unexpectedly empty
        parts = []
        for cand in response.candidates:
            for part in getattr(cand, "content", {}).parts:
                if hasattr(part, "text"):
                    parts.append(part.text)
        text = "\n".join(parts).strip()

    return text.strip()

