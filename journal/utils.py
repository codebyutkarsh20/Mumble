"""Utility helpers for the Journal module.

This module provides:
1. `transcribe_audio` – converts an uploaded audio file into raw text.  Tries the
   Whisper python package first; if not installed, returns a dummy transcript so
   the rest of the flow still works.
2. `extract_moods` / `extract_topics` – analyse diary text to determine the
   prominent emotional tones and discussion topics.  Uses the OpenAI Chat
   Completions API when an `OPENAI_API_KEY` is configured; otherwise falls back
   to a simple keyword-based heuristic so the feature still behaves gracefully
   in offline development environments.
3. `polish_text` – optionally rewrites raw speech-to-text output into a clean,
   well-formed journal paragraph via GPT.  If the OpenAI key is missing it
   simply returns the trimmed input text.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import List, Tuple

from flask import current_app

# Optional heavy dependencies -------------------------------------------------------

try:
    import openai  # type: ignore
except ImportError:  # pragma: no cover – still usable without
    openai = None

try:
    import whisper  # type: ignore
except ImportError:  # pragma: no cover
    whisper = None


# ----------------------------------------------------------------------------------
# Audio Transcription
# ----------------------------------------------------------------------------------

def transcribe_audio(file_path: str) -> str:
    """Transcribe *file_path* using OpenAI Whisper (if installed).

    The base Whisper model is accurate enough for short personal diary entries
    while remaining reasonably fast on CPU-only machines.  When the `whisper`
    package is not available we log a warning and return a placeholder."""

    if whisper is None:
        current_app.logger.warning("Whisper not installed – returning dummy transcript")
        return "(Transcription unavailable – install the 'whisper' package)"

    model = whisper.load_model("base")
    # Whisper expects an actual file on disk – ensure path is accessible.
    result = model.transcribe(file_path)
    return result.get("text", "").strip()


# ----------------------------------------------------------------------------------
# Mood & Topic Extraction (OpenAI powered with fallback)
# ----------------------------------------------------------------------------------

_analyses_cache: dict[str, Tuple[List[dict], List[dict]]] = {}


def _call_openai_analysis(text: str) -> Tuple[List[dict], List[dict]]:
    """Send *text* to GPT and parse the returned JSON lists."""

    api_key = current_app.config.get("OPENAI_API_KEY")
    if not api_key or openai is None:
        raise RuntimeError("OpenAI not configured")

    openai.api_key = api_key

    system_msg = {
        "role": "system",
        "content": (
            "You are a helpful assistant that analyses a user's personal diary text. "
            "Return _only_ a minified JSON object with exactly two keys: 'moods' and 'topics'. "
            "'moods' must be an array of {name: <emotion>, confidence: <0-1 float>} objects. "
            "'topics' must be an array of {name: <topic>, relevance: <0-1 float>} objects."
        ),
    }
    user_msg = {"role": "user", "content": text}

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[system_msg, user_msg],
        temperature=0.2,
        max_tokens=300,
    )
    raw = response.choices[0].message.content.strip()

    try:
        data = json.loads(raw)
        return data.get("moods", []), data.get("topics", [])
    except json.JSONDecodeError as exc:  # noqa: BLE001 – log and fallback
        current_app.logger.error("Failed to parse OpenAI analysis JSON: %s", raw)
        raise RuntimeError("Invalid JSON from OpenAI") from exc


# --- Fallback heuristic -----------------------------------------------------------

_FALLBACK_MOODS = {
    "happy": ["happy", "joy", "glad", "excited"],
    "sad": ["sad", "down", "unhappy", "depressed"],
    "angry": ["angry", "mad", "furious"],
    "anxious": ["anxious", "nervous", "worried"],
}

_FALLBACK_TOPICS = {
    "work": ["work", "office", "project", "meeting"],
    "family": ["family", "mom", "dad", "sister", "brother", "kids"],
    "health": ["health", "exercise", "diet", "doctor"],
}


def _keyword_fallback(text: str) -> Tuple[List[dict], List[dict]]:
    """Crude keyword detector – ensures feature works offline."""
    lower = text.lower()
    moods: list[dict] = []
    topics: list[dict] = []

    for name, kws in _FALLBACK_MOODS.items():
        score = sum(1 for kw in kws if kw in lower) / len(kws)
        if score:
            moods.append({"name": name, "confidence": round(score, 2)})

    for name, kws in _FALLBACK_TOPICS.items():
        score = sum(1 for kw in kws if kw in lower) / len(kws)
        if score:
            topics.append({"name": name, "relevance": round(score, 2)})

    return moods, topics


# --- Public helpers --------------------------------------------------------------

def _analyse(text: str) -> Tuple[List[dict], List[dict]]:
    if text in _analyses_cache:
        return _analyses_cache[text]

    try:
        moods, topics = _call_openai_analysis(text)
    except Exception as exc:  # noqa: BLE001 – any failure triggers fallback
        current_app.logger.info("OpenAI analysis failed (%s); using heuristic fallback", exc)
        moods, topics = _keyword_fallback(text)

    _analyses_cache[text] = (moods, topics)
    return moods, topics


def extract_moods(text: str) -> List[dict]:
    """Return a list of mood dicts: [{name, confidence}]"""
    moods, _ = _analyse(text)
    return moods


def extract_topics(text: str) -> List[dict]:
    """Return a list of topic dicts: [{name, relevance}]"""
    _, topics = _analyse(text)
    return topics


# ----------------------------------------------------------------------------------
# Text Polishing
# ----------------------------------------------------------------------------------

def polish_text(text: str) -> str:
    """Rewrite *text* into a polished diary paragraph via GPT if configured."""

    api_key = current_app.config.get("OPENAI_API_KEY")
    if not api_key or openai is None:
        return text.strip()

    openai.api_key = api_key
    prompt = (
        "Please rewrite the following raw speech-to-text diary entry into a clear, "
        "well-structured first-person journal paragraph. Avoid changing the meaning "
        "but improve grammar and flow.\n\n" + text.strip() + "\n\nPolished Entry:"
    )

    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        temperature=0.4,
        max_tokens=max(200, len(text) // 2),
    )
    return response.choices[0].text.strip()
