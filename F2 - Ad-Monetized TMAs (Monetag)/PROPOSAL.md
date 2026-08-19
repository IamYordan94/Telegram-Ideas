# F2 — Ad-Monetized TMAs (Monetag)

**One-liner:** more daily-loop mini apps with Monetag rewarded ads — the quiz playbook, run again.

## What it is
The exact machine that already works: a Telegram Mini App with a daily loop (one puzzle per day), a share card, and Monetag rewarded ads (watch an ad → get a hint/extra guess). Anime Daily Quiz is v1 of this machine; every new daily app is another revenue stream on the same playbook — you already have the Monetag account and the build recipe.

**Fresh app ideas (not your existing projects):**
- **Statiegeld Simulator** — daily "how much is this bag of cans worth" challenge (your world, instantly relatable to NL workers)
- **Dutch for Laborers** — one workplace phrase per day, quiz yourself, streak + share card
- **Eredivisie Predictor** — free-to-play daily football predictions, no betting (stays policy-safe)

## Money flow
- **Who pays:** ad networks (Monetag).
- **How much:** ~$2 CPM rewarded interstitial, $5–6 CPM rewarded popup (per 1,000 ad views). Small per user, real at scale.
- **How often:** payout from $5 minimum, biweekly.

## Pipe test
- **Who owns the pipe:** Monetag/Telegram. Cash flow, not a moat — traffic must stay organic or the pipe cuts.
- **Day-400:** the audience + daily habit survive; the ad network is swappable. Never buy traffic, never self-click (account ban).

## Build steps
- [ ] Pick ONE app from the ideas above
- [ ] Build: static TMA, daily seeded content (same recipe as the quiz)
- [ ] Add Monetag tag from dashboard (Telegram Mini Apps section)
- [ ] Share card with emoji grid
- [ ] Launch channel + BotFather menu button
- [ ] Verify ads show on a real phone

## Traffic engine
- Share card, daily habit, fixed release time
- Cross-promo between our own apps' channels (each app advertises the next)
- Content people actually want to share (statiegeld jokes, football banter)

## Hermes sustain role
- Build + run each app
- Daily content pipeline via cron
- Monetag dashboard: fill rates, CPM, policy compliance
- Traffic ideas + share-card experiments

## Launch speed
2–4 weeks per app.

## Risks
- Policy is strict: no bots, no self-clicks, no paid-to-click, no traffic exchanges — one violation kills the account
- CPMs are low per user — volume is everything; the share card is the real product

## First 3 moves
1. Pick the app (Statiegeld Simulator or Dutch for Laborers = strongest).
2. I build it on the quiz recipe.
3. Wire the Monetag tag and launch.
