# E2 — SaaS Bots: BUILD PLAN

Two products, both repackaging machines we already own. One laptop runs everything — we own the pipe.

## The two products

| Product | What it sells | Price (proposed — YOUR call) | Status |
|---|---|---|---|
| **QuizDay** — Daily Quiz Engine | Every day one quiz question drops into the customer's channel, branded with their name; scores + weekly leaderboard. Members get a daily reason to come back. | €19/mo | building |
| **BoardKit** — Job Board Kit | The WerkNL machine for another city/sector: own bot + channel + job flow + daily digest, set up in ~30 min. Customer brings the audience; we run the machine. | €49/mo | building |

## Architecture (plain language)

- **QuizDay:** ONE bot (ours) posts into many customer channels. Each customer = one row in a database: name, channel, question bank, post time, paid-until. Single process.
- **BoardKit:** each customer gets their OWN bot — a copy of the WerkNL machine with their name and city (and its own job database). A manager script starts/stops all boards. Several small processes.
- Both use simple local databases; nothing in the cloud; laptop stays on (exactly like WerkNL runs today).

## Money — v1

Manual and zero-friction: customer pays (Tikkie / Stripe link), we run `/paid <customer> <days>` and the bot keeps serving them until that date. No automatic billing yet — Stripe or Stars subscriptions come later only if churn numbers justify building it.

## Tasks

- [ ] Make WerkNL re-brandable (BoardKit): brand name, city, channel handle become settings — WerkNL keeps its defaults untouched
- [ ] BoardKit manager: add a board, start/stop all boards, list, extend subscription, suspend
- [ ] QuizDay engine: question banks, daily post + answer buttons, scoring, weekly leaderboard
- [ ] QuizDay banks: anime (150 questions, converted) + general knowledge (25). Football/crypto/etc. generated when the first customer asks for a topic
- [ ] Tests for both (plain Python, run from terminal, no installs)
- [ ] Demo tenants on our own channels (showroom = "this bot runs this channel")
- [ ] Onboarding sheet for customers: 2-minute BotFather guide (they create the bot, we do everything else)
- [ ] PRICING final: you decide the numbers (defaults €19 / €49)
- [ ] First 10 customers (5 quiz, 5 boards) — free first month, collect feedback, then charge

## Honest risks

- **The laptop is the infrastructure.** If it's off, every board is down → stays on + plugged, same discipline as WerkNL.
- **Free competitors:** Telegram's built-in scheduler beats us at "scheduling" — so we don't sell scheduling. We sell a daily engagement habit (QuizDay) and a fully running job board (BoardKit).
- **Churn:** fought with the weekly leaderboard (habit) and boards that earn the customer more than they cost us.

## Sustain role (what Hermes keeps doing after launch)

- Uptime checks + restart scripts
- Top up question banks per customer topic (the recurring work)
- Monthly churn report: who cancels, why, what to build next
- Customer support: questions arrive → I draft answers via the owner bot

## Names

Working names: **QuizDay** (quiz engine) and **BoardKit** (job board kit). Placeholders — rename freely.
