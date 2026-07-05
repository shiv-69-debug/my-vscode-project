/** Interview Practice — Client-side application logic. */

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
const state = {
  currentQuestion: null,
  currentAnswer: null,
  sessionId: null,
  history: [],
};

// ---------------------------------------------------------------------------
// DOM refs
// ---------------------------------------------------------------------------
const $ = (sel) => document.querySelector(sel);
const dom = {
  roleInput: $("#roleInput"),
  difficultyInput: $("#difficultyInput"),
  topicInput: $("#topicInput"),
  generateBtn: $("#generateBtn"),
  questionCard: $("#questionCard"),
  questionText: $("#questionText"),
  answerInput: $("#answerInput"),
  evaluateBtn: $("#evaluateBtn"),
  resultsCard: $("#resultsCard"),
  scoresGrid: $("#scoresGrid"),
  feedbackContent: $("#feedbackContent"),
  loadingOverlay: $("#loadingOverlay"),
  progressBar: $("#progressBar"),
  progressFill: $("#progressFill"),
  historyList: $("#historyList"),
  refreshHistoryBtn: $("#refreshHistoryBtn"),
  newSessionBtn: $("#newSessionBtn"),
  themeToggle: $("#themeToggle"),
  toastContainer: $("#toastContainer"),
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const API_BASE = "";

async function api(method, path, body = null) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API_BASE + path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

function toast(msg, duration = 3000) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = msg;
  dom.toastContainer.appendChild(el);
  setTimeout(() => el.remove(), duration);
}

function showLoading(show) {
  dom.loadingOverlay.classList.toggle("active", show);
  dom.evaluateBtn.disabled = show;
  dom.generateBtn.disabled = show;
}

function setProgress(percent) {
  dom.progressBar.classList.toggle("hidden", percent <= 0 || percent >= 100);
  dom.progressFill.style.width = `${Math.min(100, Math.max(0, percent))}%`;
}

// ---------------------------------------------------------------------------
// Session management
// ---------------------------------------------------------------------------
async function initSession() {
  try {
    const data = await api("POST", "/session/create");
    state.sessionId = data.session_id;
    console.log("Session created:", state.sessionId);
    await loadHistory();
  } catch {
    toast("Could not create session. Backend may be offline.");
  }
}

async function loadHistory() {
  try {
    const data = await api("GET", "/sessions");
    const sessions = data.sessions || [];
    state.history = sessions;
    renderHistory();
  } catch {
    dom.historyList.innerHTML = "<p style='color:var(--text-muted)'>Could not load history.</p>";
  }
}

function renderHistory() {
  if (state.history.length === 0) {
    dom.historyList.innerHTML = "<p style='color:var(--text-muted);font-size:0.8rem;'>No past sessions.</p>";
    return;
  }
  dom.historyList.innerHTML = state.history
    .map(
      (s) => `
      <div class="history-item ${s.id === state.sessionId ? "active" : ""}" data-sid="${s.id}">
        <div>${s.id}</div>
        <div class="hist-date">${new Date(s.created_at).toLocaleDateString()} · ${s.count} entries</div>
      </div>`
    )
    .join("");

  dom.historyList.querySelectorAll(".history-item").forEach((el) => {
    el.addEventListener("click", async () => {
      state.sessionId = el.dataset.sid;
      toast(`Switched to session ${state.sessionId}`);
      renderHistory();
    });
  });
}

// ---------------------------------------------------------------------------
// Theme toggle
// ---------------------------------------------------------------------------
const savedTheme = localStorage.getItem("interview-theme");
if (savedTheme === "light") document.body.classList.add("light");

dom.themeToggle.addEventListener("click", () => {
  document.body.classList.toggle("light");
  const newTheme = document.body.classList.contains("light") ? "light" : "dark";
  localStorage.setItem("interview-theme", newTheme);
});

// ---------------------------------------------------------------------------
// Generate QA
// ---------------------------------------------------------------------------
dom.generateBtn.addEventListener("click", async () => {
  dom.resultsCard.classList.add("hidden");
  dom.feedbackContent.innerHTML = "";
  dom.scoresGrid.innerHTML = "";
  dom.answerInput.value = "";

  if (!state.sessionId) await initSession();

  const role = dom.roleInput.value.trim() || "Software Engineer";
  const difficulty = dom.difficultyInput.value;
  const topic = dom.topicInput.value.trim();

  showLoading(true);
  setProgress(30);

  try {
    const data = await api("POST", "/generate_qa", {
      role,
      difficulty,
      topic: topic || undefined,
      count: 1,
    });

    setProgress(100);
    const item = data.items?.[0];
    if (!item) throw new Error("No question returned from server.");

    state.currentQuestion = item.question;
    state.currentAnswer = item.answer;
    dom.questionText.textContent = item.question;
    dom.questionCard.classList.remove("hidden");
    dom.answerInput.focus();
    toast("Question generated!");
  } catch (e) {
    console.error(e);
    dom.questionText.textContent = "Error: " + e.message;
    toast("Failed to generate question. Is Ollama running?");
  } finally {
    showLoading(false);
    setTimeout(() => setProgress(0), 600);
  }
});

// ---------------------------------------------------------------------------
// Evaluate & Coach
// ---------------------------------------------------------------------------
dom.evaluateBtn.addEventListener("click", async () => {
  dom.resultsCard.classList.add("hidden");
  dom.feedbackContent.innerHTML = "";
  dom.scoresGrid.innerHTML = "";

  if (!state.currentQuestion) {
    toast("Generate a question first.");
    return;
  }

  const userAnswer = dom.answerInput.value.trim();
  if (!userAnswer) {
    toast("Please type an answer before evaluating.");
    return;
  }

  showLoading(true);

  try {
    const data = await api("POST", "/coach", {
      question: state.currentQuestion,
      answer: userAnswer,
      session_id: state.sessionId,
    });

    const { scores, feedback } = data;

    // Render scores
    const scoreCards = [
      { label: "Accuracy", value: scores.accuracy, max: 4, cls: scores.accuracy >= 3 ? "high" : scores.accuracy >= 2 ? "mid" : "low" },
      { label: "Depth", value: scores.depth, max: 3, cls: scores.depth >= 2 ? "high" : scores.depth >= 1 ? "mid" : "low" },
      { label: "Communication", value: scores.communication, max: 3, cls: scores.communication >= 2 ? "high" : scores.communication >= 1 ? "mid" : "low" },
      { label: "Overall", value: scores.overall, max: 10, cls: scores.overall >= 7 ? "high" : scores.overall >= 4 ? "mid" : "low" },
    ];
    dom.scoresGrid.innerHTML = scoreCards
      .map(
        (s) => `
        <div class="score-card ${s.cls}">
          <div class="score-value">${s.value}/${s.max}</div>
          <div class="score-label">${s.label}</div>
        </div>`
      )
      .join("");

    // Render feedback
    dom.feedbackContent.innerHTML = `
      <div class="feedback-section">
        <h4>&#x1F4DD; Summary</h4>
        <p>${escapeHtml(feedback.summary || "No summary.")}</p>
      </div>
      ${feedback.strengths?.length ? `
        <div class="feedback-section">
          <h4>&#x2705; Strengths</h4>
          <ul>${feedback.strengths.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ul>
        </div>` : ""}
      ${feedback.improvements?.length ? `
        <div class="feedback-section">
          <h4>&#x1F4AA; Areas to Improve</h4>
          <ul>${feedback.improvements.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ul>
        </div>` : ""}
      ${feedback.model_answer ? `
        <div class="feedback-section">
          <h4>&#x1F3AF; Model Answer</h4>
          <div class="model-answer-box">${escapeHtml(feedback.model_answer)}</div>
        </div>` : ""}
    `;

    dom.resultsCard.classList.remove("hidden");
    toast("Evaluation complete!");
    await loadHistory();
  } catch (e) {
    console.error(e);
    toast("Evaluation failed. Is Ollama running?");
  } finally {
    showLoading(false);
  }
});

// ---------------------------------------------------------------------------
// Sidebar actions
// ---------------------------------------------------------------------------
dom.refreshHistoryBtn.addEventListener("click", loadHistory);

dom.newSessionBtn.addEventListener("click", async () => {
  await initSession();
  dom.questionCard.classList.add("hidden");
  dom.resultsCard.classList.add("hidden");
  dom.answerInput.value = "";
  state.currentQuestion = null;
  toast("New session created!");
});

// ---------------------------------------------------------------------------
// Keyboard shortcut
// ---------------------------------------------------------------------------
document.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.key === "Enter" && !dom.evaluateBtn.disabled) {
    dom.evaluateBtn.click();
  }
});

// ---------------------------------------------------------------------------
// Util
// ---------------------------------------------------------------------------
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
initSession();
