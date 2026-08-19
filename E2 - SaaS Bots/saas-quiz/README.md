# QuizDay — the daily quiz engine (one bot, many channels)

One Telegram bot posts a daily quiz question into each customer's channel, branded with their name. Members tap A/B/C/D, get a toast + a DM with the explanation and their weekly score. Every week the bot posts a leaderboard. Customers pay a monthly subscription.

## Running it

1. Create a bot with @BotFather (once — the shared quiz bot).
2. Copy `.env.example` → `.env`, fill `QUIZ_BOT_TOKEN` (owner id is already set).
3. `python3 main.py` (or double-click `start_quiz.bat`). Keep the laptop on.

## Adding a customer

1. The customer creates a **public channel** and adds the quiz bot as **admin** (post messages).
2. In the quiz bot's chat (as owner):

```
/addquiz psv|PSV Quiz|@psv_channel|football.json|09:00
/paid psv 30          # +30 days (they can start with a free month: /paid psv 0 works, or just skip)
/quiznow psv          # test: post today's question right now
/leaderboard psv      # test: post the leaderboard now
/suspend psv          # stop posting (keeps data)
/activate psv         # resume
/tenants              # all customers + status
/banks                # available question banks
```

- `channel` in /addquiz can be `-100...` (numeric) or `@username`. The bot must already be admin there, or Telegram refuses.
- `paid_until` empty = unlimited (use for our own demo channels). Once set, questions stop posting the day after it passes — but old buttons keep working.
- One question per day at the customer's time; the bank cycles; a second lap through the bank counts as new questions (scores key on the running number).

## Question banks

`data/banks/*.json` — each bank is a JSON list:

```json
{"q": "Question?", "options": ["A", "B", "C", "D"], "answer": 0, "explain": "why"}
```

- `answer` = index of the correct option (0–3).
- Banks shipped: `anime.json` (150), `general.json` (30). New topics get generated when a customer asks — that's the recurring sustain work.

## Verification

`python3 tests/verify_quiz.py` — banks, rotation, tenant lifecycle, scoring, leaderboard. No pytest needed.

## Honest limits

- One bot serves every channel, so the bot's public name is shared. Branding lives in the post header ("PSV Quiz — question #12"), which is what members see.
- Scores live in one database keyed by tenant — customers never see each other's data.
- If the laptop is off, no quizzes go out. Same discipline as WerkNL.
