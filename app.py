"""Flask application for the Interview Practice platform.

Provides endpoints for generating Q&A pairs, evaluating answers,
coaching with feedback, session management, and serving the UI.
"""

import json
import logging

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from config import config
from qa_generator import (
    coach_answer,
    evaluate_answer,
    generate_multiple_qa_pairs,
)
from utils import RateLimiter, session_manager, setup_logging

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
logger = setup_logging()
rate_limiter = RateLimiter(config.rate_limit)

app = Flask(__name__)
app.secret_key = config.secret_key
CORS(app, origins=config.cors_origins)


# ---------------------------------------------------------------------------
# Request hooks
# ---------------------------------------------------------------------------
@app.before_request
def log_request():
    logger.info("%s %s from %s", request.method, request.path, request.remote_addr)


@app.errorhandler(400)
def bad_request(err):
    return jsonify({"error": "Bad request", "detail": str(err)}), 400


@app.errorhandler(404)
def not_found(err):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(err):
    logger.exception("Unhandled exception")
    return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    """Serve the main interview practice UI."""
    return render_template("index.html")


# --- Q&A Generation ---

@app.route("/generate_qa", methods=["POST"])
@rate_limiter.middleware()
def generate_qa():
    data = request.get_json(silent=True) or {}

    role = data.get("role", "Software Engineer")
    difficulty = data.get("difficulty", "medium")
    topic = data.get("topic", "")
    count_raw = data.get("count", 1)

    try:
        count = int(count_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "'count' must be an integer"}), 400

    if count < 1:
        return jsonify({"error": "'count' must be >= 1"}), 400
    if count > config.max_qa_count:
        return jsonify({"error": f"'count' cannot exceed {config.max_qa_count}"}), 400

    logger.info("Generating %d Q&A for role=%r difficulty=%r topic=%r", count, role, difficulty, topic)

    try:
        items = generate_multiple_qa_pairs(role, difficulty, count, topic)
    except Exception as exc:
        logger.exception("Q&A generation failed")
        return jsonify({"error": "LLM generation failed. Is Ollama running?", "detail": str(exc)}), 502

    return jsonify({
        "role": role,
        "difficulty": difficulty,
        "topic": topic,
        "count": count,
        "items": items,
    })


# --- Evaluation ---

@app.route("/evaluate_answer", methods=["POST"])
@rate_limiter.middleware()
def evaluate_answer_route():
    data = request.get_json(silent=True) or {}

    question = data.get("question", "").strip()
    answer = data.get("answer", "").strip()

    if not question or not answer:
        return jsonify({"error": "Both 'question' and 'answer' are required"}), 400

    try:
        scores = evaluate_answer(question, answer)
    except Exception as exc:
        logger.exception("Evaluation failed")
        return jsonify({"error": "Evaluation failed. Is Ollama running?", "detail": str(exc)}), 502

    return jsonify(scores)


# --- Coaching ---

@app.route("/coach", methods=["POST"])
@rate_limiter.middleware()
def coach_route():
    data = request.get_json(silent=True) or {}

    question = data.get("question", "").strip()
    answer = data.get("answer", "").strip()
    session_id = data.get("session_id", "")

    if not question or not answer:
        return jsonify({"error": "Both 'question' and 'answer' are required"}), 400

    try:
        scores = evaluate_answer(question, answer)
        feedback = coach_answer(question, answer, scores)
    except Exception as exc:
        logger.exception("Coaching failed")
        return jsonify({"error": "Coaching failed. Is Ollama running?", "detail": str(exc)}), 502

    # Save to session if provided
    if session_id:
        try:
            session_manager.add_entry(session_id, {
                "question": question,
                "answer": answer,
                "scores": scores,
                "feedback": feedback,
            })
        except ValueError:
            pass  # session may have been deleted

    return jsonify({
        "scores": scores,
        "feedback": feedback,
    })


# --- Session Management ---

@app.route("/session/create", methods=["POST"])
def create_session():
    sid = session_manager.create()
    return jsonify({"session_id": sid})


@app.route("/session/<session_id>", methods=["GET"])
def get_session(session_id):
    data = session_manager.load(session_id)
    if data is None:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(data)


@app.route("/session/<session_id>/history", methods=["GET"])
def get_history(session_id):
    history = session_manager.get_history(session_id)
    return jsonify({"session_id": session_id, "history": history})


@app.route("/sessions", methods=["GET"])
def list_sessions():
    sessions = session_manager.list_sessions()
    return jsonify({"sessions": sessions})


@app.route("/session/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    import os
    path = session_manager._path(session_id)
    if os.path.exists(path):
        os.remove(path)
        return jsonify({"deleted": True})
    return jsonify({"error": "Session not found"}), 404


# --- Health ---

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "model": config.ollama_model,
        "version": "2.0.0",
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting Interview Practice server on http://127.0.0.1:5000")
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule}  {','.join(sorted(rule.methods - {'OPTIONS', 'HEAD'}))}")
    app.run(debug=config.debug, host="0.0.0.0", port=5000)
