# Assumptions and limitations

- Unity Stadium and every scenario value are synthetic.
- State is process-local and disappears on restart; multiple API replicas would diverge.
- The local provider is deterministic keyword/rule logic, not Gemini.
- Incident matching is an explainable asset/zone shortlist; semantic Gemini matching is not implemented.
- Imports offer preview and commit but do not yet implement idempotency keys or duplicate suppression.
- The documented state enum exists, but the local golden path implements the proposal/approval/monitoring slice rather than every possible transition and task lifecycle.
- Communication is draft generation only; there is no real publication or delivery.
- Authentication, authorization, rate limiting, Firestore, production monitoring, and live venue integrations are absent.
- Routes are operational recommendations for a synthetic demo, not certified emergency egress guidance.
