"""
Compatibility helpers for Gemini SDK variants.

The project was written against `google.genai`, while the current environment
ships `google-generativeai`. This module hides those differences and also makes
Gemini optional so the backend can still boot even when an API key is missing.
"""
import os
import warnings
from typing import Any

from dotenv import load_dotenv

load_dotenv()

google_genai = None
google_genai_types = None
legacy_genai = None


_CLIENT_KIND: str | None = None
_CLIENT: Any = None
_API_KEY = os.getenv("GEMINI_API_KEY")
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
MODEL_FALLBACKS = [
    DEFAULT_GEMINI_MODEL,
    "gemini-flash-lite-latest",
    "gemini-2.0-flash-lite",
]

if _API_KEY:
    try:
        from google import genai as google_genai
        from google.genai import types as google_genai_types
    except ImportError:
        google_genai = None
        google_genai_types = None

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            import google.generativeai as legacy_genai
    except ImportError:
        legacy_genai = None

    if google_genai is not None:
        _CLIENT = google_genai.Client(api_key=_API_KEY)
        _CLIENT_KIND = "google_genai"
    elif legacy_genai is not None:
        legacy_genai.configure(api_key=_API_KEY)
        _CLIENT = legacy_genai
        _CLIENT_KIND = "google_generativeai"


def gemini_enabled() -> bool:
    return _CLIENT is not None


def make_inline_part(data: bytes, mime_type: str) -> Any:
    if _CLIENT_KIND == "google_genai":
        return google_genai_types.Part.from_bytes(data=data, mime_type=mime_type)
    return {"mime_type": mime_type, "data": data}


def _generate_content_once(model: str, contents: Any) -> Any:
    if _CLIENT_KIND == "google_genai":
        return _CLIENT.models.generate_content(model=model, contents=contents)
    if _CLIENT_KIND == "google_generativeai":
        model_client = _CLIENT.GenerativeModel(model_name=model)
        return model_client.generate_content(contents)
    raise RuntimeError("Gemini client is unavailable")


def _is_missing_model_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "not found" in msg or "not supported for generatecontent" in msg


def generate_content(model: str, contents: Any) -> Any:
    candidates = [model] + [m for m in MODEL_FALLBACKS if m != model]
    last_exc = None
    for candidate in candidates:
        try:
            return _generate_content_once(candidate, contents)
        except Exception as exc:
            last_exc = exc
            if not _is_missing_model_error(exc):
                raise
    raise last_exc


def response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text

    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return ""

    content = getattr(candidates[0], "content", None)
    parts = getattr(content, "parts", None) or []
    if not parts:
        return ""

    return getattr(parts[0], "text", "") or ""
