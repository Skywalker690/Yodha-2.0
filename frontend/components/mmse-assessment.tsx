"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, ClipboardList, X } from "lucide-react";
import { api } from "@/lib/api";
import type { MMSEAssessment as Assessment, Patient, Visit } from "@/types";
import { Button } from "./ui/button";

const localDateTime = (iso: string) => {
  const date = new Date(iso);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

export function MMSEAssessment({
  patient,
  visit,
  reload,
}: {
  patient: Patient;
  visit: Visit;
  reload: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [attempt, setAttempt] = useState<Assessment | null>(null);
  const [points, setPoints] = useState<Record<string, number | null>>({});
  const [assessedAt, setAssessedAt] = useState("");
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const dialog = useRef<HTMLDivElement>(null);
  const request = useRef<AbortController | null>(null);
  const summary = visit.metadata.mmseAssessment;
  const imported = patient.source === "oasis-2";
  const demo = attempt?.instrument === "alzhio-cognitive-demo";
  const tasks = attempt?.definition.items || [];
  const task = tasks[step];
  const scored = tasks.filter((item) => points[item.id] != null).length;
  const complete = scored === tasks.length && tasks.length > 0;
  const preview = Object.values(points).reduce<number>(
    (total, value) => total + (value ?? 0),
    0,
  );

  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialog.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) setOpen(false);
      if (event.key !== "Tab") return;
      const controls = Array.from(
        dialog.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled), input:not(:disabled), summary, [tabindex="0"]',
        ) || [],
      );
      const first = controls[0];
      const last = controls.at(-1);
      if (
        event.shiftKey &&
        (document.activeElement === first ||
          document.activeElement === dialog.current)
      ) {
        event.preventDefault();
        last?.focus();
      } else if (
        !event.shiftKey &&
        (document.activeElement === last ||
          document.activeElement === dialog.current)
      ) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKey);
      previousFocus?.focus();
    };
  }, [open, busy]);

  const start = async () => {
    setOpen(true);
    setBusy(true);
    setError("");
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    try {
      const saved = await api<Assessment>(`/visits/${visit.id}/mmse`, {
        method: "POST",
        body: "{}",
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      setAttempt(saved);
      setPoints(saved.items);
      setAssessedAt(localDateTime(saved.assessedAt));
      const next = saved.definition.items.findIndex(
        (item) => saved.items[item.id] == null,
      );
      setStep(next < 0 ? saved.definition.items.length : next);
    } catch (cause) {
      if (!controller.signal.aborted) setError((cause as Error).message);
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  };

  const save = async (finish: boolean) => {
    if (!attempt || !assessedAt) return;
    setBusy(true);
    setError("");
    const controller = new AbortController();
    request.current = controller;
    try {
      const base = `/visits/${visit.id}/mmse/${attempt.id}`;
      const saved = await api<Assessment>(base, {
        method: "PATCH",
        signal: controller.signal,
        body: JSON.stringify({
          revision: attempt.revision,
          assessedAt: new Date(assessedAt).toISOString(),
          items: tasks.map((item) => ({
            itemId: item.id,
            points: points[item.id] ?? null,
          })),
        }),
      });
      if (controller.signal.aborted) return;
      setAttempt(saved);
      if (finish) {
        const result = await api<Assessment>(`${base}/complete`, {
          method: "POST",
          body: JSON.stringify({ revision: saved.revision }),
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        setAttempt(result);
      }
      reload();
      setOpen(false);
    } catch (cause) {
      if (!controller.signal.aborted) setError((cause as Error).message);
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  };

  return (
    <>
      <section
        className="panel cognitive-assessment-card"
        aria-label="Cognitive assessment"
      >
        <div>
          <span className="eyebrow">COGNITIVE ASSESSMENT</span>
          <h3>
            {summary?.total != null
              ? `${summary.instrument === "mmse-original" ? "MMSE" : "Demo cognitive score"}: ${summary.total}/30`
              : visit.metadata.MMSE != null
                ? `Recorded MMSE: ${visit.metadata.MMSE}/30`
                : "No completed assessment"}
          </h3>
          <p>
            {summary?.assessedAt
              ? `${visit.label} · ${new Date(summary.assessedAt).toLocaleString()} · ${summary.language}`
              : `${visit.label} · Score is calculated from task performance.`}
          </p>
        </div>
        {imported ? (
          <span className="badge">Imported study observation</span>
        ) : (
          <Button variant="outline" onClick={() => void start()}>
            <ClipboardList size={16} />{" "}
            {summary?.hasDraft ? "Resume assessment" : "Start assessment"}
          </Button>
        )}
      </section>
      {open && (
        <div className="cognitive-dialog-layer">
          <div
            className="cognitive-dialog panel"
            ref={dialog}
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-labelledby="cognitive-title"
          >
            <header className="cognitive-dialog-heading">
              <div>
                <span className="eyebrow">
                  {visit.label} · CLINICIAN-GUIDED
                </span>
                <h2 id="cognitive-title">
                  {attempt
                    ? demo
                      ? "MMSE-style demo"
                      : "MMSE assessment"
                    : "Cognitive assessment"}
                </h2>
              </div>
              <button
                className="icon-button"
                aria-label="Close assessment"
                disabled={busy}
                onClick={() => setOpen(false)}
              >
                <X size={20} />
              </button>
            </header>
            {error && (
              <p className="cognitive-error" role="alert">
                {error}
              </p>
            )}
            {!attempt ? (
              <p>
                {busy
                  ? "Loading assessment…"
                  : "Reopen the assessment to try again."}
              </p>
            ) : (
              <>
                {demo && (
                  <p className="cognitive-demo-note">
                    English demonstration tasks · not a standardized MMSE. The
                    demo score is recorded separately from clinical MMSE.
                  </p>
                )}
                <div className="cognitive-progress-row">
                  <span>
                    {scored}/{tasks.length} tasks scored
                  </span>
                  <span>{attempt.language}</span>
                </div>
                <progress
                  value={scored}
                  max={tasks.length}
                  aria-label="Assessment progress"
                />
                <div className="cognitive-dialog-content">
                  {task ? (
                    <>
                      <span className="eyebrow">
                        TASK {step + 1} OF {tasks.length}
                      </span>
                      <h3>{task.title}</h3>
                      <div className="cognitive-prompt">{task.prompt}</div>
                      {demo && task.id === "drawing" && (
                        <svg
                          className="cognitive-drawing"
                          viewBox="0 0 200 130"
                          role="img"
                          aria-label="Two overlapping rectangles to copy"
                        >
                          <rect x="25" y="20" width="95" height="65" />
                          <rect x="75" y="50" width="95" height="65" />
                        </svg>
                      )}
                      <details className="cognitive-rubric">
                        <summary>Clinician scoring guide</summary>
                        <p>{task.rubric}</p>
                      </details>
                      <fieldset disabled={busy} className="cognitive-points">
                        <legend>
                          Points earned · maximum {task.max_points}
                        </legend>
                        {Array.from(
                          { length: task.max_points + 1 },
                          (_, value) => (
                            <label key={value}>
                              <input
                                type="radio"
                                name={task.id}
                                checked={points[task.id] === value}
                                onChange={() =>
                                  setPoints((current) => ({
                                    ...current,
                                    [task.id]: value,
                                  }))
                                }
                              />
                              {value} {value === 1 ? "point" : "points"}
                            </label>
                          ),
                        )}
                      </fieldset>
                    </>
                  ) : (
                    <>
                      <h3>Review assessment</h3>
                      <p>
                        {complete
                          ? `Calculated preview: ${preview}/30. The backend verifies the final total.`
                          : "Some tasks are unanswered. Save a draft or return to complete them."}
                      </p>
                      <div className="cognitive-review-list">
                        {tasks.map((item, index) => (
                          <button
                            key={item.id}
                            disabled={busy}
                            onClick={() => setStep(index)}
                          >
                            <span>{item.title}</span>
                            <span>
                              {points[item.id] == null
                                ? "Unanswered"
                                : `${points[item.id]}/${item.max_points}`}
                            </span>
                          </button>
                        ))}
                      </div>
                      <label className="cognitive-date">
                        Assessment date and time
                        <input
                          type="datetime-local"
                          value={assessedAt}
                          onChange={(event) =>
                            setAssessedAt(event.target.value)
                          }
                          required
                          disabled={busy}
                        />
                      </label>
                    </>
                  )}
                </div>
                <footer className="cognitive-dialog-actions">
                  <Button
                    variant="ghost"
                    disabled={busy || !assessedAt}
                    onClick={() => void save(false)}
                  >
                    Save draft & close
                  </Button>
                  <div>
                    <Button
                      variant="outline"
                      disabled={busy || step === 0}
                      onClick={() => setStep((value) => value - 1)}
                    >
                      <ArrowLeft size={15} /> Back
                    </Button>
                    {task ? (
                      <Button
                        disabled={busy}
                        onClick={() => setStep((value) => value + 1)}
                      >
                        {step === tasks.length - 1 ? "Review" : "Next"}
                        <ArrowRight size={15} />
                      </Button>
                    ) : (
                      <Button
                        disabled={busy || !complete || !assessedAt}
                        onClick={() => void save(true)}
                      >
                        {busy ? "Saving…" : "Complete assessment"}
                      </Button>
                    )}
                  </div>
                </footer>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
