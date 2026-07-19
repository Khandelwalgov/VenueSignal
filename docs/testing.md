# Testing

The release gate is backend tests, frontend interaction tests, lint, static typing, production build, and tracked-size enforcement.

```bash
cd apps/api && python -m pytest -q
cd apps/web && npm test -- --run
cd apps/web && npm run lint && npm run typecheck && npm run build
python scripts/check_repo_size.py
```

Backend coverage includes validator mutations, startup failures, multi-level assets, constrained routes, operational versioning, imports and idempotency, raw/CSV prompt injection, invented plan identifiers/teams/actions, stale plans, approval gating, task dependencies/evidence, communication transitions, resolution, automatic reassessment, SQLite recreation, Gemini schemas and error contracts, one-shot repair, timeout/quota/malformed repair fallback, containment approval, duplicate requests, authentication, authorization, rate limits, declared and actual body limits, security headers, and the golden API loop. Frontend tests cover map controls, disclosure, errors/loading, route containment, keyboard use, report extraction labelling, approval-gated task creation, repaired/fallback provenance, no-route communication suppression, duplicate-click protection, verified identity, navigation areas, upload preview, execution queues, and audit display.

Security gates also run `pip-audit -r requirements-production.txt`, `pip check`, production Google SDK imports, and `npm audit --omit=dev`. `requirements-base.txt` contains the API runtime, `requirements.txt` adds test-only packages, and `requirements-production.txt` adds only the credential-backed Google adapters; the container does not install pytest.

Final 19 July 2026 result: 93 backend tests and 22 frontend tests passed; lint, TypeScript, and the Firebase-configured production build passed. The in-app browser completed the six-step real-API evaluator flow in isolated local-controller mode and verified 390, 640, 768, and 1280 px layouts without page-level horizontal overflow. The signed-out Demo Controller screen was separately verified at 390 px, 768 px, and a 1280-at-200%-equivalent viewport: its form and primary action remained reachable, the email alone was prefilled, the password stayed empty and masked, and no console error appeared. Render production settings validate, the API resolves canonical venue data from the configured monorepo root, and tests cover cross-instance operational-state refresh plus the operator-only Firestore base reset. The guided-demo quota fallback remains covered end to end; manual report intake remains fail-closed. Earlier hardening also passed `pip check`, SDK imports, Python audit, npm production audit, whitespace, JSON/YAML parsing, secret patterns, and size enforcement. Follow `docs/demo-script.md` after automated gates pass.
