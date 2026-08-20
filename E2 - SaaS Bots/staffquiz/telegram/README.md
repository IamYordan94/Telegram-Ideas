# StaffQuiz — Telegram adapter (v2 · DM-only)

> **Canonical guide for operating the product: [`../MANUAL.md`](../MANUAL.md)** —
> owner, manager, and employee roles, all commands, pricing, and the customer journey.
> This README covers the technical run/debug side only.

## Running it

1. `.env` in this folder: `STAFFQUIZ_BOT_TOKEN`, `STAFFQUIZ_OWNER_ADMIN_ID` (owner's Telegram id), optional `STAFFQUIZ_BOT_USERNAME`.
2. `python3 main.py`. PID guard file: `staffquiz.pid` — never run twice (guard exits).
3. Verify: process log shows `getMe 200` + `Application started`.

## Architecture (v2)

- **Pure DM delivery.** Questions, flashcards, and the Sunday leaderboard go to each
  registered employee's private chat. Answers are never visible to anyone else.
- A tenant may optionally carry a `group_id` (scoreboard mirror): the flashcard and a
  "question is out" announcement are also posted there. `/addcompany` 5-part form sets it;
  4-part form and `/createcompany` leave it empty.
- One bot serves many companies; each company has its own bank file (`slug.json`),
  created by cloning `starter.json` on `/createcompany`.

## Verifying

- `python3 tests/verify_telegram.py` — pure checks (no network): builders, callbacks,
  permissions, parsers, deep links, feed permissioning.
- Core suite: `cd ../core && python3 tests/verify_core.py`.
