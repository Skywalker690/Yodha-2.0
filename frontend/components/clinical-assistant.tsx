"use client";

import { useEffect, useRef, useState } from "react";
import {
  ArrowUpRight,
  BookOpen,
  BrainCircuit,
  Send,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import type { AssistantResponse, Patient } from "@/types";

type Message = {
  role: "user" | "assistant";
  content: string;
  response?: AssistantResponse;
};

const suggestions = [
  {
    label: "Summarize the case",
    question:
      "Summarize this patient's longitudinal case using the available clinical values and anatomy. Highlight important changes and limitations.",
  },
  {
    label: "What am I missing?",
    question:
      "What important clinical information is missing from this case? Separate facts present in the record from information I should verify.",
  },
  {
    label: "Explain the findings",
    question:
      "Explain the available MRI-derived anatomy findings and clinical measurements in simple clinical language, including their review status and uncertainty.",
  },
  {
    label: "Explore research",
    question:
      "Find research relevant to longitudinal brain MRI, cognitive assessment and the available findings in this case. Explain how the evidence applies and its limitations.",
    research: true,
  },
];

export function ClinicalAssistant({ patient }: { patient: Patient }) {
  const [open, setOpen] = useState(false);
  const dialog = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    dialog.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  return (
    <>
      <button
        type="button"
        className="assistant-widget-launcher"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls="clinical-assistant-dialog"
        onClick={() => setOpen(true)}
      >
        <BrainCircuit size={19} />
        <span>Clinical Assistant</span>
      </button>
      <div
        className="assistant-widget-layer"
        hidden={!open}
        onMouseDown={(event) => {
          if (event.target === event.currentTarget) setOpen(false);
        }}
      >
        <div
          id="clinical-assistant-dialog"
          className="assistant-widget-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="assistant-title"
          ref={dialog}
          tabIndex={-1}
        >
          <AssistantSession
            key={patient.id}
            patient={patient}
            onClose={() => setOpen(false)}
          />
        </div>
      </div>
    </>
  );
}

function AssistantSession({
  patient,
  onClose,
}: {
  patient: Patient;
  onClose: () => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [research, setResearch] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [failed, setFailed] = useState<{
    question: string;
    research: boolean;
  } | null>(null);
  const pending = useRef<AbortController | null>(null);
  const conversation = useRef<HTMLDivElement>(null);

  useEffect(
    () => () => {
      pending.current?.abort();
      pending.current = null;
    },
    [],
  );
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      const chat = conversation.current;
      if (chat) {
        const latestMessage = chat.querySelector<HTMLElement>(
          ".assistant-message:last-of-type",
        );
        const target = latestMessage
          ? Math.max(
              0,
              latestMessage.getBoundingClientRect().top -
                chat.getBoundingClientRect().top +
                chat.scrollTop -
                8,
            )
          : chat.scrollHeight;
        if (typeof chat.scrollTo === "function") {
          chat.scrollTo({ top: target, behavior: "smooth" });
        } else {
          chat.scrollTop = target;
        }
      }
    });
    return () => cancelAnimationFrame(frame);
  }, [messages, busy]);

  async function send(text: string, useResearch = research) {
    const trimmed = text.trim();
    if (!trimmed || trimmed.length > 1000 || pending.current) return;
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true);
    setError("");
    setFailed(null);
    setQuestion("");
    const history = messages
      .slice(-6)
      .map(({ role, content }) => ({ role, content }));
    setMessages((old) => [...old, { role: "user", content: trimmed }]);
    const timer = setTimeout(() => controller.abort(), 50000);
    try {
      const response = await api<AssistantResponse>(
        `/patients/${patient.id}/assistant`,
        {
          method: "POST",
          body: JSON.stringify({
            question: trimmed,
            history,
            useResearchSources: useResearch,
          }),
          signal: controller.signal,
        },
      );
      if (!controller.signal.aborted) {
        setMessages((old) => [
          ...old,
          { role: "assistant", content: response.answer, response },
        ]);
      }
    } catch (e) {
      if (pending.current === controller) {
        setMessages((old) => old.slice(0, -1));
        setQuestion(trimmed);
        setFailed({ question: trimmed, research: useResearch });
        setError(
          controller.signal.aborted
            ? "The assistant took too long to respond. Please retry."
            : e instanceof Error
              ? e.message
              : "The assistant could not respond. Please retry.",
        );
      }
    } finally {
      clearTimeout(timer);
      if (pending.current === controller) {
        pending.current = null;
        setBusy(false);
      }
    }
  }

  return (
    <section
      className="panel assistant-panel"
      aria-labelledby="assistant-title"
    >
      <div className="assistant-heading">
        <div className="assistant-identity">
          <div className="assistant-mark">
            <BrainCircuit size={24} />
          </div>
          <div>
            <h2 id="assistant-title">Clinical Assistant</h2>
          </div>
        </div>
        <button
          type="button"
          className="assistant-widget-close"
          aria-label="Close Clinical Assistant"
          onClick={onClose}
        >
          <X size={18} />
        </button>
      </div>
      <div className="assistant-suggestions">
        {suggestions.map((item) => (
          <button
            key={item.label}
            disabled={busy}
            onClick={() => {
              if (item.research) setResearch(true);
              void send(item.question, item.research ?? research);
            }}
          >
            {item.research ? <BookOpen size={15} /> : <Sparkles size={15} />}
            {item.label}
            <ArrowUpRight size={13} />
          </button>
        ))}
      </div>
      {messages.length > 0 && (
        <div
          className="assistant-conversation"
          role="log"
          aria-label="Conversation with Clinical Assistant"
          aria-live="polite"
          ref={conversation}
        >
          {messages.map((message, index) => (
            <article
              key={index}
              className={`assistant-message assistant-message-${message.role}`}
            >
              <div className="assistant-message-label">
                {message.role === "user" ? "You" : "Clinical Assistant"}
              </div>
              <div className="assistant-answer">{message.content}</div>
              {message.response && (
                <AnswerEvidence response={message.response} />
              )}
            </article>
          ))}
        </div>
      )}
      {busy && (
        <div className="assistant-loading" role="status">
          <span className="pulse-dot" /> Reading the case
          {research ? " and reviewing evidence" : ""}…
        </div>
      )}
      {error && (
        <div className="assistant-error" role="alert">
          <p>{error}</p>
          <Button
            variant="outline"
            size="sm"
            disabled={busy || !failed}
            onClick={() =>
              failed && void send(failed.question, failed.research)
            }
          >
            Retry question
          </Button>
        </div>
      )}
      <form
        className="assistant-composer"
        onSubmit={(event) => {
          event.preventDefault();
          void send(question);
        }}
      >
        <label htmlFor="assistant-question" className="sr-only">
          Ask about this patient
        </label>
        <textarea
          id="assistant-question"
          placeholder="Ask about this case…"
          value={question}
          maxLength={1000}
          rows={2}
          disabled={busy}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing
            ) {
              event.preventDefault();
              void send(question);
            }
          }}
        />
        <div className="assistant-composer-actions">
          <label className="assistant-research-toggle">
            <input
              type="checkbox"
              checked={research}
              disabled={busy}
              onChange={(event) => setResearch(event.target.checked)}
            />
            <BookOpen size={14} /> Research sources
          </label>
          <span className="assistant-char-count">{question.length}/1000</span>
          <Button type="submit" disabled={busy || !question.trim()} size="sm">
            <Send size={14} /> Send
          </Button>
        </div>
      </form>
      <div className="assistant-footer">
        <Button
          variant="ghost"
          size="sm"
          disabled={busy || messages.length === 0}
          onClick={() => {
            setMessages([]);
            setError("");
            setFailed(null);
            setQuestion("");
          }}
        >
          <Trash2 size={13} /> Erase memory
        </Button>
      </div>
    </section>
  );
}

function AnswerEvidence({ response }: { response: AssistantResponse }) {
  return (
    <div className="assistant-evidence">
      {response.sources.length > 0 && (
        <details className="assistant-sources">
          <summary>
            <BookOpen size={14} /> Web references ({response.sources.length})
          </summary>
          {response.sources.map((source) => (
            <div className="assistant-source" key={source.url}>
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                referrerPolicy="no-referrer"
              >
                {source.title} <ArrowUpRight size={13} />
              </a>
              {source.supportedText.map((text, i) => (
                <p key={i}>{text}</p>
              ))}
            </div>
          ))}
        </details>
      )}
      {response.researchRequested && response.sources.length === 0 && (
        <p className="assistant-no-sources">
          No web references were returned for this response.
        </p>
      )}
      {response.searchSuggestions && (
        <iframe
          title="Google Search suggestions"
          className="assistant-search-suggestions"
          sandbox="allow-popups allow-popups-to-escape-sandbox"
          referrerPolicy="no-referrer"
          srcDoc={`<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src https: data:; base-uri 'none'; form-action 'none'"><base target="_blank">${response.searchSuggestions}`}
        />
      )}
    </div>
  );
}
