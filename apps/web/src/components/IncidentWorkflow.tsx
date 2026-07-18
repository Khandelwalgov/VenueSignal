"use client";

import { useEffect, useRef, useState } from "react";

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

export default function IncidentWorkflow({
  onOperationalChange,
  readOnly,
}: {
  onOperationalChange: () => Promise<void>;
  readOnly: boolean;
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
  const [error, setError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const actionInFlight = useRef(false);
  const submittedApprovals = useRef(new Set<string>());

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
      setReports((current) => [...current, report]);
      setSelected((current) => [...current, report.id]);
      setText("");
      setAnnouncement("AI extraction complete. The report remains unverified.");
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
      setAnnouncement(`Controller verification recorded. Deterministic route analysis completed at context version ${result.impact.contextVersion}.`);
      await refreshQueues();
      await onOperationalChange();
    });
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
      setAnnouncement(`${revision ? "Containment revision" : "Response plan"} approved. ${approved.tasks.length} tasks now exist.`);
      await refreshQueues();
    });
    if (!succeeded) submittedApprovals.current.delete(approvalKey);
  }

  async function closeFallbackAndReassess() {
    if (!incident) return;
    await run(async () => {
      await setAssetStatus("A_CORRIDOR_W3", "OUT_OF_SERVICE", "EVALUATOR_WORKFLOW");
      const reassessed = await reassessIncident(incident.id);
      setIncident(reassessed);
      setAnnouncement(`Context changed to version ${reassessed.impact.contextVersion}. No verified safe step-free route currently exists. Human review is required.`);
      await refreshQueues();
      await onOperationalChange();
    });
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
      setAnnouncement(`Task changed to ${status.replaceAll("_", " ")}.`);
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
      setAnnouncement(`Communication changed to ${status.replaceAll("_", " ")}.`);
      await refreshQueues();
    });
  }

  async function terminalCommunication(item: Communication, status: "REJECTED" | "SUPERSEDED") {
    await run(async () => {
      await updateCommunication(item.id, status);
      await refreshQueues();
    });
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
    incident &&
    ["IN_PROGRESS", "MONITORING"].includes(incident.status) &&
    incident.tasks.length > 0 &&
    incident.tasks.every((task) => ["COMPLETED", "CANCELLED"].includes(task.status)),
  );

  return (
    <section className="workflow-panel" aria-labelledby="workflow-title" aria-busy={busy}>
      <div className="workflow-header">
        <div><span className="eyebrow">Human-in-the-loop incident intelligence</span><h2 id="workflow-title">Report → verify → plan → reassess</h2></div>
        <span className="count-pill">{incident?.status ?? "INTAKE"}</span>
      </div>
      <p className="muted">AI extraction is advisory. Reports remain unverified until a controller links them and confirms an asset state.</p>
      {readOnly && <p className="permission-notice" role="status">Viewer access is read-only. A server-verified controller role is required for reports, approvals, task changes, communications, and scenario mutations.</p>}
      {announcement && <p className="sr-only" role="status" aria-live="polite">{announcement}</p>}
      <div className="workflow-grid">
        <div className="workflow-step">
          <h3>1 · Collect reports</h3>
          <label htmlFor="report-text">Operational report</label>
          <textarea id="report-text" value={text} maxLength={4000} onChange={(event) => setText(event.target.value)} />
          <div className="button-row">
            <button type="button" disabled={busy || readOnly || text.trim().length < 3} onClick={submitReport}>Extract report</button>
            <button type="button" disabled={busy || readOnly} onClick={loadGoldenScenario}>Load 3-report scenario</button>
          </div>
          <ul className="report-list">
            {reports.map((report) => (
              <li key={report.id}>
                <label><input type="checkbox" disabled={readOnly} checked={selected.includes(report.id)} onChange={() => setSelected((ids) => ids.includes(report.id) ? ids.filter((id) => id !== report.id) : [...ids, report.id])} /> <strong>{report.extraction.category.replaceAll("_", " ")}</strong></label>
                <span>{report.extraction.summary}</span>
                <small>{Math.round(report.extraction.confidence * 100)}% extraction confidence · unverified claim</small>
                {report.matchCandidates?.[0] && <small>{report.matchCandidates[0].recommendation} suggestion · {Math.round(report.matchCandidates[0].score * 100)}% match confidence · controller decides</small>}
              </li>
            ))}
          </ul>
          <div className="import-box">
            <label htmlFor="report-upload">CSV or JSON evaluator import</label>
            <input id="report-upload" disabled={readOnly} type="file" accept=".csv,.json,text/csv,application/json" onChange={(event) => { setUpload(event.target.files?.[0] ?? null); setPreview(null); }} />
            <div className="button-row"><button type="button" disabled={busy || readOnly || !upload} onClick={() => previewImport(false)}>Preview import</button><button type="button" disabled={busy || readOnly || !upload || Boolean(preview?.errors.length)} onClick={() => previewImport(true)}>Commit valid import</button></div>
            {preview && <p role="status">{preview.validRows}/{preview.rowsDetected} valid · {preview.duplicateReportIds.length} duplicates · {preview.errors.length} errors</p>}
            {preview?.errors.map((item) => <small className="workflow-error" key={item}>{item}</small>)}
          </div>
        </div>

        <div className="workflow-step">
          <h3>2 · Controller verification</h3>
          <p>Link selected reports and confirm <b>Lift L2</b> as out of service. This changes operational context and validates impact deterministically.</p>
          <button type="button" disabled={busy || readOnly || selected.length === 0 || Boolean(incident)} onClick={confirmIncident}>Confirm incident and analyse impact</button>
          {incident && <div role="status" aria-live="assertive" className={`workflow-result ${incident.impact.routeResult.found ? "safe" : "unsafe"}`}><b>{incident.impact.routeResult.found ? "Fallback route verified" : "NO VERIFIED STEP-FREE ROUTE"}</b><span>{incident.impact.routeResult.message}</span><small>Deterministic result · operational context v{incident.impact.contextVersion}</small></div>}
        </div>

        <div className="workflow-step">
          <h3>3 · Human plan decision</h3>
          {incident ? <>
            <p role="status"><b>{incident.currentPlan.validity}</b> · context v{incident.currentPlan.contextVersion} · {Math.round(incident.currentPlan.confidence * 100)}% confidence</p>
            <p className="plan-source"><b>{incident.currentPlan.planSource.replaceAll("_", " ")}</b> · {incident.currentPlan.approvedAt ? `approved by ${incident.currentPlan.approvedBy ?? "controller"}` : "proposed output; controller approval required"}</p>
            <ol>{incident.currentPlan.actions.map((action) => <li key={`${action.actionType}-${action.locationId}`}><b>{action.title}</b><small>{action.assignedTeam} · {action.locationId}</small></li>)}</ol>
            <div className="button-row"><button type="button" disabled={busy || readOnly || Boolean(incident.proposedRevision) || incident.currentPlan.validity === "UNSAFE" || ["PLAN_APPROVED", "IN_PROGRESS", "MONITORING", "RESOLVED", "REJECTED"].includes(incident.status)} onClick={() => approve(false)}>Approve plan and create work</button><button type="button" disabled={busy || readOnly || Boolean(incident.proposedRevision) || ["PLAN_APPROVED", "IN_PROGRESS", "MONITORING", "RESOLVED", "REJECTED"].includes(incident.status)} onClick={() => terminalIncident("REJECTED")}>Reject unconfirmed incident</button></div>
            {incident.tasks.length > 0 && <p className="generated-counts">✓ {incident.tasks.length} tasks · {incident.communications.length} multilingual drafts</p>}
          </> : <p className="muted">A plan appears only after controller verification.</p>}
        </div>

        <div className="workflow-step">
          <h3>4 · Live reassessment</h3>
          <p>Close Corridor W3 after approval. The old plan is preserved, marked unsafe, and a revision is proposed for review.</p>
          <button type="button" disabled={busy || readOnly || !incident || incident.tasks.length === 0 || Boolean(incident.reassessment)} onClick={closeFallbackAndReassess}>Close W3 and reassess</button>
          {incident?.reassessment && <div role="status" aria-live="assertive" className={`reassessment ${incident.proposedRevision?.planSource === "DETERMINISTIC_CONTAINMENT" ? "containment" : "repaired"}`}><b>{incident.reassessment.validity}: human review required</b><span>{incident.reassessment.explanation}</span>{incident.proposedRevision && <><strong>{incident.proposedRevision.planSource.replaceAll("_", " ")}</strong><small>Context v{incident.proposedRevision.contextVersion} · {incident.proposedRevision.validity}</small><ol>{incident.proposedRevision.actions.map((action) => <li key={`${action.actionType}-${action.locationId}`}><b>{action.title}</b><small>{action.assignedTeam} · {action.locationId}</small></li>)}</ol>{!incident.impact.routeResult.found && <b>No route communication will be generated. Approval creates containment tasks only.</b>}</>}<button type="button" disabled={busy || readOnly || !incident.proposedRevision} onClick={() => approve(true)}>Approve containment revision</button></div>}
          {incident && <button className="resolve-button" type="button" disabled={busy || readOnly || !canResolve} onClick={() => terminalIncident("RESOLVED")}>Resolve after all work is terminal</button>}
        </div>
      </div>
      <div className="operations-ledger">
        <section id="task-queue" className="queue-panel" aria-labelledby="tasks-title">
          <div className="section-heading"><div><span className="eyebrow">Execution</span><h3 id="tasks-title">Task queue</h3></div><span className="count-pill">{tasks.length}</span></div>
          {tasks.length === 0 ? <p className="muted">Tasks appear only after plan approval.</p> : <ul>{tasks.map((task) => <li key={task.id}><span><strong>{task.title}</strong><small>{task.assignedTeam} · {task.status}</small>{task.blockedReason && <small>Blocked: {task.blockedReason}</small>}</span><span className="queue-actions">{nextTaskStatus(task.status) && <button type="button" disabled={busy || readOnly} onClick={() => advanceTask(task)}>Move to {nextTaskStatus(task.status)?.replaceAll("_", " ")}</button>}{["ASSIGNED", "ACKNOWLEDGED", "IN_PROGRESS"].includes(task.status) && <button type="button" disabled={busy || readOnly} onClick={() => blockTask(task)}>Block</button>}</span></li>)}</ul>}
        </section>
        <section id="communication-queue" className="queue-panel" aria-labelledby="communications-title">
          <div className="section-heading"><div><span className="eyebrow">Human-reviewed output</span><h3 id="communications-title">Communication queue</h3></div><span className="count-pill">{communications.length}</span></div>
          {communications.length === 0 ? <p className="muted">Drafts appear only after plan approval.</p> : <ul>{communications.map((item) => <li key={item.id}><span><strong lang={item.language}>{item.language.toUpperCase()} · {item.status}</strong><small lang={item.language}>{item.content}</small></span><span className="queue-actions">{nextCommunicationStatus(item.status) && <button type="button" disabled={busy || readOnly} onClick={() => advanceCommunication(item)}>Move to {nextCommunicationStatus(item.status)?.replaceAll("_", " ")}</button>}{["DRAFT", "UNDER_REVIEW"].includes(item.status) && <button type="button" disabled={busy || readOnly} onClick={() => terminalCommunication(item, "REJECTED")}>Reject</button>}{["APPROVED", "PUBLISHED_SIMULATED"].includes(item.status) && <button type="button" disabled={busy || readOnly} onClick={() => terminalCommunication(item, "SUPERSEDED")}>Supersede</button>}</span></li>)}</ul>}
        </section>
        <section id="audit-timeline" className="queue-panel audit-panel" aria-labelledby="audit-title">
          <div className="section-heading"><div><span className="eyebrow">Accountability</span><h3 id="audit-title">Audit timeline</h3></div><span className="count-pill">{audit.length}</span></div>
          {audit.length === 0 ? <p className="muted">Consequential decisions are recorded here.</p> : <ol>{audit.slice(0, 8).map((event) => <li key={event.id}><strong>{event.eventType.replaceAll("_", " ")}</strong><span>{event.summary}</span><small>Context v{event.contextVersion} · {event.actor}</small></li>)}</ol>}
        </section>
      </div>
      {error && <p className="workflow-error" role="alert">{error}</p>}
    </section>
  );
}
