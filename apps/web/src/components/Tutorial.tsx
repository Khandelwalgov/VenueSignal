"use client";

import { useEffect, useRef, useState } from "react";

export const TUTORIAL_STORAGE_KEY = "venuesignal_tutorial_completed";

const steps = [
  {
    title: "Welcome to VenueSignal",
    text: "VenueSignal helps stadium operations controllers turn fragmented reports into verified, human-approved operational responses.",
    target: "overview",
    label: "Operations overview",
  },
  {
    title: "Reports are evidence",
    text: "Gemini structures incomplete operational reports as unverified evidence. It never turns a report into verified fact automatically.",
    target: "reports",
    label: "Report intake",
  },
  {
    title: "Humans verify",
    text: "VenueSignal can suggest relationships between reports, but the controller decides what belongs to the incident and what is verified.",
    target: "incident",
    label: "Incident intelligence",
  },
  {
    title: "Routing is deterministic",
    text: "AI does not decide route truth. A validated stadium graph calculates accessibility and facility impact.",
    target: "map",
    label: "Stadium operations map",
  },
  {
    title: "AI proposes, rules validate",
    text: "Gemini may propose a response plan. Deterministic rules validate it before the controller can approve anything.",
    target: "approval",
    label: "Controller decision",
  },
  {
    title: "Safe failure",
    text: "When conditions change, VenueSignal revalidates the plan. If no verified accessible route exists, it refuses to invent one and moves to safe containment.",
    target: "no-route",
    label: "No-route containment",
  },
];

export default function Tutorial({
  open,
  onClose,
  onStartDemo,
}: {
  open: boolean;
  onClose: () => void;
  onStartDemo: () => void;
}) {
  const [index, setIndex] = useState(0);
  const panelRef = useRef<HTMLElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);
  const step = steps[index];

  useEffect(() => {
    if (!open) return;
    previousFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const timeout = window.setTimeout(() => {
      setIndex(0);
      panelRef.current?.focus();
    }, 0);
    return () => {
      window.clearTimeout(timeout);
      previousFocus.current?.focus();
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const target = document.querySelector<HTMLElement>(`[data-tour="${step.target}"]`);
    target?.classList.add("tour-highlight");
    return () => target?.classList.remove("tour-highlight");
  }, [open, step.target]);

  if (!open) return null;

  function complete(callback?: () => void) {
    try { window.localStorage.setItem(TUTORIAL_STORAGE_KEY, "true"); } catch { /* Storage can be disabled. */ }
    onClose();
    callback?.();
  }

  return (
    <aside
      ref={panelRef}
      className="tutorial-card"
      role="dialog"
      aria-labelledby="tutorial-title"
      aria-describedby="tutorial-description"
      aria-modal="false"
      tabIndex={-1}
      onKeyDown={(event) => {
        if (event.key === "Escape") complete();
        if (event.key === "ArrowRight" && index < steps.length - 1) setIndex((current) => current + 1);
        if (event.key === "ArrowLeft" && index > 0) setIndex((current) => current - 1);
      }}
    >
      <div className="tutorial-progress" aria-label={`Tutorial step ${index + 1} of ${steps.length}`}>
        <span>Quick tour</span>
        <strong>{index + 1} / {steps.length}</strong>
      </div>
      <div className="tutorial-meter" aria-hidden="true"><i style={{ width: `${((index + 1) / steps.length) * 100}%` }} /></div>
      <span className="tutorial-target">Look for · {step.label}</span>
      <h2 id="tutorial-title">{step.title}</h2>
      <p id="tutorial-description">{step.text}</p>
      <div className="tutorial-actions">
        <button type="button" className="text-button" onClick={() => complete()}>Skip tour</button>
        <div>
          {index > 0 && <button type="button" className="secondary-button" onClick={() => setIndex((current) => current - 1)}>Back</button>}
          {index < steps.length - 1 ? (
            <button type="button" className="primary-button" onClick={() => setIndex((current) => current + 1)}>Next</button>
          ) : (
            <>
              <button type="button" className="secondary-button" onClick={() => complete()}>Explore dashboard</button>
              <button type="button" className="primary-button" onClick={() => complete(onStartDemo)}>Start Guided Demo</button>
            </>
          )}
        </div>
      </div>
    </aside>
  );
}
