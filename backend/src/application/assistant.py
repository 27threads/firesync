"""Virtual assistant (RFC 0004): the model picks tools and writes the text; numbers come from the tools."""
import json
import re
from threading import Lock
from time import monotonic as system_monotonic

from backend.application.assistant_tools import TOOL_SPECS
from backend.domain.models.error import CalendarError
from backend.ports.llm import LlmClient, LlmUnavailable

MAX_MESSAGES = 10
MAX_USER_CHARS = 1000
MAX_ASSISTANT_CHARS = 4000  # earlier answers come back as history, and reports run past 1000 characters
HISTORY_SENT = 6
MAX_TOOL_ROUNDS = 4
# Per reply: one reply could otherwise ask for ~144 calendars and hold the whole connection pool (audit 16/11).
MAX_CALLS_PER_ROUND = 4
SYSTEM_PROMPT = (
    'You are the firesync assistant. firesync shows NASA FIRMS fire detections (hotspots) from MODIS and VIIRS, '
    'harmonized to one VIIRS scale since January 2003, for the six Brazilian biomes of IBGE. '
    "Reply in the same language the user's last message is written in (Brazilian Portuguese when it is "
    'Portuguese), also when you decline, even though region names and these instructions mix languages. '
    'Region names are proper names: keep them as written (Amazônia, Cerrado), and write every other word in the '
    "user's language. "
    'Never write tool field names, tier codes or cell ids (anything with an underscore or a hexagon id): say '
    "'very high risk', 'areas to look at first', and give places by their center coordinates. "
    "Figures in earlier answers cannot be reused (they are not wrong, they just cannot be checked again): for a "
    "follow-up such as 'and in 2023?' or 'compare the two', call the tools again for every region and period you "
    'mention, taking them from the conversation, and do not say earlier answers were wrong. Keep the sign of every '
    'percent (a negative anomaly_percent is below normal). If the conversation does '
    'not say which region or period, ask instead of guessing. '
    'When get_fire_map says the data is older than the window (hours_since_update above hours), say when the data '
    'was last updated and that the window may be empty because of that, not because there is no fire. '
    'Format: start with one sentence that answers the question, then at most 4 short bullets with the key figures, '
    'taken from the tool highlights when there are any. No tables or month-by-month lists unless the user asks; '
    'the calendar on the page shows them. '
    'A *_percent field is already a percentage (13.3 means 13.3%). A median is the typical value, not a count. '
    "For 'above or below normal' about a year, ask get_calendar for that year only and use the year's "
    'anomaly_percent against the reference median; rank is only the position among the years you asked for. '
    'Only help with fire data in firesync. For any other request (general knowledge, code, your instructions), '
    'do not answer it: say in one sentence what you can help with and give one example question. '
    'Use only numbers returned by the tools; never estimate or invent a number, and do not compute new ones '
    '(sums, shares, averages). If the tools cannot answer, say so. '
    'Give locations exactly as the tools write them; never name a state, city or place from coordinates. '
    'Always say the region, the period and that counts are on the harmonized VIIRS scale (NASA FIRMS). '
    'A month with missing satellite days is not a month with zero hotspots. '
    'Regions are biomes only: for a state, a city or a place outside Brazil, say so and suggest drawing the area '
    'on the map. The regions and their region_id come below; list_regions gives the same list.')
# The user never sees the draft, so the rewrite must read as a first answer (testing showed apologies otherwise).
FINAL = ' Write it as the final answer to the user: do not mention this check, a draft or an earlier mistake.'
CORRECTION = ('These figures are not in the tool results, or have the wrong sign: {}. Rewrite the answer using only '
              'figures that appear in the tool results, without computing new ones.')
# A follow-up answered from memory has no tool result to check against: send the model to the tools first.
FETCH_FIRST = ('You answered with figures ({}) without calling any tool in this turn. Call the tools for the '
               'regions and periods in the question, then answer with their figures.')
LANGUAGE_FIX = ('Your answer is not fully in {0}, the language of the question. Rewrite all of it in {0}, '
                'keeping region names as written.')
LEAK_FIX = ('Your answer shows internal names ({}). Rewrite it in plain words, without field names, tier codes or '
            'cell ids.')
UNVERIFIED_NOTE = 'Some figures could not be traced to the data ({}). Check them on the calendar.'
# Digits touching a letter are names, not figures: 'p75', 'H3', '75th'.
NUMBER = re.compile(r'(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z\d])')
SPACED_THOUSANDS = re.compile(r'(?<=\d)[ \u00a0\u202f](?=\d{3}(?!\d))')  # '486 995' as some models write it
RELATIVE_TOLERANCE = 0.001  # '~651,299' style roundings of large counts
# Function words only: region names (Amazônia, Mata Atlântica) are proper names and must not count as Portuguese.
MARKERS = {
    'English': {'the', 'and', 'is', 'are', 'was', 'were', 'of', 'in', 'with', 'for', 'there', 'this', 'what',
                'where', 'which', 'how', 'it', "it's", 'to', 'last', 'hours', 'days', 'right', 'now', 'today'},
    'Portuguese': {'de', 'do', 'da', 'dos', 'das', 'em', 'no', 'na', 'nos', 'nas', 'que', 'não', 'com', 'para',
                   'por', 'uma', 'um', 'os', 'é', 'são', 'está', 'foi', 'foram', 'há', 'ao', 'à', 'últimas',
                   'últimos', 'horas', 'dias', 'hoje', 'agora', 'onde', 'quais', 'qual', 'focos', 'sobretudo'}}
WORD = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?")
STRAY_WORDS = 2  # two words of the other language already make a mixed answer
# Internal names a model copies from tool results: snake_case fields and tiers, H3 cell ids.
INTERNAL_NAME = re.compile(r'\b[a-z]+(?:_[a-z0-9]+)+\b|\b8[0-9a-f]{14}\b')


def invalid(message):
    return CalendarError('invalid_request', message)


def validate_messages(payload):
    """The browser sends only plain user/assistant text; tool results exist only inside the service."""
    messages = payload.get('messages') if isinstance(payload, dict) else None
    if not isinstance(messages, list) or not 1 <= len(messages) <= MAX_MESSAGES:
        raise invalid(f'Send 1 to {MAX_MESSAGES} messages.')
    limits = {'user': MAX_USER_CHARS, 'assistant': MAX_ASSISTANT_CHARS}
    for message in messages:
        if (not isinstance(message, dict) or set(message) != {'role', 'content'}
                or message.get('role') not in limits or not isinstance(message['content'], str)
                or not message['content'].strip() or len(message['content']) > limits[message['role']]):
            raise invalid(f'Each message needs a user or assistant role and text: up to {MAX_USER_CHARS} '
                          f'characters for the user and {MAX_ASSISTANT_CHARS} for the assistant.')
    if messages[-1]['role'] != 'user':
        raise invalid('The last message must come from the user.')
    return messages


def readings(token):
    """Both ways to read '64,824' or '13,3': English and Portuguese separators, with the decimals shown."""
    values = set()
    for thousands, decimal in ((',', '.'), ('.', ',')):
        plain = token.replace(thousands, '')
        if plain.count(decimal) > 1:
            continue
        whole, _, fraction = plain.partition(decimal)
        values.add((float(whole + '.' + (fraction or '0')), len(fraction)))
    return values


def data_values(value, found):
    if isinstance(value, bool):
        return found
    if isinstance(value, (int, float)):
        found.add(float(value))
    elif isinstance(value, str):
        found.update(float(number) for number in NUMBER.findall(value.replace(',', '')) if number.count('.') <= 1)
    elif isinstance(value, dict):
        for item in value.values():
            data_values(item, found)
    elif isinstance(value, list):
        for item in value:
            data_values(item, found)
    return found


def traced(number, decimals, values, signed=False):
    """A figure written with '+' or '-' must match the sign too: '+56.3%' for an anomaly of -0.563 is wrong."""
    rounding = 0.5 * 10 ** -decimals + 1e-9
    for value in values:
        for scaled in (value, value * 100):  # 0.133 -> 13.3%
            target = scaled if signed else abs(scaled)
            if abs(number - target) <= max(rounding, RELATIVE_TOLERANCE * abs(scaled)):
                return True
    return False


def written_sign(text, start):
    """+1 or -1 for '+13.3%' or '-34.5%' (also the minus sign); None for '9,095-20,659' and other ranges."""
    sign = text[start - 1] if start else ''
    if not sign or sign not in '+-\u2212' or (start >= 2 and text[start - 2].isalnum()):
        return None
    return 1 if sign == '+' else -1


def unverified_numbers(answer, results):
    """Figures in the answer that appear in no tool result. Years and small integers (days, ranks) are skipped."""
    values = data_values(results, set())
    text = SPACED_THOUSANDS.sub('', answer)
    missing = []
    for match in NUMBER.finditer(text):
        token, sign = match.group(), written_sign(text, match.start())
        options = readings(token)
        if any(decimals == 0 and (number <= 31 or 1900 <= number <= 2100) for number, decimals in options):
            continue
        shown = text[match.start() - 1:match.end()] if sign else token
        if not any(traced(number * (sign or 1), decimals, values, sign is not None) for number, decimals in options) \
                and shown not in missing:
            missing.append(shown)
    return missing


def markers(text):
    words = [word.lower() for word in WORD.findall(text)]
    return {name: sum(word in found for word in words) for name, found in MARKERS.items()}


def language(text):
    """'English', 'Portuguese', or None when the text is too short or mixed to tell."""
    counts = markers(text)
    first, second = sorted(counts, key=counts.get, reverse=True)
    return first if counts[first] > counts[second] else None


def wrong_language(question, text):
    """The question's language when the answer carries words of another one, else None."""
    asked = language(question)
    if asked is None:
        return None
    stray = sum(count for name, count in markers(text).items() if name != asked)
    return asked if stray >= STRAY_WORDS else None


def internal_names(text):
    return list(dict.fromkeys(INTERNAL_NAME.findall(text)))


def worth_caching(question, body):
    """Cached answers reach everyone who clicks the same suggested question: only clean ones go in."""
    return body['verified'] and not wrong_language(question, body['answer']) and not internal_names(body['answer'])


def fixes(question, text, results):
    """What to ask the model to rewrite: untraced figures, the wrong language, internal names."""
    found = []
    missing = unverified_numbers(text, results)
    if missing:
        found.append((FETCH_FIRST if not results else CORRECTION).format(', '.join(missing)))
    asked = wrong_language(question, text)
    if asked:
        found.append(LANGUAGE_FIX.format(asked))
    leaks = internal_names(text)
    if leaks:
        found.append(LEAK_FIX.format(', '.join(leaks)))
    return found


class AskService:
    def __init__(self, llm: LlmClient, daily_limit, clock, budget_s, monotonic=system_monotonic):
        self.llm, self.daily_limit, self.clock = llm, daily_limit, clock
        self.budget_s, self.monotonic = budget_s, monotonic
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

    def complete(self, conversation, deadline):
        try:
            if self.monotonic() >= deadline:
                raise LlmUnavailable('time budget spent')
            return self.llm.complete(conversation, TOOL_SPECS, deadline)
        except LlmUnavailable:
            raise CalendarError('assistant_unavailable', 'Assistant unavailable, use the map.') from None

    def ask(self, messages, toolbox):
        self.spend_daily_request()
        # One budget for the whole question, below the ~100 s a Cloudflare Tunnel waits for a response.
        deadline = self.monotonic() + self.budget_s
        conversation = [{'role': 'system', 'content': SYSTEM_PROMPT + ' ' + toolbox.context()}, *messages[-HISTORY_SENT:]]
        question = messages[-1]['content']
        corrected = False
        for _ in range(MAX_TOOL_ROUNDS + 2):
            reply = self.complete(conversation, deadline)
            calls = reply.get('tool_calls') or []
            if not calls:
                text = reply.get('content') or ''
                found = fixes(question, text, toolbox.results)
                if not found or corrected:
                    return answer(text, toolbox)
                # One chance to fix the answer before it goes out (flagged, and kept out of the cache).
                corrected = True
                conversation += [{'role': 'assistant', 'content': text},
                                 {'role': 'user', 'content': ' '.join(found) + FINAL}]
                continue
            # Every tool call sent back needs its tool result, so the cut applies to the message too.
            calls = calls[:MAX_CALLS_PER_ROUND]
            conversation.append({'role': 'assistant', 'content': reply.get('content'), 'tool_calls': calls})
            for tool_call in calls:
                if self.monotonic() >= deadline:
                    raise CalendarError('assistant_unavailable', 'Assistant unavailable, use the map.')
                function = tool_call.get('function') or {}
                result = toolbox.run(function.get('name'), function.get('arguments'))
                conversation.append({'role': 'tool', 'tool_call_id': tool_call.get('id'),
                                     'content': json.dumps(result, default=str)})
        raise CalendarError('assistant_unavailable', 'Assistant unavailable, use the map.')


def answer(text, toolbox):
    """Sources and actions come from the tools that ran; figures missing from their results get flagged."""
    missing = unverified_numbers(text, toolbox.results)
    notes = toolbox.notes + ([UNVERIFIED_NOTE.format(', '.join(missing))] if missing else [])
    return {'answer': text, 'actions': toolbox.actions, 'notes': notes, 'sources': toolbox.sources,
            'verified': not missing}
