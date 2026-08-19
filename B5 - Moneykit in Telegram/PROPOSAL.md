# B5 — Moneykit in Telegram

**One-liner:** sell the digital kit directly in Telegram with a payment bot and instant delivery.

## What it is
The money kit already sells on Gumroad/Etsy — but those platforms take a cut and own the customer. A Telegram bot is our own checkout: buyer taps the bot, pays, and gets the download link instantly in the same chat. No platform fee, no account needed for the buyer, and the customer stays *ours* (we can message them about the next kit).

## Money flow
- **Who pays:** buyers of the kit.
- **How much:** full kit price minus payment processor fee (Stripe takes ~1.5–3%, vs Gumroad's much bigger cut).
- **How often:** every sale; plus upsells right after purchase ("bundle with X for €Y").

## Pipe test
- **Who owns the pipe:** Stripe/Telegram process the payment — but the *customer relationship* is ours. That's the part that matters.
- **Day-400:** nobody can delist us. The bot, the list of buyers, the chat history — all ours.

## Build steps
- [ ] Create an order bot (@BotFather, name it after the kit)
- [ ] Connect payment (Stripe checkout or Telegram Stars — Stripe supports iDEAL, which matters in NL)
- [ ] Auto-delivery: after payment, bot sends the download link + thank-you
- [ ] Add upsell flow ("want the full bundle?")
- [ ] Put the bot link everywhere the kit is marketed
- [ ] Optional: Telegram channel for buyers — new releases, tips, offers

## Traffic engine
- Link in bio / Gumroad / Etsy descriptions ("or buy here without fees")
- Buyers share the bot when they recommend the kit
- The buyer channel creates repeat customers for the next kit

## Hermes sustain role
- Order bot maintenance + delivery fixes
- Answer buyer questions automatically (FAQ flow in the bot)
- Upsell copy and new bundle ideas
- Sales report per week

## Launch speed
Days — the bot is small and the product already exists.

## Risks
- Payment processor needs a legal entity/verification (KYC) — Stripe asks for ID/business details. One-time friction.
- Refund requests — rare for digital goods but have a 1-line policy.

## First 3 moves
1. Check the current kit files and price.
2. Build the order bot with Stripe test mode.
3. Test one real purchase end-to-end.
