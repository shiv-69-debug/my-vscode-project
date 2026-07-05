"""Tests for the Flask application."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


class TestHealth:
    def test_health_returns_ok(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["status"] == "ok"


class TestGenerateQA:
    @patch("app.generate_multiple_qa_pairs")
    def test_generate_success(self, mock_gen, client):
        mock_gen.return_value = [{"question": "Q1", "answer": "A1"}]
        res = client.post(
            "/generate_qa",
            data=json.dumps({"role": "Dev", "difficulty": "medium", "count": 1}),
            content_type="application/json",
        )
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["items"][0]["question"] == "Q1"

    def test_generate_invalid_count(self, client):
        res = client.post(
            "/generate_qa",
            data=json.dumps({"count": "abc"}),
            content_type="application/json",
        )
        assert res.status_code == 400

    def test_generate_count_too_high(self, client):
        res = client.post(
            "/generate_qa",
            data=json.dumps({"count": 999}),
            content_type="application/json",
        )
        assert res.status_code == 400


class TestEvaluate:
    @patch("app.evaluate_answer")
    def test_evaluate_success(self, mock_eval, client):
        mock_eval.return_value = {"accuracy": 4, "depth": 3, "communication": 2, "overall": 9}
        res = client.post(
            "/evaluate_answer",
            data=json.dumps({"question": "Q", "answer": "A"}),
            content_type="application/json",
        )
        assert res.status_code == 200

    def test_evaluate_missing_fields(self, client):
        res = client.post(
            "/evaluate_answer",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert res.status_code == 400


class TestCoach:
    @patch("app.evaluate_answer")
    @patch("app.coach_answer")
    def test_coach_success(self, mock_coach, mock_eval, client):
        mock_eval.return_value = {"accuracy": 4, "depth": 3, "communication": 2, "overall": 9}
        mock_coach.return_value = {"summary": "ok", "strengths": [], "improvements": [], "model_answer": "x"}
        res = client.post(
            "/coach",
            data=json.dumps({"question": "Q", "answer": "A"}),
            content_type="application/json",
        )
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "scores" in data
        assert "feedback" in data


class TestSessions:
    def test_create_and_get_session(self, client):
        res = client.post("/session/create")
        assert res.status_code == 200
        sid = json.loads(res.data)["session_id"]

        res2 = client.get(f"/session/{sid}")
        assert res2.status_code == 200

    def test_list_sessions(self, client):
        res = client.get("/sessions")
        assert res.status_code == 200

    def test_delete_session(self, client):
        res = client.post("/session/create")
        sid = json.loads(res.data)["session_id"]
        res2 = client.delete(f"/session/{sid}")
        assert res2.status_code == 200
        assert json.loads(res2.data)["deleted"] is True

    def test_get_nonexistent_session(self, client):
        res = client.get("/session/nonexistent123")
        assert res.status_code == 404
