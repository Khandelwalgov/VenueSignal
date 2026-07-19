"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  approveIncident,
  AuditEvent,
  Communication,
  createIncident,
  createReport,
  fetchAudit,
  fetchCommunications,
  fetchIncidents,
  fetchReports,
  fetchTasks,
  importReports,
  Incident,
  ImportPreview,
  reassessIncident,
  setAssetStatus,
  VenueReport,
  updateCommunication,
  updateIncidentStatus,
  updateTask,
  WorkflowTask,
} from "@/lib/api";

const GOLDEN_REPORTS = [
  "Lift near Section 214 is stuck again. Two wheelchair users are waiting.",
  "Upper west accessible path is blocked, sending people toward Corridor W3.",
  "Crowd building near the west stairs after halftime.",
];

export interface WorkflowSummary {
  incident: Incident | null;
  reports: number;
  tasks: number;
  communications: number;
}

function SignalBadge({ kind, children }: { kind: "ai" | "verified" | "evidence" | "deterministic" | "human"; children: React.ReactNode }) {
  const symbols = { ai: "✦", verified: "✓", evidence: "?", deterministic: "◆", human: "●" };
  return <span className={`signal-badge signal-${kind}`}><span aria-hidden="true">{symbols[kind]}</span>{children}</span>;
}

function readable(value: string) {
  return value.replaceAll("_", " ");
}

function facilityLabel(id: string) {
  return ({ A_LIFT_2: "Lift L2", A_CORRIDOR_W3: "Corridor W3" } as Record<string, string>)[id] ?? readable(id);
}

function languageLabel(language: string) {
  return ({ en: "English", es: "Spanish", fr: "French" } as Record<string, string>)[language] ?? language.toUpperCase();
}

export default function IncidentWorkflow({
  onOperationalChange,
  onSummaryChange,
  readOnly,
  startDemoSignal,
}: {
  onOperationalChange: () => Promise<void>;
  onSummaryChange?: (summary: WorkflowSummary) => void;
  readOnly: boolean;
  startDemoSignal: number;
}) {
  const [text, setText] = useState(GOLDEN_REPORTS[0]);
  const [reports, setReports] = useState<VenueReport[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [incident, setIncident] = useState<Incident | null>(null);
  const [tasks, setTasks] = useState<WorkflowTask[]>([]);
  const [communications, setCommunications] = useState<Communication[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [upload, setUpload] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [demoMode, setDemoMode] = useState(false);
  const [demoStep, setDemoStep] = useState(1);
  const [containmentReviewOpen, setContainmentReviewOpen] = useState(false);
  const [communicationLanguage, setCommunicationLanguage] = useState("en");
  const actionInFlight = useRef(false);
  const submittedApprovals = useRef(new Set<string>());
  const handledDemoSignal = useRef(0);

  async function refreshQueues() {
    const [storedReports, incidents, storedTasks, storedCommunications, events] = await Promise.all([
      fetchReports(), fetchIncidents(), fetchTasks(), fetchCommunications(), fetchAudit(),
    ]);
    setReports(storedReports);
    setTasks(storedTasks);
    setCommunications(storedCommunications);
    setAudit(events);
    if (incidents.length) setIncident(incidents[0]);
  }

  useEffect(() => {
    const timeout = window.setTimeout(() => void refreshQueues().catch(() => undefined), 0);
    return () => window.clearTimeout(timeout);
  }, []);

  useEffect(() => {
    onSummaryChange?.({ incident, reports: reports.length, tasks: tasks.length, communications: communications.length });
  }, [communications.length, incident, onSummaryChange, reports.length, tasks.length]);

  const startGuidedDemo = useCallback(() => {
    setDemoMode(true);
    setContainmentReviewOpen(false);
    if (incident?.reassessment || incident?.proposedRevision) setDemoStep(6);
    else if (incident?.tasks.length) setDemoStep(5);
    else if (incident) setDemoStep(3);
    else if (reports.length >= 3) setDemoStep(2);
    else setDemoStep(1);
    window.requestAnimationFrame(() => {
      const workspace = document.getElementById("incidents");
      if (typeof workspace?.scrollIntoView === "function") workspace.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [incident, reports.length]);

  useEffect(() => {
    if (startDemoSignal <= handledDemoSignal.current) return;
    handledDemoSignal.current = startDemoSignal;
    startGuidedDemo();
  }, [startDemoSignal, startGuidedDemo]);

  async function run(action: () => Promise<void>): Promise<boolean> {
    if (actionInFlight.current) return false;
    actionInFlight.current = true;
    setBusy(true);
    setError(null);
    try { await action(); return true; }
    catch (reason: unknown) { setError(reason instanceof Error ? reason.message : "Workflow action failed."); return false; }
    finally { actionInFlight.current = false; setBusy(false); }
  }

  async function submitReport() {
    await run(async () => {
      const report = await createReport(text);
      setReports((current) => [...current.filter((item) => item.id !== report.id), report]);
      setSelected((current) => current.includes(report.id) ? current : [...current, report.id]);
      setText("");
      setAnnouncement("AI extraction complete. The report remains unverified evidence.");
    });
  }

  async function loadGoldenScenario() {
    const succeeded = await run(async () => {
      const created: VenueReport[] = [];
      for (const [index, rawText] of GOLDEN_REPORTS.entries()) {
        setAnalysisProgress(index + 1);
        created.push(await createReport(rawText, true));
      }
      setReports(created);
      setSelected(created.slice(0, 2).map((report) => report.id));
      setAnnouncement("Three incoming reports were structured as unverified evidence. The controller must confirm their relationship.");
    });
    setAnalysisProgress(0);
    if (succeeded) setDemoStep(2);
  }

  async function confirmIncident() {
    const succeeded = await run(async () => {
      const result = await createIncident(selected);
      setIncident(result);
      setAnnouncement("Incident created. Lift L2 is verified unavailable and the deterministic accessibility impact is ready.");
      await refreshQueues();
      await onOperationalChange();
    });
    if (succeeded) setDemoStep(3);
  }

  async function approve(revision = false) {
    if (!incident) return;
    const planId = revision ? incident.proposedRevision?.id : incident.currentPlan.id;
    const approvalKey = `${incident.id}:${planId ?? "missing"}`;
    if (submittedApprovals.current.has(approvalKey)) return;
    submittedApprovals.current.add(approvalKey);
    const succeeded = await run(async () => {
      const approved = await approveIncident(incident.id, revision);
      setIncident(approved);
      setAnnouncement(`${revision ? "Containment revision" : "Response plan"} approved. ${approved.tasks.length} operational tasks now exist.`);
      await refreshQueues();
    });
    if (!succeeded) submittedApprovals.current.delete(approvalKey);
    if (succeeded && !revision) setDemoStep(5);
  }

  async function closeFallbackAndReassess() {
    if (!incident) return;
    const succeeded = await run(async () => {
      await setAssetStatus("A_CORRIDOR_W3", "OUT_OF_SERVICE", "EVALUATOR_WORKFLOW");
      const reassessed = await reassessIncident(incident.id);
      setIncident(reassessed);
      setAnnouncement("Route conditions changed. The former plan is unsafe, no verified step-free route remains, and human review is required.");
      await refreshQueues();
      await onOperationalChange();
    });
    if (succeeded) setDemoStep(6);
  }

  async function previewImport(commit: boolean) {
    if (!upload) return;
    await run(async () => {
      const result = await importReports(upload, commit);
      setPreview(result);
      if (commit) await refreshQueues();
    });
  }

  function nextTaskStatus(status: string): string | null {
    return ({ CREATED: "ASSIGNED", ASSIGNED: "ACKNOWLEDGED", ACKNOWLEDGED: "IN_PROGRESS", IN_PROGRESS: "COMPLETED" } as Record<string, string>)[status] ?? null;
  }

  async function advanceTask(task: WorkflowTask) {
    const status = nextTaskStatus(task.status);
    if (!status) return;
    await run(async () => {
      await updateTask(task.id, status, status === "COMPLETED" ? "Completion confirmed in controller workspace." : undefined);
      setAnnouncement(`Task changed to ${readable(status)}.`);
      await refreshQueues();
    });
  }

  async function blockTask(task: WorkflowTask) {
    await run(async () => {
      await updateTask(task.id, "BLOCKED", undefined, "Controller recorded an execution blocker requiring plan review.");
      await refreshQueues();
    });
  }

  function nextCommunicationStatus(status: string): string | null {
    return ({ DRAFT: "UNDER_REVIEW", UNDER_REVIEW: "APPROVED", APPROVED: "PUBLISHED_SIMULATED" } as Record<string, string>)[status] ?? null;
  }

  async function advanceCommunication(item: Communication) {
    const status = nextCommunicationStatus(item.status);
    if (!status) return;
    await run(async () => {
      await updateCommunication(item.id, status);
      setAnnouncement(`Communication changed to ${readable(status)}.`);
      await refreshQueues();
    });
  }

  async function terminalCommunication(item: Communication, status: "REJECTED" | "SUPERSEDED") {
    await run(async () => { await updateCommunication(item.id, status); await refreshQueues(); });
  }

  async function terminalIncident(status: "RESOLVED" | "REJECTED") {
    if (!incident) return;
    await run(async () => {
      setIncident(await updateIncidentStatus(
        incident.id,
        status,
        status === "RESOLVED" ? "Controller verified execution completion and incident closure." : "Controller rejected the unconfirmed incident.",
      ));
      await refreshQueues();
    });
  }

  const canResolve = Boolean(
    incident && ["IN_PROGRESS", "MONITORING"].includes(incident.status) && incident.tasks.length > 0 &&
    incident.tasks.every((task) => ["COMPLETED", "CANCELLED"].includes(task.status)),
  );

  const taskGroups = useMemo(() => [
    { title: "Requires attention", items: tasks.filter((task) => ["CREATED", "BLOCKED"].includes(task.status)) },
    { title: "In progress", items: tasks.filter((task) => ["ASSIGNED", "ACKNOWLEDGED", "IN_PROGRESS"].includes(task.status)) },
    { title: "Complete", items: tasks.filter((task) => ["COMPLETED", "CANCELLED"].includes(task.status)) },
  ], [tasks]);

  const communicationLanguages = useMemo(
    () => Array.from(new Set(communications.map((item) => item.language))),
    [communications],
  );
  const activeCommunicationLanguage = communicationLanguages.includes(communicationLanguage)
    ? communicationLanguage
    : communicationLanguages[0] ?? "en";
  const communicationGroups = useMemo(() => {
    const visible = communications.filter((item) => item.language === activeCommunicationLanguage);
    return [
      { title: "Awaiting review", items: visible.filter((item) => ["DRAFT", "UNDER_REVIEW"].includes(item.status)) },
      { title: "Approved", items: visible.filter((item) => item.status === "APPROVED") },
      { title: "Simulated published or closed", items: visible.filter((item) => ["PUBLISHED_SIMULATED", "REJECTED", "SUPERSEDED"].includes(item.status)) },
    ];
  }, [activeCommunicationLanguage, communications]);

  const route = incident?.impact.routeResult;
  const plan = incident?.currentPlan;
  const proposedRevision = incident?.proposedRevision;

  return (
    <section id="incidents" className="workflow-panel" aria-labelledby="workflow-title" aria-busy={busy} data-tour="incident">
      <div className="workflow-header">
        <div>
          <span className="eyebrow">Active incident workspace</span>
          <h2 id="workflow-title">From fragmented reports to a verified response</h2>
          <p>AI structures evidence. Deterministic rules verify safety. The controller decides.</p>
        </div>
        <div className="workflow-header-actions">
          {demoMode && <span className="demo-mode-badge">Guided demo · {demoStep}/6</span>}
          {demoMode && <button type="button" className="text-button" onClick={() => setDemoMode(false)}>Exit guide</button>}
        </div>
      </div>

      {readOnly && <p className="permission-notice" role="status">Viewer access is read-only. A server-verified controller role is required for operational decisions.</p>}
      {error && <p className="workflow-error visible-workflow-error" role="alert">{error} {demoMode && demoStep === 1 ? "The guided scenario did not advance. Retry to resume the idempotent analysis." : ""}</p>}
      {announcement && <p className="sr-only" role="status" aria-live="assertive">{announcement}</p>}

      {demoMode && (
        <ol className="demo-progress" aria-label={`Guided demo step ${demoStep} of 6`}>
          {["Reports", "Relationship", "Impact", "Response", "Activation", "Change"].map((label, index) => (
            <li key={label} className={demoStep === index + 1 ? "current" : demoStep > index + 1 ? "complete" : ""} aria-current={demoStep === index + 1 ? "step" : undefined}>
              <span>{demoStep > index + 1 ? "✓" : index + 1}</span>{label}
            </li>
          ))}
        </ol>
      )}

      <div className="incident-stage" data-tour={demoStep === 6 ? "no-route" : demoStep === 5 ? "change" : demoStep === 4 ? "approval" : undefined}>
        {demoMode && demoStep === 1 && (
          <div className="stage-content">
            <div className="stage-heading"><span>Step 1 of 6 · Incoming evidence</span><h3>Three reports arrive</h3><p>They describe one possible accessibility disruption from different viewpoints.</p></div>
            <div className="incoming-reports">
              {GOLDEN_REPORTS.map((report, index) => <article key={report}><span>Report {index + 1}</span><SignalBadge kind="evidence">Unverified evidence</SignalBadge><p>{report}</p></article>)}
            </div>
            <div className="stage-action"><SignalBadge kind="ai">AI structures reports as evidence</SignalBadge><button type="button" className="primary-button" disabled={busy || readOnly} onClick={loadGoldenScenario}>{busy ? `Analysing report ${analysisProgress || 1} of 3…` : error ? "Retry analysis" : "Analyse reports"}</button></div>
          </div>
        )}

        {demoMode && demoStep === 2 && (
          <div className="stage-content">
            <div className="stage-heading"><span>Step 2 of 6 · Incident intelligence</span><SignalBadge kind="ai">AI insight</SignalBadge><h3>AI suggests an incident relationship</h3><p>Evidence remains unverified until the controller confirms what belongs together.</p></div>
            {reports.some((report) => report.provenance === "GUIDED_DEMO_QUOTA_FALLBACK") && <p className="fallback-notice" role="status">Gemini quota was unavailable, so the guided demo used the labelled local extraction fallback.</p>}
            <div className="evidence-grid">
              {reports.map((report) => (
                <article key={report.id}>
                  <SignalBadge kind="evidence">Unverified evidence</SignalBadge>
                  <h4>{readable(report.extraction.category)}</h4>
                  <p>{report.extraction.summary}</p>
                  <small>{Math.round(report.extraction.confidence * 100)}% extraction confidence</small>
                  {report.extraction.candidateAssetIds[0] && <small><b>Candidate facility:</b> {facilityLabel(report.extraction.candidateAssetIds[0])}</small>}
                  {report.matchCandidates?.[0] && <small><b>{Math.round(report.matchCandidates[0].score * 100)}% relationship confidence</b> · {readable(report.matchCandidates[0].recommendation)}</small>}
                </article>
              ))}
            </div>
            <div className="controller-decision"><SignalBadge kind="human">Controller decision required</SignalBadge><p>Link the first two reports and confirm Lift L2 unavailable.</p><button type="button" className="primary-button" disabled={busy || readOnly || selected.length === 0} onClick={confirmIncident}>Confirm incident</button></div>
          </div>
        )}

        {demoMode && demoStep === 3 && incident && route && (
          <div className="stage-content">
            <div className="stage-heading"><span>Step 3 of 6 · Deterministic impact</span><SignalBadge kind="deterministic">Deterministic validation</SignalBadge><h3>Accessibility impact verified</h3><p>Lift L2 is unavailable. The verified step-free fallback uses Corridor W3.</p></div>
            <div className="situation-grid">
              <article><SignalBadge kind="verified">Verified fact</SignalBadge><strong>Lift L2 unavailable</strong><p>Accessible access to Sections 209–218 is affected.</p></article>
              <article><SignalBadge kind="deterministic">Deterministic validation</SignalBadge><strong>{route.found ? "Accessible route: Corridor W3" : "No route verified"}</strong><p>Distance: {Math.round(route.distanceMeters)} m · public step-free path</p></article>
              <article><span className="priority-badge">High priority</span><strong>Assistance required</strong><p>Two wheelchair users are reported waiting. The claim remains unverified.</p></article>
            </div>
            <div className="stage-action"><span>Operational state updated</span><button type="button" className="primary-button" onClick={() => setDemoStep(4)}>Review response</button></div>
          </div>
        )}

        {demoMode && demoStep === 4 && incident && plan && (
          <div className="stage-content">
            <div className="stage-heading"><span>Step 4 of 6</span><h3>Review the proposed response</h3><p>The response is not actionable until deterministic validation passes and a human approves it.</p></div>
            <div className="recommendation-card">
              <div className="recommendation-labels"><SignalBadge kind="ai">AI proposal</SignalBadge><SignalBadge kind="deterministic">Deterministic validation · passed</SignalBadge></div>
              <h4>{plan.operationalObjective}</h4>
              <ol>{plan.actions.map((action) => <li key={`${action.actionType}-${action.locationId}`}><span aria-hidden="true">✓</span><div><strong>{action.title}</strong><small>{readable(action.assignedTeam)}</small></div></li>)}</ol>
              <details className="technical-details"><summary>Review details</summary><p>Source: {readable(plan.planSource)} · confidence {Math.round(plan.confidence * 100)}% · state version {plan.contextVersion}</p></details>
            </div>
            <div className="controller-decision"><SignalBadge kind="human">Human approval required</SignalBadge><button type="button" className="primary-button" disabled={busy || readOnly || plan.validity === "UNSAFE"} onClick={() => approve(false)}>Approve plan</button></div>
          </div>
        )}

        {demoMode && demoStep === 5 && incident && (
          <div className="stage-content activation-state">
            <div className="success-mark" aria-hidden="true">✓</div>
            <div className="stage-heading"><span>Step 5 of 6</span><h3>Response activated</h3><p>The approved plan is now translated into controlled operational work.</p></div>
            <div className="activation-counts"><a href="#tasks"><strong>{incident.tasks.length}</strong><span>Operational tasks created</span></a><a href="#communications"><strong>{incident.communications.length}</strong><span>Multilingual drafts prepared</span></a></div>
            <p className="calm-note">Nothing was created before approval. Communication remains draft-only until reviewed.</p>
            <div className="activation-links"><a href="#tasks">View tasks</a><a href="#communications">Review communications</a></div>
            <div className="stage-action"><span>Next, the verified fallback will become unavailable.</span><button type="button" className="primary-button" disabled={busy || readOnly || Boolean(incident.reassessment)} onClick={closeFallbackAndReassess}>Continue scenario</button></div>
          </div>
        )}

        {demoMode && demoStep === 6 && incident && route && (
          <div className="stage-content no-route-state" role="status" aria-live="assertive">
            <div className="no-route-heading"><span aria-hidden="true">!</span><div><span>Step 6 of 6 · Conditions changed</span><h3>No verified safe step-free route</h3><p>Lift L2 and Corridor W3 are unavailable. VenueSignal will not issue positive route guidance.</p></div></div>
            <div className="invalidated-plan"><span>Previous plan</span><strong>Unsafe</strong><small>Corridor W3 closed · verified fallback invalidated</small></div>
            <div className="containment-panel">
              <div><SignalBadge kind="deterministic">Safe containment</SignalBadge><h4>{proposedRevision?.planSource === "GEMINI_REPAIRED" ? "Gemini proposal repaired and revalidated" : "Deterministic containment proposed"}</h4></div>
              <ul>{(proposedRevision?.actions ?? []).map((action) => <li key={`${action.actionType}-${action.locationId}`}><span aria-hidden="true">✓</span>{action.title}</li>)}</ul>
              <strong className="no-guidance">× No route guidance will be published.</strong>
            </div>
            {!containmentReviewOpen ? (
              <div className="stage-action"><SignalBadge kind="human">Human approval required</SignalBadge><button type="button" className="primary-button" onClick={() => setContainmentReviewOpen(true)}>Review containment plan</button></div>
            ) : (
              <div className="controller-decision containment-decision"><p>{incident.reassessment?.explanation}</p><details className="technical-details"><summary>Technical recovery details</summary><p>Source: {readable(proposedRevision?.planSource ?? "unknown")} · state version {proposedRevision?.contextVersion ?? "—"}</p></details><button type="button" className="primary-button" disabled={busy || readOnly || !proposedRevision} onClick={() => approve(true)}>Approve containment revision</button></div>
            )}
          </div>
        )}

        {!demoMode && !incident && (
          <div className="empty-incident">
            <span aria-hidden="true">✓</span><div><h3>No active incident requires attention</h3><p>Start the guided demo from Operations, or use report tools below for evaluator-supplied evidence.</p></div>
          </div>
        )}

        {!demoMode && incident && (
          <div className={`stage-content incident-summary ${!route?.found ? "is-unsafe" : ""}`}>
            <div className="stage-heading"><span>{incident.status === "PLAN_PROPOSED" ? "Controller attention required" : readable(incident.status)}</span><h3>Lift L2 accessibility disruption</h3><p>{route?.found ? "Lift L2 is unavailable. A public step-free fallback remains verified." : "Lift L2 and Corridor W3 are unavailable. Positive route guidance is withheld."}</p></div>
            <div className="situation-grid">
              <article><SignalBadge kind="verified">Verified</SignalBadge><strong>{incident.verifiedFacts[0] ?? "Lift L2 unavailable"}</strong></article>
              <article><SignalBadge kind="deterministic">Impact</SignalBadge><strong>{route?.found ? "W3 fallback" : "No verified route"}</strong>{route?.found && <p>{Math.round(route.distanceMeters)} m</p>}</article>
              <article><SignalBadge kind="human">Next action</SignalBadge><strong>{proposedRevision ? "Review containment" : incident.tasks.length ? "Monitor execution" : "Approve response"}</strong></article>
            </div>
            {!incident.tasks.length && !proposedRevision && <div className="button-row"><button type="button" className="primary-button" disabled={busy || readOnly || plan?.validity === "UNSAFE"} onClick={() => approve(false)}>Approve plan and create work</button><button type="button" className="secondary-button" disabled={busy || readOnly} onClick={() => terminalIncident("REJECTED")}>Reject unconfirmed incident</button></div>}
            {proposedRevision && <button type="button" className="primary-button" onClick={() => { setDemoMode(true); setDemoStep(6); }}>Review no-route containment</button>}
          </div>
        )}
      </div>

      <details id="reports" className="advanced-panel" data-tour="reports">
        <summary><span><b>Reports and evaluator intake</b><small>Manual entry, relationship selection, and CSV/JSON import</small></span><span className="count-pill">{reports.length}</span></summary>
        <div className="advanced-content">
          <div className="report-entry">
            <label htmlFor="report-text">Operational report</label>
            <textarea id="report-text" value={text} maxLength={4000} onChange={(event) => setText(event.target.value)} />
            <div className="button-row"><button type="button" className="primary-button" disabled={busy || readOnly || text.trim().length < 3} onClick={submitReport}>Extract report</button><button type="button" className="secondary-button" disabled={busy || readOnly} onClick={loadGoldenScenario}>Load 3-report scenario</button></div>
          </div>
          <ul className="report-list">
            {reports.length === 0 && <li className="queue-empty">No incoming reports are awaiting analysis.</li>}
            {reports.map((report) => <li key={report.id}><label><input type="checkbox" disabled={readOnly} checked={selected.includes(report.id)} onChange={() => setSelected((ids) => ids.includes(report.id) ? ids.filter((id) => id !== report.id) : [...ids, report.id])} /><span><b>{readable(report.extraction.category)}</b><small>{report.extraction.summary}</small></span></label><SignalBadge kind="evidence">Unverified</SignalBadge></li>)}
          </ul>
          <div className="manual-actions"><button type="button" className="primary-button" disabled={busy || readOnly || selected.length === 0 || Boolean(incident)} onClick={confirmIncident}>Confirm incident and analyse impact</button><details><summary>Import CSV or JSON</summary><label htmlFor="report-upload">CSV or JSON evaluator import</label><input id="report-upload" disabled={readOnly} type="file" accept=".csv,.json,text/csv,application/json" onChange={(event) => { setUpload(event.target.files?.[0] ?? null); setPreview(null); }} /><div className="button-row"><button type="button" className="secondary-button" disabled={busy || readOnly || !upload} onClick={() => previewImport(false)}>Preview import</button><button type="button" className="secondary-button" disabled={busy || readOnly || !upload || Boolean(preview?.errors.length)} onClick={() => previewImport(true)}>Commit valid import</button></div>{preview && <p role="status">{preview.validRows}/{preview.rowsDetected} valid · {preview.duplicateReportIds.length} duplicates · {preview.errors.length} errors</p>}{preview?.errors.map((item) => <small className="workflow-error" key={item}>{item}</small>)}</details></div>
        </div>
      </details>

      {incident?.tasks.length ? <div className="response-summary"><div><span aria-hidden="true">✓</span><span><strong>Response activated</strong><small>{incident.tasks.length} tasks created · {incident.communications.length} communication drafts prepared</small></span></div><div><a href="#tasks">View tasks</a><a href="#communications">Review communications</a></div></div> : null}

      <div className="operations-ledger">
        <details id="tasks" className="queue-panel">
          <summary><span><b>Tasks</b><small>{tasks.length ? `${tasks.length} operational assignments` : "No operational tasks are currently assigned."}</small></span><span className="count-pill">{tasks.length}</span></summary>
          <div className="queue-groups">{taskGroups.map((group) => group.items.length > 0 && <section key={group.title}><h3>{group.title}</h3><ul>{group.items.map((task) => <li key={task.id}><span><strong>{task.title}</strong><small>{readable(task.assignedTeam)} · {readable(task.status)}</small>{task.blockedReason && <small>Blocked: {task.blockedReason}</small>}</span><span className="queue-actions">{nextTaskStatus(task.status) && <button type="button" disabled={busy || readOnly} onClick={() => advanceTask(task)}>Move to {readable(nextTaskStatus(task.status) ?? "")}</button>}{["ASSIGNED", "ACKNOWLEDGED", "IN_PROGRESS"].includes(task.status) && <button type="button" disabled={busy || readOnly} onClick={() => blockTask(task)}>Block</button>}</span></li>)}</ul></section>)}</div>
        </details>
        <details id="communications" className="queue-panel">
          <summary><span><b>Communications</b><small>{communications.length ? `${communications.length} human-reviewed drafts` : "No communication drafts are awaiting review."}</small></span><span className="count-pill">{communications.length}</span></summary>
          <div className="queue-groups">
            {communications.length > 0 && <><p className="simulated-note">Simulated drafts only. Nothing is delivered to the public.</p><div className="language-tabs" role="group" aria-label="Communication language">{communicationLanguages.map((language) => <button key={language} type="button" aria-pressed={activeCommunicationLanguage === language} onClick={() => setCommunicationLanguage(language)}>{languageLabel(language)}</button>)}</div></>}
            {communicationGroups.map((group) => group.items.length > 0 && <section key={group.title}><h3>{group.title}</h3><ul>{group.items.map((item) => <li key={item.id}><span><strong lang={item.language}>{languageLabel(item.language)} · {readable(item.status)}</strong><small lang={item.language}>{item.content}</small></span><span className="queue-actions">{nextCommunicationStatus(item.status) && <button type="button" disabled={busy || readOnly} onClick={() => advanceCommunication(item)}>Move to {readable(nextCommunicationStatus(item.status) ?? "")}</button>}{["DRAFT", "UNDER_REVIEW"].includes(item.status) && <button type="button" disabled={busy || readOnly} onClick={() => terminalCommunication(item, "REJECTED")}>Reject</button>}{["APPROVED", "PUBLISHED_SIMULATED"].includes(item.status) && <button type="button" disabled={busy || readOnly} onClick={() => terminalCommunication(item, "SUPERSEDED")}>Supersede</button>}</span></li>)}</ul></section>)}
          </div>
        </details>
      </div>

      <details id="audit" className="advanced-panel audit-panel">
        <summary><span><b>Audit and technical details</b><small>Decision history, identifiers, provider provenance, and state versions</small></span><span className="count-pill">{audit.length}</span></summary>
        <div className="audit-content">
          {incident && <dl><div><dt>Incident ID</dt><dd>{incident.id}</dd></div><div><dt>Operational state</dt><dd>Version {incident.impact.contextVersion}</dd></div><div><dt>Plan source</dt><dd>{readable(proposedRevision?.planSource ?? plan?.planSource ?? "none")}</dd></div></dl>}
          {audit.length === 0 ? <p>No consequential decisions recorded yet.</p> : <ol>{audit.slice(0, 8).map((event) => <li key={event.id}><strong>{readable(event.eventType)}</strong><span>{event.summary}</span><small>State version {event.contextVersion} · {event.actor}</small></li>)}</ol>}
        </div>
      </details>

      {incident && <button className="resolve-button text-button" type="button" disabled={busy || readOnly || !canResolve} onClick={() => terminalIncident("RESOLVED")}>Resolve incident after all work is complete</button>}
    </section>
  );
}
