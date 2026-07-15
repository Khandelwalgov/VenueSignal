"use client";

import { useState } from "react";

import {
  approveIncident,
  createIncident,
  createReport,
  Incident,
  reassessIncident,
  setAssetStatus,
  VenueReport,
} from "@/lib/api";

const GOLDEN_REPORTS = [
  "Lift near Section 214 is stuck again. Two wheelchair users are waiting.",
  "Upper west accessible path is blocked, sending people toward Corridor W3.",
  "Crowd building near the west stairs after halftime.",
];

export default function IncidentWorkflow({ onOperationalChange }: { onOperationalChange: () => Promise<void> }) {
  const [text, setText] = useState(GOLDEN_REPORTS[0]);
  const [reports, setReports] = useState<VenueReport[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [incident, setIncident] = useState<Incident | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try { await action(); }
    catch (reason: unknown) { setError(reason instanceof Error ? reason.message : "Workflow action failed."); }
    finally { setBusy(false); }
  }

  async function submitReport() {
    await run(async () => {
      const report = await createReport(text);
      setReports((current) => [...current, report]);
      setSelected((current) => [...current, report.id]);
      setText("");
    });
  }

  async function loadGoldenScenario() {
    await run(async () => {
      const created = [] as VenueReport[];
      for (const rawText of GOLDEN_REPORTS) created.push(await createReport(rawText));
      setReports(created);
      setSelected(created.slice(0, 2).map((report) => report.id));
      setIncident(null);
    });
  }

  async function confirmIncident() {
    await run(async () => {
      const result = await createIncident(selected);
      setIncident(result);
      await onOperationalChange();
    });
  }

  async function approve(revision = false) {
    if (!incident) return;
    await run(async () => setIncident(await approveIncident(incident.id, revision)));
  }

  async function closeFallbackAndReassess() {
    if (!incident) return;
    await run(async () => {
      await setAssetStatus("A_CORRIDOR_W3", "OUT_OF_SERVICE", "EVALUATOR_WORKFLOW");
      setIncident(await reassessIncident(incident.id));
      await onOperationalChange();
    });
  }

  return (
    <section className="workflow-panel" aria-labelledby="workflow-title">
      <div className="workflow-header">
        <div><span className="eyebrow">Human-in-the-loop incident intelligence</span><h2 id="workflow-title">Report → verify → plan → reassess</h2></div>
        <span className="count-pill">{incident?.status ?? "INTAKE"}</span>
      </div>
      <p className="muted">AI extraction is advisory. Reports remain unverified until a controller links them and confirms an asset state.</p>
      <div className="workflow-grid">
        <div className="workflow-step">
          <strong>1 · Collect reports</strong>
          <label htmlFor="report-text">Operational report</label>
          <textarea id="report-text" value={text} maxLength={4000} onChange={(event) => setText(event.target.value)} />
          <div className="button-row">
            <button type="button" disabled={busy || text.trim().length < 3} onClick={submitReport}>Extract report</button>
            <button type="button" disabled={busy} onClick={loadGoldenScenario}>Load 3-report scenario</button>
          </div>
          <ul className="report-list">
            {reports.map((report) => (
              <li key={report.id}>
                <label><input type="checkbox" checked={selected.includes(report.id)} onChange={() => setSelected((ids) => ids.includes(report.id) ? ids.filter((id) => id !== report.id) : [...ids, report.id])} /> <strong>{report.extraction.category.replaceAll("_", " ")}</strong></label>
                <span>{report.extraction.summary}</span>
                <small>{Math.round(report.extraction.confidence * 100)}% extraction confidence · unverified claim</small>
              </li>
            ))}
          </ul>
        </div>

        <div className="workflow-step">
          <strong>2 · Controller verification</strong>
          <p>Link selected reports and confirm <b>Lift L2</b> as out of service. This changes operational context and validates impact deterministically.</p>
          <button type="button" disabled={busy || selected.length === 0 || Boolean(incident)} onClick={confirmIncident}>Confirm incident and analyse impact</button>
          {incident && <div className={`workflow-result ${incident.impact.routeResult.found ? "safe" : "unsafe"}`}><b>{incident.impact.routeResult.found ? "Fallback route verified" : "No verified step-free route"}</b><span>{incident.impact.routeResult.message}</span></div>}
        </div>

        <div className="workflow-step">
          <strong>3 · Review response plan</strong>
          {incident ? <>
            <p><b>{incident.currentPlan.validity}</b> · context v{incident.currentPlan.contextVersion} · {Math.round(incident.currentPlan.confidence * 100)}% confidence</p>
            <ol>{incident.currentPlan.actions.map((action) => <li key={`${action.actionType}-${action.locationId}`}><b>{action.title}</b><small>{action.assignedTeam} · {action.locationId}</small></li>)}</ol>
            <button type="button" disabled={busy || incident.status === "PLAN_APPROVED"} onClick={() => approve(false)}>Approve plan and create work</button>
            {incident.tasks.length > 0 && <p className="generated-counts">✓ {incident.tasks.length} tasks · {incident.communications.length} multilingual drafts</p>}
          </> : <p className="muted">A plan appears only after controller verification.</p>}
        </div>

        <div className="workflow-step">
          <strong>4 · Live reassessment</strong>
          <p>Close Corridor W3 after approval. The old plan is preserved, marked unsafe, and a revision is proposed for review.</p>
          <button type="button" disabled={busy || !incident || incident.tasks.length === 0 || Boolean(incident.reassessment)} onClick={closeFallbackAndReassess}>Close W3 and reassess</button>
          {incident?.reassessment && <div className="reassessment"><b>{incident.reassessment.validity}: human review required</b><span>{incident.reassessment.explanation}</span><button type="button" disabled={busy || !incident.proposedRevision} onClick={() => approve(true)}>Approve containment revision</button></div>}
        </div>
      </div>
      {error && <p className="workflow-error" role="alert">{error}</p>}
    </section>
  );
}
