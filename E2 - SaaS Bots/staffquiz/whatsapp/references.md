# WhatsApp adapter — references

Every factual claim made in `README.md` and `parity.md` is listed here with its
source URL. Where a source could not be fetched live during research (Meta's
developer docs are JavaScript-rendered and return empty content to plain
fetchers), the canonical URL is still listed and the claim is one that Meta's
own documentation states on that page; such entries are marked **[canonical]**.

> House search backend (SearXNG) returned junk for most keyword queries during
> this research, so these sources were fetched directly or are canonical
> Meta/WhatsApp URLs. Re-verify rate-card numbers against the live pricing page
> before final budgeting — rates change.

---

## 1. Cloud API vs Baileys

| Claim | Source |
|---|---|
| Baileys is "a WebSockets-based TypeScript library for interacting with the WhatsApp Web API" (i.e. an unofficial, reverse-engineered client). | https://github.com/WhiskeySockets/Baileys |
| Baileys is "not affiliated, associated, authorized, endorsed by … WhatsApp"; maintainers "discourage any stalkerware, bulk or automated messaging" and say "use at your own discretion". | https://github.com/WhiskeySockets/Baileys (README "Disclaimer") |
| Baileys is TypeScript/JavaScript (Node.js) — a stack mismatch with a Python production backend. | https://github.com/WhiskeySockets/Baileys (repo language/topics: nodejs, typescript, websockets) |
| The official route is the WhatsApp Business **Cloud API**, hosted by Meta, accessed over HTTPS/JSON (no special SDK — works from Python). | https://developers.facebook.com/docs/whatsapp/cloud-api **[canonical]** |
| On-Premises API was sunset **Oct 23, 2025**; everyone must use Cloud API. | https://developers.facebook.com/docs/whatsapp/on-premises/sunset |
| Cloud API throughput/reliability: up to **1,000 messages/second**, **99.9% uptime**, <5s p99 latency; GDPR & LGPD compliance, SOC2/SOC3 (ISO 27001 in progress). | https://developers.facebook.com/docs/whatsapp/on-premises/sunset |
| The WhatsApp Business Platform is positioned for customer engagement (notifications, promotions, commerce, customer care, verifications). | https://business.whatsapp.com/products/business-platform |

## 2. Requirements to go live (Cloud API)

| Claim | Source |
|---|---|
| You need a Meta Business account, a Meta developer **App** with the WhatsApp product added, and a **phone number** registered to it (verified via SMS/voice). | https://developers.facebook.com/docs/whatsapp/cloud-api/get-started **[canonical]** |
| The phone number must be a valid number that can receive an OTP; it must not already be active on consumer WhatsApp (or you migrate it). | https://developers.facebook.com/docs/whatsapp/cloud-api/phone-numbers **[canonical]** |
| A **display name** is required and is reviewed/approved. | https://developers.facebook.com/docs/whatsapp/cloud-api/phone-numbers **[canonical]** |
| **Business verification** (Meta Business verification, in Business Settings → Security Center) is required to raise messaging tiers and for some production use; it is document-based review. | https://www.facebook.com/business/help/2058515294227817 **[canonical]** |
| Cloud API requires registering your webhook and verifying it with a `hub.challenge` token handshake. | https://developers.facebook.com/docs/whatsapp/cloud-api/guides/set-up-webhooks **[canonical]** |
| Messages to individual users: Cloud API is **1:1** (business number ↔ customer number). It does not support sending to WhatsApp **groups** the way consumer WhatsApp does. | https://developers.facebook.com/docs/whatsapp/cloud-api/messages **[canonical]** (see also parity.md note) |

## 3. Pricing (current model)

| Claim | Source |
|---|---|
| Authoritative pricing page (per-country rates, categories, free entry points). | https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing **[canonical — live page is JS-rendered]** |
| As of **July 1, 2025** WhatsApp moved to a **message-based** (per-template-message) pricing model, replacing the older conversation-based model. | https://respond.io/blog/whatsapp-business-api-pricing |
| **User-initiated** messages open a **24-hour service window** during which free-form text and **utility** templates are free. | https://respond.io/blog/whatsapp-business-api-pricing |
| **Business-initiated** messages outside the window must be **pre-approved templates**, billed by category — **utility** (cheapest), **authentication**, **marketing** (most expensive). Sending multiple templates in the *same category* within one conversation does not add extra charges for that category. | https://respond.io/blog/whatsapp-business-api-pricing |
| Rates vary by the **recipient's phone country code** (Netherlands has its own band; check the rate card). | https://respond.io/blog/whatsapp-business-api-pricing |
| **Free entry points**: conversations opened via Click-to-WhatsApp ads or a Facebook Page CTA button are free (and, historically, extend the window). | https://respond.io/blog/whatsapp-business-api-pricing |
| The **first 1,000 service conversations per month are free** (free tier). | https://respond.io/blog/whatsapp-business-api-pricing (FAQ) |
| Cloud API access/sign-up itself is **free** — you only pay per-message charges (plus any BSP markup if you go through a Business Solution Provider rather than directly with Meta). | https://respond.io/blog/whatsapp-business-api-pricing (FAQ) |

> No reliable public **Netherlands €-per-message** figure could be pinned during
> this research because Meta's live rate card is JS-gated. **Budgeting rule of
> thumb:** utility messages are the cheapest category and are the right
> classification for a daily-quiz reminder; for a 30–40 person tenant sending
> ~1–2 messages/staff/day, even a few cents per message is tens of euros a month
> — immaterial at this scale, and largely free if staff open the window daily or
> you use a free entry point. Confirm exact cents on the live rate card.

## 4. Interactive messages (reply buttons / list)

| Claim | Source |
|---|---|
| Cloud API interactive messages: **reply buttons** (up to **3** options), **list** (up to **10** selectable items split into sections), product, product-list. | https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/messages/interactive/ (SDK hosted by Meta) |
| Reply-button `title` max **20 chars** (no emoji/markdown), `id` max **256 chars** (id returned in the webhook on click). | https://developers.cm.com/messaging/docs/whatsapp-interactive-messages |
| List message: max **10** options; section title max **24** chars; row title max **24** chars; row description max **72** chars. | https://developers.cm.com/messaging/docs/whatsapp-interactive-messages |
| Media header on a reply-button message supports image / video / document (no audio). | https://developers.cm.com/messaging/docs/whatsapp-interactive-messages |
| Other interactive types available: CTA URL button, location request, **interactive Flows** (multi-screen forms), call-permission request, media carousel. | https://developers.cm.com/messaging/docs/whatsapp-interactive-messages |

## 5. Templates / marketing-message rules

| Claim | Source |
|---|---|
| Template messages are required to initiate a conversation outside the 24-hour window, and each template is reviewed/approved by Meta. | https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-message-templates **[canonical]** |
| Templates are categorized **utility / authentication / marketing** and billed accordingly. | https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing **[canonical]** |

## 6. Netherlands market adoption

| Claim | Source |
|---|---|
| The Netherlands' leading social-media research is Newcom's annual **Nationale Social Media Onderzoek** (16th edition for 2026). | https://www.newcom.nl/publicaties/nationale-social-media-onderzoek-basis-2026 |
| The 2026 edition notes **daily WhatsApp use is still increasing**, WhatsApp sits in the platform "big-5", and 93% of Signal users also use WhatsApp — consistent with WhatsApp being the dominant Dutch messenger. | https://www.newcom.nl/publicaties/nationale-social-media-onderzoek-basis-2026 |

> The precise 2026 NL reach % for WhatsApp is inside Newcom's (free but
> form-gated) report; the page above is the landing page for it. If you need a
> hard reach number for the pitch, download the Newcom Basis 2026 report. The
> qualitative claim "NL is WhatsApp-dominant" is what matters for this decision
> and is well supported.

## 7. General

| Claim | Source |
|---|---|
| WhatsApp is used by 2B+ people worldwide (scale/ubiquity context). | https://www.whatsapp.com/ |
| Meta Cloud API terms / hosting terms. | https://www.facebook.com/legal/Meta-Hosting-Terms-Cloud-API |
