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

## 2026-07-18 — Stages F–G and production hardening

**Objective:** Implement persistence, real provider/authentication adapters, full lifecycle hardening, expanded controller UI, deployment configuration, and complete product requirements.

**Key changes**

- Added validated environment configuration that fails unsafe production startup.
- Added memory, SQLite, and Firestore repositories for operational and workflow state.
- Added official Gemini structured-output integration with authoritative context, bounded retries, safe error classification, and metadata-only logging.
- Added Firebase Admin token verification, server-derived controller/viewer roles, optional Firebase web sign-in, and protected every API route.
- Added request/body limits, rate limiting, trace IDs, browser-security headers, production OpenAPI disablement, explicit CORS, deny-all Firestore client rules, and a non-root container.
- Added idempotent reports/imports, match evidence, deterministic task/communication/resolution state machines, completion evidence, blocked reasons, and automatic plan reassessment.
- Expanded the workspace with top-level operational areas, verified identity, CSV/JSON preview, persistent queues, lifecycle controls, translations, and audit timeline.
- Added Cloud Build, Firestore emulator configuration, production environment template, HTTP seed tooling, dependency audits, and `PRD.md`.

**Tests added:** security/auth roles, rate/body limits, security headers, SQLite recreation, duplicate fingerprints, Gemini structured/error contracts, task dependencies/evidence, communication transitions, resolution, automatic reassessment, identity, upload preview, queues, and audit UI.

**Final verification**

- Backend: 71 tests passed; `pip check` passed; production SDK imports passed.
- Frontend: 12 tests passed; ESLint passed with zero warnings; TypeScript passed; Next.js production build passed.
- Dependency security: Python and npm production audits reported zero known vulnerabilities.
- Configuration: Firebase/Firestore JSON and Cloud Build/GitHub Actions YAML parsed successfully.
- Browser: full golden flow passed through containment revision approval; verified identity displayed correctly; duplicate plan approval disabled; no browser console warnings/errors.
- Responsive: no horizontal document overflow at 1280 px, 768 px, or 390 px.
- Security headers: final frontend response included CSP, no-sniff, deny-frame, no-referrer, permissions, and opener policies without `X-Powered-By`.
- Repository: whitespace check passed; source size 737.56 KB, including untracked-but-not-ignored release files.

**External verification at that checkpoint:** live Gemini, Firebase, Firestore, Secret Manager, Cloud Run, and hosted frontend credentials; organizational security/privacy/operational acceptance. Docker was unavailable locally, so the container definition was not built in this workspace.

## 2026-07-18 — User-configured live Gemini validation

**Configuration:** The ignored root `.env` selected development auth, memory persistence, and `AI_PROVIDER=gemini` with a present key and `gemini-2.5-flash`. An ignored `apps/web/.env.local` was added for the public local API/auth settings so Next.js consumed the intended values. No secret value was printed, logged, or added to source control.

**Passed**

- Readiness reported a valid graph, memory persistence, disabled local auth, and provider `GEMINI`.
- A direct synthetic report returned HTTP 200, provider `GEMINI`, 90% confidence, and authoritative candidate `A_LIFT_2`.
- The browser golden intake produced three structured reports, an 85% human-review match suggestion for the related lift report, and a 10% `CREATE_NEW` suggestion for the crowd report.
- Controller confirmation produced the deterministic 530 m W3 fallback.
- Gemini produced a schema-valid, domain-valid initial plan with four actions; approval created four tasks and three multilingual drafts.
- Closing W3 produced the deterministic no-route state and a Gemini reassessment explanation marked `UNSAFE`.
- A task advanced from `CREATED` to `ASSIGNED`; the English communication advanced from `DRAFT` to `UNDER_REVIEW`.
- Browser diagnostics contained no warnings or errors.
- Existing gates remained green: 71 backend tests, 12 frontend tests, ESLint, TypeScript, production build, dependency consistency, whitespace, and size enforcement.

**Failed safely**

- Gemini's proposed containment revision included `STAFF_VERIFIED_ROUTE` after deterministic routing had established that no verified route existed.
- Approval returned HTTP 409: `A route action cannot be approved when no verified route exists`.
- The current approved plan remained preserved and `UNSAFE`; no invalid revision tasks were created.

**Required correction:** prevalidate generated revisions before presenting them as approvable, then perform a bounded repair/regeneration attempt or construct a deterministic containment-only fallback that excludes route staffing until route verification succeeds.

**External verification still required:** Firebase Authentication/custom claims, Firestore/ADC, Secret Manager, Cloud Run, hosted frontend domains, and organizational acceptance.

## 2026-07-18 — Final pre-submission hardening

**Safety recovery:** Generated plans now pass deterministic validation before review. Invalid Gemini proposals and structured errors are retained in recovery records, exactly one authoritative repair call is allowed, repaired proposals are revalidated, and timeout/quota/malformed/second-invalid results fall back to deterministic containment. Sources are explicit: `GEMINI`, `GEMINI_REPAIRED`, `DETERMINISTIC_CONTAINMENT`, and `LOCAL_DETERMINISTIC`.

**No-route enforcement:** Containment excludes `STAFF_VERIFIED_ROUTE`, positive guidance, and communication generation. Earlier route drafts become `SUPERSEDED` when route truth changes. Approval remains mandatory and is idempotent at both service and UI levels.

**Hostile hardening:** Canonical filtering now removes model-invented extraction IDs; instruction detection is deterministic for manual and CSV inputs; recent-report matching is bounded without a fragile category/ID prefilter; production explicitly rejects demo reset; the request limit checks actual streamed bytes as well as declared length; rejection responses receive security headers.

**UX/accessibility:** The no-route state, context version, plan validity, provider/source, repaired/containment distinction, and communication suppression are explicit. Workflow sections use semantic headings and status announcements; duplicate clicks are synchronously guarded; the skip link targets a focusable main region. Responsive checks found no horizontal overflow at 390 px, 768 px, or a 200%-reflow-equivalent 640 CSS px. Reduced motion, mirrored map controls, text route descriptions, and non-colour status symbols remain present.

**Live Gemini acceptance:** Against `gemini-2.5-flash`, readiness and all report calls returned 200; three extractions and bounded match assessments were schema-valid. Controller confirmation returned 200 and a domain-valid initial Gemini plan at context v2; approval returned 200, four tasks, and three language drafts. W3 closure/reassessment returned 200 and no verified route at v3. The first revision failed with `NO_VERIFIED_ROUTE`; one repair produced a schema-valid and domain-valid `GEMINI_REPAIRED` plan with four containment actions. Fallback was not required. Revision approval returned 200; a duplicate UI activation produced one execution request, eight total tasks (four old plus four containment), zero new communications, and three older drafts in `SUPERSEDED`.

**Final gates:** 86 backend tests, 13 frontend tests, ESLint, TypeScript, Next production build, `pip check`, production SDK imports, Python and npm vulnerability audits, JSON/YAML parsing, whitespace, tracked-secret patterns, ignored environment-file checks, and repository-size enforcement all passed. Final source size was 1.17 MB. Docker remained unavailable, so the container was inspected but not locally built.

**Final fallback rerun:** A later fully hardened live rerun reached Gemini quota during plan generation and reassessment. Both calls were safely replaced by approval-gated `DETERMINISTIC_CONTAINMENT`. Two approvals produced eight tasks and zero communications; a repeated revision-approval request left both counts unchanged. This separately proves the quota branch after the earlier successful `GEMINI_REPAIRED` browser run.

**External verification still required:** live Firebase identities/custom claims, Firestore/ADC persistence, Secret Manager/IAM, Cloud Run/container deployment, hosted origins, and organizational privacy/security/assistive-technology acceptance.

## 2026-07-18 — Live Firebase connection preparation

**Connected configuration:** The ignored frontend environment now targets Firebase project `venuesignal` with email/password authentication and the public web-app configuration. The ignored backend environment selects Firebase authentication, Firestore persistence, project `venuesignal`, and the already-working Gemini provider. Offline `disabled`/`memory` defaults remain documented in `.env.example`.

**Live result:** An in-memory Firebase Identity Toolkit login for `admin@venuesignal.com` succeeded and returned an ID token. Neither the password nor token was printed or persisted. The check was authentication-only and is not counted as server authorization.

**Infrastructure tooling:** Added role assignment, isolated Firestore write/read/delete, token-based `/auth/me`, and password-to-token local smoke utilities. Added the project-specific live-deployment runbook, a dedicated Cloud Run service identity in Cloud Build, explicit production Gemini model configuration, public Vercel values, ADC/IAM/Secret Manager commands, restart persistence steps, and the live golden-flow checklist. Private Firebase Admin JSON filenames are ignored; the discovered untracked key file was not read or used and was removed from the repository directory.

**Validation:** 86 backend tests and 13 frontend tests passed. ESLint, TypeScript, the Next production build with Firebase configuration, `pip check`, Python and npm vulnerability audits, Firebase/Cloud Build parsing, deny-all Firestore-rule inspection, whitespace, tracked-secret patterns, ignored-secret checks, one-branch inspection, and the 1.25 MB source-size gate passed.

**Credential blocker:** Application Default Credentials are absent, and `gcloud` and `firebase` are not installed. Therefore the CONTROLLER claim, server-verified `/api/auth/me`, live Firestore smoke/persistence, rules deployment, real viewer authorization, live-infrastructure golden flow, Secret Manager/IAM inspection, Cloud Run, and Vercel-to-API browser acceptance remain intentionally unexecuted. The exact non-key ADC commands are in `docs/live-deployment.md`; no service-account JSON key is required or permitted.
## 19 July 2026 — Final frontend refinement and demo continuity

- Reduced the first-visit tutorial to six keyboard-accessible steps with persistent completion and direct Guided Demo / Explore Dashboard exits.
- Reworked the first screen around the product thesis, primary Guided Demo action, compact operational summary, stadium map, and current situation.
- Tightened the six guided stages with explicit unverified-evidence, AI-insight, deterministic-validation, and human-approval boundaries.
- Strengthened the W3-closure screen with the unsafe previous plan, withheld route guidance, safe containment, and second approval gate.
- Added compact language selection for simulated communication drafts and moved auth/provider internals under progressive disclosure.
- Added a quota-only server-side guided-demo fallback. It is restricted to `GUIDED_DEMO` reports, persists `GUIDED_DEMO_QUOTA_FALLBACK` provenance, uses the labelled deterministic local provider, and never changes manual report fail-closed behavior.
- Browser validation completed the real six-step API flow in isolated local-controller mode and checked 390, 640, 768, and 1280 px layouts. No console errors or page-level horizontal overflow were found.
- Final gates: 91 backend tests and 17 frontend interaction tests passed; ESLint, TypeScript, and the Firebase-configured Next.js production build passed. The remaining warning is Starlette's third-party `TestClient`/`httpx` deprecation notice.

## 19 July 2026 — Judge demo access

**Objective:** Let a PromptWars evaluator understand the product, use the dedicated Firebase account, and reach the Guided Demo without exposing credentials or weakening authorization.

**Implementation:** Replaced the compact signed-out header form with a dedicated Demo Controller access screen. It pre-fills only `admin@venuesignal.com`, preserves password-manager semantics, keeps the password empty and masked, supports native Enter submission, announces `Signing in…`, and normalizes provider errors into concise evaluator copy. The tutorial and internal navigation remain hidden until authentication; after server verification, identity collapses to `Demo Controller` and `CONTROLLER`, with auth mode retained only under system details. The operational empty state now also offers the Guided Demo directly.

**Security:** No password endpoint, public credential flag, client secret, signup, anonymous access, or role selector was added. Firebase email/password sign-in, bearer-token verification, and the server-authoritative `CONTROLLER` claim remain unchanged. Current tracked files, build output, and available Git history contain neither the previously shared demo password nor the pasted OpenAI secret prefix.

**Validation:** 22 frontend tests, ESLint, TypeScript, the Firebase-configured production build, 11 backend security tests, scoped whitespace validation, and the 1.41 MB repository-size gate passed. Browser checks at 390 px, 768 px, and the 200%-zoom equivalent found no page overflow or console error. Live incognito sign-in remains a submission action because the compromised development password must first be rotated.
