# F1 — Mini Games with Stars

**One-liner:** a new casual game inside Telegram; extra plays and boosts cost Stars.

## What it is
A Telegram Mini App game (like the Anime Quiz, but a fresh game): daily puzzle, word game, or casual arcade. Free to play, Stars for extra lives/plays/boosters. The playbook is proven — the quiz already runs the same rail. The game just needs its own daily loop so people come back every day.

**Fresh game ideas (daily-loop shaped):**
- **Daily Case** — one short mystery per day, solve it in 2 minutes, share your score
- **Guess the Price** — one Dutch retail price to guess per day (surprisingly addictive)
- **Daily Word** — word game, 6 guesses, emoji-grid share (Wordle shape, Dutch or English)

## Money flow
- **Who pays:** players who want extra plays or boosts.
- **How much:** 5–10 Stars per extra play/booster.
- **How often:** daily impulse after the free play.

## Pipe test
- **Who owns the pipe:** official Stars rail (safe), we own the game + audience.
- **Day-400:** the game and its players are ours; only the rail is rented — and it's the safe one.

## Build steps
- [ ] Pick the game concept (Daily Case = strongest, ties into mystery appetite)
- [ ] Build: static TMA, daily seeded content (I do it — same architecture as the quiz)
- [ ] Stars buttons: extra play, hint, skip
- [ ] Share card (the growth engine — emoji grid + score)
- [ ] Launch channel + BotFather menu button
- [ ] Test the whole loop on a phone before announcing

## Traffic engine
- The share card — every share brings new players
- Daily habit: new case/puzzle every day at a fixed time
- The quiz's audience already exists and overlaps — one post there reaches them (allowed: it's your channel)

## Hermes sustain role
- Build + run the game
- Daily content generation (cases, prices, words) via cron
- Stars pricing experiments
- Weekly report: plays, shares, purchases

## Launch speed
2–4 weeks to a live game.

## Risks
- Same as B2: needs players before Stars matter — launch to the existing quiz audience first
- The daily loop must be genuinely fun or retention dies in week 2

## First 3 moves
1. Pick the game concept.
2. I build the first playable version.
3. Soft-launch to the quiz channel.
