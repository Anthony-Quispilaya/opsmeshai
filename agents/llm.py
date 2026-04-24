from __future__ import annotations

import json
import urllib.error
import urllib.request

from backend.app.core.config import get_settings


class LLMResponder:
    """Minimal OpenAI chat responder for Sprint 5 kickoff."""

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.openai_api_key.strip()
        self.model = settings.openai_model.strip()
        self.base_url = settings.openai_base_url.rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def generate_reply(
        self,
        user_message: str,
        history: list[dict] | None = None,
    ) -> str:
        if not self.enabled:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        if not self.model:
            raise RuntimeError("OPENAI_MODEL is not configured.")

        messages: list[dict] = [
            {
                "role": "system",
                "content": (
                    "You are OpsMesh AI, an intelligent operations assistant. "
                    "You help teams manage transactions, support tickets, and compliance records. "
                    "Be concise, specific, and action-oriented. "
                    "When the user refers to 'it', 'that', 'the last one', or uses pronouns, "
                    "resolve them from the conversation history."
                ),
            }
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.4,
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"OpenAI API error ({exc.code}): {body}") from exc
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc

        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("OpenAI response did not include choices.")
        message = choices[0].get("message") or {}
        content = (message.get("content") or "").strip()
        if not content:
            raise RuntimeError("OpenAI response content was empty.")
        return content
