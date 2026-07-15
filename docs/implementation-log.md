# VenueSignal Implementation Log

This log records concise engineering decisions and verifiable results. It does not contain private reasoning.

## 2026-07-15 — Baseline audit

**Stage:** Pre-Stage A

**Objective:** Reproduce the known audit findings before modifying the implementation.

**Repository state**

- Branch: `main` (the only local branch)
- Tracked files: 41
- Tracked size: 323.52 KB
- Existing working-tree change: `staffOnly` added to the frontend `Edge` type; preserved
- Package managers: npm (`apps/web/package-lock.json`) and pip (`apps/api/requirements.txt`)

**Commands and results**

- `venv/bin/python -m pytest -q`: 10 passed, 1 dependency deprecation warning
- `venv/bin/pytest -q`: failed during collection with `ModuleNotFoundError: app`
- `npm run lint`: passed
- `npx tsc --noEmit`: passed
- `npm run build`: passed
- `python scripts/check_repo_size.py`: passed at 323.52 KB

**Confirmed defects**

- Independent traversal from the West Accessible Entrance reached 27 of 40 nodes.
- Thirteen nodes were unreachable and eleven were completely isolated.
- Stair S2, Stair S3, and Escalator E2 had served nodes on multiple levels without transition edges.
- Medical points, waiting points, and the quiet assistance area were disconnected.
- Graph validation checked references and a few local invariants but did not perform reachability, membership, component, or transition-integrity analysis.
- Level responses filtered assets only by their declared home level; selecting Lift L2 on Level 2 could not resolve details.
- Canonical data loaded lazily and its path depended on the process working directory.
- `.env.example` omitted the `/api` prefix expected by the frontend client.
- The interface omitted zone selection, filters, validation status, statistics, and a derived accessibility summary.
- Documentation described planned incident and routing capabilities as if they were implemented.

**Next step:** Repair Unity Stadium connectivity and implement structured graph validation.

## 2026-07-15 — Stage A complete

**Objective:** Finish and harden the canonical Unity Stadium foundation.

**Key changes**

- Repaired all disconnected amenities and vertical transitions through intentional public paths.
- Added Scanner Bank N2 and Corridor W3 as real graph assets.
- Preserved the flagship state sequence: base Lift L2 route, longer Corridor W3 fallback after Lift L2 outage, and no verified step-free route when both are unavailable.
- Replaced string-only validation with structured issues containing code, severity, entity, and related identifiers.
- Added membership, value, topology, transition, component, reachability, step-free, and scenario-readiness validation.
- Moved canonical loading into FastAPI lifespan startup with a module-relative data path and injectable service.
- Fixed multi-level asset serialization and added asset relationship, zone, node, readiness, and accessibility-summary APIs.
- Upgraded the interface to a recognisable synthetic stadium workspace with zone geometry, distinct facility symbols, mirrored controls, filters, validation statistics, and graph-derived accessibility summaries.
- Added responsive layouts, non-colour status cues, visible focus, reduced-motion handling, loading and error states, and the full synthetic-data disclosure.
- Removed the runtime Google Font download so production builds are network-independent.

**Tests added**

- 26 additional backend tests, including validator mutations, startup failure cases, multi-level assets, and accessibility endpoints.
- 6 frontend interaction tests covering disclosure, validation, statistics, level/zone selection, Lift L2 regression, filtering, keyboard activation, loading, and network failure.

**Commands and exact results**

- `venv/bin/python -m pytest -q`: 36 passed, 1 third-party deprecation warning
- `venv/bin/pytest -q`: 36 passed, 1 third-party deprecation warning
- `npm run lint`: passed
- `npm run typecheck`: passed
- `npm test`: 6 passed
- `npm run build`: passed; static `/` and `/_not-found` routes generated
- `python scripts/check_repo_size.py`: passed at 443.30 KB
- Browser verification: level switching, structured Lift L2 selection on Level 2, map details, and a 768 px no-horizontal-overflow layout verified

**Graph result**

- 3 levels, 11 zones, 40 nodes, 47 edges, 12 assets
- 1 connected component, 0 isolated nodes
- 11 designated accessible destinations, all step-free reachable in base state
- 42 step-free edges, 10 vertical transitions, 6 accessibility-critical assets
- Validator result: zero errors and zero warnings

**Known limitation:** This checkpoint validates base-state reachability but does not yet expose mutable state or route recommendations; those belong to Stage B.

**Next step:** Implement immutable canonical definitions plus a mutable operational overlay and deterministic constrained routing.

## 2026-07-15 — Stage B complete

**Objective:** Add mutable operational state and deterministic constrained routing without mutating canonical topology.

**Key changes**

- Added a thread-safe in-memory operational overlay for asset/edge status, edge crowd, context version, timestamps, and event history.
- Every state mutation increments `contextVersion`; reset preserves audit history and also increments the version.
- Added weighted Dijkstra routing with step-free, staff-only, maximum walking distance, crowd threshold, rest-point, noise preference, edge status, and dependent-asset constraints.
- Added structured no-route results and explicit rejected-reason codes.
- Added state, event, mutation, reset, and route-query APIs with validated request/response schemas.
- Added real synthetic evaluator controls to the frontend. They call backend mutation APIs, rerun route validation, update effective facility status, and show context-versioned route state.
- Added a route overlay and an operational containment response when no verified step-free route exists.

**Golden route proof**

- Context v1: normal Lift L2 route verified, 215 m.
- Context v2 after Lift L2 outage: Corridor W3 fallback verified, 530 m.
- Context v3 after Corridor W3 outage: no verified safe step-free route.
- Context v4 after reset: normal Lift L2 route restored.

**Commands and exact results**

- `venv/bin/python -m pytest -q`: 44 passed, 1 third-party deprecation warning
- `npm run lint`: passed
- `npm run typecheck`: passed
- `npm test`: 7 passed
- `npm run build`: passed
- `python scripts/check_repo_size.py`: passed at 451.38 KB

**Known limitation:** Operational state is intentionally in memory; persistence is deferred until domain lifecycles are stable.

**Next step:** Add evaluator reports, incident lifecycle, isolated AI provider contracts, approval, tasks, communication drafts, and plan reassessment.

## 2026-07-15 — Stages C–E local core loop complete

**Objective:** Complete the credential-free golden incident workflow through reassessment.

**Key changes**

- Added bounded manual/CSV/JSON report intake, advisory structured extraction, unverified-claim labelling, injection-pattern detection, and related-report suggestions.
- Added incidents, verified facts, contradictions, deterministic impact analysis, response plans, tasks, multilingual communication drafts, audit records, and reassessment models.
- Isolated AI behind a provider protocol. The active local provider is deterministic and labelled; the Gemini boundary makes no fake network claim.
- Required a human to link reports and confirm the Lift L2 state before the operational overlay changes.
- Validated generated plans against action/team/location allow-lists and the current operational context before approval.
- Created tasks and communication drafts only after approval.
- Preserved the approved plan when Corridor W3 closes, marked it unsafe, generated a containment revision, and required a second approval.
- Added a four-step accessible UI using the same APIs as evaluator input.

**Tests added**

- Workflow service and API tests for extraction, linking, prompt injection, approval, tasks/drafts, stale context, invented IDs, reassessment, CSV/JSON imports, malformed input, and formula-like text.
- Frontend interaction test proving unverified extraction and approval-gated work creation.

**Verified results**

- Backend: 53 tests passed.
- Frontend: 8 tests passed; lint, TypeScript, and production build passed.
- Browser golden loop: three reports loaded; controller verification produced W3 fallback; approval produced 3 tasks and 3 drafts; W3 closure produced no route, `UNSAFE`, and a reviewable revision.
- Responsive browser check at 768 px: document width equalled viewport width (no horizontal overflow).

**Known limitations:** in-memory persistence, deterministic local provider, simplified incident shortlist, no authentication/rate limiting, and no real communication delivery. These are documented rather than presented as integrations.

## 2026-07-15 — Release-readiness pass

**Objective:** Align local commands, deployment scaffolding, and submission documentation with the implementation.

**Key changes**

- Added Cloud Run-compatible backend container configuration, environment-driven venue path, restricted CORS template, and explicit multipart dependency.
- Updated CI actions and aligned CI with `python -m pytest`, Vitest, lint, TypeScript, build, and repository-size commands.
- Rewrote the README and required product, architecture, testing, security, accessibility, AI, limitation, demo, and checklist documents to distinguish working features from credential-dependent work.
- Final tracked size: 570.29 KB; largest tracked file is the 276 KB frontend lockfile.
- Docker CLI was unavailable in the workspace, so the container definition was reviewed but not locally built.

**Remaining external blockers:** a Gemini credential/integration, Firebase project for Authentication and Firestore, and deployment accounts/URLs. The complete local core loop does not require them.
