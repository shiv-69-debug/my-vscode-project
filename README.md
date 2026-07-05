# 🎯 Interview Practice — AI-Powered Mock Interviews

An intelligent interview preparation platform that generates role-specific
technical questions, evaluates your answers, and provides personalised coaching
feedback — all powered by local LLMs via [Ollama](https://ollama.com).

## ✨ Features

- **🔮 Smart Q&A Generation** — Generate tailored interview questions for any
  role (Python Developer, DevOps, Frontend…) at any difficulty level.
- **📊 Multi-Dimensional Scoring** — Answers scored on accuracy (0–4), depth
  (0–3), and communication (0–3) by a senior-interviewer persona.
- **🎓 Coaching Feedback** — Get summarised strengths, actionable improvements,
  and a polished model answer after every evaluation.
- **🕰️ Session History** — Every session is saved so you can track your
  progress over time.
- **🌙 Dark & Light Mode** — Toggle theme; preference persists across visits.
- **⚡ Rate Limiting** — Protects the API from abuse.
- **🩺 Health Check** — `/health` endpoint for monitoring.
- **🐳 Docker Ready** — One-command deploy with Docker Compose.
- **🧪 Tested** — Comprehensive pytest suite for core logic and API routes.

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) installed and running
- Pull the model: `ollama pull qwen2:0.5b` (or set `OLLAMA_MODEL` env var)

### Local Development

```bash
# Clone & enter the repo
git clone https://github.com/shiv-69-debug/my-vscode-project.git
cd my-vscode-project

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Visit **http://127.0.0.1:5000**

### Docker

```bash
docker compose up --build
```

The app will be available at http://localhost:5000. Ollama must be running on
the host; the compose file uses `host.docker.internal` to access it.

## 📋 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves the interview practice UI |
| `POST` | `/generate_qa` | Generate Q&A pairs |
| `POST` | `/evaluate_answer` | Score an answer |
| `POST` | `/coach` | Score + coaching feedback |
| `POST` | `/session/create` | Create a new session |
| `GET` | `/session/<id>` | Get session details |
| `GET` | `/session/<id>/history` | Get session history |
| `GET` | `/sessions` | List all sessions |
| `DELETE` | `/session/<id>` | Delete a session |
| `GET` | `/health` | Health check |

### Example: Generate a question

```bash
curl -X POST http://localhost:5000/generate_qa \
  -H "Content-Type: application/json" \
  -d '{"role":"Python Developer","difficulty":"medium","count":1}'
```

### Example: Evaluate an answer

```bash
curl -X POST http://localhost:5000/coach \
  -H "Content-Type: application/json" \
  -d '{"question":"What is a decorator?","answer":"A function wrapper"}'
```

## ⚙️ Configuration

All settings are controlled via environment variables (or a `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `qwen2:0.5b` | Model to use for generation |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server address |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |
| `SECRET_KEY` | `change-me-in-production` | Flask secret key |
| `MAX_QA_COUNT` | `10` | Max questions per request |
| `CACHE_ENABLED` | `false` | Enable in-memory result caching |
| `CACHE_TTL` | `3600` | Cache TTL in seconds |
| `RATE_LIMIT` | `100 per minute` | API rate limit |
| `LOG_LEVEL` | `INFO` | Logging level |
| `SESSION_DIR` | `sessions` | Session storage directory |
| `MAX_HISTORY` | `50` | Max history entries per session |

## 🧪 Running Tests

```bash
pip install pytest
pytest
```

## 📁 Project Structure

```
├── app.py                  # Flask application
├── qa_generator.py         # LLM prompts, parsing, scoring, coaching
├── config/
│   └── __init__.py         # Centralised configuration
├── utils/
│   ├── __init__.py
│   ├── logger.py           # Logging setup
│   ├── rate_limiter.py     # IP-based rate limiter
│   └── session.py          # File-based session store
├── tests/
│   ├── test_app.py         # API route tests
│   └── test_qa_generator.py # Core logic tests
├── templates/
│   └── index.html          # Modern responsive UI
├── static/
│   └── app.js              # Client-side logic
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pytest.ini
└── .env                    # Local configuration
```

## 🔧 Production Deployment

For production use, the Docker image runs with **Gunicorn** (2 workers,
120-second timeout for LLM calls). Set a strong `SECRET_KEY`, disable
`FLASK_DEBUG`, and consider mounting a persistent volume for `sessions/`.

```bash
docker compose up -d
```

## 📄 License

MIT
