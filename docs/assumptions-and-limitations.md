# Assumptions and limitations

- Unity Stadium and all scenario values are synthetic; routes are not certified emergency-egress guidance.
- Memory mode disappears on restart. SQLite is durable but single-process. Firestore is required for horizontally scaled production.
- The local AI provider is deterministic. Live Gemini was verified with the user-configured key and available quota on 18 July 2026; future runs still depend on external availability, quota, and the configured model.
- Firebase and Firestore adapters require a configured Google Cloud/Firebase project, ADC/service account, users, and role claims.
- Communication publication is intentionally simulated; no real delivery connector exists.
- Rate limiting is process-local. A distributed gateway or store is recommended for multi-instance abuse protection.
- Firestore tasks, communications, and audit events are embedded in incident documents for the current contest scale; high-volume deployments may split subcollections and add transactions/indexes.
- The application does not process real personal data in the demo. Production privacy, retention, deletion, residency, monitoring, backup, and incident-response policies remain organizational obligations.
- The deterministic containment plan is deliberately specific to Unity Stadium's Lift L2/Corridor W3 no-route scenario. It does not claim generalized emergency planning or certified egress guidance.
- Firebase Auth, Firestore credentials, Render secrets, and final hosted-domain behavior require live project verification.
