"""OpenAI chat-completions adapter with an ordered provider chain (RFC 0004).

Any provider that speaks this format fits in ASSISTANT_PROVIDERS, so an exhausted quota falls to the next one.
"""
import json
import logging
import urllib.request

from backend.ports.llm import LlmUnavailable

logger = logging.getLogger('uvicorn.error.firesync')
# A ceiling, not a target: reasoning models spend part of it thinking before the answer.
MAX_TOKENS = 4000
USER_AGENT = 'firesync-assistant/1.0'


class ProviderChain:
    def __init__(self, providers, timeout, opener=urllib.request.urlopen):
        self.providers, self.timeout, self.opener = providers, timeout, opener

    @classmethod
    def from_env(cls, value, timeout, opener=urllib.request.urlopen):
        """`base_url|key|model[|reasoning_effort]` entries separated by commas, in fallback order.

        Without the fourth field the parameter is not sent (models that do not reason reject it). Empty: assistant off.
        """
        providers = [tuple(part.strip() for part in item.split('|')) for item in value.split(',') if item.strip()]
        if any(len(provider) not in (3, 4) or not all(provider) for provider in providers):
            raise ValueError('ASSISTANT_PROVIDERS entries must be base_url|key|model[|reasoning_effort], '
                             'separated by commas.')
        return cls([(*provider, None)[:4] for provider in providers], timeout, opener) if providers else None

    def complete(self, messages, tools):
        for base_url, key, model, effort in self.providers:
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
                # shortcut: the timeout is per provider, so a slow chain can take a multiple of it.
                with self.opener(request, timeout=self.timeout) as response:
                    message = json.load(response)['choices'][0]['message']
                if not message.get('content') and not message.get('tool_calls'):
                    raise ValueError('empty reply (the model spent max_tokens reasoning)')
                return message
            except (OSError, ValueError, KeyError, IndexError, TypeError) as error:  # quota, 5xx, timeout, bad body
                logger.warning('Assistant provider failed, trying the next one: %s %s', base_url, error)
        raise LlmUnavailable('Every assistant provider failed.')
