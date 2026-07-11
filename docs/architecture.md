# Architecture

## Current Architecture
The current architecture establishes the foundation:
- **Frontend**: Next.js App Router (React, TypeScript), providing an accessible SVG-based map and details panel.
- **Backend**: FastAPI (Python, Pydantic), providing graph validation, domain models, and API endpoints to serve venue state.
- **Data**: Canonical JSON files defining the venue graphs.

## Future Architecture
- **Firestore**: Will store mutable operational state (asset status, edges status, incidents, plans) separate from the canonical venue definition.
- **Gemini**: Will integrate into the backend to provide reasoning, plan generation, and audience-specific communication.

## Frontend/Backend Boundaries
- **Backend** is the source of truth for the graph logic. The deterministic engine in FastAPI evaluates paths, accessible routes, and constraints.
- **Frontend** is purely a view layer. It maps data provided by the backend to SVG paths and zones but does not perform independent pathfinding.

## Domain-Layer Principles
- The visual map is presentation. The graph is operational truth.
- Never infer route truth from the SVG.
- The map and the graph share stable identifiers (e.g., node and edge IDs).
