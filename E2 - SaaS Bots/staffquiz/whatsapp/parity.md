# StaffQuiz — Telegram → WhatsApp feature parity

This document maps every StaffQuiz feature as built for Telegram onto its
WhatsApp equivalent, and — just as important — states what **cannot** be
reproduced on WhatsApp and what we substitute instead.

**Headline:** WhatsApp Cloud API is a *customer-service / business-messaging*
platform, not a chat-bot playground. It is **1:1 only** (no groups) and is
built around an opt-in, template-gated messaging model. Three things break
cleanly:

1. **No groups.** Telegram delivers the daily quiz and leaderboard to a team
   group; WhatsApp Cloud API cannot send to groups at all. Everything becomes
   1:1.
2. **Only 3 reply buttons.** Telegram inline keyboards fit 4 (or more)
   answers; WhatsApp reply buttons cap at **3**.
3. **No native "reveal"/spoiler.** Telegram can hide answer text behind a
   button/spoiler; WhatsApp has no hidden-text reveal in the Cloud API.

Everything else has a workable equivalent, listed below.

---

## Feature parity table

| StaffQuiz feature (Telegram) | WhatsApp equivalent | Not possible on WhatsApp → substitute |
|---|---|---|
| **Daily question with 4 tap-answers** | **Interactive reply-button message** ("interactive" type, `button` subtype). Each answer is a button; the button `id` (e.g. `q0_a2`) comes back in the webhook so the engine can score it. | **4 answers don't fit** — reply buttons cap at **3** (`title` also caps at 20 chars, no emoji/markdown). Substitute: (a) ship 3-answer questions on WhatsApp, or (b) keep 4 answers using an **interactive list message** (up to 10 rows, but it's a tap-menu-then-pick two-step and feels slower), or (c) number answers 1–4 in the body text and accept a typed "1/2/3/4" reply. **Recommendation: standardize on 3-answer questions** (one shared question bank where the 4th option is dropped or the distractors are trimmed). |
| **Flashcards with reveal** | Two-step flow: send the card **front** with a single **"Show answer" reply button**, then send the **back** as a plain text message when the button press arrives. | **No native spoiler/hidden text.** Telegram can wrap the answer so it's hidden until tapped; WhatsApp Cloud API has no such element. The two-message button flow is the honest substitute. "View once" media exists but only self-destructs images/video — it does not gate a reveal. |
| **Registration with language choice** | **First-message onboarding flow.** The staff member texts the business number (they *must* start — WhatsApp won't let a business message them first without consent/template). The bot replies with a welcome + either a **reply-button message** (3 buttons: e.g. NL / EN / PL) or a **list message** (more languages, up to 10) to pick their language, then confirms and stores the choice. | Nothing blocking — this maps cleanly. Only caveat: language list >3 needs a list message (slower UX) rather than buttons. |
| **Weekly leaderboard** | **Plain-text message, sent 1:1 to every participant.** Each person gets their own rank line ("You: #3, 14/15") plus a top-N table. | **No shared group leaderboard.** The fun "we're all on this board together" group moment is lost. Substitute: personalized 1:1 rank message (arguably more motivating per-person), optionally with a per-team aggregate. You cannot post one board to a room. |
| **Aggregate manager report** | **Plain text and/or a document (PDF/CSV) sent 1:1 to the manager's number.** | Nothing blocking. Cloud API supports text and `document` media; the report is aggregate-and-anonymous by design, which fits WhatsApp's data-minimization posture well. |
| **Content intake via chat** (team lead feeds PDF/typed notes/photos/links) | **Inbound webhook.** The bot receives `text`, `image`, and `document` messages from the team lead; media is fetched via the Cloud API **media endpoint** (media ID → download URL). | Mostly works. Caveats: (a) a **24-hour service window** applies — the team lead must have messaged the bot within 24h for free-form replies to be legal/cheap; (b) PDF/image must come as a WhatsApp media message (files are fine); (c) very large files are impractical. Recommendation: keep the Telegram bot as the primary *intake* surface if it's easier, or drive intake with a "Send us your material" button. |

---

## Cross-cutting differences that shape the design

### The 24-hour service window (the big one)
On WhatsApp, a conversation is split into **service** (the user messaged first,
opening a 24-hour window where you may reply freely) and **business-initiated**
(outside that window, you may only send **pre-approved templates**).

- **Daily quiz push** is business-initiated → it must go out as an **approved
  template** (utility category — cheap, and Meta's rules for utility are more
  lenient than marketing), *or* we design the loop so staff message the bot
  each day (e.g. a morning "Ready!" text) to open the window, *or* we use a
  **free entry point** (a "Click to chat" link) which Meta treats as user
  initiated and doesn't bill.
- This is the single largest product difference from Telegram, where the bot
  can message the group whenever it wants. Budget it in from day one.

### Message/billing categories
Business-initiated templates are billed by category, per message, with rates
that vary by the **recipient's** country code: **utility** (cheapest),
**authentication**, **marketing** (most expensive). Our daily question is a
utility-style reminder — keep it classified utility to stay cheap and
low-friction. See `references.md` for the pricing model and sources.

### Privacy
The aggregate-only report and no-per-employee-monitoring promise carry over
unchanged. Cloud API is GDPR-compliant and ISO/SOC-certified (see
`references.md`), and our design never sends identifiable per-person data to
anyone but the individual themselves.

### Buttons/UX limits to remember
- Reply buttons: max **3**, title max **20 chars**, id max **256 chars**
  (the id is what we get back in the webhook).
- List messages: max **10** rows, section title max **24** chars, row title
  max **24**, description max **72**.
- Media header on a reply-button message: image / video / document (no audio).

---

## Bottom line for the engine (what `adapter.py` must guarantee)

1. `send_question` → interactive reply-button message, **3** buttons max.
2. `send_flashcard` → front + "Show answer" button; answer on button press.
3. `send_leaderboard` → 1:1 plain-text message per participant.
4. `send_aggregate_report` → 1:1 text/document to the manager.
5. `handle_inbound` → parse webhook, route button ids / text / media / status.
