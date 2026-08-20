# StaffQuiz — The Manual (v2 · no group needed)

> Everything below can be operated **from your phone in Telegram** — no laptop, no terminal.
> The laptop only has to stay **on and plugged in** (it's the server).

StaffQuiz is the third product on the E2 engine: a company's staff get a daily quiz + flashcards
in their **private chat**, trained on that company's own products and procedures. Answers are
always private; the manager sees only anonymous team statistics.

---

## The machine at a glance

| Piece | Where | What it does |
|---|---|---|
| The brain (`staffquiz/core/`) | repo, E2 folder | questions, scores, streaks, reports |
| The mouth (`staffquiz/telegram/`) | repo + laptop | the bot: @staffle_bot |
| The mouth #2 (`staffquiz/whatsapp/`) | repo, spec only | WhatsApp version (Cloud API) — later |
| Question banks | `staffquiz/data/banks/*.json` | each company has its own bank file |
| The database | laptop only (gitignored) | companies, staff, scores, payments |

**Repo:** `github.com/IamYordan94/Telegram-Ideas` → `E2 - SaaS Bots/staffquiz/`
**Live bot:** [@staffle_bot](https://t.me/staffle_bot) — running on the laptop right now.

---

## ROLE 1 — You (the owner / seller)

Your whole job is **sales + money + content quality**. Everything technical is handled
by messaging Hermes. Your daily tool is your phone.

### Your commands (private chat with @staffle_bot — only YOUR Telegram ID unlocks these)

| Command | What it does |
|---|---|
| `/tenants` | every company: status, bank, quiz time, paid-until |
| `/addcompany slug\|Name\|bank.json\|HH:MM` | add a company yourself (4-part form; group optional) |
| `/setadmin slug TELEGRAM_ID` | give the buyer their mini-key (they run /myid to find it) |
| `/paid slug 30` | +30 days subscription |
| `/suspend slug` / `/activate slug` | pause / resume a company |
| `/fun slug friday:scifi.json` | fun-day banks |
| `/feed bank.json` | add questions/cards to any bank (see formats below) |
| `/report slug` | pull a company's aggregate report |
| `/quiznow slug` / `/leaderboard slug` | post immediately (demo/testing) |

### Onboarding a client — two ways

**A. Self-serve (preferred):** the client does it themselves:
1. You give them the bot link + the price
2. They run `/createcompany slug\|Company Name\|09:00` in their DM → 14-day free trial, they become admin
3. They `/feed` their content (or send you a PDF → Hermes converts → you `/feed` it)
4. They `/invite` → share the staff link
5. Trial ends → they pay → you `/paid slug 30`

**B. You-managed:** you run `/addcompany …`, then `/setadmin` with their ID,
then hand them the link from `/invite`.

### Pricing (locked)

- **€99 one-time setup** (content conversion + onboarding)
- **€49/mo** up to 25 staff · **€79/mo** up to 50
- First month free / 14-day trial for self-serve

### The money loop

Client pays → you run `/paid slug 30` → bot keeps serving until that date.
Unpaid companies stop posting automatically (they stay in the list).

---

## ROLE 2 — The manager (your client)

Everything from their phone, in the private chat with @staffle_bot.

| Step | What they do |
|---|---|
| 1. Sign up | `/createcompany cafe\|Café Amsterdam\|09:00` → 14-day trial |
| 2. Feed content | `/feed` → paste lines (formats below) → preview → ✅ approve |
| 3. Invite staff | `/invite` → share the link in their WhatsApp group |
| 4. Daily | nothing — the quiz drops at 09:00 |
| 5. Weekly | `/report` → anonymous gap report (which topics the team misses) |
| 6. Changes | new product? `/feed` the new facts — live next day |

### The /feed formats (copy these exactly)

```
Q: What's our refund policy? | A) 14 days | B) 30 days | C) 7 days | D) Never | answer: A | topic: service | explain: We always refund within 14 days.
CARD: Product 15 price | BACK: €89 with 2-year warranty | topic: products
```

- One item per line. `Q:` makes a question (needs 4 options + `answer:` letter).
- `CARD:` makes a flashcard (front + BACK).
- `topic:` groups items in the report. Wrong format = the bot says which line is wrong.
- Documents (PDF, photos, links) → send them to Hermes instead; Hermes converts.

### Their commands

| Command | Who | What |
|---|---|---|
| `/createcompany` | anyone | sign up, 14-day trial |
| `/feed` | company admin | add content (own bank only) |
| `/invite` | company admin | staff registration link |
| `/report` | company admin | aggregate gap report (own company only) |
| `/myid` | anyone | their numeric Telegram ID (for /setadmin) |
| `/start` / `/me` | anyone | register / own stats |

**Privacy:** the manager NEVER sees who answered what. Reports are team-level only.
That's a legal feature, not a missing one.

---

## ROLE 3 — The employee

| Step | What they do |
|---|---|
| 1. Tap the invite link | opens @staffle_bot → name → department → language (1 minute) |
| 2. Daily | the question arrives in their DM at company time → tap A/B/C/D |
| 3. After answering | instant ✅/❌ + explanation + streak + week score (their DM) |
| 4. Sunday | leaderboard in their DM — compare with colleagues over coffee |
| 5. Anytime | `/me` for streak and score |

Nobody ever sees their answers. Nobody. The leaderboard shows who's on top, never who was wrong.

---

## The daily loop (the product, in one picture)

```
09:00   question + flashcard → every employee's DM (private)
        answers recorded → personal feedback instantly
Sunday  leaderboard → everyone's DM
Weekly  manager runs /report → sees topic gaps, not people
Monthly manager pays → /paid → loop continues
```

---

## Where everything lives

| What | Where |
|---|---|
| Repo root | `github.com/IamYordan94/Telegram-Ideas` |
| StaffQuiz | `E2 - SaaS Bots/staffquiz/` — `core/` (brain) · `telegram/` (bot) · `whatsapp/` (spec) |
| This manual | `E2 - SaaS Bots/staffquiz/MANUAL.md` |
| Build plan + pricing | `E2 - SaaS Bots/BUILD_PLAN.md` |
| Feature roadmap (1–6) | `E2 - SaaS Bots/staffquiz/FEATURES-SPEC.md` |
| WhatsApp research | `E2 - SaaS Bots/staffquiz/whatsapp/README.md` + `parity.md` |
| Sister products | `E2 - SaaS Bots/saas-quiz/` (QuizDay, €19 channels) · `saas-kit/` (BoardKit, €49 job boards) |

## Live right now

- **@staffle_bot** running on the laptop — demo company `canal` (Canal Tours Amsterdam, 30 questions + 8 flashcards, trial until 2026-09-03)
- Demo tenant `demo` (customer-service bank) also live
- WerkNL job board running separately (I2 folder)

**The one rule:** the laptop stays on + plugged in. Everything else works from your phone.
