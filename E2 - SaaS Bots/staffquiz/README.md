# StaffQuiz — daily training quizzes + flashcards for staff

The third product on the E2 SaaS engine: a company feeds us their material (products, procedures, sales techniques — any format), and their staff get a daily 2-minute quiz + flashcards in the chat they already use. Scores, streaks, leaderboards — plus an aggregate gap report for the manager. **No per-employee monitoring** — that's both the pitch and the privacy-safe design.

## Structure

| Folder | What it is | Status |
|---|---|---|
| `core/` | Platform-neutral engine: banks (questions + flashcards), scores, streaks, aggregate report, fun-bank schedule, content intake parser | building (subagent) |
| `telegram/` | Telegram adapter: group delivery, registration, leaderboards, manager commands | building (subagent) |
| `whatsapp/` | WhatsApp adapter: Cloud API vs Baileys decision doc + skeleton | researching (subagent) |

## Why WhatsApp matters

The Netherlands is WhatsApp-dominant — for staff on the floor, WhatsApp is where they already live. Telegram is our free, fast playground (no approvals, instant demos); WhatsApp is the commercial target. The WhatsApp adapter therefore gets built as a documented spec + skeleton now, with the real integration following the Cloud API route (see `whatsapp/README.md` when it lands).

## Product principles

1. **The bot narrates, the team lead drives.** Material goes in through the bot chat (any format: PDF, typed notes, photos, links) → converted to flashcards + questions → team lead previews and approves → live.
2. **Voluntary + game-framed.** Never a test, never tied to evaluations. Leaderboard is fun; the manager report is aggregate and anonymous.
3. **Follow the company's changes.** New product launches → team lead feeds the bot → new cards and questions enter rotation the same day.
4. **Mixed banks.** Work content on work days, fun content (general knowledge, sci-fi, football) on fun days — configured per weekday.
