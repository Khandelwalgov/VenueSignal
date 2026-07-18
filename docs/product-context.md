# Product Context

## Challenge Interpretation
The PromptWars Virtual Challenge 04 requires a GenAI-powered solution to optimize stadium operations and enhance the FIFA World Cup 2026 experience. We are building VenueSignal, an operational intelligence product that avoids becoming an unfocused super-app.

## User Persona
Venue Operations Controller

## Product Problem
Venue controllers deal with fragmented operational reports and changing venue-state data. It's difficult to calculate the cascading facility and accessibility impacts when disruptions occur (e.g. lift outage, corridor closure).

## Product Thesis
VenueSignal receives fragmented operational reports, fuses related information into a coherent incident, calculates facility and accessibility impact using deterministic graph logic, proposes an explainable response plan, requires human approval, creates operational tasks and communication drafts, and reassesses the plan when new conditions arise.

## Scope & Non-Goals
VenueSignal is strictly focused on facility and access disruptions that create accessibility, crowd-flow, or operational consequences. It is **not**:
- A World Cup fan super-app
- A generic chatbot
- A full indoor consumer navigation platform
- A digital twin of a real FIFA venue
- An autonomous emergency-response system

## Input-to-Action Loop
INPUT → CONTEXT → REASONING → EXPLANATION → HUMAN DECISION → ACTION → UPDATED STATE → REASSESSMENT

## Basic Breadth vs Deep Speciality
**Basic Support**: Broad support for facility outages, access obstructions, gate closures, crowd congestion.
**Deep Speciality**: Detailed analysis of lifts, escalators, gates, turnstiles, accessible entrances, restrooms, and temporary route obstructions using incident fusion, contradiction detection, and accessibility-impact analysis.

## Accessibility Role
Accessibility is a core impact layer, not an afterthought. The deterministic engine verifies step-free routes, and a safe valid outcome could be "No verified step-free route currently exists", prompting operational containment rather than false guidance.

## AI vs Deterministic Responsibilities
- **AI providers (local and Gemini adapters)**: Used for advisory report extraction, clarification questions, situation synthesis, plan proposals, and reassessment explanations. AI is NEVER the source of route truth or execution.
- **Deterministic Engine**: Controls graph topology, route existence, status transitions, accessibility constraints, task creation, and human-approval logic.

## Current delivery status

The complete golden loop is implemented with selectable memory, SQLite, and Firestore repositories; deterministic local and official Gemini providers; and local, test, and Firebase authentication modes. Gemini has completed a live credential-backed acceptance run, including one-shot invalid-plan repair. Firebase and Firestore remain contract-tested/configuration-reviewed without a live-project claim. Real communication delivery remains deliberately out of scope: publication is visibly simulated and human reviewed.
