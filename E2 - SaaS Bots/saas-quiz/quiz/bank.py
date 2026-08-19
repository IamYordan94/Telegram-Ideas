"""QuizDay — question bank loading and rotation.

Bank format (JSON list):
[
  {"q": "Question text?", "options": ["A..", "B..", "C..", "D.."],
   "answer": 0, "explain": "short why"},
  ...
]
"""
import json
from pathlib import Path


def load_bank(banks_dir, filename):
    path = Path(banks_dir) / filename
    if not path.is_file():
        raise FileNotFoundError(f"bank file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError(f"bank {filename} must be a non-empty list")
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"bank {filename} item {i} is not an object")
        for key in ("q", "options", "answer"):
            if key not in item:
                raise ValueError(f"bank {filename} item {i} missing '{key}'")
        if not isinstance(item["options"], list) or len(item["options"]) != 4:
            raise ValueError(f"bank {filename} item {i} needs exactly 4 options")
        if not isinstance(item["answer"], int) or not 0 <= item["answer"] <= 3:
            raise ValueError(f"bank {filename} item {i} answer must be 0-3")
    return data


def next_question(bank, q_index):
    """q_index grows forever; the bank is cycled when exhausted.

    Returns (question, bank_position). Scores key on the global q_index,
    so a second lap through the bank counts as new questions.
    """
    return bank[q_index % len(bank)], q_index % len(bank)
