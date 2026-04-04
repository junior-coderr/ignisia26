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
_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
_USE_VERTEX = str(os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "")).strip().lower() in {"1", "true", "yes"}
_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("VERTEX_PROJECT_ID")
_LOCATION = (
    os.getenv("GOOGLE_CLOUD_LOCATION")
    or os.getenv("VERTEX_LOCATION")
    or os.getenv("VERTEX_AI_LOCATION")
)
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
MODEL_FALLBACKS = [
    DEFAULT_GEMINI_MODEL,
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

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


def _init_google_genai_client():
    if google_genai is None:
        return None

    if _USE_VERTEX and _PROJECT and _LOCATION:
        return google_genai.Client(vertexai=True, project=_PROJECT, location=_LOCATION)

    if _API_KEY:
        try:
            # Vertex AI express mode uses an API key while still targeting Vertex.
            return google_genai.Client(vertexai=True, api_key=_API_KEY)
        except Exception:
            return google_genai.Client(api_key=_API_KEY)

    if _PROJECT and _LOCATION:
        return google_genai.Client(vertexai=True, project=_PROJECT, location=_LOCATION)

    return None


try:
    _CLIENT = _init_google_genai_client()
    if _CLIENT is not None:
        _CLIENT_KIND = "google_genai"
    elif legacy_genai is not None and _API_KEY:
        legacy_genai.configure(api_key=_API_KEY)
        _CLIENT = legacy_genai
        _CLIENT_KIND = "google_generativeai"
except Exception as exc:
    warnings.warn(f"Gemini client initialization failed: {exc}")
    _CLIENT = None
    _CLIENT_KIND = None


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


def response_usage(response: Any) -> dict:
    usage = getattr(response, "usage_metadata", None) or getattr(response, "usage", None)
    if usage is None:
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    def _read(value: Any, *names: str) -> int:
        if isinstance(value, dict):
            for name in names:
                if name in value and value[name] is not None:
                    return int(value[name])
            return 0
        for name in names:
            attr = getattr(value, name, None)
            if attr is not None:
                return int(attr)
        return 0

    prompt_tokens = _read(usage, "prompt_token_count", "input_tokens", "prompt_tokens")
    completion_tokens = _read(usage, "candidates_token_count", "output_tokens", "completion_tokens")
    total_tokens = _read(usage, "total_token_count", "total_tokens")
    if total_tokens == 0:
        total_tokens = prompt_tokens + completion_tokens

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }
