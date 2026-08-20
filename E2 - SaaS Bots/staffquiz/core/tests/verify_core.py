"""Plain-Python verifier for the StaffQuiz core engine.

Run from the ``core/`` directory::

    python3 tests/verify_core.py

Exits 0 and prints ``ALL OK`` when every check passes; exits 1 and lists the
failed checks otherwise. No pytest — just asserts and a ``check`` helper.
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))   # .../core/tests
CORE = os.path.dirname(HERE)                         # .../core
PARENT = os.path.dirname(CORE)                       # .../staffquiz
sys.path.insert(0, PARENT)

import core  # noqa: E402  (also exercises __init__.py)
from core import bank, content, db, schedule  # noqa: E402

CHECKS = 0
FAILURES = []


def check(name, cond):
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILURES.append(name)
        print(f"FAIL: {name}")


def expect_raises(name, exc, fn):
    global CHECKS
    CHECKS += 1
    try:
        fn()
    except exc:
        return
    except Exception as e:  # wrong exception type
        FAILURES.append(name)
        print(f"FAIL: {name} (raised {type(e).__name__}: {e}, expected {exc.__name__})")
        return
    FAILURES.append(name)
    print(f"FAIL: {name} (no exception raised, expected {exc.__name__})")


# ── shared fixtures ────────────────────────────────────────────────────────
tmp = tempfile.TemporaryDirectory()
BANKS = Path(tmp.name) / "banks"
BANKS.mkdir()
DB_PATH = str(Path(tmp.name) / "test.db")
db.init_db(DB_PATH)


def write_bank(name, data):
    (BANKS / name).write_text(json.dumps(data), encoding="utf-8")


def load(name, data):
    write_bank(name, data)
    return bank.load_bank(str(BANKS), name)


# ══ bank.load_bank — loading & validation ══════════════════════════════════
valid = [
    {"type": "question", "q": "2+2?", "options": ["1", "2", "3", "4"],
     "answer": 3, "topic": "math"},
    {"type": "flashcard", "front": "H2O", "back": "water", "topic": "chem"},
]
write_bank("ok.json", valid)
items = bank.load_bank(str(BANKS), "ok.json")
check("load_bank returns list of 2", isinstance(items, list) and len(items) == 2)
check("load_bank question preserved", items[0]["answer"] == 3)
check("load_bank flashcard preserved", items[1]["front"] == "H2O")
check("answer index 3 is valid", items[0]["answer"] == 3)

expect_raises("load_bank missing file", FileNotFoundError,
              lambda: bank.load_bank(str(BANKS), "nope.json"))
expect_raises("load_bank empty list", ValueError, lambda: load("empty.json", []))
expect_raises("load_bank non-list", ValueError, lambda: load("notlist.json", {"q": "x"}))
expect_raises("load_bank bad answer idx 4", ValueError,
              lambda: load("badans.json", [{"type": "question", "q": "x?",
                                            "options": ["a", "b", "c", "d"], "answer": 4}]))
expect_raises("load_bank negative answer", ValueError,
              lambda: load("negans.json", [{"type": "question", "q": "x?",
                                            "options": ["a", "b", "c", "d"], "answer": -1}]))
expect_raises("load_bank bool answer", ValueError,
              lambda: load("boolans.json", [{"type": "question", "q": "x?",
                                             "options": ["a", "b", "c", "d"], "answer": True}]))
expect_raises("load_bank missing options", ValueError,
              lambda: load("missopt.json", [{"type": "question", "q": "x?",
                                             "options": ["a", "b", "c"], "answer": 0}]))
expect_raises("load_bank wrong type", ValueError,
              lambda: load("badtype.json", [{"type": "quiz", "q": "x?",
                                             "options": ["a", "b", "c", "d"], "answer": 0}]))
expect_raises("load_bank missing type", ValueError,
              lambda: load("notype.json", [{"q": "x?", "options": ["a", "b", "c", "d"],
                                            "answer": 0}]))
expect_raises("load_bank flashcard missing back", ValueError,
              lambda: load("noback.json", [{"type": "flashcard", "front": "hi"}]))
expect_raises("load_bank non-dict item", ValueError,
              lambda: load("notobj.json", ["just a string"]))

# ══ bank.next_item — rotation wrap ══════════════════════════════════════════
b3 = [{"type": "question", "q": f"q{i}", "options": ["a", "b", "c", "d"], "answer": 0}
      for i in range(3)]
item, pos = bank.next_item(b3, 0)
check("rotation pos 0", pos == 0 and item["q"] == "q0")
item, pos = bank.next_item(b3, 2)
check("rotation pos 2", pos == 2 and item["q"] == "q2")
item, pos = bank.next_item(b3, 3)
check("rotation wraps to 0", pos == 0 and item["q"] == "q0")
item, pos = bank.next_item(b3, 4)
check("rotation second lap pos 1", pos == 1 and item["q"] == "q1")
item, pos = bank.next_item(b3, 7)
check("rotation third lap", pos == 1)

# ══ bank.dedupe_merge ═══════════════════════════════════════════════════════
existing = [
    {"type": "question", "q": "A", "options": ["1", "2", "3", "4"], "answer": 0},
    {"type": "flashcard", "front": "F", "back": "b"},
]
new = [
    {"type": "question", "q": "A", "options": ["9", "9", "9", "9"], "answer": 1},  # dup (same q)
    {"type": "flashcard", "front": "F", "back": "different"},                       # dup (same front)
    {"type": "question", "q": "B", "options": ["1", "2", "3", "4"], "answer": 0},  # new
]
merged, added, skipped = bank.dedupe_merge(existing, new)
check("dedupe added count", added == 1)
check("dedupe skipped count", skipped == 2)
check("dedupe merged length", len(merged) == 3)
check("dedupe keeps existing first", merged[0]["q"] == "A")
check("dedupe appends new last", merged[2]["q"] == "B")
check("dedupe does not mutate input", len(existing) == 2)

# ══ db — tenant lifecycle ═══════════════════════════════════════════════════
tid = db.add_tenant(DB_PATH, "acme", "Acme Corp", group_id="g1",
                    default_bank="general.json", quiz_time="09:30")
check("add_tenant returns id", tid is not None)
t = db.get_tenant(DB_PATH, "acme")
check("get_tenant slug", t["slug"] == "acme")
check("get_tenant default_bank", t["default_bank"] == "general.json")
check("get_tenant quiz_time", t["quiz_time"] == "09:30")
check("get_tenant active default 1", t["active"] == 1)
check("get_tenant group_id", t["group_id"] == "g1")
check("get_tenant_by_id", db.get_tenant_by_id(DB_PATH, tid)["name"] == "Acme Corp")
check("list_tenants has 1", len(db.list_tenants(DB_PATH)) == 1)
db.set_q_index(DB_PATH, tid, 5)
check("set_q_index", db.get_tenant_by_id(DB_PATH, tid)["q_index"] == 5)
db.set_active(DB_PATH, tid, False)
check("set_active False", db.get_tenant_by_id(DB_PATH, tid)["active"] == 0)
db.set_active(DB_PATH, tid, True)
check("set_active True", db.get_tenant_by_id(DB_PATH, tid)["active"] == 1)

# fun_banks round-trip (dict in, dict out)
tid2 = db.add_tenant(DB_PATH, "funco", "Fun Co", default_bank="general.json",
                     fun_banks={"friday": "scifi.json", "saturday": "general.json"})
tfun = db.get_tenant(DB_PATH, "funco")
check("fun_banks round-trip dict", tfun["fun_banks"] ==
      {"friday": "scifi.json", "saturday": "general.json"})
check("fun_banks default empty", db.get_tenant(DB_PATH, "acme")["fun_banks"] == {})

# ══ db — employee upsert ════════════════════════════════════════════════════
eid = db.upsert_employee(DB_PATH, tid, "u1", name="Alice", department="eng", language="en")
check("upsert_employee returns id", eid is not None)
emp = db.get_employee(DB_PATH, tid, "u1")
check("get_employee name", emp["name"] == "Alice")
check("get_employee department", emp["department"] == "eng")
eid2 = db.upsert_employee(DB_PATH, tid, "u1", name="Alice B.", department="eng", language="nl")
check("upsert same uid stable id", eid2 == eid)
emp2 = db.get_employee(DB_PATH, tid, "u1")
check("upsert updates fields", emp2["name"] == "Alice B." and emp2["language"] == "nl")
check("get_employee missing is None", db.get_employee(DB_PATH, tid, "nobody") is None)
check("get_employee_by_id", db.get_employee_by_id(DB_PATH, eid)["uid"] == "u1")

# ══ db — record_answer first-wins ═══════════════════════════════════════════
check("record_answer first True", db.record_answer(DB_PATH, tid, eid, 0, True, topic="math") is True)
check("record_answer dup False", db.record_answer(DB_PATH, tid, eid, 0, False, topic="math") is False)
check("record_answer correct=None->0", db.record_answer(DB_PATH, tid, eid, 1, None) is True)

# ══ db — week_leaderboard ordering ══════════════════════════════════════════
lt = db.add_tenant(DB_PATH, "lb", "LB", default_bank="general.json")
a = db.upsert_employee(DB_PATH, lt, "a", name="A", department="eng")
b = db.upsert_employee(DB_PATH, lt, "b", name="B", department="eng")
c = db.upsert_employee(DB_PATH, lt, "c", name="C", department="sales")
for i in range(5):                     # A: 3 correct of 5 answered
    db.record_answer(DB_PATH, lt, a, i, i < 3)
for i in range(3):                     # B: 3 correct of 3 answered
    db.record_answer(DB_PATH, lt, b, 100 + i, True)
db.record_answer(DB_PATH, lt, c, 200, True)   # C: 1 correct of 1

lb = db.week_leaderboard(DB_PATH, lt, days=7, limit=10)
check("leaderboard length", len(lb) == 3)
check("leaderboard order B,A,C", [r["uid"] for r in lb] == ["b", "a", "c"])
check("leaderboard correct values", [r["correct"] for r in lb] == [3, 3, 1])
check("leaderboard answered values", [r["answered"] for r in lb] == [3, 5, 1])
check("leaderboard limit", len(db.week_leaderboard(DB_PATH, lt, days=7, limit=1)) == 1)

# ══ db — department_board grouping ══════════════════════════════════════════
board = db.department_board(DB_PATH, lt, days=7)
by_dept = {r["department"]: r for r in board}
check("department_board 2 depts", len(board) == 2)
check("department eng top is B (3 correct, fewer answered)", by_dept["eng"]["uid"] == "b")
check("department sales top is C", by_dept["sales"]["uid"] == "c")
check("department_board sorted best first", board[0]["department"] == "eng")

# ══ db — streak_days ════════════════════════════════════════════════════════
se = db.upsert_employee(DB_PATH, lt, "streaker", name="S")
today = datetime.now(timezone.utc).date()


def day(n):
    return (today - timedelta(days=n)).strftime("%Y-%m-%d") + "T12:00:00+00:00"


db.record_answer(DB_PATH, lt, se, 300, True, answered_at=day(0))
db.record_answer(DB_PATH, lt, se, 301, True, answered_at=day(1))
db.record_answer(DB_PATH, lt, se, 302, True, answered_at=day(2))
check("streak_days 3 consecutive", db.streak_days(DB_PATH, se) == 3)

se2 = db.upsert_employee(DB_PATH, lt, "gapper", name="G")
db.record_answer(DB_PATH, lt, se2, 400, True, answered_at=day(0))
db.record_answer(DB_PATH, lt, se2, 401, True, answered_at=day(2))  # gap at day(1)
check("streak_days gap breaks streak -> 1", db.streak_days(DB_PATH, se2) == 1)

se3 = db.upsert_employee(DB_PATH, lt, "yesterday", name="Y")
db.record_answer(DB_PATH, lt, se3, 500, True, answered_at=day(1))
db.record_answer(DB_PATH, lt, se3, 501, True, answered_at=day(2))
check("streak_days no answer today -> 0", db.streak_days(DB_PATH, se3) == 0)

se4 = db.upsert_employee(DB_PATH, lt, "empty", name="E")
check("streak_days no answers -> 0", db.streak_days(DB_PATH, se4) == 0)

# ══ db — participation_pct ══════════════════════════════════════════════════
pt = db.add_tenant(DB_PATH, "part", "Part", default_bank="g.json")
pids = [db.upsert_employee(DB_PATH, pt, f"p{i}") for i in range(4)]
db.record_answer(DB_PATH, pt, pids[0], 0, True)
db.record_answer(DB_PATH, pt, pids[1], 0, True)
check("participation_pct 2/4 = 50", abs(db.participation_pct(DB_PATH, pt) - 50.0) < 1e-9)
pe = db.add_tenant(DB_PATH, "empty_part", "Empty", default_bank="g.json")
check("participation_pct no employees = 0", db.participation_pct(DB_PATH, pe) == 0.0)

# ══ db — aggregate_report ═══════════════════════════════════════════════════
at = db.add_tenant(DB_PATH, "agg", "Agg", default_bank="g.json")
ae1 = db.upsert_employee(DB_PATH, at, "ae1", name="E1")
db.upsert_employee(DB_PATH, at, "ae2", name="E2")  # registered but silent
for i in range(4):                       # math: 2 correct / 4
    db.record_answer(DB_PATH, at, ae1, i, i < 2, topic="math")
for i in range(4):                       # sci: 1 correct / 4
    db.record_answer(DB_PATH, at, ae1, 10 + i, i < 1, topic="sci")
for i in range(3):                       # hist: 3 correct / 3
    db.record_answer(DB_PATH, at, ae1, 20 + i, True, topic="hist")

rep = db.aggregate_report(DB_PATH, at)
ptopic = rep["per_topic"]
check("aggregate math pct 50", ptopic["math"]["correct_pct"] == 50.0)
check("aggregate sci pct 25", ptopic["sci"]["correct_pct"] == 25.0)
check("aggregate hist pct 100", ptopic["hist"]["correct_pct"] == 100.0)
check("aggregate math answered 4", ptopic["math"]["answered"] == 4)
check("aggregate sci correct 1", ptopic["sci"]["correct"] == 1)
check("aggregate weakest ordering", rep["weakest_topics"] == ["sci", "math", "hist"])
check("aggregate active_employees 1", rep["active_employees"] == 1)
check("aggregate participation 50", abs(rep["participation_pct"] - 50.0) < 1e-9)

# ══ schedule ════════════════════════════════════════════════════════════════
t_default = {"slug": "x", "default_bank": "general.json", "fun_banks": {}}
check("pick_bank default", schedule.pick_bank(t_default, "monday") == "general.json")
t_fun = {"slug": "x", "default_bank": "general.json",
         "fun_banks": {"friday": "scifi.json"}}
check("pick_bank fun override", schedule.pick_bank(t_fun, "friday") == "scifi.json")
check("pick_bank fun weekday falls to default", schedule.pick_bank(t_fun, "monday") == "general.json")
check("pick_bank weekday case-insensitive", schedule.pick_bank(t_fun, "FRIDAY") == "scifi.json")
t_fun_str = {"slug": "x", "default_bank": "general.json",
             "fun_banks": json.dumps({"friday": "scifi.json"})}
check("pick_bank parses JSON string", schedule.pick_bank(t_fun_str, "friday") == "scifi.json")

cfg = schedule.parse_fun_config("friday:scifi.json, saturday:general.json")
check("parse_fun_config", cfg == {"friday": "scifi.json", "saturday": "general.json"})
check("parse_fun_config empty str", schedule.parse_fun_config("") == {})
check("parse_fun_config None", schedule.parse_fun_config(None) == {})
expect_raises("parse_fun_config bad weekday", ValueError,
              lambda: schedule.parse_fun_config("funday:scifi.json"))
expect_raises("parse_fun_config no colon", ValueError,
              lambda: schedule.parse_fun_config("friday"))
expect_raises("pick_bank bad weekday", ValueError,
              lambda: schedule.pick_bank(t_default, "funday"))

# ══ content — parse_typed_notes round-trip ══════════════════════════════════
notes = (
    "Q: What is 2+2? | A) 3 | B) 4 | C) 5 | D) 6 | answer: B | topic: math | explain: basic arithmetic\n"
    "CARD: H2O | BACK: water | topic: chem\n"
    "q: who wrote hamlet | a) shakespeare | b) twain | c) austen | d) joyce | ANSWER: a | Topic: literature\n"
)
items = content.parse_typed_notes(notes)
check("parse_typed_notes 3 items", len(items) == 3)
q = items[0]
check("question type", q["type"] == "question")
check("question q text", q["q"] == "What is 2+2?")
check("question options", q["options"] == ["3", "4", "5", "6"])
check("question answer index", q["answer"] == 1)
check("question topic", q["topic"] == "math")
check("question explain", q["explain"] == "basic arithmetic")
c = items[1]
check("flashcard type", c["type"] == "flashcard")
check("flashcard front", c["front"] == "H2O")
check("flashcard back", c["back"] == "water")
check("flashcard topic", c["topic"] == "chem")
q3 = items[2]
check("lowercase keys tolerated", q3["type"] == "question" and q3["answer"] == 0)
check("topic key case tolerated", q3["topic"] == "literature")

js = content.items_to_bank_json(items)
check("items_to_bank_json pretty", "\n  " in js)
roundtrip = json.loads(js)
check("items_to_bank_json round-trip", len(roundtrip) == 3 and roundtrip[0]["answer"] == 1)

expect_raises("parse missing option", ValueError,
              lambda: content.parse_typed_notes("Q: x | A) a | B) b | C) c | answer: A"))
expect_raises("parse bad answer letter", ValueError,
              lambda: content.parse_typed_notes(
                  "Q: x | A) a | B) b | C) c | D) d | answer: Z"))
expect_raises("parse unknown field", ValueError,
              lambda: content.parse_typed_notes(
                  "Q: x | A) a | B) b | C) c | D) d | answer: A | bogus: y"))
expect_raises("parse no prefix", ValueError,
              lambda: content.parse_typed_notes("hello world"))
expect_raises("parse card missing back", ValueError,
              lambda: content.parse_typed_notes("CARD: front only"))
expect_raises("parse blank answer", ValueError,
              lambda: content.parse_typed_notes(
                  "Q: x | A) a | B) b | C) c | D) d | answer:"))

try:
    content.parse_typed_notes("Q: ok | A) a | B) b | C) c | D) d | answer: A\nthis is junk\n")
    check("malformed line raised", False)
except ValueError as e:
    check("malformed error includes line number", "line 2" in str(e).lower())


# ── summary ────────────────────────────────────────────────────────────────
tmp.cleanup()
if FAILURES:
    print(f"\n{len(FAILURES)} FAILURE(S):")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)

print(f"\nALL OK — {CHECKS} checks passed")
sys.exit(0)
