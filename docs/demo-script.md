# Golden demo script

1. Start the API and web app, open the dashboard, and point out the synthetic badge, valid graph, one component, zero isolated nodes, and normal 215 m step-free route.
2. In the incident workflow select **Load 3-report scenario**. Explain that all extracted claims remain unverified and confidence describes extraction, not truth.
3. Keep the first two reports selected. Choose **Confirm incident and analyse impact**. This is the human verification boundary: Lift L2 becomes unavailable, context advances, and deterministic routing verifies the longer Corridor W3 fallback.
4. Review the proposed action locations and teams. Choose **Approve plan and create work**. Only now do tasks and three language drafts appear.
5. Choose **Close W3 and reassess**. Context advances again; deterministic routing returns **No verified safe step-free route currently exists**. The approved plan is preserved and marked unsafe, and all earlier route drafts become `SUPERSEDED`.
6. Point out the revision source. If Gemini's first revision was invalid, VenueSignal withholds it, records exact validation errors, performs exactly one repair attempt, validates again, and displays either `GEMINI_REPAIRED` or `DETERMINISTIC_CONTAINMENT`. Neither state contains `STAFF_VERIFIED_ROUTE`.
7. Read the containment actions and the statement that no route communication will be generated. Choose **Approve containment revision** to demonstrate the second human decision boundary. Only containment tasks are added; no new communication draft appears.
8. Reset canonical base state before repeating the scenario.

The walkthrough takes about three minutes and uses the same API paths as evaluator-entered reports.
