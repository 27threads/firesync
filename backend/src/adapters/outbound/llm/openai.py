"""OpenAI chat-completions adapter with an ordered provider chain (RFC 0004).

Any provider that speaks this format fits in ASSISTANT_PROVIDERS, so an exhausted quota falls to the next one.
"""
import json
import logging
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from time import monotonic as system_monotonic

from backend.ports.llm import LlmUnavailable

logger = logging.getLogger('uvicorn.error.firesync')
# A ceiling, not a target: reasoning models spend part of it thinking before the answer.
MAX_TOKENS = 4000
USER_AGENT = 'firesync-assistant/1.0'
# urllib's timeout is per socket read, so a provider that trickles keep-alive bytes never hits it; the call runs
# here and the caller stops waiting at the deadline.
# shortcut: an abandoned call keeps its thread until the provider closes; size the pool if that ever fills up.
CALLS = ThreadPoolExecutor(max_workers=8, thread_name_prefix='assistant-provider')
COOLDOWN_S = 60


class ProviderChain:
    def __init__(self, providers, timeout, opener=urllib.request.urlopen, monotonic=system_monotonic):
        self.providers, self.timeout, self.opener, self.monotonic = providers, timeout, opener, monotonic
        self.failed_at = {}  # base_url -> when it last failed

    def in_order(self):
        """Providers that failed in the last COOLDOWN_S go last: a provider out of quota or timing out would
        otherwise take its share of every question's time budget. They stay in the list, in case all fail."""
        now = self.monotonic()
        return sorted(self.providers, key=lambda provider: now - self.failed_at.get(provider[0], -COOLDOWN_S) < COOLDOWN_S)

    @classmethod
    def from_env(cls, value, timeout, opener=urllib.request.urlopen, monotonic=system_monotonic):
        """`base_url|key|model[|reasoning_effort]` entries separated by commas, in fallback order.

        Without the fourth field the parameter is not sent (models that do not reason reject it). Empty: assistant off.
        """
        providers = [tuple(part.strip() for part in item.split('|')) for item in value.split(',') if item.strip()]
        if any(len(provider) not in (3, 4) or not all(provider) for provider in providers):
            raise ValueError('ASSISTANT_PROVIDERS entries must be base_url|key|model[|reasoning_effort], '
                             'separated by commas.')
        return cls([(*provider, None)[:4] for provider in providers], timeout, opener, monotonic) if providers else None

    def complete(self, messages, tools, deadline):
        for base_url, key, model, effort in self.in_order():
            remaining = deadline - self.monotonic()
            if remaining <= 0:
                break
            payload = {'model': model, 'messages': messages, 'tools': tools, 'max_tokens': MAX_TOKENS}
            if effort:
                payload['reasoning_effort'] = effort
            body = json.dumps(payload)
            request = urllib.request.Request(base_url.rstrip('/') + '/chat/completions', data=body.encode(),
                                             headers={'Authorization': 'Bearer ' + key,
                                                      'Content-Type': 'application/json',
                                                      # Cloudflare in front of some providers blocks Python-urllib (error 1010).
                                                      'User-Agent': USER_AGENT})
            try:
                call = CALLS.submit(self.fetch, request, min(self.timeout, remaining))
                message = call.result(timeout=min(self.timeout, remaining))['choices'][0]['message']
                if not message.get('content') and not message.get('tool_calls'):
                    raise ValueError('empty reply (the model spent max_tokens reasoning)')
                self.failed_at.pop(base_url, None)
                return message
            except (OSError, ValueError, KeyError, IndexError, TypeError) as error:  # quota, 5xx, timeout, bad body
                self.failed_at[base_url] = self.monotonic()
                logger.warning('Assistant provider failed, trying the next one: %s %s: %s',
                               base_url, type(error).__name__, error)
        raise LlmUnavailable('Every assistant provider failed.')

    def fetch(self, request, timeout):
        with self.opener(request, timeout=timeout) as response:
            return json.load(response)
