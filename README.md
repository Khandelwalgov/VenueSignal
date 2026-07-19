# VenueSignal

**AI proposes. Deterministic logic verifies. Humans decide.**

VenueSignal is an AI-assisted incident-intelligence workspace for stadium operations. It turns fragmented facility, accessibility, and crowd reports into a verified operational picture, then keeps every consequential action under controller approval.

> **Synthetic-data disclosure:** Unity Stadium is fictional. It is not an official FIFA venue map. All geometry, crowd values, asset states, reports, routes, and telemetry are synthetic or evaluator-supplied.

## Problem

A lift outage, an obstructed accessible path, and a crowd build-up may arrive as separate, incomplete reports. A venue controller must establish what is actually true, understand the accessibility consequence, coordinate work, and avoid publishing unsafe guidance. VenueSignal keeps uncertain evidence distinct from verified facts and calculates route truth from a validated stadium graph—not from an AI response.

## Golden scenario

Three reports describe a stuck lift near Section 214, a blocked upper-west accessible path, and crowding near the west stairs. Gemini structures them as unverified evidence; the controller confirms the incident; deterministic routing verifies Corridor W3 as the fallback. A constrained response becomes tasks and multilingual drafts only after approval. When W3 closes, the old plan becomes unsafe, positive route guidance is withheld, and a repaired or deterministic containment plan returns for human approval.

## Live demo

Open `http://localhost:3000`, complete or skip the first-visit tour, then select **Start Guided Demo**. Six focused steps call the real report, incident, routing, planning, approval, operational-state, and reassessment APIs. No frontend result is faked. The same capabilities remain available for manual evaluation under **Reports and evaluator intake**, **Venue and system details**, Tasks, Communications, and Audit.

If Gemini returns an explicit quota error during the guided scenario, the backend alone switches that scenario to the deterministic, labelled `LOCAL_DEMO_PROVIDER`. The report provenance becomes `GUIDED_DEMO_QUOTA_FALLBACK`, the interface discloses the fallback, and all routing, validation, approval, task, communication, mutation, and reassessment APIs still run normally. Manual report intake remains fail-closed; API keys are never entered or stored in the browser.

## Architecture

The controller workspace is Next.js and TypeScript. FastAPI and Pydantic own the domain API. The immutable Unity Stadium topology lives in `data/venues/unity-stadium.json`; versioned operational overlays use memory, SQLite, or Firestore repositories. Firebase verifies identity and roles, while Gemini is an optional structured-output provider. The SVG map presents results but never determines route truth.

## AI vs deterministic responsibilities

| Responsibility | Owner |
| --- | --- |
| Structure untrusted reports, suggest relationships, propose and explain plans | Gemini or the labelled local demo provider |
| Validate identifiers, topology, routes, facility dependencies, accessibility constraints, plan actions, and context version | Deterministic application code |
| Confirm evidence, approve or reject plans, review communications, and close incidents | Authenticated venue controller |

The primary persona is a Venue Operations Controller. The product is deliberately not consumer navigation, autonomous emergency response, a generic chatbot, or a real-venue digital twin.

## Implemented now

- Synthetic three-level venue: 40 nodes, 47 edges, 12 assets, one connected component, no isolated nodes
- Eager startup validation with structured integrity, membership, topology, transition, reachability, accessibility, and scenario-readiness checks
- Interactive stadium map with mirrored controls, filters, validation statistics, facility details, and textual accessibility status
- Immutable canonical graph plus versioned operational overlays backed by memory, SQLite, or Firestore adapters
- Deterministic constrained routing with step-free, staff, distance, crowd, asset dependency, rest-point, and noise rules
- Manual report entry and bounded CSV/JSON import API with row errors and formula-like text defence
- Advisory local provider plus an official Gemini structured-output adapter with retries and fail-closed errors
- Quota-only guided-demo fallback with explicit local-provider/provenance labels; manual reports still fail closed
- Human-controlled report linking and verified asset-state application
- Deterministic impact analysis and plan validation against allowed actions, teams, identifiers, and context version
- Approval-gated tasks and English, Spanish, and French communication drafts
- Reassessment that preserves the old approved plan, marks it unsafe, and proposes a reviewable containment revision
- Pre-review deterministic validation, exactly one Gemini repair attempt, audited invalid proposals, and deterministic no-route containment fallback
- Explicit plan provenance (`GEMINI`, `GEMINI_REPAIRED`, `DETERMINISTIC_CONTAINMENT`, or local deterministic) and automatic supersession of route drafts when no route remains
- Firebase server token verification, controller/viewer authorization, rate limiting, request IDs, security headers, and production configuration validation
- Deterministic task, communication, incident-resolution, import-idempotency, and automatic reassessment lifecycles
- Controller task, communication, import, identity, and audit UI

The local provider is deliberately deterministic and clearly labelled `LOCAL_DEMO_PROVIDER`. Live Gemini extraction, matching, plan generation, reassessment, one-shot repair, and approval were verified with the configured key on 18 July 2026. Firebase email/password sign-in was also verified against project `venuesignal`; server-side claims and Firestore still require local ADC before their live acceptance can run. See the comprehensive [PRD](PRD.md).

## Safeguards

AI may structure untrusted reports and propose explanations. Deterministic code owns identifiers, routes, statuses, dependencies, state changes, allowed actions, plan validation, task creation, and audit records. Claims remain visibly unverified. Plans never auto-approve. “No verified safe step-free route currently exists” is a supported result.

See [architecture](docs/architecture.md), [AI usage](docs/ai-usage.md), [security](docs/security.md), [live deployment](docs/live-deployment.md), and [decisions](docs/decisions.md).

## Local setup

Requirements: Python 3.12 and Node.js 20+.

```bash
cp .env.example .env
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --app-dir apps/api --reload --port 8000 --env-file .env
```

In another terminal:

```bash
cd apps/web
cp .env.example .env.local
npm ci
npm run dev
```

Open `http://localhost:3000`. API documentation is at `http://localhost:8000/docs`; health and readiness are `/health` and `/ready`.

The root `requirements.txt` installs the development/test dependencies and the Google-backed adapters needed for a complete local validation. Use `PERSISTENCE_BACKEND=sqlite` for durable local state. Configure `AUTH_MODE=firebase`, `PERSISTENCE_BACKEND=firestore`, and `AI_PROVIDER=gemini` when exercising the corresponding production adapters.

## Golden demo

Use **Start Guided Demo** on the Operations screen. Analyse the three reports, confirm the relationship, review deterministic impact, approve the validated response, and continue the scenario. VenueSignal closes Corridor W3 through the real operational-state API, revalidates the approved plan, withholds unsafe route guidance, and presents a containment revision for a second approval. Full narration: [demo script](docs/demo-script.md).

Evaluator data uses the same API as demo data: manual reports call `POST /api/workflow/reports`; CSV/JSON files use `POST /api/workflow/reports/import?commit=false` for preview and `commit=true` after validation. Uploads are limited to 200 KB and 50 rows.

## Quality gates

```bash
cd apps/api && python -m pytest -q
cd apps/web && npm test -- --run && npm run lint && npm run typecheck && npm run build
python scripts/check_repo_size.py
```

See [testing](docs/testing.md), [accessibility](docs/accessibility.md), and the [implementation log](docs/implementation-log.md).

## Deployment readiness

The backend includes a Cloud Run-compatible Dockerfile and configurable restricted CORS. From the repository root, build with `docker build -f apps/api/Dockerfile -t venuesignal-api .`; replace the Cloud Build `_WEB_ORIGIN` substitution with the deployed frontend origin. The frontend can be deployed to Vercel or Firebase Hosting with `NEXT_PUBLIC_API_BASE_URL=https://api.example/api`.

Production deployment requires custom role claims, deployed secrets, a final frontend origin, and operational/security/privacy review. Adapter code, emulator configuration, Cloud Build, non-root container, and environment templates are included. Follow the project-specific [live deployment runbook](docs/live-deployment.md), then review [assumptions and limitations](docs/assumptions-and-limitations.md) and the [submission checklist](docs/submission-checklist.md).

AI development tools were used to audit, implement, and test the repository. Generated changes remain subject to the same deterministic validators and automated quality gates as hand-written changes.
