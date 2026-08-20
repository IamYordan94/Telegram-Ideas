"""StaffQuiz (Telegram) — entry point with single-instance PID guard. Usage: python3 main.py"""
import ctypes
import os
import sys

PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "staffquiz.pid")


def pid_is_alive(pid: int) -> bool:
    """True if a process with this pid exists on Windows (no signal needed)."""
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if handle:
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    return False


def main():
    if os.path.exists(PID_FILE):
        try:
            old = int(open(PID_FILE).read().strip())
        except (ValueError, OSError):
            old = 0
        if old and pid_is_alive(old):
            print(f"StaffQuiz already running (pid {old}) — exiting.")
            return

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    try:
        # main.py lives inside telegram/, so import the sibling bot module directly.
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from bot import main as bot_main
        bot_main()
    finally:
        try:
            os.remove(PID_FILE)
        except OSError:
            pass


if __name__ == "__main__":
    main()
