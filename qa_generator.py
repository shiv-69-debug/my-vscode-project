"""Interview QA generation, evaluation, and coaching module.

Provides robust parsing, configurable scoring, optional caching,
and structured output validation for the interview practice app.
"""

import json
import hashlib
import logging
import time
from typing import Optional

import ollama

from config import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_key(*args: str) -> str:
    """Produce a short deterministic cache key from string arguments."""
    return hashlib.sha256("|".join(args).encode()).hexdigest()[:16]


# Simple in-memory cache when Redis is not available
_cache: dict = {}


def _cache_get(key: str) -> Optional[dict]:
    if not config.cache_enabled:
        return None
    entry = _cache.get(key)
    if entry and time.time() - entry["ts"] < config.cache_ttl_seconds:
        return entry["data"]
    return None


def _cache_set(key: str, data: dict) -> None:
    if not config.cache_enabled:
        return
    _cache[key] = {"ts": time.time(), "data": data}


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def call_llm(prompt: str, system: Optional[str] = None) -> str:
    """Call Ollama with the given prompt and optional system message."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    logger.debug("Calling Ollama model=%s prompt_len=%d", config.ollama_model, len(prompt))

    response = ollama.chat(
        model=config.ollama_model,
        host=config.ollama_host,
        messages=messages,
    )
    return response.message.content.strip()


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def build_qa_prompt(role: str, difficulty: str, topic: str = "") -> str:
    """Build a prompt for generating one Q&A pair."""
    topic_line = f"Topic focus: {topic}" if topic else ""
    return (
        "You are a senior technical interviewer for a top-tier company.\n"
        f"Role: {role}\n"
        f"Difficulty: {difficulty}\n"
        f"{topic_line}\n"
        "Task: Create ONE interview question with its ideal concise answer.\n\n"
        "Output format (VERY IMPORTANT – follow EXACTLY):\n"
        "QUESTION: <the question>\n"
        "ANSWER: <the answer>\n\n"
        "Rules:\n"
        "1. Start each line with exactly 'QUESTION:' or 'ANSWER:' – capitals, colon, space.\n"
        "2. Do NOT add any introductory or closing text.\n"
        "3. Make the answer technically thorough yet clear.\n"
        "4. The answer must be good enough to serve as a model answer for scoring."
    )


def build_eval_prompt(question: str, answer: str) -> str:
    """Build a prompt for scoring a candidate answer."""
    return (
        "You are a senior technical interviewer evaluating a candidate.\n"
        "Score the answer on three dimensions and return ONLY valid JSON.\n\n"
        f"QUESTION:\n{question}\n\n"
        f"CANDIDATE ANSWER:\n{answer}\n\n"
        "Scoring (strict integer scales):\n"
        f"- accuracy: 0–{config.accuracy_max}  (0=completely wrong, {config.accuracy_max}=fully correct)\n"
        f"- depth: 0–{config.depth_max}  (0=shallow, {config.depth_max}=deep insight)\n"
        f"- communication: 0–{config.communication_max}  (0=unclear, {config.communication_max}=very clear)\n\n"
        "Output format (only JSON, no markdown, no extra text):\n"
        "{\n"
        f'  "accuracy": <0-{config.accuracy_max}>,\n'
        f'  "depth": <0-{config.depth_max}>,\n'
        f'  "communication": <0-{config.communication_max}>,\n'
        "  \"overall\": <accuracy+depth+communication>\n"
        "}"
    )


def build_coach_prompt(question: str, user_answer: str, scores: dict) -> str:
    """Build a prompt for coaching feedback."""
    return (
        "You are a kind, expert interview coach.\n"
        "Review the candidate's answer and give constructive, actionable feedback.\n\n"
        f"QUESTION:\n{question}\n\n"
        f"CANDIDATE ANSWER:\n{user_answer}\n\n"
        f"SCORES:\naccuracy: {scores.get('accuracy', 0)}/{config.accuracy_max}\n"
        f"depth: {scores.get('depth', 0)}/{config.depth_max}\n"
        f"communication: {scores.get('communication', 0)}/{config.communication_max}\n"
        f"overall: {scores.get('overall', 0)}/{config.overall_max}\n\n"
        "Return ONLY valid JSON (no markdown fences, no extra text) with these keys:\n"
        "{\n"
        '  "summary": "one-sentence overall assessment",\n'
        '  "strengths": ["specific strength 1", "specific strength 2", ...],\n'
        '  "improvements": ["specific improvement 1", "specific improvement 2", ...],\n'
        '  "model_answer": "a polished, high-quality model answer to the question"\n'
        "}"
    )


# ---------------------------------------------------------------------------
# Safe JSON parsing
# ---------------------------------------------------------------------------

def _parse_json(raw: str, fallback: dict) -> dict:
    """Parse LLM output as JSON, stripping markdown fences if present."""
    text = raw.strip()
    # Remove common markdown code fences
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop the first line (```json or ```) and the last line (```)
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM JSON. Raw: %.200s", raw)
        return fallback


def _validate_scores(data: dict) -> dict:
    """Clamp and validate score values."""
    for key in ["accuracy", "depth", "communication", "overall"]:
        val = data.get(key)
        if not isinstance(val, (int, float)):
            val = 0
        data[key] = int(val)
    # Clamp
    data["accuracy"] = max(0, min(data["accuracy"], config.accuracy_max))
    data["depth"] = max(0, min(data["depth"], config.depth_max))
    data["communication"] = max(0, min(data["communication"], config.communication_max))
    data["overall"] = max(0, min(data.get("overall", 0), config.overall_max))
    return data


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_qa_pair(role: str, difficulty: str, topic: str = "") -> dict:
    """Generate a single Q&A pair. Results are cached when enabled."""
    cache_key = _hash_key("qa", role, difficulty, topic)
    cached = _cache_get(cache_key)
    if cached:
        return cached

    prompt = build_qa_prompt(role, difficulty, topic)
    raw = call_llm(prompt, system="You are an expert technical interviewer. Be precise and thorough.")

    question = ""
    answer = ""
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("QUESTION:"):
            question = stripped.split(":", 1)[1].strip()
        elif stripped.upper().startswith("ANSWER:"):
            answer = stripped.split(":", 1)[1].strip()

    result = {"question": question or "No question generated.", "answer": answer or "No answer generated."}
    _cache_set(cache_key, result)
    return result


def generate_multiple_qa_pairs(role: str, difficulty: str, count: int, topic: str = "") -> list:
    """Generate multiple Q&A pairs sequentially."""
    items = []
    for i in range(count):
        logger.info("Generating Q&A %d/%d for role=%s difficulty=%s", i + 1, count, role, difficulty)
        # Vary the cache key by index so we don't get duplicates
        qa = generate_qa_pair(role, difficulty, f"{topic}#{i}" if topic else "")
        items.append(qa)
    return items


def evaluate_answer(question: str, answer: str) -> dict:
    """Score a candidate answer. Results are cached."""
    cache_key = _hash_key("eval", question, answer)
    cached = _cache_get(cache_key)
    if cached:
        return dict(cached)

    prompt = build_eval_prompt(question, answer)
    raw = call_llm(prompt)
    scores = _parse_json(raw, {"accuracy": 0, "depth": 0, "communication": 0, "overall": 0})
    scores = _validate_scores(scores)
    _cache_set(cache_key, dict(scores))
    return scores


def coach_answer(question: str, user_answer: str, scores: dict) -> dict:
    """Generate coaching feedback including model answer."""
    prompt = build_coach_prompt(question, user_answer, scores)
    raw = call_llm(prompt, system="You are an encouraging, expert interview coach.")
    fallback = {
        "summary": "Unable to generate feedback. Please try again.",
        "strengths": [],
        "improvements": [],
        "model_answer": "",
    }
    feedback = _parse_json(raw, fallback)
    return {
        "summary": feedback.get("summary", ""),
        "strengths": feedback.get("strengths", []) or [],
        "improvements": feedback.get("improvements", []) or [],
        "model_answer": feedback.get("model_answer", ""),
    }
