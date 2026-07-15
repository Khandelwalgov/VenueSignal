# Security

## Implemented controls

- Restricted configurable CORS; only GET/POST and `Content-Type` are allowed.
- Pydantic request bounds and enumerations; authoritative identifiers are checked server-side.
- Reports are untrusted evidence. Instruction-like text is flagged and never changes system policy.
- Uploads accept only bounded CSV/JSON extensions and MIME types, max 200 KB/50 rows, with row validation and formula-like text rejection.
- The API key boundary is server-side; no credential appears in client code or logs.
- Consequential state changes, plan proposals, approvals, and reassessments produce audit records.
- Plans are rejected for stale context, invented locations, unknown teams, or disallowed actions.
- Safe error responses do not expose secrets.

## Required before production

Firebase token verification and server-derived CONTROLLER/VIEWER roles, per-user rate limiting, durable audit persistence, CSRF/threat review for the deployment shape, stricter file sniffing, observability redaction, and penetration testing. The local demo intentionally has no authentication and must not be exposed as a production control surface.
