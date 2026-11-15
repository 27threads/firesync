from typing import Protocol


class LlmUnavailable(Exception):
    """Every configured language-model provider failed or the time budget ran out."""


class LlmClient(Protocol):
    def complete(self, messages: list[dict], tools: list[dict], deadline: float) -> dict:
        """Return one assistant message in the OpenAI chat format before `deadline` (monotonic seconds)."""
        ...
