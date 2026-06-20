import ollama
import json


       
def build_prompt(role, difficulty):
    prompt = (
        "You are a senior interviewer.\n"
        f"Role: {role}\n"
        f"Difficulty: {difficulty}\n"
        "Task: Create one interview question AND its ideal answer.\n"
        "Output format (very important):\n"
        "Question: <write the question here>\n"
        "Answer: <write the answer here>\n"
        "Rules:\n"
        "1. Do not add any text before 'Question:' or after the answer line.\n"
        "2. Do not use bullet points or markdown.\n"
        "3. Keep the answer concise but technically correct."
    )
    return prompt



def call_llm(prompt):
    response = ollama.chat(
        model="qwen2:0.5b",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.message.content.strip()

def generate_qa_pair(role, difficulty):
    prompt = build_prompt(role, difficulty)
    text = call_llm(prompt)

    # Expected format:
    # Question: ...
    # Answer: ...
    question = ""
    answer = ""

    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith("question:"):
            question = line[len("Question:"):].strip()
        elif line.lower().startswith("answer:"):
            answer = line[len("Answer:"):].strip()

    return {
        "question": question,
        "answer": answer
    }

def generate_multiple_qa_pairs(role, difficulty, count):
    items = []
    for _ in range(count):
        qa = generate_qa_pair(role, difficulty)
        items.append(qa)
    return items

def coach_answer(question, user_answer, scores):
    prompt = (
        "You are an interview coach.\n"
        "You will see an interview question, the candidate's answer, and an evaluation of that answer.\n"
        "Your job is to give short, practical feedback and a stronger model answer.\n\n"
        "Question:\n"
        f"{question}\n\n"
        "Candidate answer:\n"
        f"{user_answer}\n\n"
        "Scores:\n"
        f"accuracy: {scores.get('accuracy')}\n"
        f"depth: {scores.get('depth')}\n"
        f"communication: {scores.get('communication')}\n"
        f"overall: {scores.get('overall')}\n\n"
        "Respond in JSON only, with this structure:\n"
        "{\n"
        "  \"summary\": \"short one-sentence summary of how they did\",\n"
        "  \"strengths\": [\"bullet point strength 1\", \"bullet point strength 2\"],\n"
        "  \"improvements\": [\"bullet point improvement 1\", \"bullet point improvement 2\"],\n"
        "  \"model_answer\": \"a concise, high-quality answer to the question\"\n"
        "}\n"
    )

    raw = call_llm(prompt)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "summary": "Unable to parse feedback.",
            "strengths": [],
            "improvements": [],
            "model_answer": ""
        }

    return {
        "summary": data.get("summary", ""),
        "strengths": data.get("strengths", []),
        "improvements": data.get("improvements", []),
        "model_answer": data.get("model_answer", "")
    }

def evaluate_answer(question, answer):
    prompt = (
        "You are a senior technical interviewer.\n"
        "Your task is to evaluate a candidate's answer to an interview question.\n"
        "Rate the answer on three criteria and return only valid JSON.\n\n"
        "Question:\n"
        f"{question}\n\n"
        "Candidate answer:\n"
        f"{answer}\n\n"
        "Scoring rules:\n"
        "- accuracy: 0-4 (0 = completely wrong, 4 = fully correct and precise)\n"
        "- depth: 0-3 (0 = very shallow, 3 = excellent depth and insight)\n"
        "- communication: 0-3 (0 = very unclear, 3 = very clear and well-structured)\n\n"
        "Output format (must be valid JSON, no extra text):\n"
        "{\n"
        "  \"accuracy\": <integer 0-4>,\n"
        "  \"depth\": <integer 0-3>,\n"
        "  \"communication\": <integer 0-3>,\n"
        "  \"overall\": <integer 0-10>\n"
        "}\n\n"
        "Rules:\n"
        "1. overall = accuracy + depth + communication.\n"
        "2. Do not include explanations or comments.\n"
        "3. Do not include any keys other than accuracy, depth, communication, overall.\n"
    )

    raw = call_llm(prompt)

    # Try to parse JSON safely
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: return something safe if model output isn't valid JSON
        return {
            "accuracy": 0,
            "depth": 0,
            "communication": 0,
            "overall": 0
        }

    # Basic type/field checks
    for key in ["accuracy", "depth", "communication", "overall"]:
        if key not in data or not isinstance(data[key], int):
            data[key] = 0

    return data

