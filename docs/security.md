# Security

## Implemented controls

- `Settings` rejects wildcard CORS, invalid backends/providers, disabled production authentication, non-Firestore production persistence, production demo reset, loopback production origins, and missing provider/project configuration.
- All `/api` routes require identity. Mutation routes require server-verified `CONTROLLER`; `VIEWER` is read-only.
- Firebase ID tokens are verified with the Admin SDK and revocation checking. Roles come from trusted custom claims, not frontend state.
- Local disabled and deterministic test auth modes are explicitly separated from production.
- Configurable IP-window rate limiting returns `429` with `Retry-After`.
- Request bodies are limited by both declared `Content-Length` and actual streamed bytes; uploads, import rows, field lengths, percentages, and enumerations are also bounded.
- CORS permits explicit origins, GET/POST/PATCH, and only required headers.
- API responses receive request ID, no-sniff, deny-frame, no-referrer, permissions, CSP, and no-store headers. The web app adds a deployment-aware CSP, opener policy, permissions policy, and removes framework disclosure. HSTS is added by the API in production.
- Production OpenAPI UI is disabled and the container runs as a non-root user.
- Direct Firestore client access is denied; server Admin SDK adapters are authoritative.
- Reports are untrusted evidence. Instruction-like text is flagged and never changes system policy.
- Import fingerprints and explicit idempotency keys prevent duplicate corroboration.
- Gemini credentials stay server-side; prompts and report contents are not written to call metadata logs.
- Initial provider failures return a sanitized `503` and commit no report or incident state; repair failures are contained by the deterministic fallback.
- Model plans are validated before they become actionable. Stale context, self-approval, empty plans, invalid dependencies, invented locations, unknown teams, disallowed actions, unsafe route actions, and invalid no-route validity are structured errors.
- An invalid plan receives exactly one Gemini repair attempt. The original/repaired attempts and error codes are audited. A second invalid result, timeout, quota failure, or malformed output produces deterministic containment; no recursion occurs.
- No-route reassessment supersedes existing route drafts and cancels the outstanding task tied to the invalidated route-staffing action. Containment approval creates no route communication, and repeated approval is idempotent.
- Task dependencies, completion evidence, blocked reasons, communication review, resolution, and publication simulation are deterministic.
- Consequential actions record actor, context, timestamp, and summary.

## Production obligations

Deployers must create Firebase users and custom claims, configure Secret Manager and ADC, restrict CORS to the real frontend, set conservative rate limits, enable Cloud logging/alerting, define data retention and deletion, review service-account IAM, test backup/restore, and complete penetration and privacy reviews. Cloud Run is publicly reachable at the transport layer so browser Firebase tokens can reach the API; application middleware remains the authorization boundary.
