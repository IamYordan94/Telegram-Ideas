"""Typed-notes content intake parser and bank preview export.

``parse_typed_notes`` turns a plain-text training document into bank items.
Each non-blank line is one item, with fields separated by ``|``::

    Q: the question text | A) optA | B) optB | C) optC | D) optD | answer: A | topic: optional | explain: optional
    CARD: the front text | BACK: the back text | topic: optional

The parser is tolerant of whitespace and key case (``q:``, ``ANSWER:``,
``Topic:``, ``a)`` all work) but STRICT about correctness: any malformed line
raises ``ValueError`` carrying its 1-based line number, so training content is
never silently dropped. The ``|`` character cannot appear inside field text.
"""

import json
import re

_OPTION_RE = re.compile(r"^([A-Da-d])\s*[).:]\s*(.*)$")
_ANSWER_LETTER = {"A": 0, "B": 1, "C": 2, "D": 3}
_OPTION_ORDER = ("A", "B", "C", "D")


def parse_typed_notes(text):
    """Parse typed-notes text into a list of bank items.

    Blank lines are skipped. Every other line must start with ``Q:`` (question)
    or ``CARD:`` (flashcard) and be fully well-formed, otherwise ``ValueError``
    is raised with the offending line number.
    """
    items = []
    for lineno, raw in enumerate(str(text).splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        head = parts[0].upper()
        if head.startswith("Q:"):
            items.append(_parse_question(parts, lineno))
        elif head.startswith("CARD:"):
            items.append(_parse_flashcard(parts, lineno))
        else:
            raise ValueError(
                f"line {lineno}: unrecognized item (expected 'Q:' or 'CARD:' prefix): {raw!r}"
            )
    return items


def _parse_answer(raw, lineno):
    up = raw.upper()
    if up in _ANSWER_LETTER:
        return _ANSWER_LETTER[up]
    if raw.isdigit() and 0 <= int(raw) <= 3:
        return int(raw)
    raise ValueError(f"line {lineno}: invalid answer {raw!r} (expected A-D or 0-3)")


def _parse_question(parts, lineno):
    head = parts[0]
    if ":" not in head:
        raise ValueError(f"line {lineno}: question is missing ':' after 'Q'")
    qtext = head.split(":", 1)[1].strip()
    if not qtext:
        raise ValueError(f"line {lineno}: empty question text")

    options = {}
    answer = None
    topic = None
    explain = None
    for part in parts[1:]:
        part = part.strip()
        if not part:
            continue
        low = part.lower()
        if low.startswith("answer:"):
            if answer is not None:
                raise ValueError(f"line {lineno}: duplicate 'answer' field")
            answer = _parse_answer(part.split(":", 1)[1].strip(), lineno)
        elif low.startswith("topic:"):
            if topic is not None:
                raise ValueError(f"line {lineno}: duplicate 'topic' field")
            topic = part.split(":", 1)[1].strip() or None
        elif low.startswith("explain:"):
            if explain is not None:
                raise ValueError(f"line {lineno}: duplicate 'explain' field")
            explain = part.split(":", 1)[1].strip() or None
        else:
            m = _OPTION_RE.match(part)
            if m and m.group(1).upper() in _OPTION_ORDER:
                letter = m.group(1).upper()
                if letter in options:
                    raise ValueError(f"line {lineno}: duplicate option {letter}")
                options[letter] = m.group(2).strip()
            else:
                raise ValueError(f"line {lineno}: unrecognized field {part!r}")

    missing = [l for l in _OPTION_ORDER if l not in options]
    if missing:
        raise ValueError(f"line {lineno}: question missing option(s) {', '.join(missing)}")
    if answer is None:
        raise ValueError(f"line {lineno}: question missing 'answer' field")
    for letter in _OPTION_ORDER:
        if not options[letter]:
            raise ValueError(f"line {lineno}: option {letter} has empty text")

    item = {
        "type": "question",
        "q": qtext,
        "options": [options[l] for l in _OPTION_ORDER],
        "answer": answer,
    }
    if topic is not None:
        item["topic"] = topic
    if explain is not None:
        item["explain"] = explain
    return item


def _parse_flashcard(parts, lineno):
    head = parts[0]
    if ":" not in head:
        raise ValueError(f"line {lineno}: flashcard is missing ':' after 'CARD'")
    front = head.split(":", 1)[1].strip()
    if not front:
        raise ValueError(f"line {lineno}: empty flashcard front")

    back = None
    topic = None
    explain = None
    for part in parts[1:]:
        part = part.strip()
        if not part:
            continue
        low = part.lower()
        if low.startswith("back:"):
            if back is not None:
                raise ValueError(f"line {lineno}: duplicate 'BACK' field")
            back = part.split(":", 1)[1].strip()
        elif low.startswith("topic:"):
            if topic is not None:
                raise ValueError(f"line {lineno}: duplicate 'topic' field")
            topic = part.split(":", 1)[1].strip() or None
        elif low.startswith("explain:"):
            if explain is not None:
                raise ValueError(f"line {lineno}: duplicate 'explain' field")
            explain = part.split(":", 1)[1].strip() or None
        else:
            raise ValueError(f"line {lineno}: unrecognized field {part!r}")

    if not back:
        raise ValueError(f"line {lineno}: flashcard missing 'BACK' field")

    item = {"type": "flashcard", "front": front, "back": back}
    if topic is not None:
        item["topic"] = topic
    if explain is not None:
        item["explain"] = explain
    return item


def items_to_bank_json(items):
    """Return a pretty JSON string of bank items, for previews."""
    return json.dumps(items, indent=2, ensure_ascii=False)
