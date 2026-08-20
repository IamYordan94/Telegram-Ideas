"""Per-weekday bank scheduling and fun-bank config parsing."""

import json

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def normalize_weekday(name):
    """Return the canonical lowercase weekday name, or raise ValueError."""
    n = str(name).strip().lower()
    if n not in WEEKDAYS:
        raise ValueError(f"invalid weekday {name!r}; expected one of monday..sunday")
    return n


def parse_fun_config(text):
    """Parse a compact fun-bank config string into ``{weekday: bank_filename}``.

    Example: ``"friday:scifi.json,saturday:general.json"`` ->
    ``{"friday": "scifi.json", "saturday": "general.json"}``. Blank/None input
    returns ``{}``; an entry without a colon, an empty bank filename, or a
    non-weekday key raises ``ValueError``.
    """
    result = {}
    if not text:
        return result
    for chunk in str(text).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            raise ValueError(
                f"invalid fun_banks entry {chunk!r}: expected 'weekday:bank.json'"
            )
        weekday, bankfile = chunk.split(":", 1)
        weekday = normalize_weekday(weekday)
        bankfile = bankfile.strip()
        if not bankfile:
            raise ValueError(f"invalid fun_banks entry {chunk!r}: empty bank filename")
        result[weekday] = bankfile
    return result


def _coerce_fun_banks(value):
    """Normalise a tenant's fun_banks field (dict or JSON string) into a dict."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            data = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
        return data if isinstance(data, dict) else {}
    return {}


def pick_bank(tenant, weekday_name):
    """Return the bank filename a tenant should use on a given weekday.

    A fun_banks override for that weekday wins; otherwise the tenant's
    ``default_bank`` is returned. ``tenant`` is a mapping (e.g. a dict from
    ``db.get_tenant``) whose ``fun_banks`` may be a dict or a JSON string.
    Raises ``ValueError`` for an invalid weekday name.
    """
    weekday = normalize_weekday(weekday_name)
    fun = _coerce_fun_banks(tenant.get("fun_banks"))
    if weekday in fun and fun[weekday]:
        return fun[weekday]
    return tenant.get("default_bank")
