"""OpenAI chat-completions adapter with an ordered provider chain (RFC 0004).

Any provider that speaks this format fits in ASSISTANT_PROVIDERS, so an exhausted quota falls to the next one.
"""
import json
import logging
import urllib.request

from backend.ports.llm import LlmUnavailable

logger = logging.getLogger('uvicorn.error.firesync')
MAX_TOKENS = 600


class ProviderChain:
    def __init__(self, providers, timeout, opener=urllib.request.urlopen):
        self.providers, self.timeout, self.opener = providers, timeout, opener

    @classmethod
    def from_env(cls, value, timeout, opener=urllib.request.urlopen):
        """`base_url|key|model` entries separated by commas, in fallback order. Empty: assistant off."""
        providers = [tuple(part.strip() for part in item.split('|')) for item in value.split(',') if item.strip()]
        if any(len(provider) != 3 or not all(provider) for provider in providers):
            raise ValueError('ASSISTANT_PROVIDERS entries must be base_url|key|model, separated by commas.')
        return cls(providers, timeout, opener) if providers else None

    def complete(self, messages, tools):
        for base_url, key, model in self.providers:
            body = json.dumps({'model': model, 'messages': messages, 'tools': tools, 'max_tokens': MAX_TOKENS})
            request = urllib.request.Request(base_url.rstrip('/') + '/chat/completions', data=body.encode(),
                                             headers={'Authorization': 'Bearer ' + key,
                                                      'Content-Type': 'application/json'})
            try:
                # shortcut: the timeout is per provider, so a slow chain can take a multiple of it.
                with self.opener(request, timeout=self.timeout) as response:
                    return json.load(response)['choices'][0]['message']
            except (OSError, ValueError, KeyError, IndexError, TypeError) as error:  # quota, 5xx, timeout, bad body
                logger.warning('Assistant provider failed, trying the next one: %s %s', base_url, error)
        raise LlmUnavailable('Every assistant provider failed.')
