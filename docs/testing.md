# Testing

The release gate is backend tests, frontend interaction tests, lint, static typing, production build, and tracked-size enforcement.

```bash
cd apps/api && python -m pytest -q
cd apps/web && npm test -- --run
cd apps/web && npm run lint && npm run typecheck && npm run build
python scripts/check_repo_size.py
```

Backend coverage includes validator mutations, startup failures, multi-level assets, constrained routes, operational versioning, imports, untrusted instructions, invented plan identifiers, stale plans, approval gating, reassessment, and the golden API loop. Frontend tests cover map controls, disclosure, errors/loading, route containment, keyboard use, report extraction labelling, and approval-gated task creation.

The full browser walkthrough is manual because it spans two local processes. Follow `docs/demo-script.md` after automated gates pass.
