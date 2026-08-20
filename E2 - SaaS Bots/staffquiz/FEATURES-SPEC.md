# StaffQuiz — Feature Spec 1–6

Order matters: **Phase 1** ships first (simple, small code deltas), **Phase 2** follows once the first companies are live. All six reuse the core engine (`staffquiz/core/`) — no feature requires a rebuild.

---

## Feature 1 — Spaced repetition (re-ask what people got wrong)

**What it is:** questions the team keeps missing come back automatically until they stick. Memory science: a fact is remembered when it's re-tested at growing intervals.

**How staff see it (v1, Phase 1):** the daily post includes one extra section — "🔁 Review: 60% missed this one" — the question with the lowest correct % from the last 14 days, re-asked with full buttons.

**How staff see it (v2, Phase 2):** personal DM reviews — each employee gets their *own* missed questions DM'd to them on a schedule (next day, then +3, +7, +14 days; clears after 2 correct).

**Data & code:**
- v1: `core/db.py` — new function `weakest_question(tenant_id, days=14, min_answers=3)` → item index + correct % (from answers, joined to the bank). `telegram/bot.py` — daily job posts review item after the main question.
- v2: new table `reviews(employee_id, item_index, next_at, correct_streak)`; a daily loop job finds due reviews, DMs them, updates the interval.

**Acceptance:** weakest-question math verified in `tests/`; review post appears in the group without disturbing the normal daily flow.

---

## Feature 2 — Scenario of the day

**What it is:** "A customer says your quote is too expensive. You: A / B / C / D" — sales/situational judgment training instead of facts.

**How staff see it:** a question with a 🎭 header instead of 🎯, otherwise identical (buttons, scores, leaderboard).

**Data & code:**
- `core/bank.py` — optional `"kind": "scenario"` field on question items (default "question"); validation unchanged otherwise.
- `telegram/bot.py` — header emoji switch on `kind`; same callback flow.
- Scenarios share banks with normal questions; a bank can be all-scenario ("sales-drills.json") or mixed.

**Acceptance:** bank with mixed kinds loads, builds correct headers, and both kinds score identically.

---

## Feature 3 — Multilingual per employee (NL / EN / PL / UA)

**What it is:** the same daily question, in each employee's own language. Critical for the NL market (shift workers with 2–4 languages on one floor).

**Honest trade-off to decide when we build it:** the group shows ONE message. Two designs:
- **Phase A (start simple):** stacked group post — question + options in each language, one block under the other (max 2 languages per company to keep it readable). Buttons stay A–D.
- **Phase B (full):** per-employee DM delivery in their chosen language; the group gets only the announcement + leaderboard. Better UX for 3–4 languages; loses the shared "we answered together" moment in the group.

**Data & code:**
- Phase A: bank item gains optional `"q_lang"` and `"options_lang"` maps (language code → translated text); `telegram/bot.py` builder renders all configured languages.
- Phase B: `employees.language` (already in schema) drives DM delivery; daily job becomes per-employee for question sending, group keeps leaderboard only.
- Translations are content work: I generate them per bank (sustain task), or the client provides.

**Acceptance:** a two-language bank renders both blocks in one post; per-employee language is stored at registration (already built).

---

## Feature 4 — Certification badges

**What it is:** complete a topic → permanent badge ("Allergen Master 🏅"). Proof of training that managers (and auditors — HACCP!) love.

**How staff see it:** when they hit the threshold (e.g. ≥80% correct on a topic, min 5 answers), the bot announces it in the group: "🏅 Mark earned: Allergen Master". Badges are permanent and listed in the manager report as counts.

**Data & code:**
- `core/db.py` — new table `badges(employee_id, topic, earned_at, UNIQUE(employee_id, topic))`; function `check_badges(tenant_id, threshold=0.8, min_answers=5)` returns newly-earned badge events (never re-announces old ones).
- `telegram/bot.py` — weekly job calls `check_badges`, posts new ones as a single batch message (no spam per person).
- Aggregate only in the manager report: "Badges this month: Allergen Master ×4" — no per-employee list (privacy design).

**Acceptance:** threshold math verified; repeated runs never re-announce; report shows counts only.

---

## Feature 5 — New-hire onboarding pack

**What it is:** a new employee's first 14 days get a personal path — daily "know the company" cards + basics quiz, in their language. Replaces the handbook nobody reads.

**How staff see it:** day 1 of work: register in the bot → from day 1 the bot DMs them personally: welcome card, product cards, a 3-question basics quiz, day by day for 14 days. After that, they merge into the normal group rhythm.

**Data & code:**
- `core/db.py` — `employees.joined_at` (set at registration); tenants get `onboarding_bank` (nullable) + `onboarding_days` (default 14).
- New table `onboarding_progress(employee_id, day_index, done_at)`.
- `telegram/bot.py` — daily job: for each employee with `joined_at` within N days, DM the next onboarding item (flashcards + a short question) and record progress. Group flow untouched.
- Onboarding bank is just a normal bank (flashcards + questions) — no schema change needed.

**Acceptance:** fresh employee gets day-1 DM on registration day; the sequence advances one per day; ends silently after day N.

---

## Feature 6 — Team battles

**What it is:** departments compete, not just individuals. "Service vs Sales — this week's winner 🏆".

**How staff see it:** the Sunday leaderboard gains a team section: department totals + a crown for the winning department. Bragging rights drive daily participation.

**Data & code:**
- `core/db.py` — `department_totals(tenant_id, days=7)` → per-department correct sums + participation; `department_board` (already planned in core) covers winners.
- `telegram/bot.py` — Sunday job renders: individual top 10, then team standings with 🏆.
- Optional later: battle mode toggle per tenant (when OFF, hide team section).

**Acceptance:** totals math verified; Sunday post shows both sections; empty departments don't appear.

---

## Build order

- [ ] Phase 1: Feature 2 (scenario kind) — smallest delta
- [ ] Phase 1: Feature 1 v1 (group review question)
- [ ] Phase 1: Feature 6 (team standings)
- [ ] Phase 1: Feature 4 (badges)
- [ ] Phase 2: Feature 3 (multilingual — decide Phase A/B with the first 2-language customer)
- [ ] Phase 2: Feature 5 (onboarding pack)
- [ ] Phase 2: Feature 1 v2 (personal DM reviews)

Every feature lands with: core function + adapter rendering + tests in `tests/verify_core.py` / `tests/verify_telegram.py` + a README line. Green verifier before commit, per house rule.
