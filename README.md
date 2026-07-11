# PromptWars Virtual Challenge 04 - VenueSignal

**VenueSignal**
*AI-assisted incident fusion and accessibility-aware response planning for stadium operations*

## Summary
VenueSignal is an operational intelligence tool designed for a Venue Operations Controller. It receives fragmented operational reports, fuses them into coherent incidents, and calculates their facility and accessibility impacts using deterministic graph logic. It proposes response plans (requiring human approval), issues operational tasks, and reassesses plans when new conditions arise.

- **Primary Persona**: Venue Operations Controller
- **Primary Vertical**: Operational Intelligence
- **Supporting Vertical**: Real-time Decision Support

**Synthetic Venue Disclosure:**
Unity Stadium is a synthetic venue created for demonstrating operational incident reasoning, accessibility-impact analysis, and constrained route recovery. It is not an official FIFA venue map. All crowd telemetry, asset status, and operational events are synthetic or evaluator-supplied.

## Architecture Overview
The current architecture is a lightweight monorepo containing:
- `apps/web`: Next.js frontend, providing an interactive SVG-based operations map and textual summaries.
- `apps/api`: FastAPI backend in Python, providing the deterministic graph logic, validation, and domain entities.
- `data/venues`: Canonical JSON definitions of venues, particularly Unity Stadium.

## Current Implemented Phase
Phase 0 (Repository & Engineering Foundation) and Phase 1 (Domain Model & API Foundation).

## Directory Structure
```
/
  apps/
    web/       # Next.js Frontend
    api/       # FastAPI Backend
  data/
    venues/    # Canonical JSON venue data
  docs/        # Project documentation
  scripts/     # Utility scripts (e.g., repo size check)
  examples/    # Future examples and synthetic payloads
```

## Prerequisites
- Node.js (v20+)
- Python (3.11+)

## Local Setup & Run Commands

**1. Clone the repository**
(This repository is self-contained)

**2. Setup API**
```bash
cd apps/api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
fastapi dev app/main.py
```

**3. Setup Web**
```bash
cd apps/web
npm ci
npm run dev
```

**4. Testing**
Backend: `cd apps/api && pytest`
Frontend: `cd apps/web && npm run lint && npx tsc --noEmit && npm run build`

**5. Repository Size Check**
```bash
python scripts/check_repo_size.py
```

## Non-goals & Constraints
- This is NOT a World Cup fan super-app, a consumer navigation platform, or a digital twin of a real venue.
- The project is constrained to a single branch and < 10MB tracked size limit.
- AI is not used for routing, and it cannot execute actions without human validation.

## Future Phases
- Firestore integration for operational state management.
- Gemini integration for reasoning over incidents, report extraction, and plan generation.
- Full end-to-end incident fusion workflow.
