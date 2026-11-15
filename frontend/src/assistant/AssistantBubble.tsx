import { type KeyboardEvent, useEffect, useRef, useState } from 'react';
import { ApiClientError, askAssistant, fetchAuditPackage } from '../api/client';
import type { AssistantAction, AssistantMessage, AssistantResponse, AssistantSource } from '../api/types';
import { downloadBlob } from '../export/ExportBar';

export const SUGGESTED_QUESTIONS = [
  'What was the worst month in the Pantanal in 2020?',
  'Was 2024 above normal in the Cerrado?',
  'How many hotspots in the Amazon in the last 7 days?',
  'Where is it burning right now?',
  'Give me a fire report for last year in the Amazon.',
];

const MAX_ASSISTANT_CHARS = 4000; // same limit as the API for earlier answers sent back as history

export function describeSource(source: AssistantSource): string {
  const what = source.endpoint.includes('detections') ? `fire map, last ${source.hours ?? 24} h` : source.endpoint.includes('regions') ? 'region list' : 'calendar';
  const where = source.region ? ` · ${source.region}` : '';
  const when = source.start && source.end ? ` · ${source.start} to ${source.end}` : '';
  return `NASA FIRMS via firesync ${what}${where}${when} · data version ${source.data_version}`;
}

/** Bold spans in a line of the answer; the model writes light markdown and React escapes the rest. */
function inline(line: string) {
  return line.split(/\*\*(.+?)\*\*/g).map((part, index) => (index % 2 ? <strong key={index}>{part}</strong> : part));
}

/** Paragraphs and '-' / '*' bullet lists only: enough for the answers, no markdown dependency or raw HTML. */
export function AnswerText({ text }: { text: string }) {
  const blocks: { bullets: boolean; lines: string[] }[] = [];
  for (const raw of text.split('\n')) {
    const line = raw.trim();
    if (!line) continue;
    const bullet = /^[-*•]\s+/.test(line);
    const content = line.replace(/^[-*•]\s+/, '');
    const last = blocks[blocks.length - 1];
    if (last && last.bullets === bullet && bullet) last.lines.push(content);
    else blocks.push({ bullets: bullet, lines: [content] });
  }
  return (
    <>
      {blocks.map((block, index) =>
        block.bullets ? (
          <ul key={index} className="assistant-msg__list">
            {block.lines.map((line, item) => (
              <li key={item}>{inline(line)}</li>
            ))}
          </ul>
        ) : (
          <p key={index}>{inline(block.lines[0])}</p>
        ),
      )}
    </>
  );
}

interface Turn {
  message: AssistantMessage;
  reply?: AssistantResponse;
}

interface Props {
  onShowCalendar: (action: AssistantAction) => void;
  /** Esconde só o botão flutuante (por exemplo, enquanto o hero ocupa a tela). O painel aberto não some. */
  hideBubble?: boolean;
}

function failureText(error: unknown): string {
  if (error instanceof ApiClientError && (error.code === 'assistant_unavailable' || error.code === 'rate_limited')) {
    return error.message;
  }
  return 'Assistant unavailable, use the map.';
}

/** Floating chat (RFC 0004). Optional: the page works the same without it. */
export function AssistantBubble({ onShowCalendar, hideBubble = false }: Props) {
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const panelRef = useRef<HTMLElement>(null);
  const bubbleRef = useRef<HTMLButtonElement>(null);
  const wasOpen = useRef(false);

  useEffect(() => {
    if (open) inputRef.current?.focus();
    else if (wasOpen.current) bubbleRef.current?.focus(); // back to the button that opened the panel
    wasOpen.current = open;
  }, [open]);

  // Keeps Tab inside the open panel, so keyboard users do not land on the map behind it.
  function trapFocus(event: KeyboardEvent) {
    if (event.key !== 'Tab' || !panelRef.current) return;
    const focusable = panelRef.current.querySelectorAll<HTMLElement>('button:not([disabled]), textarea');
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  async function send(text: string) {
    const question = text.trim();
    if (!question || busy) return;
    const history: AssistantMessage[] = turns.flatMap((turn) =>
      turn.reply?.answer
        ? [turn.message, { role: 'assistant' as const, content: turn.reply.answer.slice(0, MAX_ASSISTANT_CHARS) }]
        : [turn.message],
    );
    const message: AssistantMessage = { role: 'user', content: question.slice(0, 1000) };
    setTurns((current) => [...current, { message }]);
    setDraft('');
    setFailure(null);
    setBusy(true);
    try {
      const reply = await askAssistant([...history, message].slice(-10));
      setTurns((current) => current.map((turn, index) => (index === current.length - 1 ? { ...turn, reply } : turn)));
    } catch (error) {
      setFailure(failureText(error));
    } finally {
      setBusy(false);
    }
  }

  async function download(action: AssistantAction) {
    try {
      const { blob, filename } = await fetchAuditPackage({ area: action.area, start: action.start, end: action.end });
      downloadBlob(blob, filename);
    } catch (error) {
      setFailure(error instanceof ApiClientError ? error.message : 'Download failed.');
    }
  }

  if (!open) {
    if (hideBubble) return null;
    return (
      <button ref={bubbleRef} type="button" className="assistant-bubble" aria-label="Ask about fire data" onClick={() => setOpen(true)}>
        ?
      </button>
    );
  }

  return (
    <section
      ref={panelRef}
      className="assistant-panel"
      role="dialog"
      aria-modal="true"
      aria-label="Fire data assistant"
      onKeyDown={(event) => {
        if (event.key === 'Escape') setOpen(false);
        trapFocus(event);
      }}
    >
      <header className="assistant-panel__head">
        <strong>Ask firesync</strong>
        <button type="button" className="assistant-panel__close" aria-label="Close assistant" onClick={() => setOpen(false)}>
          ×
        </button>
      </header>
      <div className="assistant-panel__log" aria-live="polite">
        {turns.length === 0 && (
          <ul className="assistant-panel__chips">
            {SUGGESTED_QUESTIONS.map((question) => (
              <li key={question}>
                <button type="button" className="chip" onClick={() => void send(question)}>
                  {question}
                </button>
              </li>
            ))}
          </ul>
        )}
        {turns.map((turn, index) => (
          <div key={index}>
            <p className="assistant-msg assistant-msg--user">{turn.message.content}</p>
            {turn.reply && (
              <div className="assistant-msg">
                <AnswerText text={turn.reply.answer} />
                {turn.reply.sources.length > 0 && (
                  <ul className="assistant-msg__sources" aria-label="Sources">
                    {turn.reply.sources.map((source) => (
                      <li key={describeSource(source)}>{describeSource(source)}</li>
                    ))}
                  </ul>
                )}
                {turn.reply.notes.map((note) => (
                  <p key={note} className="assistant-msg__note">
                    {note}
                  </p>
                ))}
                {turn.reply.actions.map((action) => (
                  <button
                    key={action.type + (action.start ?? '') + (action.end ?? '')}
                    type="button"
                    className="chip"
                    onClick={() => (action.type === 'show_calendar' ? onShowCalendar(action) : void download(action))}
                  >
                    {action.type === 'show_calendar' ? 'Show on calendar' : 'Download audit package'}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && <p className="assistant-msg assistant-msg__note">Thinking…</p>}
        {failure && (
          <p className="assistant-msg assistant-msg__note" role="alert">
            {failure}
          </p>
        )}
      </div>
      <form
        className="assistant-panel__form"
        onSubmit={(event) => {
          event.preventDefault();
          void send(draft);
        }}
      >
        <textarea
          ref={inputRef}
          value={draft}
          maxLength={1000}
          rows={2}
          aria-label="Your question"
          placeholder="Ask about fires in Brazil…"
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              void send(draft);
            }
          }}
        />
        <button type="submit" className="chip" disabled={busy || !draft.trim()}>
          Send
        </button>
      </form>
      <p className="assistant-msg__note">Numbers from NASA FIRMS (MODIS + VIIRS), harmonized to the VIIRS scale.</p>
    </section>
  );
}
