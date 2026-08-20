"""StaffQuiz — WhatsApp adapter (skeleton / message-flow contract).

This module defines the *contract* the WhatsApp integration must satisfy so the
platform-neutral `core/` engine can drive it without knowing anything about
WhatsApp. It is deliberately a skeleton: every function has a full signature,
a docstring that pins down the behaviour, and a body that raises
`NotImplementedError` with a clear message. Nothing here talks to the network,
so importing this module is always safe and side-effect free.

Target: the Meta WhatsApp Business **Cloud API** (hosted, HTTPS/JSON). See
`README.md` for the Cloud API vs Baileys decision and `parity.md` for what
StaffQuiz features can and cannot be reproduced on WhatsApp.

Design notes
------------
* Standard library only — no third-party imports. The real adapter will send
  HTTPS requests with `urllib.request` (or a thin `requests`-style helper), but
  the skeleton must stay import-safe on a bare interpreter.
* All "send" functions take `tenant` and `to` and return a delivery result. The
  result shape is intentionally left as a dict so the real implementation can
  carry the Cloud API `messages` response id, a `delivery` webhook status, etc.
* `handle_inbound` is the single entry point for webhook payloads. It must be
  pure routing: parse the payload, classify the event, and return a normalized
  dict the engine understands — never perform side effects.
"""

from __future__ import annotations

__all__ = [
    "CONFIG_SCHEMA",
    "OPTIONAL_CONFIG_SCHEMA",
    "send_question",
    "send_flashcard",
    "send_leaderboard",
    "send_aggregate_report",
    "handle_inbound",
]

# ---------------------------------------------------------------------------
# Configuration contract
# ---------------------------------------------------------------------------
# Required environment keys for a Cloud API deployment. The real adapter reads
# these from the process environment (or a secrets manager) at startup and must
# refuse to start (fail fast) if any of them are missing.
#
#   phone_number_id      — the Cloud API numeric phone number ID (e.g. from the
#                          WhatsApp > API Setup page of the Meta app). Identifies
#                          the sender. Appears in the send URL path as the
#                          "From" phone number ID.
#   access_token         — a System User / User access token with the
#                          `whatsapp_business_messaging` and
#                          `whatsapp_business_management` permissions. Sent as
#                          the Bearer token on every Graph API call.
#   webhook_verify_token — the token you set in the app's webhook config; Meta
#                          echoes it back on the initial `hub.challenge`
#                          handshake so you can prove you own the endpoint.
#   app_secret           — the Meta app secret, used to validate the
#                          `X-Hub-Signature-256` (HMAC-SHA256) header on every
#                          inbound webhook so we only trust Meta's servers.
CONFIG_SCHEMA: dict = {
    "phone_number_id": (
        "Cloud API phone number ID identifying the WhatsApp Business sender "
        "(from the Meta app > WhatsApp > API Setup)."
    ),
    "access_token": (
        "Meta Graph API access token (bearer) with whatsapp_business_messaging "
        "and whatsapp_business_management scopes."
    ),
    "webhook_verify_token": (
        "Arbitrary secret string configured in the Meta webhook; verified "
        "during the initial hub.challenge handshake."
    ),
    "app_secret": (
        "Meta app secret used to verify the X-Hub-Signature-256 header on "
        "inbound webhook payloads."
    ),
}

# Optional keys the adapter may read. Not required to boot, but recommended for
# production.
OPTIONAL_CONFIG_SCHEMA: dict = {
    "graph_version": (
        "Meta Graph API version string, e.g. 'v20.0'. Defaults to a pinned "
        "version if unset."
    ),
    "business_account_id": (
        "WhatsApp Business Account (WABA) ID. Useful for template management "
        "and for resolving sender identity across multiple numbers."
    ),
    "api_base_url": (
        "Base URL for the Graph API. Defaults to "
        "https://graph.facebook.com/."
    ),
}


# ---------------------------------------------------------------------------
# Message-flow contract — outbound
# ---------------------------------------------------------------------------

def send_question(tenant: str, item: dict, q_index: int, to: str) -> dict:
    """Send one daily quiz question to a single recipient.

    Parameters
    ----------
    tenant : str
        Tenant/company identifier (maps to a Cloud API phone_number_id + token).
    item : dict
        A single question item from the core bank. Expected to contain the
        prompt text and a list of answer options (the core engine guarantees
        between 3 and 4 options; see `parity.md` for the WhatsApp 3-button cap).
    q_index : int
        Zero-based position of this question in the day's quiz, used to build
        stable button ids (e.g. ``q{index}_a{choice}``) so inbound button
        presses can be routed back to the right question and answer.
    to : str
        Recipient phone number in E.164 form (e.g. ``31612345678``).

    Returns
    -------
    dict
        Delivery result, minimally ``{"ok": bool, "message_id": str | None,
        "error": str | None}``. The real implementation posts an
        ``interactive`` reply-button message (up to 3 buttons) via the Cloud
        API ``/messages`` endpoint.
    """
    raise NotImplementedError(
        "send_question is not implemented yet — post an interactive "
        "reply-button message to /PHONE_NUMBER_ID/messages (max 3 buttons)."
    )


def send_flashcard(tenant: str, item: dict, to: str) -> dict:
    """Send one flashcard to a recipient.

    Parameters
    ----------
    tenant : str
        Tenant/company identifier.
    item : dict
        A flashcard item from the core bank (front text and back/reveal text).
    to : str
        Recipient phone number in E.164 form.

    Returns
    -------
    dict
        Delivery result (same shape as :func:`send_question`).

    Notes
    -----
    WhatsApp has no native "spoiler"/hidden-text reveal. The agreed substitute
    (see `parity.md`) is a two-step flow: send the card *front* with a single
    "Show answer" reply button, then send the *back* as a plain text message
    when the button press arrives via `handle_inbound`.
    """
    raise NotImplementedError(
        "send_flashcard is not implemented yet — send the card front plus a "
        "'Show answer' reply button; the back is sent on button press."
    )


def send_leaderboard(tenant: str, to: str) -> dict:
    """Send the weekly leaderboard to a recipient.

    Parameters
    ----------
    tenant : str
        Tenant/company identifier.
    to : str
        Recipient phone number in E.164 form.

    Returns
    -------
    dict
        Delivery result (same shape as :func:`send_question`).

    Notes
    -----
    Cloud API cannot post to WhatsApp *groups*, so there is no shared
    leaderboard. Each participant receives their own 1:1 plain-text
    leaderboard message (personal rank line + top-N). See `parity.md`.
    """
    raise NotImplementedError(
        "send_leaderboard is not implemented yet — Cloud API cannot message "
        "groups; send a plain-text leaderboard 1:1 to each participant."
    )


def send_aggregate_report(tenant: str, to: str) -> dict:
    """Send the anonymous aggregate gap report to the manager.

    Parameters
    ----------
    tenant : str
        Tenant/company identifier.
    to : str
        The manager's phone number in E.164 form (the only recipient).

    Returns
    -------
    dict
        Delivery result (same shape as :func:`send_question`).

    Notes
    -----
    Privacy-preserving by design: the report is aggregate-only (no per-employee
    rows). Sent 1:1 to the manager as plain text and/or a PDF/CSV document via
    the Cloud API ``document`` media type.
    """
    raise NotImplementedError(
        "send_aggregate_report is not implemented yet — send an anonymous, "
        "aggregate-only report 1:1 to the manager (text and/or document)."
    )


# ---------------------------------------------------------------------------
# Message-flow contract — inbound
# ---------------------------------------------------------------------------

def handle_inbound(payload: dict) -> dict:
    """Route a single Cloud API webhook payload to a normalized engine event.

    Parameters
    ----------
    payload : dict
        The decoded JSON body of a Cloud API webhook (the ``entry`` array, or a
        single already-unwrapped entry). Callers are expected to have verified
        the ``X-Hub-Signature-256`` signature *before* calling this function.

    Returns
    -------
    dict
        A normalized event dict, e.g.::

            {
              "type": "answer" | "reveal_request" | "text" | "media"
                     | "registration" | "status" | "unsupported",
              "tenant": str,
              "from": str,          # E.164 sender number
              "phone_number_id": str,
              "button_id": str | None,   # set for interactive button presses
              "text": str | None,        # set for free-form text messages
              "media": dict | None,      # set for image/document content intake
              "status": str | None,      # set for delivery/read status updates
              "raw": dict,               # the original (sub)payload
            }

    Notes
    -----
    Responsibilities: (1) skip status-only updates and route them as
    ``type == "status"`` rather than user events; (2) map interactive reply
    button ids of the form ``q{index}_a{choice}`` (questions) and
    ``reveal_{card_id}`` (flashcards) back to the corresponding engine events;
    (3) classify inbound text/media as registration, language choice, or
    content intake using the tenant's onboarding state.
    """
    raise NotImplementedError(
        "handle_inbound is not implemented yet — parse the webhook entry array "
        "and return a normalized routed event dict (see docstring)."
    )
