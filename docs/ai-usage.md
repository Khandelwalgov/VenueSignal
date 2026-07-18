# AI usage

`AIProvider` isolates model assistance from domain rules. `LocalDemoAIProvider` is deterministic and offline. `GeminiProvider` uses the official Google Gen AI Python SDK with JSON-schema responses, bounded initial-call transport retries, timeout/quota/malformed-output classification, authoritative asset/zone/node context, task/model/attempt/latency metadata, and server-only credentials.

AI performs report extraction, shortlist semantic assessment, response-plan proposals, and reassessment explanation. It does not determine topology, route truth, facility state, report verification, linking, allowed actions, plan validity, task creation, lifecycle transitions, or approval.

Raw reports are labelled as untrusted evidence. Instruction-like text is detected independently of the model, and model-returned candidate IDs are filtered against canonical IDs. Related-report reasoning considers at most 20 recent reports so model category/ID variance cannot suppress human-reviewable matching. Known IDs and action/team allow-lists are injected from authoritative data and checked again after generation. A provider failure cannot relax deterministic constraints or create work.

Local default: `AI_PROVIDER=local`. Live Gemini: install `requirements-production.txt`, set `AI_PROVIDER=gemini`, `GEMINI_API_KEY`, and optionally `GEMINI_MODEL`. Injected clients test success, malformed output, timeout, quota, and retry contracts.

Invalid proposals are withheld before review. The service records the original plan and structured validation errors, makes exactly one repair-generation call with the authoritative context, original plan, error codes, current route result, valid identifiers, and prohibited actions, then validates again. A valid repair is marked `GEMINI_REPAIRED`. A second invalid result or repair failure becomes `DETERMINISTIC_CONTAINMENT`; it cannot staff or publish a route and still requires approval.

User-authorized live acceptance completed on 18 July 2026 against `gemini-2.5-flash`: readiness, three extractions, bounded semantic matching, initial plan, approval, four tasks, three language drafts, reassessment, invalid-plan detection (`NO_VERIFIED_ROUTE`), exactly one repair, repaired-plan validation, containment approval, and duplicate-click protection passed. The repair was required and succeeded; deterministic fallback was not required. Credentials were neither printed nor stored in tracked files.

A final fully hardened rerun later encountered `AIProviderQuotaError` during plan generation and reassessment. The deterministic fallback was required and passed: both proposals were `DETERMINISTIC_CONTAINMENT`, remained approval-gated, created no communication, and repeated approval created no duplicate tasks. This is an external quota limitation, not a relaxation of safety.
