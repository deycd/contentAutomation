from functools import lru_cache
from typing import Optional

from groq import Groq
from langchain_groq import ChatGroq
from google import genai

from contentAutomation.config import settings


# ----------------------------------------------------------------------
# Groq
# ----------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_groq_client() -> Groq:
    """Return a cached, reusable Groq client instance."""
    return Groq(
        api_key=settings.groq_api_key or None,
        timeout=settings.groq_timeout,
    )


@lru_cache(maxsize=4)
def get_chat_llm(
    model: Optional[str] = None,
    temperature: float = 0.2,
) -> ChatGroq:
    """Return a cached ChatGroq instance."""
    return ChatGroq(
        model=model or settings.groq_chat_model,
        temperature=temperature,
        api_key=settings.groq_api_key or None,
    )


# ----------------------------------------------------------------------
# Google Gemini
# ----------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_google_client() -> genai.Client:
    """Return a cached, reusable Google GenAI client instance."""

    if not settings.google_api_key:
        raise ValueError(
            "GOOGLE_API_KEY is not configured."
        )

    return genai.Client(
        api_key=settings.google_api_key,
    )


# ----------------------------------------------------------------------
# Lazy clients
# ----------------------------------------------------------------------

class _LazyClient:
    def __getattr__(self, name):
        return getattr(get_groq_client(), name)


class _LazyLLM:
    def __getattr__(self, name):
        return getattr(get_chat_llm(), name)


class _LazyGoogleClient:
    def __getattr__(self, name):
        return getattr(get_google_client(), name)


# ----------------------------------------------------------------------
# Backward-compatible global references
# ----------------------------------------------------------------------

groq_client = _LazyClient()
llm = _LazyLLM()
google_client = _LazyGoogleClient()