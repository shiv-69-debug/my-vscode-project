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

def save_questions_to_file(questions, filename):
    with open(filename, "w", encoding="utf-8") as f:
        for i, q in enumerate(questions, start=1):
            f.write(f"Q{i}: {q}\n")

def save_data_to_json(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def make_json_filename(role, difficulty):
    safe_role = role.lower().replace(" ", "_")
    safe_diff = difficulty.lower().replace(" ", "_")
    return f"{safe_role}_{safe_diff}_questions.json"  

role = input("Enter role: ")

print("Choose difficulty:")
print("1. Easy")
print("2. Medium")
print("3. Hard")
choice = input("Enter 1, 2, or 3: ")

if choice == "1":
    difficulty = "Easy"
elif choice == "2":
    difficulty = "Medium"
elif choice == "3":
    difficulty = "Hard"
else:
    print("Invalid choice, defaulting to Medium")
    difficulty = "Medium"

while True:
    try:
        count = int(input("How many questions do you want? "))
        if count > 0:
            break
        else:
            print("Please enter a number greater than 0.")
    except ValueError:
        print("Please enter a valid whole number.")

            
items = generate_multiple_qa_pairs(role, difficulty, count)

for i, qa in enumerate(items, start=1):
    print(f"Q{i}: {qa['question']}")
    print(f"A{i}: {qa['answer']}")
    print()

data = {
    "role": role,
    "difficulty": difficulty,
    "items": items  # list of {"question": ..., "answer": ...}
}

json_filename = make_json_filename(role, difficulty)
save_data_to_json(data, json_filename)
print(f"Saved Q+A pairs to {json_filename}")


