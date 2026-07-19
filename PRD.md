# VenueSignal Product Requirements Document

**Product:** VenueSignal  
**Challenge:** PromptWars Virtual Challenge 04 — Smart Stadiums & Tournament Operations  
**Primary persona:** Venue Operations Controller  
**Primary vertical:** Operational Intelligence  
**Supporting vertical:** Real-time Decision Support  
**Document status:** Implemented product baseline and production-integration specification  
**Last updated:** 18 July 2026

## 1. Executive summary

VenueSignal is an incident-intelligence system for facility and access disruptions inside a tournament venue. It transforms fragmented, untrusted operational reports into structured evidence; suggests—but never automatically performs—incident linking; applies only human-confirmed facility changes; calculates accessibility and route consequences with deterministic graph code; proposes a constrained response plan; requires human approval; creates tasks and multilingual communication drafts; and revalidates the approved plan whenever operational context changes.

The product is intentionally narrow. It is not a fan super-app, indoor consumer navigation system, generic chatbot, official FIFA map, autonomous emergency-response system, or digital twin of a real stadium. Its deep speciality is disruptions such as lift failures, corridor closures, scanner failures, blocked step-free paths, accessible-facility outages, and infrastructure-driven crowd buildup.

The core product equation is:

`untrusted input + authoritative venue context + deterministic safety rules + bounded AI assistance + visible human approval = explainable operational action`

## 2. Problem and opportunity

Venue controllers receive reports through radio, staff observations, accessibility teams, maintenance systems, and evaluator feeds. Those reports are often incomplete, duplicated, contradictory, multilingual, or separated from their operational consequences. A lift fault may be reported near a seating section while another team reports a blocked corridor and a third reports crowd accumulation. The controller must determine whether the reports are related, what is verified, which route dependencies fail, who is affected, what action is permitted, and whether a previously approved response is still safe.

Without VenueSignal:

- reports remain fragmented;
- claims are easily mistaken for facts;
- route and accessibility consequences require manual cross-checking;
- response plans can become stale after conditions change;
- task and communication provenance is difficult to audit;
- positive route guidance may be issued even when evidence is insufficient.

With VenueSignal:

- evidence is normalized and labelled as unverified;
- possible related reports are shortlisted with reasons and confidence;
- the controller explicitly links reports and confirms facility state;
- graph truth is recomputed against the current versioned overlay;
- response actions are checked against allow-lists and known identifiers;
- work and communication are created only after approval;
- operational mutations automatically trigger active-plan reassessment;
- “No verified safe step-free route currently exists” is a first-class safe outcome.

## 3. Goals

### 3.1 Product goals

1. Make the incident thesis understandable in under 30 seconds.
2. Demonstrate a real state-changing workflow rather than generated prose or a static dashboard.
3. Keep AI advisory and deterministic code authoritative for safety-critical facts and execution.
4. Make accessibility consequences visible at every relevant stage.
5. Preserve evidence, decisions, context versions, and operational actions for audit.
6. Support a credential-free local demo and credential-backed Google production deployment through the same domain interfaces.

### 3.2 Success indicators

- A controller can complete the golden scenario in under four minutes.
- No task or communication is created before plan approval.
- Every mutable venue operation increments `contextVersion`.
- A stale plan is rejected at approval.
- Closing Lift L2 and Corridor W3 results in no verified step-free route.
- Viewer identities cannot mutate operational state.
- Duplicate evaluator imports are idempotent.
- The canonical graph starts with one component, no isolated nodes, and all designated accessible destinations reachable step-free.

## 4. Non-goals

- Certified emergency egress planning
- Real-time positioning or personal tracking
- Automated emergency dispatch
- Autonomous incident merging or plan approval
- Real message delivery or public-address integration
- Official venue or FIFA data
- General fan engagement, ticketing, commerce, travel, or entertainment
- AI-generated graph traversal

## 5. Users and roles

### 5.1 Controller

The controller can create and import reports, review extraction, link reports, verify facility state, approve plans, mutate operational overlays, advance tasks, review communications, simulate publication, resolve incidents, reset scenarios, and inspect audit history.

### 5.2 Viewer

The viewer can inspect venue state, reports, incidents, routes, tasks, communications, and audit history. The viewer cannot mutate any consequential state.

### 5.3 Authentication modes

- `disabled`: local development only; the server supplies a local controller identity.
- `test`: deterministic bearer tokens for authorization tests.
- `firebase`: the backend verifies Firebase ID tokens, including revocation, and derives the role from trusted custom claims. Production configuration refuses disabled authentication.

## 6. Synthetic venue

Unity Stadium is a fictional three-level tournament venue. It is not an official FIFA stadium map. All geometry, routes, facility states, reports, crowd values, operational events, and telemetry are synthetic or evaluator-supplied.

The venue has two representations:

1. A visual React/SVG stadium map for comprehension and selection.
2. A machine-readable graph that is the sole source of topology and route truth.

The canonical graph contains 3 levels, 11 zones, 40 nodes, 47 edges, and 12 assets. It models entrances, concourses, seating, lifts, stairs, escalators, corridors, scanners, accessible restrooms, medical points, waiting points, a quiet assistance area, dependencies, staff-only paths, crowd values, noise, rest points, distance, and estimated time.

## 7. Product principles and authority boundaries

### 7.1 AI may

- structure untrusted reports;
- identify candidate assets and zones from authoritative lists;
- expose missing information and clarification questions;
- assess semantic report similarity;
- synthesize verified facts and labelled claims;
- propose constrained response plans;
- generate audience-specific draft communications;
- explain why changed context affects an approved plan.

### 7.2 Deterministic code must

- load and validate canonical topology;
- own all identifiers, statuses, transitions, dependencies, routes, constraints, and context versions;
- calculate facility and accessibility impact;
- enforce controller/viewer authorization;
- validate plan actions, locations, teams, route availability, and freshness;
- create tasks and audit events;
- enforce task, communication, and incident state machines;
- reject unsafe, stale, malformed, invented, or unauthorized actions;
- provide safe failure.

### 7.3 AI must never

- invent a venue identifier or route;
- silently verify a report;
- auto-link reports;
- approve or execute a response plan;
- issue route guidance that deterministic validation rejects;
- treat text inside an uploaded report as system instructions;
- conceal uncertainty or missing evidence.

## 8. End-to-end functional requirements

### 8.1 Venue startup and validation

The backend must load the canonical venue during FastAPI lifespan startup using a module-relative or configured path. Missing files, malformed JSON, schema errors, or graph-integrity errors must fail startup. Warnings may allow startup but must be exposed.

Validation covers duplicate identifiers and edges; references; percentages; capacities; distances; time; coordinates; status/type support; memberships; transition consistency; staff-only paths; dependencies; reachability; graph components; isolated nodes; primary gates; medical points; waiting points; accessible restrooms; step-free destinations; and flagship scenario readiness.

### 8.2 Venue inspection

The API and UI expose venue status, statistics, full graph, levels, zones, nodes, multi-level assets, validation, and base accessibility reachability. A multi-level asset appears on every served level and exposes served levels, zones, nodes, edges, dependencies, status, criticality, and description.

### 8.3 Operational overlay

Canonical JSON remains immutable. Runtime state is stored in a separate overlay containing asset, edge, zone, and crowd overrides; context version; last update time; and event history. Every mutation is typed, bounded, audited, and versioned. Reset removes overrides without erasing history.

### 8.4 Deterministic routing

Weighted Dijkstra evaluates shortest feasible routes under step-free, public/staff, maximum-distance, crowd, dependent-asset, rest-point, and lower-noise rules. Responses contain ordered node and edge IDs, distance, estimated time, satisfied constraints, rejected reasons, message, and operational context version. The engine returns an explicit no-route response rather than relaxing safety constraints.

### 8.5 Report intake

The controller can enter a report manually or preview/commit CSV and JSON imports. Inputs support English, Spanish, and French labels, bounded source metadata, and synthetic provenance. Imports accept only approved extension/MIME combinations, at most 200 KB and 50 rows, return row-level errors, and reject formula-like report content.

Every report receives a normalized SHA-256 fingerprint. Explicit idempotency keys take precedence; otherwise normalized text, language, and source determine identity. Repeated manual or uploaded data returns the original report instead of duplicating evidence.

### 8.6 Extraction and incident fusion

Extraction returns category, summary, candidate IDs, affected groups, symptoms, urgency, confidence, unverified claims, missing information, clarification questions, injection warning, and provider attribution. Verified facts remain empty until controller action.

Related-report reasoning compares at most the 20 most recent reports. The bounded comparison avoids a model-category or omitted-ID prefilter suppressing a potentially related report. The AI provider must return `LINK`, `CREATE_NEW`, or `HUMAN_REVIEW_REQUIRED`, with reasons, differences, contradictions, and match confidence. The controller remains the only merge authority.

### 8.7 Incident confirmation and impact

Incident creation requires unique known report IDs, a known asset, and an allowed status. The controller’s confirmation updates the operational overlay and becomes a verified fact. Report claims remain separately labelled.

Impact analysis returns affected nodes, edges, zones, inaccessible destinations, accessibility consequences, deterministic route result, rejected route reasons, crowd/capacity concerns, required capabilities, and context version.

### 8.8 Response plan

The AI provider receives verified facts, labelled claims, deterministic impact, known IDs, allowed action types, known teams, and current context. The plan includes situation assessment, objective, actions, rationale, risks, assumptions, missing information, confidence, reassessment triggers, validity, context version, and source.

Deterministic validation runs before a proposal is exposed and again at approval. It returns structured errors for stale versions, model self-approval, empty actions, invalid dependencies, unknown teams or locations, disallowed action types, invalid no-route validity, and route actions when no route exists. No task or communication exists before approval.

If the first Gemini plan is invalid, VenueSignal preserves it in a recovery record, supplies the exact errors and current authoritative context to exactly one repair call, and validates again. A valid repair is exposed as `GEMINI_REPAIRED`. A second invalid output, timeout, quota error, or malformed output produces `DETERMINISTIC_CONTAINMENT`. The fallback is bounded to waiting-point, accessibility-dispatch, asset-inspection, and route-status-verification actions. No recursive generation occurs, and every source still requires human approval.

The six-step guided scenario has an additional quota-only continuity boundary. A controller-submitted report marked `GUIDED_DEMO` may fall back server-side to `LOCAL_DEMO_PROVIDER` only when Gemini raises the classified quota error. The persisted report is labelled `GUIDED_DEMO_QUOTA_FALLBACK`, the UI discloses the switch, and the normal incident, deterministic routing, validation, approval, task, communication, state-mutation, and reassessment APIs continue. Ordinary/manual report intake never uses this path and remains fail-closed. No third-party API key is accepted by the browser.

### 8.9 Tasks

Task states are `CREATED`, `ASSIGNED`, `ACKNOWLEDGED`, `IN_PROGRESS`, `BLOCKED`, `COMPLETED`, and `CANCELLED`. Transitions are deterministic. Dependencies must complete before work begins. Completion requires evidence. Blocking requires a reason and marks the plan `REQUIRES_MODIFICATION` for controller review.

### 8.10 Communications

Approval of a verified-route plan creates affected-fan drafts in English, Spanish, and French. States are `DRAFT`, `UNDER_REVIEW`, `APPROVED`, `PUBLISHED_SIMULATED`, `SUPERSEDED`, and `REJECTED`. Transitions are deterministic, actor-attributed, and audited. `PUBLISHED_SIMULATED` never claims real delivery. When no verified route exists, earlier route drafts are superseded, the outstanding task tied to route staffing is cancelled, and containment approval creates no route communication.

### 8.11 Reassessment

Active approved incidents are automatically reassessed after asset, edge, or crowd mutations. The system records old and new context versions, changed facts, invalidated assumptions, affected actions, route difference, validity, explanation, and human-review requirement. The approved plan remains preserved and is marked `UNSAFE` or otherwise changed; a validated repaired or deterministic containment revision is separate and cannot replace it until approval.

### 8.12 Resolution

Only active incidents can resolve. All tasks must be completed or cancelled first. Approved incidents cannot be rejected. Resolution marks the plan resolved and records the actor and reason.

## 9. Golden scenario acceptance

Initial reports:

1. “Lift near Section 214 is stuck again. Two wheelchair users are waiting.”
2. “Upper west accessible path is blocked, sending people toward Corridor W3.”
3. “Crowd building near the west stairs after halftime.”

Expected sequence:

- reports are extracted as unverified evidence;
- the first two are suggested as related;
- the third is shown as a possible consequence, never automatically confirmed;
- the controller links reports and confirms Lift L2 unavailable;
- the normal 215 m route is invalidated;
- stairs are rejected for the step-free constraint;
- the 530 m W3 fallback is verified while open;
- a plan proposes maintenance, accessibility assistance, and staffing;
- approval creates one task per validated action and three language drafts;
- closing W3 increments context and automatically revalidates the plan;
- no safe step-free route remains;
- the old plan becomes unsafe and is not rewritten;
- an invalid route-staffing revision is withheld and repaired at most once;
- containment uses a staffed waiting point, accessibility assistance, inspection, and route verification without positive route guidance;
- existing route drafts become superseded and no new route communication is generated;
- the revision requires approval.

## 10. User interface requirements

The controller workspace provides top-level navigation for Operations, Reports, Incidents, Venue State, Tasks, Communications, Scenarios, and Audit while keeping the flagship loop on one page.

### 10.1 Left rail

- level selector;
- golden scenario controls;
- zone list;
- facility filter and mirrored asset controls.

### 10.2 Center

- recognizable stadium bowl and field;
- level/zone geometry;
- selectable facilities and useful nodes;
- edge and route overlays;
- non-colour status patterns and symbols;
- map description and operational-truth disclaimer.

### 10.3 Right rail

- selected entity detail;
- current route/no-route status;
- graph validation and statistics;
- base step-free availability.

### 10.4 Workflow and ledgers

- manual and file report intake;
- extraction confidence and unverified status;
- report-match recommendation and controller boundary;
- controller confirmation;
- impact and plan review;
- approval and revision controls;
- task queue with lifecycle actions;
- communication queue with language attributes and review actions;
- audit timeline with context and actor.

### 10.5 Identity

Local mode shows the server-provided development controller. Firebase mode provides email/password sign-in through the modular Firebase SDK, persists the session locally, sends the Firebase ID token to the API, and displays the server-verified role.

## 11. Accessibility requirements

- keyboard-complete workflow;
- native controls and labelled forms;
- skip link and semantic headings;
- visible focus;
- accessible SVG title and description;
- mirrored map controls;
- no colour-only state;
- textual route and map alternatives;
- screen-reader status and error messages;
- translation language attributes;
- responsive reflow without horizontal document scrolling;
- text resizing and reduced motion;
- understandable import errors;
- no SVG-only action.

Accessibility is both an interface standard and domain capability. No verified step-free route is a valid and visible safety result.

## 12. Architecture

### 12.1 Frontend

Next.js 16 App Router, React 19, TypeScript, modular Firebase Authentication, native SVG, and typed API clients. The interactive workspace is a client boundary because it requires state and events. Secrets never enter the client bundle; Firebase web identifiers are public configuration, while the Gemini key stays server-side.

### 12.2 Backend

FastAPI, Pydantic, explicit settings validation, domain services, weighted Dijkstra, provider protocols, repository protocols, security middleware, and typed route models.

### 12.3 Persistence

- In-memory adapters for isolated tests and ephemeral demos.
- SQLite adapters for durable local and single-process deployment.
- Firestore adapters for production reports, incidents, tasks embedded in incidents, communications, operational state, context, and audit events.

Canonical topology remains version-controlled JSON and is never destructively moved into mutable storage.

### 12.4 AI providers

- `LocalDemoAIProvider`: deterministic, offline, schema-compatible demo provider.
- `GeminiProvider`: official Google Gen AI SDK, JSON-schema output, bounded retries, timeout/quota/malformed-response classification, model/task/attempt/latency metadata, no prompt content logging, and server-only key.

### 12.5 Deployment

- Frontend: Vercel or Firebase Hosting.
- Backend: non-root Cloud Run container.
- Build/deploy: Cloud Build and Artifact Registry.
- Secrets: Secret Manager.
- Auth: Firebase Authentication.
- Data: Firestore and emulator configuration.

## 13. API surface

Health: `/health`, `/ready`.  
Identity: `/api/auth/me`.  
Venue: list, summary, graph, levels, assets, zones, nodes, validation, accessibility summary.  
Operations: state, events, asset/edge/crowd mutation, reset, route query.  
Workflow: reports, import preview/commit, incidents, approval, reassessment, terminal status, tasks, communications, audit, reset.

All `/api` routes require identity. Mutation routes require controller role. Health/readiness remain available for infrastructure probes.

## 14. Security and privacy requirements

- production requires Firebase authentication, Firestore persistence, a non-loopback CORS origin, and disabled demo reset by default;
- Firebase ID tokens are verified server-side with revocation checking;
- roles come from trusted token claims, never frontend assertions;
- CORS uses explicit origins and never wildcard;
- request and upload sizes are bounded;
- IP rate limiting returns `429` and `Retry-After`;
- request IDs support traceability without logging evidence content;
- security headers disable framing, MIME sniffing, browser sensors, and uncontrolled content;
- production OpenAPI UI is disabled;
- direct Firestore client access is denied;
- Cloud Run uses a non-root user;
- secrets are injected through Secret Manager or server environment;
- prompt-like report text is flagged and isolated;
- plan output is schema- and domain-validated;
- mutable actions and decisions are audited;
- API errors are safe and do not expose credentials or stack traces.

## 15. Reliability and performance

- startup blocks on invalid canonical data or invalid production settings;
- health and readiness are separate;
- repositories use deep copies or serialized boundaries to prevent hidden mutation;
- SQLite writes are transactional;
- Firestore documents use stable application IDs;
- AI calls retry a bounded number of times and fail closed;
- routing is deterministic and independent of provider availability;
- request and model input lengths are bounded;
- tracked repository size warns above 8 MB and fails above 9.5 MB.

For a multi-instance production deployment, Firestore is required. SQLite is intended only for a single API process.

## 16. Testing and quality requirements

Backend tests cover graph mutation validation, startup, venue APIs, routes and constraints, operational versioning, report extraction, raw/CSV injection handling, matching, approval, stale plans, invented IDs/teams/actions, one-shot repair, invalid repaired output, timeout/quota/malformed repair fallback, containment, duplicate execution, tasks, dependencies, communications, resolution, automatic reassessment, imports, idempotency, SQLite persistence, Gemini error contracts, authentication, authorization, rate limits, declared/actual request limits, and security headers.

Frontend tests cover rendering, disclosure, map alternatives, level/zone/asset controls, keyboard use, loading/errors, no-route containment, repaired/fallback provenance, no-route communication suppression, duplicate-click protection, advisory extraction, approval gating, verified identity, top-level information architecture, upload preview, task/communication lifecycle controls, and audit display.

Release gates are backend tests, production SDK imports, frontend tests, ESLint, TypeScript, Next.js production build, npm production audit, whitespace checks, and repository-size enforcement. Final manual verification uses the in-app browser across the golden flow and responsive breakpoints.

## 17. Data retention and privacy assumptions

The demonstration contains no real personal data. Production operators must define retention, deletion, access logging, lawful basis, regional storage, and incident-record policies before processing real reports. The application should store only operationally necessary content and avoid sensitive spectator identity where aggregate accessibility needs are sufficient.

## 18. Risks and mitigations

| Risk | Mitigation |
|---|---|
| AI invents an identifier | Schema plus deterministic known-ID validation |
| AI suggests an unsafe route | Proposal withheld; one constrained repair; deterministic containment if still invalid |
| Report contains prompt injection | Treat as untrusted evidence, detect instruction patterns, never concatenate as policy |
| Plan becomes stale | Context-version validation and automatic reassessment |
| Viewer attempts mutation | Server-side role dependency returns 403 |
| Duplicate uploads create false corroboration | SHA-256 fingerprints and deterministic report IDs |
| Direct Firestore access bypasses API | Deny-all client rules; Admin SDK only |
| No route exists | Explicit containment response and human review |
| External AI unavailable | Deterministic route/state continues; provider fails closed |
| Local multi-process divergence | Use Firestore in production |

## 19. Established implementation status

Implemented and tested locally:

- complete validated graph and stadium UI;
- route and operational-state engine;
- report, incident, impact, plan, approval, task, communication, reassessment, and resolution domain;
- local, SQLite, and Firestore repository implementations;
- local and Gemini AI provider implementations;
- local/test/Firebase authentication implementations;
- controller/viewer authorization;
- rate limiting, security headers, body/upload bounds, idempotency, and audit;
- Firebase/Firestore emulator configuration;
- non-root Cloud Run container and Cloud Build definition;
- controller workspace, upload, ledgers, verified identity, and audit UI.

Credential-dependent validation still required outside this repository:

- a real Firebase project and custom role claims;
- Application Default Credentials and Firestore database;
- Secret Manager entries, Artifact Registry repository, Cloud Run service, frontend hosting project, and public domains;
- final venue-operator, security, privacy, and assistive-technology review.

These are deployment prerequisites, not hidden demo implementations.

Live Gemini credentials were validated on 18 July 2026 against `gemini-2.5-flash`. Structured extraction, bounded semantic matching, initial plan generation, multilingual approval output, and reassessment explanation completed successfully. Gemini's first no-route revision included `STAFF_VERIFIED_ROUTE`; pre-review deterministic validation recorded `NO_VERIFIED_ROUTE` and withheld it. Exactly one repair call returned only `INSPECT_ASSET`, `VERIFY_ROUTE_STATUS`, `DISPATCH_ACCESSIBILITY_TEAM`, and `ESTABLISH_WAITING_POINT`; it passed schema and deterministic validation as `GEMINI_REPAIRED`. Containment approval was idempotent, old route drafts remained `SUPERSEDED`, and no new communication was generated.

A subsequent fully hardened rerun reached Gemini quota during initial plan generation and reassessment. Both HTTP workflows remained available and returned approval-gated `DETERMINISTIC_CONTAINMENT`; repeated approval stayed at eight total tasks and zero communications. Thus the final pass verified both the successful repaired-model branch and the quota-fallback branch without retry recursion.

## 20. Launch acceptance checklist

1. All automated gates pass with zero high/critical dependency vulnerabilities.
2. Canonical validation reports zero errors and documented warnings only.
3. Golden scenario passes in the production build.
4. Firebase controller and viewer identities produce expected 200/403 behavior.
5. Firestore persistence survives API restart and emulator integration tests.
6. Gemini extraction and plan output pass schema/domain validation with live credentials.
7. Secret values are absent from source, client bundles, logs, and error responses.
8. Production CORS contains only deployed frontend origins.
9. Cloud Run readiness succeeds and production OpenAPI is disabled.
10. Keyboard, screen reader, 200% zoom, reduced motion, and mobile/tablet checks pass.
11. Operational owner approves the no-route containment language.
12. Privacy, retention, incident response, monitoring, backup, and rollback policies are assigned.

## 21. Final local verification record

The completed repository was verified on 18 July 2026 with:

- 93 backend tests passing in Python 3.12;
- 22 frontend interaction tests passing;
- zero ESLint warnings or errors;
- successful TypeScript static checking;
- successful Next.js 16 production compilation and static generation;
- successful `pip check` and production Google SDK import checks;
- zero known Python and npm production dependency vulnerabilities at audit time;
- valid Firebase/Firestore JSON and Cloud Build/GitHub Actions YAML;
- clean whitespace validation and a 1.17 MB source repository, well below the contest limit;
- a real-browser live-Gemini golden flow proving report intake, bounded related-report reasoning, controller confirmation, the 530 m W3 fallback, approval-gated creation of four tasks and three translations, W3 closure, explicit no-route state, `UNSAFE` reassessment, `NO_VERIFIED_ROUTE` rejection, exactly one valid repair, and revision approval;
- browser regression checks proving the server identity contract and duplicate-approval UI guard;
- 1280 px, 768 px, and 390 px layouts with document width equal to viewport width and no horizontal overflow;
- local development CSP compatibility verified after correcting a development-only React runtime block; the production CSP remains strict;
- final frontend headers including CSP, deny-frame, no-sniff, no-referrer, permissions policy, opener policy, and no framework disclosure.

The container definition could not be locally built because Docker is not installed in the evaluation workspace. CI and Cloud Build definitions perform the production dependency install/build path when run in their configured environments. Live Firebase, Firestore, IAM, Secret Manager, Cloud Run, and hosted-domain verification still require the external project resources listed above. Live Gemini and the complete repaired containment path are verified.

## 22. Future extensions after launch

Future work should remain within the operational-intelligence thesis: live facility integrations, team/resource availability, stronger time-window incident retrieval, richer contradiction resolution, Firestore transactional counters, background reassessment workers, approved delivery connectors, and venue-specific canonical graph import tooling. Consumer features, unrelated fan experiences, microservice proliferation, vector databases, and multi-agent orchestration remain out of scope unless a demonstrated operational requirement changes the product thesis.
