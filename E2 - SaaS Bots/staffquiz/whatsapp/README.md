# StaffQuiz on WhatsApp — decision & go-live plan

*Plain-language decision doc. For the technical message-flow contract, see
`adapter.py`; for the feature-by-feature mapping, see `parity.md`; for the
source of every claim, see `references.md`.*

---

## The short version

StaffQuiz should go to market on WhatsApp through the **official WhatsApp
Business Cloud API** (Meta's hosted, pay-as-you-go platform). We keep the
unofficial **Baileys** library only as an internal demo toy, never in front of
customers — because Baileys runs on a personal WhatsApp number and can get that
number banned with zero recourse, which is an unacceptable risk for a B2B
product whose whole promise is "your team's daily training just works."

## Why this decision at all

The Netherlands is a WhatsApp country. Staff on the floor — horeca, facilities,
logistics — already live in WhatsApp, and Newcom's national social-media
research shows daily WhatsApp use is still *growing* there. Telegram is our
free playground for building and demoing fast; WhatsApp is where the paying
customers are. So the question isn't *whether* to do WhatsApp, but *how*.

There are exactly two ways to build a WhatsApp bot, and they could not be more
different:

1. **The official Cloud API** — Meta's own platform for businesses. You register
   a business, a phone number, and an app with Meta, then talk to WhatsApp over
   a normal web API. You pay per message. It is legal, stable, and cannot get
   you banned.
2. **Baileys** — a community library that pretends to be the WhatsApp *web
   app* (reverse-engineered). Free to run, no approval, works immediately —
   but it runs on a consumer WhatsApp account and violates WhatsApp's terms of
   service, so your number can be banned at any moment.

Here they are side by side:

| | **Cloud API (recommended)** | **Baileys (unofficial)** |
|---|---|---|
| **What you need** | Meta Business account, a Meta developer app, a dedicated phone number, a display name, and (for scale) business verification. | Any personal WhatsApp number + a Node.js server. |
| **Cost model** | Free to sign up. Per-message fees by category (utility is cheapest) and by the recipient's country; the first 1,000 service conversations a month are free; conversations a customer starts are free to answer within 24 hours. For a 30–40 person tenant this is tens of euros a month at most. | €0 to Meta, but you pay in **risk** and in developer time babysitting a fragile reverse-engineered connection. |
| **Ban risk** | None — it's Meta's own platform. | **Real and permanent.** WhatsApp bans numbers that automate outside the official API, with no appeal. Lose the number = lose every tenant attached to it. |
| **Integration effort** | Moderate: HTTPS/JSON API (works fine from our Python stack), but requires Meta account setup, number verification, template approval, and webhook plumbing. | Low to start (it's a drop-in library), high to keep (it breaks when WhatsApp changes the web protocol, and it's Node.js — not our Python stack). |
| **Group messaging** | **Not supported** — 1:1 only. (The one real feature cost; see below.) | Technically can join groups, but using it for bulk/automated group messaging is exactly what gets you banned. |
| **Verdict** | ✅ **Go to market on this.** | ⛔ Internal demo only — and only ever on a throwaway number. |

**Recommendation:** Cloud API. Baileys is kept purely so we can *show* the
product working in a demo without waiting for Meta's approval — never as the
production path, and never pointed at a real customer.

---

## The one real feature cost (say it out loud)

WhatsApp's business platform is built for **1:1 customer conversations**, not
for group chat bots. Concretely:

- **The bot cannot post to a WhatsApp group.** Telegram lets us drop the daily
  quiz and leaderboard into a team group; on WhatsApp, every message goes to
  each person individually. This isn't a blocker — arguably 1:1 is *better*
  for a daily 2-minute habit — but it means "the shared leaderboard moment"
  becomes "everyone gets their own leaderboard text."
- **A daily quiz answer has at most 3 buttons**, not 4. WhatsApp reply buttons
  cap at three (and 20 characters each). We standardize questions to 3 answers,
  or use a list-style message for 4.
- **No "tap to reveal" for flashcards.** WhatsApp has no hidden-text/spoiler.
  We substitute a two-step flow: the card front with a "Show answer" button,
  then the answer as a follow-up message.
- **The bot can't message staff out of the blue.** Outside a 24-hour window
  that *the staff member* opens by messaging first, every outbound message must
  be a pre-approved template (or come via a free "click-to-chat" entry point).
  The daily quiz push therefore ships as an approved utility template — plan for
  that review.

All six StaffQuiz features still ship; `parity.md` maps each one to its
WhatsApp equivalent and its substitute. None of the four above is fatal.

---

## Recommended go-live path (Cloud API)

Realistic, in order, with honest time estimates:

| Step | What you actually do | Realistic time |
|---|---|---|
| 1. **Meta Business account** | Create a Business Manager account at business.facebook.com (or reuse one). Verify your business identity there. | 1–3 days (mostly waiting on identity checks) |
| 2. **Phone number** | Get a number that is *not* on consumer WhatsApp — a separate business mobile/SIP number. You'll need to receive a one-time SMS or call on it. | 1–2 days (sourcing a SIM/number) |
| 3. **Developer app** | Create a Meta developer app, add the "WhatsApp" product, and link it to the business account. | 1–2 hours |
| 4. **Register the number** | Add the number to the app: set the **display name** (reviewed by Meta), verify the number via OTP. | Hours for the technical part; **display-name review up to a few days** |
| 5. **Test mode** | Meta lets you message up to 5 "test" numbers immediately, no verification needed. Build the whole integration against this. | Start the same day |
| 6. **Webhook** | Point Meta at our endpoint; set a verify token; wire inbound messages, button presses, and status updates. | 1–2 days |
| 7. **Business verification** | Submit Meta Business verification (Business Settings → Security Center). This unlocks production scale (raising the messaging tier) and is document-based. | **Days to weeks** — the long pole; docs can bounce back for revision |
| 8. **Templates** | Submit the daily-quiz reminder and any other proactive messages as **utility** templates for approval. | Days (usually fast for utility) |
| 9. **Go live** | Flip the tenant from test numbers to real staff numbers. | — |

**Net:** the *engineering* is days; the *paperwork* (Meta verification +
display-name + template review) is where the calendar goes, realistically
**1–4 weeks** end-to-end before the first real tenant is live — and it's the
same for every business, not something we can compress.

### What you can do in parallel (don't wait)
- Build the entire adapter against **test mode** (step 5) — no approval needed.
- Ship and validate the **Telegram** adapter to real customers meanwhile; the
  core engine is shared, so WhatsApp inherits everything except the messaging
  layer.
- Prepare the exact template text and display name early so the reviews are
  one-and-done.

---

## Honest risks

1. **Approval time is unpredictable.** Meta's business verification and display
   name / template reviews are the real schedule risk (days to weeks, and
   rejections restart the clock). Don't promise a customer a WhatsApp launch
   date until step 7 is done.
2. **Group messaging is gone.** We cannot reproduce Telegram's group experience.
   If a customer's mental model is "our team talks in a group," we must re-set
   that expectation to "each person gets their own daily message." (For
   multilingual shift workers, 1:1 in their own language is arguably the better
   product anyway.)
3. **3-button cap and template rules** constrain the quiz UX. We standardize on
   3-answer questions and an approved utility template for the daily push.
4. **NL market adoption is *not* the risk** — it's the reason. WhatsApp is
   dominant and still growing in the Netherlands, so the market is there; the
   risk is purely execution (approval + the group/button limitations above).
5. **Baileys temptation.** It will always look like the "fast" path for a
   demo. Use it only on a throwaway number, never with a real tenant's staff,
   and never brand it. A banned number is unrecoverable.

## Sources

Every claim above is cited in [`references.md`](references.md). The pricing
model is documented on Meta's pricing page and in third-party pricing
breakdowns; the Cloud API/On-Premises facts come from Meta's sunset notice;
Baileys' ToS position comes from its own README disclaimer; NL adoption comes
from Newcom's Nationale Social Media Onderzoek.
