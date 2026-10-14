"""Thin wrapper over the Anthropic API. Returns None when no key is configured."""
from .config import ANTHROPIC_KEY, MODEL

_client = None
if ANTHROPIC_KEY:
    import anthropic
    _client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)


def available() -> bool:
    return _client is not None


def ask(system: str, prompt: str, max_tokens: int = 700) -> str | None:
    if not _client:
        return None
    msg = _client.messages.create(
        model=MODEL, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text
