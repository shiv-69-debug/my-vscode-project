const questionBox = document.getElementById('questionBox');
const answerInput = document.getElementById('answerInput');
const scoresBox = document.getElementById('scoresBox');
const roleInput = document.getElementById('roleInput');
const difficultyInput = document.getElementById('difficultyInput');
const generateBtn = document.getElementById('generateBtn');
const evaluateBtn = document.getElementById('evaluateBtn');

let currentQuestion = null;

generateBtn.addEventListener('click', async () => {
  scoresBox.innerHTML = '';
  answerInput.value = '';

  const role = roleInput.value || 'Software Engineer';
  const difficulty = difficultyInput.value || 'medium';

  try {
    const res = await fetch('http://127.0.0.1:5000/generate_qa', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        role: role,
        difficulty: difficulty,
        count: 1
      })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      questionBox.textContent = 'Error generating question: ' + (err.error || res.statusText);
      return;
    }

    const data = await res.json();
    const item = data.items && data.items[0];
    if (!item) {
      questionBox.textContent = 'No question received.';
      return;
    }

    currentQuestion = item.question;
    questionBox.textContent = currentQuestion;
  } catch (e) {
    console.error(e);
    questionBox.textContent = 'Network error while generating question.';
  }
});

evaluateBtn.addEventListener('click', async () => {
  scoresBox.innerHTML = '';

  if (!currentQuestion) {
    scoresBox.textContent = 'Generate a question first.';
    return;
  }

  const userAnswer = answerInput.value.trim();
  if (!userAnswer) {
    scoresBox.textContent = 'Please type an answer before evaluating.';
    return;
  }

  try {
    const res = await fetch('http://127.0.0.1:5000/coach', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        question: currentQuestion,
        answer: userAnswer
      })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      scoresBox.textContent = 'Error coaching: ' + (err.error || res.statusText);
      return;
    }

    const data = await res.json();
    const scores = data.scores || {};
    const fb = data.feedback || {};

    scoresBox.innerHTML = `
      <div>Accuracy: ${scores.accuracy}/4</div>
      <div>Depth: ${scores.depth}/3</div>
      <div>Communication: ${scores.communication}/3</div>
      <div><strong>Overall: ${scores.overall}/10</strong></div>
      <hr/>
      <div><strong>Summary:</strong> ${fb.summary || ''}</div>
      <div><strong>Strengths:</strong></div>
      <ul>
        ${(fb.strengths || []).map(s => `<li>${s}</li>`).join('')}
      </ul>
      <div><strong>Improvements:</strong></div>
      <ul>
        ${(fb.improvements || []).map(s => `<li>${s}</li>`).join('')}
      </ul>
      <div><strong>Model answer:</strong></div>
      <pre>${fb.model_answer || ''}</pre>
    `;
  } catch (e) {
    console.error(e);
    scoresBox.textContent = 'Network error while coaching.';
  }
});