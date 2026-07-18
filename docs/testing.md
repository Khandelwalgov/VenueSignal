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

Final 18 July 2026 result: 86 backend tests and 13 frontend tests passed; lint, TypeScript, production build, `pip check`, SDK imports, Python audit, npm production audit, whitespace, JSON/YAML parsing, secret patterns, and size enforcement passed. The full browser walkthrough spans both local processes; follow `docs/demo-script.md` after automated gates pass.
