"""E.164-style phone normalization for user preferred numbers and inbound matching."""


def normalize_e164(value: str) -> str:
    raw = value.strip()
    if not raw:
        return raw
    if raw.startswith("+"):
        return "+" + "".join(ch for ch in raw[1:] if ch.isdigit())
    digits = "".join(ch for ch in raw if ch.isdigit())
    return f"+{digits}" if digits else raw
