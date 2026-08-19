# B2 — Stars Extra Plays (Anime Quiz)

**One-liner:** keep the free daily quiz, sell extra plays with Telegram Stars.

## What it is
Anime Daily Quiz already has the hardest part: a daily loop people come back to. This adds the money rail. Free play per day (as now), then each extra play costs Stars. Players buy Stars inside Telegram, spend them in the app, we withdraw the earnings as TON and sell for euros.

## Money flow
- **Who pays:** quiz players who want more than one play per day.
- **How much:** 5–10 Stars per extra play (€0.05–0.10) or star packs (3 plays / 10 plays / skip-a-hard-question hint).
- **How often:** impulse — right after the daily play ends, the "one more quiz?" button appears.

## Pipe test
- **Who owns the pipe:** Telegram (Stars rail) — but it's the *official* rail, 100% policy-safe, no ad network, no ban risk.
- **Day-400:** Telegram takes its share, we keep ours. No gray zone at all.

## Build steps
- [ ] Add a Stars invoice button in the app after the daily play
- [ ] Set prices: extra play, 3-pack, hint
- [ ] Track plays-per-user so we can tune the price
- [ ] Enable Stars withdrawal (Stars → TON → euros)
- [ ] Redeploy, test the purchase flow on a phone

## Traffic engine
Already exists: the daily share card (🟩/🟥 grid). Every share brings a new player; more players = more daily plays = more payers.

## Hermes sustain role
- Daily question pipeline (already running)
- Price testing: raise/lower cost, watch conversion
- New spend moments: hints, streak insurance ("lost your streak? 15 Stars to save it"), special event quizzes
- Weekly revenue report

## Launch speed
Days. The app is live; this is one new feature.

## Risks
- Players may not care enough to pay — fix by making the free play feel scarce and the score competitive.
- Low player count = low revenue. The share card is the growth lever, ads come second.

## First 3 moves
1. Check the current Anime Daily Quiz code and Monetag setup.
2. Add the Stars button after the daily play.
3. Post one teaser in the channel: "extra plays now live."
