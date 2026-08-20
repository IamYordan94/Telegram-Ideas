"""Question bank v2 schema, loading, rotation and de-duplication.

A bank is a JSON list of items. Two item types are supported::

    question:
        {"type": "question", "q": "text", "options": ["A..", "B..", "C..", "D.."],
         "answer": 0, "explain": "...", "topic": "..."}

    flashcard:
        {"type": "flashcard", "front": "text", "back": "text",
         "explain": "...", "topic": "..."}

The ``type`` field is required on every item so the two shapes never have to
be guessed from their keys.
"""

import json
from pathlib import Path


def load_bank(banks_dir, filename):
    """Load and validate a bank JSON file, returning its list of items.

    Raises ``FileNotFoundError`` if the file is missing, and ``ValueError``
    with a clear message if the bank is malformed: not a non-empty list, an
    item that is not an object, an unknown item type, a question without
    exactly 4 non-empty options or with an out-of-range ``answer``, or a
    flashcard without ``front``/``back``.
    """
    path = Path(banks_dir) / filename
    if not path.is_file():
        raise FileNotFoundError(f"bank file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"bank {filename} must be a JSON list of items")
    if not data:
        raise ValueError(f"bank {filename} must not be empty")
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"bank {filename} item {i} is not an object")
        itype = item.get("type")
        if itype == "question":
            _validate_question(item, filename, i)
        elif itype == "flashcard":
            _validate_flashcard(item, filename, i)
        else:
            raise ValueError(
                f"bank {filename} item {i} has invalid type {itype!r}; "
                "expected 'question' or 'flashcard'"
            )
    return data


def _validate_question(item, filename, i):
    for key in ("q", "options", "answer"):
        if key not in item:
            raise ValueError(f"bank {filename} item {i} missing '{key}'")
    if not isinstance(item["q"], str) or not item["q"].strip():
        raise ValueError(f"bank {filename} item {i} 'q' must be non-empty text")
    opts = item["options"]
    if not isinstance(opts, list) or len(opts) != 4:
        raise ValueError(f"bank {filename} item {i} needs exactly 4 options")
    if not all(isinstance(o, str) and o.strip() for o in opts):
        raise ValueError(f"bank {filename} item {i} every option must be non-empty text")
    ans = item["answer"]
    # note: bool is a subclass of int, so reject it explicitly
    if isinstance(ans, bool) or not isinstance(ans, int) or not 0 <= ans <= 3:
        raise ValueError(f"bank {filename} item {i} 'answer' must be an int 0-3")
    for key in ("explain", "topic"):
        if key in item and item[key] is not None and not isinstance(item[key], str):
            raise ValueError(f"bank {filename} item {i} '{key}' must be text")


def _validate_flashcard(item, filename, i):
    for key in ("front", "back"):
        if key not in item:
            raise ValueError(f"bank {filename} item {i} missing '{key}'")
        if not isinstance(item[key], str) or not item[key].strip():
            raise ValueError(f"bank {filename} item {i} '{key}' must be non-empty text")
    for key in ("explain", "topic"):
        if key in item and item[key] is not None and not isinstance(item[key], str):
            raise ValueError(f"bank {filename} item {i} '{key}' must be text")


def next_item(bank, q_index):
    """Return the item for a monotonically growing ``q_index``.

    The bank is cycled when exhausted (``q_index`` wraps modulo ``len(bank)``),
    so a second lap through the bank counts as fresh items — matching the
    saas-quiz rotation design. Returns ``(item, position)`` where ``position``
    is the index into the bank.
    """
    if not bank:
        raise ValueError("cannot get next_item from an empty bank")
    position = q_index % len(bank)
    return bank[position], position


def _item_key(item):
    """Identity key for de-duplication: (type, question text) or (type, front)."""
    itype = item.get("type")
    if itype == "question":
        return ("question", item.get("q"))
    if itype == "flashcard":
        return ("flashcard", item.get("front"))
    return None


def dedupe_merge(existing_items, new_items):
    """Merge ``new_items`` into ``existing_items``, skipping text-identical dupes.

    Identity is the question text for questions and the front text for
    flashcards. Items with no recognised identity are treated as unique and
    always appended. Returns ``(merged, added_count, skipped_count)``; the
    input ``existing_items`` list is not mutated.
    """
    merged = list(existing_items)
    seen = {_item_key(it) for it in existing_items}
    seen.discard(None)
    added = 0
    skipped = 0
    for it in new_items:
        key = _item_key(it)
        if key is None:
            merged.append(it)
            added += 1
            continue
        if key in seen:
            skipped += 1
        else:
            seen.add(key)
            merged.append(it)
            added += 1
    return merged, added, skipped
