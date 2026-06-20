from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from qa_generator import generate_multiple_qa_pairs, evaluate_answer, coach_answer

app = Flask(__name__)
CORS(app)  # allow all origins for now (simple for local dev)

@app.before_request
def log_request():
    print("Incoming:", request.method, request.path)
   
MAX_COUNT = 10

@app.route("/generate_qa", methods=["POST"])
def generate_qa():
    data = request.get_json()

    role = data.get("role")
    difficulty = data.get("difficulty")
    count = data.get("count", 5)

    try:
        count = int(count)
    except (TypeError, ValueError):
        return jsonify({"error": "count must be an integer"}), 400

    if count <= 0:
        return jsonify({"error": "count must be > 0"}), 400
    
    if count > MAX_COUNT:
        return jsonify({"error": f"count too large, max is {MAX_COUNT}"}), 400

    items = generate_multiple_qa_pairs(role, difficulty, count)

    return jsonify({
        "role": role,
        "difficulty": difficulty,
        "items": items
    })

@app.route("/evaluate_answer", methods=["POST"])
def evaluate_answer_route():
    data = request.get_json()

    question = data.get("question")
    answer = data.get("answer")

    if not question or not answer:
        return jsonify({"error": "question and answer are required"}), 400

    scores = evaluate_answer(question, answer)

    return jsonify(scores)

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")    

@app.route("/coach", methods=["POST"])
def coach_route():
    data = request.get_json()

    question = data.get("question")
    answer = data.get("answer")

    if not question or not answer:
        return jsonify({"error": "question and answer are required"}), 400

    scores = evaluate_answer(question, answer)
    feedback = coach_answer(question, answer, scores)

    return jsonify({
        "scores": scores,
        "feedback": feedback
    })

if __name__ == "__main__":
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(rule, rule.methods)
    app.run(debug=True)