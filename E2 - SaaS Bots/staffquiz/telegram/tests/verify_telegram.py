"""StaffQuiz (Telegram) verification — run directly:  python3 tests/verify_telegram.py

No pytest, no network, no real token. Exercises:
  - config defaults
  - pure message builders (HTML escaping, spoiler, aggregate report privacy)
  - callback encode/decode edge cases
  - core schedule pick_bank / parse_fun_config integration
  - adapter-local persistence (paid_until, posts table, group lookup)
  - core db tenant/employee/answer/leaderboard/report/streak
"""
import json
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent      # .../staffquiz/telegram
REPO = BASE.parent                                   # .../staffquiz
sys.path.insert(0, str(BASE))                        # for `import bot` / `import config`

if not (REPO / "core" / "bank.py").is_file():
    print("ERROR: staffquiz/core is missing — cannot verify the adapter.")
    sys.exit(1)

sys.path.insert(0, str(REPO.parent))                 # .../E2 - SaaS Bots → `staffquiz.core`

import config
import bot
from bot import (
    build_question_text, build_flashcard_text, build_report_text,
    build_leaderboard_text, encode_answer_callback, decode_answer_callback,
    parse_hm, item_kind, LETTERS, WEEKDAYS,
)
from staffquiz.core import bank, db, schedule

FAILS = []


def check(name, cond):
    if cond:
        print(f"  ok  {name}")
    else:
        print(f"FAIL  {name}")
        FAILS.append(name)


TENANT = {
    "id": 1, "slug": "acme", "name": "Acme & Sons", "group_id": "-1001",
    "default_bank": "general.json", "quiz_time": "09:00", "q_index": 0,
    "paid_until": None, "active": 1, "fun_banks": {},
}
Q = {"type": "question", "q": "Is 2 < 3?", "options": ["a < b", "b & c", "c", "d"],
     "answer": 0, "explain": "2 < 3 is <true>", "topic": "math"}
FC = {"type": "flashcard", "front": "Who is the <boss>?", "back": "The <unknown> & co"}


def main():
    # ── config ──
    check("DB_PATH default → telegram/data/staffquiz.db",
          str(config.DB_PATH).replace("\\", "/").endswith("telegram/data/staffquiz.db"))
    check("BANKS_DIR default → staffquiz/data/banks",
          str(config.BANKS_DIR).replace("\\", "/").endswith("staffquiz/data/banks"))
    check("ready() returns a bool", isinstance(config.ready(), bool))
    check("OWNER_ADMIN_ID is int", isinstance(config.OWNER_ADMIN_ID, int))
    check("BOT_TOKEN is str", isinstance(config.BOT_TOKEN, str))

    # ── message builders ──
    qtxt = build_question_text(TENANT, Q, 0)
    check("question text branded (escaped)", "Acme &amp; Sons" in qtxt)
    check("question text numbered", "question #1" in qtxt)
    check("question body escaped", "Is 2 &lt; 3?" in qtxt)
    check("question options escaped", "a &lt; b" in qtxt)
    check("question has A./B./C./D.", all(f"{L}." in qtxt for L in LETTERS))
    check("question has tap hint", "Tap your answer" in qtxt)

    ftxt = build_flashcard_text(TENANT, FC, 5)
    check("flashcard header numbered", "Flashcard #6" in ftxt)
    check("flashcard has spoiler open/close",
          "<tg-spoiler>" in ftxt and "</tg-spoiler>" in ftxt)
    check("flashcard front escaped", "&lt;boss&gt;" in ftxt)
    check("flashcard back escaped inside spoiler", "&lt;unknown&gt; &amp; co" in ftxt)
    check("flashcard tap-to-reveal hint", "tap to reveal" in ftxt.lower())

    rep = {
        "active_employees": 12, "participation_pct": 60.0,
        "per_topic": {
            "safety": {"correct_pct": 80.0, "answered": 10, "correct": 8},
            "sales": {"correct_pct": 20.0, "answered": 5, "correct": 1},
        },
        "weakest_topics": ["sales"],
    }
    rtxt = build_report_text(TENANT, rep)
    check("report shows active employees", "Active employees" in rtxt and "12" in rtxt)
    check("report shows participation", "60%" in rtxt)
    check("report lists topics", "safety" in rtxt and "sales" in rtxt)
    check("report lists weakest topic", "sales" in rtxt)
    check("report escapes tenant name", "Acme &amp; Sons" in rtxt)
    # PRIVACY: aggregate only — no per-employee identifiers may ever appear.
    check("report has NO per-employee lines", "user_id" not in rtxt and "uid" not in rtxt
          and "employee" not in rtxt.lower().replace("active employees", ""))

    top = [{"employee_id": 1, "uid": "u1", "name": "Mark & Co", "department": "floor",
            "correct": 5, "answered": 5},
           {"employee_id": 2, "uid": "u2", "name": "Lisa", "department": "bar",
            "correct": 3, "answered": 3}]
    dept = [{"department": "floor", "name": "Mark & Co", "uid": "u1", "correct": 5, "answered": 5}]
    ltxt = build_leaderboard_text(TENANT, top, dept)
    check("leaderboard medals", "🥇" in ltxt and "🥈" in ltxt)
    check("leaderboard escapes names", "Mark &amp; Co" in ltxt)
    check("leaderboard department champions", "Department champions" in ltxt)
    check("leaderboard no-answer fallback",
          "No answers yet" in build_leaderboard_text(TENANT, [], []))

    # ── callback encode/decode ──
    check("encode → 4 colon parts", encode_answer_callback(7, 12, 3) == "ans:7:12:3")
    check("decode roundtrip", decode_answer_callback("ans:7:12:3") == (7, 12, 3))
    check("decode wrong prefix → None", decode_answer_callback("x:1:2:3") is None)
    check("decode too few parts → None", decode_answer_callback("ans:1:2") is None)
    check("decode too many parts → None", decode_answer_callback("ans:1:2:3:4") is None)
    check("decode non-int → None", decode_answer_callback("ans:a:2:3") is None)
    check("decode empty → None", decode_answer_callback("") is None)
    check("decode None → None", decode_answer_callback(None) is None)

    # ── helpers ──
    check("parse_hm ok", parse_hm("09:30") == (9, 30))
    try:
        parse_hm("nope")
        check("parse_hm rejects junk", False)
    except ValueError:
        check("parse_hm rejects junk", True)
    check("sunday = 6", WEEKDAYS["sunday"] == 6)
    check("item_kind question", item_kind(Q) == "question")
    check("item_kind flashcard", item_kind(FC) == "flashcard")

    # ── core schedule ──
    check("pick_bank default weekday", schedule.pick_bank(TENANT, "monday") == "general.json")
    t_fun = dict(TENANT, fun_banks={"friday": "scifi.json", "saturday": "general.json"})
    check("pick_bank fun override friday", schedule.pick_bank(t_fun, "friday") == "scifi.json")
    check("pick_bank fun override saturday", schedule.pick_bank(t_fun, "saturday") == "general.json")
    check("pick_bank fallthrough monday", schedule.pick_bank(t_fun, "monday") == "general.json")
    check("parse_fun_config",
          schedule.parse_fun_config("friday:scifi.json,saturday:general.json")
          == {"friday": "scifi.json", "saturday": "general.json"})
    try:
        schedule.parse_fun_config("funday:x.json")
        check("parse_fun_config rejects bad weekday", False)
    except ValueError:
        check("parse_fun_config rejects bad weekday", True)

    # ── core bank ──
    with tempfile.TemporaryDirectory() as td:
        banks = Path(td) / "banks"
        banks.mkdir()
        (banks / "general.json").write_text(json.dumps([Q, FC]), encoding="utf-8")
        b = bank.load_bank(banks, "general.json")
        check("bank loads question+flashcard", len(b) == 2)
        item0, pos0 = bank.next_item(b, 0)
        check("next_item position 0", pos0 == 0 and item0 == b[0])
        item1, pos1 = bank.next_item(b, 3)
        check("next_item wraps", pos1 == 1 and item1 == b[1])
        try:
            bank.load_bank(banks, "nope.json")
            check("missing bank raises", False)
        except FileNotFoundError:
            check("missing bank raises", True)

    # ── core db + adapter persistence (temp file) ──
    with tempfile.TemporaryDirectory() as td:
        p = str(Path(td) / "staffquiz.db")
        old_db_path = config.DB_PATH
        config.DB_PATH = p
        try:
            db.init_db(p)
            bot._ensure_paid_column()
            bot._ensure_posts_table()

            tid = db.add_tenant(p, "acme", "Acme & Sons", "-1001", "general.json", quiz_time="09:30")
            t = db.get_tenant(p, "acme")
            check("tenant added + readable",
                  bool(t) and t["id"] == tid and t["quiz_time"] == "09:30"
                  and t["default_bank"] == "general.json" and t["group_id"] == "-1001")
            check("tenant by group lookup", bot._find_tenant_by_group("-1001")["slug"] == "acme")
            check("unknown group → None", bot._find_tenant_by_group("-9999") is None)

            # paid_until (adapter-added column + helpers)
            check("paid NULL = unlimited", bot._tenant_paid_ok(t))
            until = bot._extend_paid(tid, 30)
            check("extend_paid = today+30", until == (date.today() + timedelta(days=30)).isoformat())
            t2 = db.get_tenant(p, "acme")
            check("paid_until persisted on tenant", t2["paid_until"] == until)
            check("paid_ok after extend", bot._tenant_paid_ok(t2))
            bot._extend_paid(tid, -99)  # roll back to the past
            check("expired paid → not ok", bot._tenant_paid_ok(db.get_tenant(p, "acme")) is False)
            db.set_active(p, tid, False)
            check("suspend flips active", db.get_tenant(p, "acme")["active"] == 0)
            db.set_active(p, tid, True)
            check("activate flips back", db.get_tenant(p, "acme")["active"] == 1)
            bot._set_fun_banks(tid, {"friday": "scifi.json"})
            check("fun_banks stored (dict round-trip)",
                  db.get_tenant(p, "acme")["fun_banks"] == {"friday": "scifi.json"})

            # posts table (offline grading source)
            bot._store_post(tid, 0, Q)
            got = bot._get_post(tid, 0)
            check("post store/roundtrip", got == Q and got["answer"] == 0)
            check("missing post → None", bot._get_post(tid, 999) is None)

            # employees
            db.upsert_employee(p, tid, "111", "Mark & Co", "floor", "nl")
            eid = db.upsert_employee(p, tid, "111", "Mark 2", "floor", "en")  # re-register updates
            emp = db.get_employee(p, tid, "111")
            check("upsert updates employee", emp["name"] == "Mark 2" and emp["language"] == "en")
            db.upsert_employee(p, tid, "222", "Lisa", "bar", "nl")
            check("unknown employee → None", db.get_employee(p, tid, "999") is None)

            # answers (record_answer takes employee_id, not uid)
            check("first answer recorded",
                  db.record_answer(p, tid, eid, 0, 1, topic="safety") is True)
            check("duplicate answer ignored",
                  db.record_answer(p, tid, eid, 0, 1, topic="safety") is False)
            db.record_answer(p, tid, db.get_employee(p, tid, "222")["id"], 0, 0, topic="safety")
            db.record_answer(p, tid, eid, 1, 1, topic="sales")
            check("employee week correct mark=2", bot._employee_week_correct(tid, eid) == 2)
            check("streak ≥ 1 after a correct answer", db.streak_days(p, eid) >= 1)

            top_rows = db.week_leaderboard(p, tid)
            check("leaderboard order (mark first, 2 pts)",
                  top_rows[0]["uid"] == "111" and top_rows[0]["correct"] == 2)
            check("leaderboard uses registered name", top_rows[0]["name"] == "Mark 2")

            depts = db.department_board(p, tid)
            floors = [d for d in depts if d["department"] == "floor"]
            check("department champion (floor → Mark 2)",
                  floors and floors[0]["name"] == "Mark 2" and floors[0]["correct"] == 2)

            rep2 = db.aggregate_report(p, tid)
            check("report active employees = 2", rep2["active_employees"] == 2)
            check("report topics {safety, sales}",
                  set(rep2["per_topic"].keys()) == {"safety", "sales"})
            # safety = 1/2 correct (50%) < sales = 1/1 (100%) → safety is weakest
            check("report weakest ordered (safety first)", rep2["weakest_topics"][0] == "safety")
            check("report participation 100%", rep2["participation_pct"] == 100.0)
            # feed the real report into the builder
            built = build_report_text(db.get_tenant(p, "acme"), rep2)
            check("report builder consumes core shape", "safety" in built and "sales" in built)
        finally:
            config.DB_PATH = old_db_path

    # ── adapter surface (import-time only — no network) ──
    check("build_application callable", callable(bot.build_application))
    check("main callable", callable(bot.main))

    # ── onboarding UX (addcompany forms + company pick) ──
    parts, err = bot.parse_addcompany_args(
        "/addcompany acme|Acme BV|-100123|demo.json|09:00", "private", 111)
    check("addcompany: 5-part form parses", err == "" and parts[0] == "acme" and parts[2] == "-100123")
    parts, err = bot.parse_addcompany_args(
        "/addcompany acme|Acme BV|demo.json|09:00", "group", -100777)
    check("addcompany: 4-part form in group uses chat id",
          err == "" and parts[2] == "-100777" and parts[3] == "demo.json")
    parts, err = bot.parse_addcompany_args(
        "/addcompany acme|Acme BV|demo.json|09:00", "private", 111)
    check("addcompany: 4-part form in DM = pure-DM mode (no group)",
          err == "" and parts[2] == "" and parts[3] == "demo.json")
    parts, err = bot.parse_addcompany_args("/addcompany", "private", 111)
    check("addcompany: no args rejected", err != "" and parts == [])
    kb = bot.company_keyboard([])
    check("company pick: 0 companies → no keyboard", kb is None)
    kb = bot.company_keyboard([{"id": 1, "name": "Only Co"}])
    check("company pick: 1 company → no keyboard (auto-assign)", kb is None)
    kb = bot.company_keyboard([{"id": 1, "name": "A"}, {"id": 2, "name": "B"}])
    check("company pick: 2 companies → 2 buttons",
          kb is not None and len(kb.inline_keyboard) == 2
          and kb.inline_keyboard[0][0].callback_data == "pick:1")

    # ── no-group architecture (DM delivery) ──
    tenants = [
        {"id": 1, "slug": "acme", "name": "Acme", "active": 1, "admin_id": 222,
         "default_bank": "acme.json"},
        {"id": 2, "slug": "beta", "name": "Beta", "active": 1, "admin_id": None,
         "default_bank": "beta.json"},
    ]

    class _FakeUpdate:
        def __init__(self, uid, text):
            self.effective_user = type("U", (), {"id": uid})()
            self.message = type("M", (), {"text": text})()
    check("deep link: known slug resolves", bot.resolve_start_tenant(tenants, ["acme"])["id"] == 1)
    check("deep link: unknown slug → None", bot.resolve_start_tenant(tenants, ["nope"]) is None)
    check("deep link: no args → None", bot.resolve_start_tenant(tenants, []) is None)
    check("mini-key: tenant admin found", bot.tenant_admin_for_uid(tenants, 222)["slug"] == "acme")
    check("mini-key: stranger → None", bot.tenant_admin_for_uid(tenants, 999) is None)
    check("registration link has bot username + slug",
          "staffle_bot?start=acme" in bot.registration_link("acme"))
    ann = bot.build_announcement_text({"name": "Acme"}, 3)
    check("announcement mentions private answers", "private chat" in ann and "3 players" in ann)
    slug, name, qtime, err = bot.parse_createcompany_args("/createcompany acme|Acme BV|08:30")
    check("createcompany parses", err == "" and slug == "acme" and qtime == "08:30")
    slug, name, qtime, err = bot.parse_createcompany_args("/createcompany acme")
    check("createcompany rejects short form", err != "" and slug == "")
    t, err = bot.resolve_invite_tenant(config.OWNER_ADMIN_ID, tenants, "acme")
    check("invite: owner gets any company", err == "" and t["slug"] == "acme")
    t, err = bot.resolve_invite_tenant(222, tenants, "")
    check("invite: tenant admin gets own company", err == "" and t["slug"] == "acme")
    t, err = bot.resolve_invite_tenant(999, tenants, "")
    check("invite: stranger rejected", err != "" and t is None)
    bankfile, t, err = bot.parse_feed_command(_FakeUpdate(222, "/feed"), tenants)
    check("feed: tenant admin feeds own bank", err == "" and bankfile == "acme.json" and t["slug"] == "acme")
    bankfile, t, err = bot.parse_feed_command(_FakeUpdate(222, "/feed beta.json"), tenants)
    check("feed: tenant admin cannot feed another bank",
          err != "" and "only feed your company" in err)
    bankfile, t, err = bot.parse_feed_command(_FakeUpdate(999, "/feed"), tenants)
    check("feed: stranger rejected", err != "" and bankfile == "")
    bankfile, t, err = bot.parse_feed_command(
        _FakeUpdate(config.OWNER_ADMIN_ID, "/feed demo-service.json"), tenants)
    check("feed: owner feeds any bank", err == "" and bankfile == "demo-service.json")

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: {FAILS}")
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()
