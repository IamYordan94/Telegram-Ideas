# I2 — Job Board NL — Build Plan (Amsterdam)

> **Goal:** A Telegram channel + bot where employers pay to post jobs; workers join free and get instant alerts. Launch in Amsterdam across 3 high-turnover sectors.

**One-liner:** We own the channel, the worker list, and the employer relationships — the marketplace is ours.

---

## 1. The 3 sectors (chosen for "sticky")

A job board is only sticky if **both sides keep coming back on their own**: workers check daily because jobs appear daily, and employers repost weekly because the sector has constant turnover. Saturated = both sides already abundant — we don't create demand, we become the connector.

| # | Sector | Why it's sticky |
|---|--------|-----------------|
| 1 | **Moving / verhuizing** | Amsterdam is a moving-heavy city (expats, students, small flats). Man-with-a-van + moving companies always need day-laborers. Gig-heavy, high churn, international workforce. *(Your pick.)* |
| 2 | **Horeca (hospitality)** | Amsterdam's most saturated labor market. Bars, restaurants, hotels always hiring — kitchen, dishwash, waiters. Highest turnover of any sector = employers repost every week = recurring revenue without re-selling. |
| 3 | **Cleaning (schoonmaak)** | Everyone hires cleaners (offices, hotels, private homes). High churn, huge international + solo supply. Directly adjacent to the workforce you already know. |

**Why these 3 together:** they're all (a) high-volume daily jobs, (b) dominated by international workers who *don't* use Indeed and live in WhatsApp/Telegram groups, and (c) high-turnover so the same employers repost constantly. That's the definition of sticky. Construction was considered but skipped — more regulated, slower, harder for international workers to access.

---

## 2. Product overview (plain language)

- **Channel:** a daily job digest — "Amsterdam jobs today: moving, horeca, cleaning."
- **Bot:** workers pick their sector(s) → get job alerts the moment a matching job goes up.
- **Each post:** job title, employer, area, pay (if public), shift/hours, a "respond" button.
- **Employers:** submit a vacancy → free (goes into the next digest) or **paid** (posted immediately + pinned/featured + shown first).
- **Premium worker tier:** €2–5/month for *instant* alerts before the daily digest.

---

## 3. The two engines

**Money engine** (who pays):
- Employers / uitzendbureaus: **€15–25 per post**, **€100 for a 10-post pack**, featured/pinned = extra.
- Premium worker tier: **€2–5/month**.
- Recurring comes from agencies on monthly packs + featured renewals.

**Traffic engine** (why people return):
- Workers join for real jobs → tell coworkers (word-of-mouth, and *your break room is the channel*).
- The **daily digest** is the habit; **instant alerts** are the premium.

---

## 4. Build plan (checkboxes)

### Phase 0 — Setup (Week 0)
- [ ] Lock the 3 sectors: Moving, Horeca, Cleaning (Amsterdam area)
- [ ] Pick the channel/bot name (options: *Jobs Amsterdam*, *WerkNL*, *AM Jobs* — decide in chat)
- [ ] Create Telegram channel + bot via @BotFather
- [ ] Stand up the repo structure for the bot code

### Phase 1 — Build the bot (Weeks 1–2, Hermes)
- [ ] Posting flow: admin/employer submits a vacancy → auto-formatted post
- [ ] Channel: scheduled daily digest
- [ ] Alert routing: worker subscribes to sector → gets matching job alerts
- [ ] "Respond" button on every post
- [ ] Paywall logic: free vs paid posts (paid = immediate + pinned/featured)
- [ ] Moderation flags (spam, dead job, fake employer)
- [ ] Basic admin panel: approve/edit/remove jobs

### Phase 2 — Seed jobs (Weeks 1–2, in parallel)
- [ ] Scraper: pull public vacancies for the 3 sectors (Indeed + public boards)
- [ ] Auto-draft daily posts so the channel has real jobs from day 1
- [ ] Label seeded posts clearly (builds trust; no fake jobs)

### Phase 3 — Grow workers (Weeks 2–6, your face)
- [ ] Post share-cards in Amsterdam laborer groups (Telegram + WhatsApp)
- [ ] Word of mouth at work — *this is the unfair advantage*
- [ ] Target: **200–500 subscribed workers** before selling anything

### Phase 4 — First paying employer (Month 2)
- [ ] Sell the first pack with one pitch: *"your vacancy in front of X workers today"*
- [ ] Turn on the premium worker tier (instant alerts)
- [ ] Target: **first 1–2 paying employers**

### Phase 5 — Recurring + sustain (Month 3+)
- [ ] Move agencies onto monthly packs
- [ ] Track **which jobs fill fastest** — that stat is the sales argument
- [ ] Bot chases renewals + flags dead listings
- [ ] Hermes runs the machine, you run the face

---

## 5. Hermes sustain role (after launch)
- Daily scrape + draft for any dead days
- Alert routing + moderation
- Renewal reminders to agencies
- Monthly stats: posts/day, fill rate, which sector grows fastest

---

## 6. Metrics that matter
- Workers subscribed (per sector)
- Jobs posted/day
- **Fill rate** (jobs marked "filled" — the number that sells employers)
- Paying employers + MRR

---

## 7. Risks
1. **Two-sided chicken-and-egg** → solved by seed jobs (channel alive day 1) + your worker access.
2. **Trust** → one fake/dead vacancy hurts badly; moderation is non-negotiable.
3. **Legal / GDPR** → only real jobs from real employers; no personal data beyond a Telegram username.

---

## 8. Open decisions (decide before building)
- [ ] Channel/bot name
- [ ] Final pricing (default: €15–25/post, €100/10-pack, premium tier €2–5/mo)
- [ ] Do we start Moving-only for week 1, or all 3 from day 1? (recommend: all 3, seed scraper covers each)

---

## 9. Approve to start
- [ ] Sectors: Moving, Horeca, Cleaning
- [ ] Amsterdam area
- [ ] Pricing as above
- [ ] Name: ______ (fill in)
