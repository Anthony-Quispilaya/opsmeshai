import json
import urllib.error
import urllib.request

from backend.app.core.config import get_settings


def send_photon_bridge_message(channel: str, thread_id: str, recipient: str, text: str) -> dict:
    """POST outbound text to the local Photon bridge (iMessage, etc.)."""
    settings = get_settings()
    bridge_payload = {
        "channel": channel,
        "thread_id": thread_id,
        "recipient": recipient,
        "text": text,
    }
    req = urllib.request.Request(
        f"{settings.photon_bridge_url.rstrip('/')}/send",
        data=json.dumps(bridge_payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-photon-bridge-token": settings.photon_bridge_token,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Photon bridge error: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"Photon bridge unavailable: {exc}") from exc
