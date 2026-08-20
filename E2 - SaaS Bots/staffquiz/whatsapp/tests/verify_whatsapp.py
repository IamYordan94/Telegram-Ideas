"""Plain-assert verification for the WhatsApp adapter skeleton.

Runs with stdlib only — no pytest required:

    python3 tests/verify_whatsapp.py

Checks:
  1. adapter.py imports cleanly.
  2. Every contract function exists and raises NotImplementedError with a
     non-empty message when called.
  3. CONFIG_SCHEMA documents all four required env keys.
  4. parity.md exists and mentions every StaffQuiz/Telegram feature in scope.

Exit code 0 = all green; anything else prints a clear failure and exits 1.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WHATSAPP_DIR = os.path.dirname(HERE)  # .../staffquiz/whatsapp
ADAPTER_PATH = os.path.join(WHATSAPP_DIR, "adapter.py")
PARITY_PATH = os.path.join(WHATSAPP_DIR, "parity.md")

failures = []


def check(condition, message):
    if condition:
        print("  ok  - " + message)
    else:
        print("FAIL  - " + message)
        failures.append(message)


def main():
    print("StaffQuiz WhatsApp adapter — verification\n")

    # --- 1. Import the adapter (import-safe) -------------------------------
    print("[1] adapter.py imports cleanly")
    if not os.path.exists(ADAPTER_PATH):
        check(False, "adapter.py exists at " + ADAPTER_PATH)
        _finish()
    sys.path.insert(0, WHATSAPP_DIR)
    try:
        import adapter  # noqa: E402
    except Exception as exc:  # noqa: BLE001
        check(False, "import adapter raised: %r" % (exc,))
        _finish()
    check(True, "import adapter succeeded")

    # --- 2. Contract functions exist and raise NotImplementedError ----------
    print("\n[2] Contract functions present + raise NotImplementedError")
    required_functions = [
        "send_question",
        "send_flashcard",
        "send_leaderboard",
        "send_aggregate_report",
        "handle_inbound",
    ]
    for name in required_functions:
        fn = getattr(adapter, name, None)
        if not callable(fn):
            check(False, "%s is callable" % name)
            continue
        try:
            # Exercise each with representative-but-minimal args.
            if name == "handle_inbound":
                fn({})
            elif name == "send_question":
                fn("t", {"prompt": "?", "options": ["a", "b", "c"]}, 0, "31612345678")
            elif name == "send_flashcard":
                fn("t", {"front": "?", "back": "!"}, "31612345678")
            elif name in ("send_leaderboard", "send_aggregate_report"):
                fn("t", "31612345678")
        except NotImplementedError as exc:
            msg = str(exc).strip()
            check(bool(msg), "%s raises NotImplementedError with a clear message" % name)
        except Exception as exc:  # noqa: BLE001
            check(False, "%s raises NotImplementedError (got %r instead)" % (name, exc))
        else:
            check(False, "%s raises NotImplementedError (it returned instead)" % name)

    # --- 3. CONFIG_SCHEMA documents all required env keys ------------------
    print("\n[3] CONFIG_SCHEMA keys")
    schema = getattr(adapter, "CONFIG_SCHEMA", None)
    check(isinstance(schema, dict), "CONFIG_SCHEMA is a dict")
    required_keys = [
        "phone_number_id",
        "access_token",
        "webhook_verify_token",
        "app_secret",
    ]
    if isinstance(schema, dict):
        for key in required_keys:
            check(
                key in schema and isinstance(schema[key], str) and bool(schema[key].strip()),
                "CONFIG_SCHEMA documents required key '%s'" % key,
            )

    # --- 4. parity.md exists and covers every feature ----------------------
    print("\n[4] parity.md coverage")
    check(os.path.exists(PARITY_PATH), "parity.md exists at " + PARITY_PATH)
    if os.path.exists(PARITY_PATH):
        with open(PARITY_PATH, "r", encoding="utf-8") as fh:
            parity_text = fh.read().lower()
        features = {
            "daily question": ["daily question"],
            "tap-answers (4)": ["tap-answer", "4 tap-answer"],
            "flashcards": ["flashcard"],
            "reveal": ["reveal"],
            "registration": ["registration"],
            "language choice": ["language"],
            "weekly leaderboard": ["leaderboard"],
            "aggregate manager report": ["manager report", "aggregate"],
            "content intake via chat": ["content intake"],
        }
        for label, needles in features.items():
            found = any(n in parity_text for n in needles)
            check(found, "parity.md mentions feature: %s" % label)

    _finish()


def _finish():
    print()
    if failures:
        print("FAILED: %d check(s) failed." % len(failures))
        sys.exit(1)
    print("ALL CHECKS PASSED.")
    sys.exit(0)


if __name__ == "__main__":
    main()
