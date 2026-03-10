"""LLM service abstraction for PaperMind.

This module introduces a thin service layer around LLM providers. For now,
only Gemini is supported and is used exclusively for *generation* tasks
(answering questions, summarisation, etc.). Embeddings continue to be handled
locally via Sentence Transformers and pgvector.
"""

from __future__ import annotations

from typing import List, Optional

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

