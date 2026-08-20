# StaffQuiz — Telegram adapter (group delivery)

One bot posts a daily quiz question **or** flashcard into each company's group, branded with their name. Staff tap A/B/C/D, get a toast + a DM with the explanation, their streak and week score. Every Sunday the bot posts a leaderboard (top 10 + department champions). The manager gets an **aggregate, anonymous** gap report — never per-employee data.

This adapter sits on top of the platform-neutral `staffquiz/core` engine (banks, scores, streaks, aggregate report, fun-bank schedule) in the parent folder.

## Running it

1. Create the bot once with **@BotFather** → copy the token.
2. `cp .env.example .env` and fill `STAFFQUIZ_BOT_TOKEN` (owner id is already set to `5472865187`).
3. `python3 main.py` from this folder. Keep the laptop on (it's the infrastructure).

```
cd staffquiz/telegram
python3 main.py
```

Optional `.env` overrides: `STAFFQUIZ_DB_PATH` (default `telegram/data/staffquiz.db`), `STAFFQUIZ_BANKS_DIR` (default `staffquiz/data/banks`).

## Onboarding a company

1. The customer creates a **group** (or supergroup) and adds the bot as **admin** (post messages).
2. In the bot's chat, as owner (`STAFFQUIZ_OWNER_ADMIN_ID`):

```
/addcompany acme|Acme Corp|-1001234567890|general.json|09:00
/paid acme 30          # +30 days subscription (free month to start: skip or /paid acme 0)
/quiznow acme          # test: post today's item right now
/leaderboard acme      # test: post the leaderboard now
```

3. Staff join the group and run `/start` to register (name → department → language). `/start` again anytime to update. `/me` shows their stats.

## Command cheat-sheet

**Owner** (gated on `STAFFQUIZ_OWNER_ADMIN_ID`):

| Command | What it does |
|---|---|
| `/addcompany slug\|Name\|group_id\|bank\|HH:MM` | add a company, resolve the group (must be group/supergroup), schedule daily + weekly jobs |
| `/fun slug friday:scifi.json,saturday:general.json` | fun-bank overrides per weekday (other days keep the default bank) |
| `/report slug` | aggregate report → DM: per-topic correct %, participation %, weakest topics, active employees |
| `/quiznow slug` · `/leaderboard slug` | post today's item / this week's leaderboard now (test) |
| `/tenants` | all companies + status |
| `/paid slug 30` | extend subscription by N days |
| `/suspend slug` · `/activate slug` | pause / resume posting (keeps data) |

**Staff** (anyone): `/start` (register/update), `/me` (name, department, streak, week score), `/cancel`.

- `group_id` in `/addcompany` can be `-100…` (numeric) or `@username`; the bot must already be admin there.
- `paid_until` empty = unlimited (our demo groups). Once set, posting stops the day after it lapses (old buttons keep working).

## Question banks

`staffquiz/data/banks/*.json` — a JSON list of items. Two shapes (the `type` field is required):

```json
{"type": "question",  "q": "Which product…?", "options": ["A", "B", "C", "D"], "answer": 0, "explain": "why", "topic": "products"}
{"type": "flashcard", "front": "H2O", "back": "water", "topic": "chem"}
```

- `answer` = index of the correct option (0–3).
- `topic` feeds the aggregate report's per-topic breakdown (falls back to the bank filename when absent).
- One item per day; the bank cycles, so a second lap counts as fresh items.

## Privacy design

The `/report` command is **aggregate and anonymous by design** — per-topic correct %, participation, weakest topics, active-employee count. There are **no per-employee lines**, and there never will be: managers see gaps, not people. This is both the sales pitch and the legal-safe posture (the core `db` module deliberately exposes no per-employee answer export). The weekly leaderboard ranks employees — that's the game, and it's voluntary.

## Verification

```
cd staffquiz/telegram
python3 tests/verify_telegram.py
```

No pytest, no network, no token. Exercises config defaults, HTML escaping in the message builders, the flashcard spoiler markup, callback encode/decode edge cases, core schedule/db integration, and the adapter-local subscription + post-history tables. Prints `ALL OK` on success.

## Notes for the parallel core

The adapter consumes the core's public API (`bank.load_bank`, `bank.next_item`, `schedule.pick_bank`, `schedule.parse_fun_config`, and `db.*`). Three things the core does **not** provide are handled inside this adapter: the `paid_until` subscription column (added via `ALTER TABLE` on first run), tenant lookup by group id, and a `telegram_posts` table that records which item was posted at each `q_index` so answers grade correctly even when the item came from a fun-override bank.
