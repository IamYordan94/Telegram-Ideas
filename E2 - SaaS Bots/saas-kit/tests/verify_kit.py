"""BoardKit verification — run directly:  python3 tests/verify_kit.py  (no pytest needed)"""
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import kit_db
import kit

FAILS = []


def check(name, cond):
    if cond:
        print(f"  ok  {name}")
    else:
        print(f"FAIL  {name}")
        FAILS.append(name)


def main():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        dbp = str(td / "kit.db")
        kit_db.init_db(dbp)
        kit_db.add_board(dbp, "rotterdam", "Rotterdam Werkt", "Rotterdam",
                         "111:TESTTOKEN", "-100777", channel_username="@rotterdam_werkt",
                         admin_id=999, digest_hour=7)
        b = kit_db.get_board(dbp, "rotterdam")
        check("board added", bool(b) and b["brand"] == "Rotterdam Werkt")
        check("paid_ok when NULL", kit_db.paid_ok(b))
        until = kit_db.extend_paid(dbp, "rotterdam", 30)
        check("extend 30 = today+30", until == (date.today() + timedelta(days=30)).isoformat())
        check("paid_ok after extend", kit_db.paid_ok(kit_db.get_board(dbp, "rotterdam")))
        kit_db.set_active(dbp, "rotterdam", False)
        check("suspend flips active", kit_db.get_board(dbp, "rotterdam")["active"] == 0)
        kit_db.set_active(dbp, "rotterdam", True)
        check("activate flips back", kit_db.get_board(dbp, "rotterdam")["active"] == 1)

        try:
            kit_db.add_board(dbp, "rotterdam", "x", "y", "z", "-1", admin_id=1)
            check("duplicate slug rejected", False)
        except Exception:
            check("duplicate slug rejected", True)

        # ── board files ──
        kit.add_board_files(b, td / "boards", td / "werknl-src")
        board_dir = td / "boards" / "rotterdam"
        check("board dir created", (board_dir / "main.py").is_file() and (board_dir / ".env").is_file())
        env = (board_dir / ".env").read_text(encoding="utf-8")
        check("env has token + db path + brand",
              "111:TESTTOKEN" in env and "board.db" in env and "WERKNL_BRAND_NAME=Rotterdam Werkt" in env)
        check("env has digest hour + username",
              "WERKNL_DIGEST_HOUR=7" in env and "WERKNL_CHANNEL_USERNAME=@rotterdam_werkt" in env)
        mainpy = (board_dir / "main.py").read_text(encoding="utf-8")
        check("main.py rendered with werkNL src", str(td / "werknl-src") in mainpy)
        check("no template placeholder left", "{{WERKNL_SRC}}" not in mainpy)

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: {FAILS}")
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()
