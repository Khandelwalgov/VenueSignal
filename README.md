# VenueSignal

AI-assisted incident intelligence and accessibility-aware response planning for the PromptWars Virtual Challenge 04 — Smart Stadiums & Tournament Operations.

VenueSignal helps a venue operations controller turn fragmented facility reports into a human-approved operational response. Before VenueSignal, a lift report, an access-obstruction report, and a crowd report remain disconnected. After controller verification, VenueSignal applies the confirmed state to a deterministic venue graph, validates the accessibility impact, proposes a constrained plan, creates work only after approval, and reassesses the approved plan when conditions change.

> **Synthetic-data disclosure:** Unity Stadium is fictional. It is not an official FIFA venue map. All geometry, crowd values, asset states, reports, routes, and telemetry are synthetic or evaluator-supplied.

## Product focus

- Primary persona: Venue Operations Controller
- Primary vertical: Operational Intelligence
- Supporting vertical: Real-time Decision Support
- Deep speciality: facility and access disruption with accessibility and crowd-flow consequences
- Non-goals: consumer navigation, autonomous emergency response, a generic chatbot, or a real-venue digital twin

The working loop is: report → advisory extraction → human report linking and facility verification → deterministic impact analysis → constrained plan proposal → human approval → tasks and multilingual drafts → context change → deterministic reassessment → human approval of the revision.

## Implemented now

- Synthetic three-level venue: 40 nodes, 47 edges, 12 assets, one connected component, no isolated nodes
- Eager startup validation with structured integrity, membership, topology, transition, reachability, accessibility, and scenario-readiness checks
- Interactive stadium map with mirrored controls, filters, validation statistics, facility details, and textual accessibility status
- Immutable canonical graph plus thread-safe, versioned, in-memory operational overlays and audit events
- Deterministic constrained routing with step-free, staff, distance, crowd, asset dependency, rest-point, and noise rules
- Manual report entry and bounded CSV/JSON import API with row errors and formula-like text defence
- Advisory local AI provider for structured extraction, plan proposals, and reassessment explanations
- Human-controlled report linking and verified asset-state application
- Deterministic impact analysis and plan validation against allowed actions, teams, identifiers, and context version
- Approval-gated tasks and English, Spanish, and French communication drafts
- Reassessment that preserves the old approved plan, marks it unsafe, and proposes a reviewable containment revision

The local provider is deliberately deterministic and clearly labelled `LOCAL_DEMO_PROVIDER`. A credential-gated Gemini boundary exists, but there is no claimed live Gemini integration. Firebase Authentication and Firestore are not implemented.

## Architecture and safeguards

`apps/web` is a Next.js/TypeScript view and controller workspace. `apps/api` is a FastAPI/Pydantic domain API. `data/venues/unity-stadium.json` is canonical topology; an in-memory overlay holds mutable state. The SVG is presentation only and never determines route truth.

AI may structure untrusted reports and propose explanations. Deterministic code owns identifiers, routes, statuses, dependencies, state changes, allowed actions, plan validation, task creation, and audit records. Claims remain visibly unverified. Plans never auto-approve. “No verified safe step-free route currently exists” is a supported result.

See [architecture](docs/architecture.md), [AI usage](docs/ai-usage.md), [security](docs/security.md), and [decisions](docs/decisions.md).

## Local setup

Requirements: Python 3.11+ and Node.js 20+.

```bash
cp .env.example .env
cd apps/api
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd apps/web
npm ci
npm run dev
```

Open `http://localhost:3000`. API documentation is at `http://localhost:8000/docs`; health and readiness are `/health` and `/ready`.

## Golden demo

Reset the route state, then use **Load 3-report scenario** in the workflow. Link the first two reports, confirm the incident, review and approve the plan, then close Corridor W3 and reassess. The fallback disappears, the approved plan becomes unsafe, and a containment revision requires approval. Full narration: [demo script](docs/demo-script.md).

Evaluator data uses the same API as demo data: manual reports call `POST /api/workflow/reports`; CSV/JSON files use `POST /api/workflow/reports/import?commit=false` for preview and `commit=true` after validation. Uploads are limited to 200 KB and 50 rows.

## Quality gates

```bash
cd apps/api && python -m pytest -q
cd apps/web && npm test -- --run && npm run lint && npm run typecheck && npm run build
python scripts/check_repo_size.py
```

See [testing](docs/testing.md), [accessibility](docs/accessibility.md), and the [implementation log](docs/implementation-log.md).

## Deployment readiness

The backend includes a Cloud Run-compatible Dockerfile and configurable restricted CORS. From the repository root, build with `docker build -f apps/api/Dockerfile -t venuesignal-api .`; supply `PORT` and `CORS_ALLOWED_ORIGINS`. The frontend can be deployed to Vercel or Firebase Hosting with `NEXT_PUBLIC_API_BASE_URL=https://api.example/api`.

Production use is blocked on real authentication/authorization, durable persistence, rate limiting, an actual Gemini adapter with retries/timeouts, and operational review. See [assumptions and limitations](docs/assumptions-and-limitations.md) and [submission checklist](docs/submission-checklist.md).

AI development tools were used to audit, implement, and test the repository. Generated changes remain subject to the same deterministic validators and automated quality gates as hand-written changes.
