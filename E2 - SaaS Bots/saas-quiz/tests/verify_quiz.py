"""QuizDay verification — run directly:  python3 tests/verify_quiz.py  (no pytest needed)"""
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from quiz import bank, db
from quiz.bot import parse_hm, question_text, WEEKDAYS

FAILS = []


def check(name, cond):
    if cond:
        print(f"  ok  {name}")
    else:
        print(f"FAIL  {name}")
        FAILS.append(name)


def main():
    # ── banks ──
    for fn in ("anime.json", "general.json"):
        b = bank.load_bank(BASE / "data" / "banks", fn)
        check(f"bank {fn} loads ({len(b)} questions)", len(b) >= 25)
    b = bank.load_bank(BASE / "data" / "banks", "anime.json")
    check("every anime item has 4 options + answer 0-3",
          all(len(x["options"]) == 4 and 0 <= x["answer"] <= 3 for x in b))
    check("rotation starts at 0", bank.next_question(b, 0)[1] == 0)
    q1, _ = bank.next_question(b, len(b))
    check("rotation wraps after one lap", q1 == b[0])
    try:
        bank.load_bank(BASE / "data" / "banks", "nope.json")
        check("missing bank raises", False)
    except FileNotFoundError:
        check("missing bank raises", True)

    # ── tenants + scores (temp db) ──
    with tempfile.TemporaryDirectory() as td:
        p = str(Path(td) / "quiz.db")
        db.init_db(p)
        tid = db.add_tenant(p, "psv", "PSV Quiz", "-100123", "anime.json", quiz_time="09:30")
        t = db.get_tenant(p, "psv")
        check("tenant added + readable", bool(t) and t["id"] == tid and t["quiz_time"] == "09:30")
        check("get by id matches", db.get_tenant_by_id(p, tid)["slug"] == "psv")
        try:
            db.add_tenant(p, "psv", "x", "-1", "anime.json")
            check("duplicate slug rejected", False)
        except Exception:
            check("duplicate slug rejected", True)
        check("paid_until NULL = unlimited", db.tenant_paid_ok(t))
        until = db.extend_paid(p, tid, 30)
        check("extend_paid = today+30", until == (date.today() + timedelta(days=30)).isoformat())
        check("paid_ok after extend", db.tenant_paid_ok(db.get_tenant(p, "psv")))
        db.set_tenant_active(p, tid, False)
        check("suspend flips active", db.get_tenant(p, "psv")["active"] == 0)
        db.set_tenant_active(p, tid, True)
        check("activate flips back", db.get_tenant(p, "psv")["active"] == 1)

        check("first answer recorded", db.record_answer(p, tid, 111, "mark", 0, 1) is True)
        check("duplicate answer ignored", db.record_answer(p, tid, 111, "mark", 0, 1) is False)
        db.record_answer(p, tid, 222, "lisa", 0, 0)
        db.record_answer(p, tid, 111, "mark", 1, 1)
        top = db.week_top(p, tid)
        check("leaderboard order (mark first, 2 pts)", top[0]["user_id"] == 111 and top[0]["n"] == 2)
        check("user week count", db.user_week_correct(p, tid, 111) == 2)

    # ── bot helpers ──
    check("parse_hm ok", parse_hm("09:30") == (9, 30))
    try:
        parse_hm("nope")
        check("parse_hm rejects junk", False)
    except ValueError:
        check("parse_hm rejects junk", True)
    check("sunday = 6", WEEKDAYS["sunday"] == 6)
    txt = question_text({"name": "PSV Quiz"}, b[0], 3)
    check("question text branded + numbered", "PSV Quiz" in txt and "question #4" in txt and "A." in txt)

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: {FAILS}")
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()
