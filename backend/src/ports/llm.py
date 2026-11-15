from typing import Protocol


class LlmUnavailable(Exception):
    """Every configured language-model provider failed."""


class LlmClient(Protocol):
    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        """Return one assistant message in the OpenAI chat format: content and optional tool_calls."""
        ...
