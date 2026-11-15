"""Virtual assistant (RFC 0004): the model picks tools and writes the text; numbers come from the tools."""
import json
from threading import Lock

from backend.application.assistant_tools import TOOL_SPECS
from backend.domain.models.error import CalendarError
from backend.ports.llm import LlmClient, LlmUnavailable

MAX_MESSAGES = 10
MAX_MESSAGE_CHARS = 1000
HISTORY_SENT = 6
MAX_TOOL_ROUNDS = 4
SYSTEM_PROMPT = (
    'You are the firesync assistant. firesync shows NASA FIRMS fire detections (hotspots) from MODIS and VIIRS, '
    'harmonized to one VIIRS scale since January 2003, for the six Brazilian biomes of IBGE. '
    "Answer in the language of the user's last message. Keep answers short. "
    'Use only numbers returned by the tools; never estimate or invent a number, and do not compute new ones '
    '(sums, shares, averages). If the tools cannot answer, say so. '
    'Give locations exactly as the tools write them; never name a state, city or place from coordinates. '
    'Always say the region, the period and that counts are on the harmonized VIIRS scale (NASA FIRMS). '
    'A month with missing satellite days is not a month with zero hotspots. '
    'Regions are biomes only: for a state, a city or a place outside Brazil, say so and suggest drawing the area '
    'on the map. Use list_regions to find a region_id.')


def invalid(message):
    return CalendarError('invalid_request', message)


def validate_messages(payload):
    """The browser sends only plain user/assistant text; tool results exist only inside the service."""
    messages = payload.get('messages') if isinstance(payload, dict) else None
    if not isinstance(messages, list) or not 1 <= len(messages) <= MAX_MESSAGES:
        raise invalid(f'Send 1 to {MAX_MESSAGES} messages.')
    for message in messages:
        if (not isinstance(message, dict) or set(message) != {'role', 'content'}
                or message['role'] not in ('user', 'assistant') or not isinstance(message['content'], str)
                or not message['content'].strip() or len(message['content']) > MAX_MESSAGE_CHARS):
            raise invalid(f'Each message needs a user or assistant role and 1 to {MAX_MESSAGE_CHARS} characters of text.')
    if messages[-1]['role'] != 'user':
        raise invalid('The last message must come from the user.')
    return messages


class AskService:
    def __init__(self, llm: LlmClient, daily_limit, clock):
        self.llm, self.daily_limit, self.clock = llm, daily_limit, clock
        self.day, self.used = None, 0
        self.lock = Lock()

    def spend_daily_request(self):
        # shortcut: counted per API process and reset on restart; move to the database if the API scales out.
        with self.lock:
            today = self.clock().date()
            if today != self.day:
                self.day, self.used = today, 0
            if self.used >= self.daily_limit:
                raise CalendarError('assistant_unavailable', 'Daily limit reached, use the map.')
            self.used += 1

    def complete(self, conversation):
        try:
            return self.llm.complete(conversation, TOOL_SPECS)
        except LlmUnavailable:
            raise CalendarError('assistant_unavailable', 'Assistant unavailable, use the map.') from None

    def ask(self, messages, toolbox):
        self.spend_daily_request()
        conversation = [{'role': 'system', 'content': SYSTEM_PROMPT + ' ' + toolbox.context()}, *messages[-HISTORY_SENT:]]
        actions, notes = [], []
        for _ in range(MAX_TOOL_ROUNDS + 1):
            reply = self.complete(conversation)
            calls = reply.get('tool_calls') or []
            if not calls:
                return {'answer': reply.get('content') or '', 'actions': actions, 'notes': notes}
            conversation.append({'role': 'assistant', 'content': reply.get('content'), 'tool_calls': calls})
            for tool_call in calls:
                function = tool_call.get('function') or {}
                result, new_actions, new_notes = toolbox.run(function.get('name'), function.get('arguments'))
                actions += [action for action in new_actions if action not in actions]
                notes += [note for note in new_notes if note not in notes]
                conversation.append({'role': 'tool', 'tool_call_id': tool_call.get('id'),
                                     'content': json.dumps(result, default=str)})
        raise CalendarError('assistant_unavailable', 'Assistant unavailable, use the map.')
