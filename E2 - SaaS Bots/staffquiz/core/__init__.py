"""StaffQuiz core engine — platform-neutral quiz/flashcard logic.

This package is the pure-Python, stdlib-only brain of StaffQuiz:

* ``bank``      — question bank v2 schema, loading, rotation, de-duplication
* ``db``        — sqlite persistence (tenants, employees, answers, aggregates)
* ``schedule``  — per-weekday bank scheduling and fun-bank config parsing
* ``content``   — typed-notes content intake parser and bank preview export

Nothing in this package depends on a chat platform (Telegram, Slack, etc.);
platform adapters live elsewhere and call into these functions.
"""
