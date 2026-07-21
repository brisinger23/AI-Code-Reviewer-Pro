"""Core review engine backed by the OpenAI Responses API."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from prompts import build_system_prompt, build_user_prompt
from utils import extract_json, local_metrics

# Default model. Overridable via the OPENAI_MODEL environment variable so the
# app can be pointed at a newer or cheaper model without code changes.
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


class ReviewError(RuntimeError):
    """Raised when a review cannot be produced (config, API, or parse error)."""


@dataclass
class ReviewResult:
    """Structured outcome of a review, plus locally computed metrics."""

    data: dict[str, Any]
    metrics: dict[str, int] = field(default_factory=dict)


def _get_client():
    """Construct an OpenAI client, surfacing a clear error if unconfigured."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ReviewError(
            "OPENAI_API_KEY is not set. Add it to your environment or a .env "
            "file (see README) before running a review."
        )
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ReviewError(
            "The 'openai' package is not installed. Run: pip install -r "
            "requirements.txt"
        ) from exc
    return OpenAI(api_key=api_key)


def review_code(
    code: str,
    language: str,
    mode: str,
    model: str | None = None,
) -> ReviewResult:
    """Run a single code review and return a structured result.

    Uses the OpenAI Responses API. The model is instructed to emit a strict
    JSON object which is parsed into a dictionary the UI can render.
    """
    if not code or not code.strip():
        raise ReviewError("Please paste some code to review.")

    client = _get_client()
    model = model or DEFAULT_MODEL

    system_prompt = build_system_prompt(language)
    user_prompt = build_user_prompt(code, language, mode)

    try:
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_output_tokens=4096,
        )
    except Exception as exc:  # noqa: BLE001 - surface any API failure cleanly
        raise ReviewError(f"OpenAI request failed: {exc}") from exc

    text = _response_text(response)
    if not text:
        raise ReviewError("The model returned an empty response.")

    try:
        data = extract_json(text)
    except ValueError as exc:
        raise ReviewError(
            f"Could not parse the model's response as JSON. {exc}"
        ) from exc

    return ReviewResult(data=_normalize(data), metrics=local_metrics(code))


def _response_text(response: Any) -> str:
    """Extract text from a Responses API result across SDK shapes."""
    # Preferred convenience accessor in recent SDKs.
    text = getattr(response, "output_text", None)
    if text:
        return text.strip()

    # Fallback: walk the structured output blocks.
    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            piece = getattr(content, "text", None)
            if isinstance(piece, str):
                chunks.append(piece)
    return "".join(chunks).strip()


# Keys that must always exist so the renderer never trips on missing fields.
_ARRAY_KEYS = ("bugs", "security_issues", "performance_issues", "best_practices")
_OBJECT_KEYS = ("architecture_review", "complexity")


def _normalize(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure every expected key exists with a sane default."""
    for key in _ARRAY_KEYS:
        if not isinstance(data.get(key), list):
            data[key] = []
    for key in _OBJECT_KEYS:
        if not isinstance(data.get(key), dict):
            data[key] = {}
    data.setdefault("overall_score", "—")
    data.setdefault("summary", "")
    data.setdefault("refactored_code", "")
    return data
