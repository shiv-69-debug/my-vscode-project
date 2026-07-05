"""Tests for the qa_generator module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from qa_generator import (
    _cache_get,
    _cache_set,
    _parse_json,
    _validate_scores,
    build_eval_prompt,
    build_qa_prompt,
    call_llm,
    coach_answer,
    evaluate_answer,
    generate_multiple_qa_pairs,
    generate_qa_pair,
)


class TestPromptBuilders:
    def test_build_qa_prompt_includes_role_and_difficulty(self):
        prompt = build_qa_prompt("DevOps", "hard")
        assert "DevOps" in prompt
        assert "hard" in prompt
        assert "QUESTION:" in prompt
        assert "ANSWER:" in prompt

    def test_build_qa_prompt_with_topic(self):
        prompt = build_qa_prompt("FE Dev", "easy", "React Hooks")
        assert "React Hooks" in prompt

    def test_build_eval_prompt_includes_question_and_answer(self):
        prompt = build_eval_prompt("What is Python?", "A snake")
        assert "What is Python?" in prompt
        assert "A snake" in prompt
        assert '"accuracy"' in prompt


class TestParseJson:
    def test_parses_valid_json(self):
        assert _parse_json('{"a":1}', {}) == {"a": 1}

    def test_strips_markdown_fences(self):
        raw = '```json\n{"x":2}\n```'
        assert _parse_json(raw, {}) == {"x": 2}

    def test_returns_fallback_on_invalid(self):
        assert _parse_json("not json", {"fallback": True}) == {"fallback": True}

    def test_strips_fences_without_lang_tag(self):
        raw = '```\n{"y":3}\n```'
        assert _parse_json(raw, {}) == {"y": 3}


class TestValidateScores:
    def test_clamps_low_values(self):
        data = _validate_scores({"accuracy": -5, "depth": -10, "communication": -1, "overall": -99})
        assert data["accuracy"] == 0
        assert data["depth"] == 0
        assert data["communication"] == 0
        assert data["overall"] == 0

    def test_clamps_high_values(self):
        data = _validate_scores({"accuracy": 99, "depth": 99, "communication": 99, "overall": 999})
        assert data["accuracy"] == 4
        assert data["depth"] == 3
        assert data["communication"] == 3
        assert data["overall"] == 10

    def test_fills_missing_keys(self):
        data = _validate_scores({})
        assert data == {"accuracy": 0, "depth": 0, "communication": 0, "overall": 0}


class TestCache:
    def setup_method(self):
        # Clear any stale cache entries
        import qa_generator
        qa_generator._cache.clear()

    @patch("qa_generator.config.cache_enabled", True)
    def test_cache_set_and_get(self):
        _cache_set("test_key", {"val": 42})
        assert _cache_get("test_key") == {"val": 42}

    @patch("qa_generator.config.cache_enabled", True)
    @patch("qa_generator.config.cache_ttl_seconds", 0)
    def test_expired_cache_returns_none(self):
        _cache_set("test_key", {"val": 42})
        assert _cache_get("test_key") is None

    @patch("qa_generator.config.cache_enabled", False)
    def test_disabled_cache_returns_none(self):
        _cache_set("test_key", {"val": 1})
        assert _cache_get("test_key") is None


class TestCallLLM:
    @patch("qa_generator.ollama.chat")
    def test_call_llm_returns_content(self, mock_chat):
        mock_chat.return_value.message.content = "Hello world  "
        result = call_llm("test prompt")
        assert result == "Hello world"

    @patch("qa_generator.ollama.chat")
    def test_call_llm_with_system(self, mock_chat):
        mock_chat.return_value.message.content = "ok"
        result = call_llm("prompt", system="You are helpful.")
        assert result == "ok"
        assert mock_chat.call_args[1]["messages"][0]["role"] == "system"


class TestGenerateQA:
    @patch("qa_generator.call_llm")
    def test_generate_qa_pair(self, mock_llm):
        mock_llm.return_value = "QUESTION: What is Python?\nANSWER: A programming language."
        result = generate_qa_pair("Dev", "easy")
        assert result["question"] == "What is Python?"
        assert result["answer"] == "A programming language."

    @patch("qa_generator.call_llm")
    def test_generate_multiple_pairs(self, mock_llm):
        mock_llm.return_value = "QUESTION: Q?\nANSWER: A."
        items = generate_multiple_qa_pairs("Dev", "easy", 3)
        assert len(items) == 3
        assert items[0]["question"] == "Q?"


class TestEvaluateAnswer:
    @patch("qa_generator.call_llm")
    def test_evaluate_answer(self, mock_llm):
        mock_llm.return_value = '{"accuracy":4,"depth":3,"communication":2,"overall":9}'
        scores = evaluate_answer("Q?", "A!")
        assert scores["accuracy"] == 4
        assert scores["depth"] == 3
        assert scores["overall"] == 9

    @patch("qa_generator.call_llm")
    def test_evaluate_answer_fallback_on_bad_json(self, mock_llm):
        mock_llm.return_value = "not json at all"
        scores = evaluate_answer("Q?", "A!")
        assert scores == {"accuracy": 0, "depth": 0, "communication": 0, "overall": 0}


class TestCoachAnswer:
    @patch("qa_generator.call_llm")
    def test_coach_answer(self, mock_llm):
        mock_llm.return_value = json.dumps({
            "summary": "Good job.",
            "strengths": ["clear"],
            "improvements": ["add depth"],
            "model_answer": "Better answer here.",
        })
        feedback = coach_answer("Q?", "A!", {"accuracy": 3, "depth": 2, "communication": 3, "overall": 8})
        assert feedback["summary"] == "Good job."
        assert feedback["strengths"] == ["clear"]
        assert feedback["model_answer"] == "Better answer here."

    @patch("qa_generator.call_llm")
    def test_coach_answer_fallback(self, mock_llm):
        mock_llm.return_value = "gibberish"
        feedback = coach_answer("Q?", "A!", {"accuracy": 0})
        assert feedback["summary"] != ""
        assert feedback["strengths"] == []
