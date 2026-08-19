"""BoardKit — manage WerkNL-based job boards for customers.

Usage: python3 kit.py <command> [args]

Commands:
  add <slug> <brand> <city> <bot_token> <channel_id> <admin_id> [--digest 8] [--username @x]
        create a board: folder + .env + entry point
  list                       every board, payment status, running or not
  run                        start every active board that isn't already running
  stop <slug> | all          stop board(s)
  status                     same as list
  paid <slug> <days>         extend subscription from today
  suspend <slug>             stop posting (keeps data)
  activate <slug>            resume posting
  remove <slug>              delete registry row + board folder (data stays unless -f)
"""
import ctypes
import os
import subprocess
import sys
from pathlib import Path

import kit_db

BASE = Path(__file__).resolve().parent
BOARDS_DIR = BASE / "boards"
DATA_DB = BASE / "data" / "kit.db"
WERKNL_SRC = BASE.parent.parent / "I2 - Job Board NL" / "werknl"
TEMPLATE_MAIN = BASE / "board_template" / "main.py"

PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


# ── process helpers ──

def pid_is_alive(pid: int) -> bool:
    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if handle:
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    return False


def terminate(pid: int) -> bool:
    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not handle:
        return False
    ok = ctypes.windll.kernel32.TerminateProcess(handle, 1)
    ctypes.windll.kernel32.CloseHandle(handle)
    return bool(ok)


def board_running(slug) -> bool:
    pid_file = BOARDS_DIR / slug / "board.pid"
    if not pid_file.is_file():
        return False
    try:
        pid = int(pid_file.read_text().strip())
    except (ValueError, OSError):
        return False
    return bool(pid) and pid_is_alive(pid)


# ── board files ──

def render_env(board, board_dir: Path) -> str:
    db_path = (board_dir / "data" / "board.db").as_posix()
    return (
        f"WERKNL_BOT_TOKEN={board['bot_token']}\n"
        f"WERKNL_CHANNEL_ID={board['channel_id']}\n"
        f"WERKNL_ADMIN_ID={board['admin_id']}\n"
        f"WERKNL_DB_PATH={db_path}\n"
        f"WERKNL_DIGEST_HOUR={board['digest_hour']}\n"
        f"WERKNL_BRAND_NAME={board['brand']}\n"
        f"WERKNL_BRAND_CITY={board['city']}\n"
        f"WERKNL_CHANNEL_USERNAME={board['channel_username'] or '@your_channel'}\n"
    )


def render_main(werknl_src: Path) -> str:
    return TEMPLATE_MAIN.read_text(encoding="utf-8").replace("{{WERKNL_SRC}}", str(werknl_src))


def add_board_files(board, boards_dir: Path, werknl_src: Path):
    board_dir = boards_dir / board["slug"]
    board_dir.mkdir(parents=True, exist_ok=True)
    (board_dir / "data").mkdir(parents=True, exist_ok=True)
    (board_dir / ".env").write_text(render_env(board, board_dir), encoding="utf-8")
    (board_dir / "main.py").write_text(render_main(werknl_src), encoding="utf-8")


def start_board(board, boards_dir: Path) -> bool:
    board_dir = boards_dir / board["slug"]
    log_path = board_dir / "boot.log"
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"\n--- BoardKit start {kit_db.now_iso()} ---\n")
        subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=str(board_dir),
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    return True


# ── commands ──

def usage():
    print(__doc__)


def cmd_add(args):
    if len(args) < 6:
        print("Usage: add <slug> <brand> <city> <bot_token> <channel_id> <admin_id> [--digest 8] [--username @x]")
        return 1
    slug, brand, city, token, channel, admin = args[:6]
    try:
        admin_id = int(admin)
    except ValueError:
        print("admin_id must be a number (the customer's Telegram id).")
        return 1
    digest = 8
    username = ""
    i = 6
    while i < len(args):
        if args[i] == "--digest" and i + 1 < len(args):
            try:
                digest = int(args[i + 1])
            except ValueError:
                print("--digest must be a number (0-23).")
                return 1
            i += 2
        elif args[i] == "--username" and i + 1 < len(args):
            username = args[i + 1]
            i += 2
        else:
            print(f"unknown argument: {args[i]}")
            return 1
    kit_db.init_db(DATA_DB)
    if kit_db.get_board(DATA_DB, slug):
        print(f"slug '{slug}' already exists.")
        return 1
    board = {
        "slug": slug, "brand": brand, "city": city, "bot_token": token,
        "channel_id": channel, "channel_username": username, "admin_id": admin_id,
        "digest_hour": digest,
    }
    kit_db.add_board(DATA_DB, **board)
    add_board_files(board, BOARDS_DIR, WERKNL_SRC)
    print(f"✅ Board '{slug}' created ({brand}, {city}).")
    print(f"   Files: boards/{slug}/  — start everything with: python3 kit.py run")
    print("   Reminder: the board's bot must be admin of its channel before posting.")
    return 0


def cmd_list(_args):
    kit_db.init_db(DATA_DB)
    boards = kit_db.list_boards(DATA_DB)
    if not boards:
        print("No boards yet. Add one: python3 kit.py add <slug> <brand> <city> <token> <channel> <admin_id>")
        return 0
    print(f"{'STATUS':8} {'SLUG':20} {'PAID UNTIL':12} RUNNING")
    for b in boards:
        running = "yes" if board_running(b["slug"]) else "no"
        if b["active"] and kit_db.paid_ok(b):
            status = "active"
        else:
            status = "paused"
        paid = b["paid_until"] or "free"
        print(f"{status:8} {b['slug']:20} {paid:12} {running}")
    return 0


def cmd_run(_args):
    kit_db.init_db(DATA_DB)
    started = skipped = 0
    for b in kit_db.list_boards(DATA_DB):
        if not b["active"] or not kit_db.paid_ok(b):
            print(f"⏸️  {b['slug']}: paused (inactive or unpaid) — skipped")
            skipped += 1
            continue
        if board_running(b["slug"]):
            print(f"♻️  {b['slug']}: already running")
            skipped += 1
            continue
        if start_board(b, BOARDS_DIR):
            print(f"▶️  {b['slug']}: started")
            started += 1
    print(f"done — {started} started, {skipped} skipped.")


def cmd_stop(args):
    if not args:
        print("Usage: stop <slug> | all")
        return 1
    kit_db.init_db(DATA_DB)
    targets = [b["slug"] for b in kit_db.list_boards(DATA_DB)] if args[0] == "all" else [args[0]]
    for slug in targets:
        pid_file = BOARDS_DIR / slug / "board.pid"
        if not pid_file.is_file():
            print(f"{slug}: no pid file — not running")
            continue
        try:
            pid = int(pid_file.read_text().strip())
        except (ValueError, OSError):
            print(f"{slug}: pid file unreadable")
            continue
        if terminate(pid):
            print(f"⏹️  {slug}: stopped (pid {pid})")
        else:
            print(f"{slug}: could not terminate pid {pid}")
    return 0


def cmd_paid(args):
    if len(args) != 2:
        print("Usage: paid <slug> <days>")
        return 1
    slug, days_s = args
    try:
        days = int(days_s)
    except ValueError:
        print("days must be a number.")
        return 1
    kit_db.init_db(DATA_DB)
    if not kit_db.get_board(DATA_DB, slug):
        print(f"no board '{slug}'.")
        return 1
    until = kit_db.extend_paid(DATA_DB, slug, days)
    print(f"✅ '{slug}' paid until {until}.")
    return 0


def cmd_suspend(args):
    if not args:
        print("Usage: suspend <slug>")
        return 1
    kit_db.init_db(DATA_DB)
    if not kit_db.get_board(DATA_DB, args[0]):
        print(f"no board '{args[0]}'.")
        return 1
    kit_db.set_active(DATA_DB, args[0], False)
    print(f"⏸️  '{args[0]}' suspended (digest + posting stop).")
    return 0


def cmd_activate(args):
    if not args:
        print("Usage: activate <slug>")
        return 1
    kit_db.init_db(DATA_DB)
    if not kit_db.get_board(DATA_DB, args[0]):
        print(f"no board '{args[0]}'.")
        return 1
    kit_db.set_active(DATA_DB, args[0], True)
    print(f"▶️  '{args[0]}' active.")
    return 0


def cmd_remove(args):
    if not args:
        print("Usage: remove <slug>")
        return 1
    kit_db.init_db(DATA_DB)
    if not kit_db.get_board(DATA_DB, args[0]):
        print(f"no board '{args[0]}'.")
        return 1
    if board_running(args[0]):
        pid_file = BOARDS_DIR / args[0] / "board.pid"
        pid = int(pid_file.read_text().strip())
        terminate(pid)
    kit_db.remove_board(DATA_DB, args[0])
    print(f"🗑️  '{args[0]}' removed from registry (board folder kept: boards/{args[0]}/).")
    return 0


COMMANDS = {
    "add": cmd_add, "list": cmd_list, "status": cmd_list, "run": cmd_run,
    "stop": cmd_stop, "paid": cmd_paid, "suspend": cmd_suspend,
    "activate": cmd_activate, "remove": cmd_remove,
}


def main():
    if len(sys.argv) < 2:
        usage()
        return 1
    cmd = sys.argv[1]
    fn = COMMANDS.get(cmd)
    if not fn:
        print(f"unknown command '{cmd}'.")
        usage()
        return 1
    return fn(sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())
