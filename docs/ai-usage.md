# AI usage

`AIProvider` isolates model work from domain rules. `LocalDemoAIProvider` is the active, deterministic, offline provider. It structures reports, proposes schema-valid response plans from verified facts plus labelled claims, and explains reassessment. Its output is advisory and visibly attributed.

AI does not determine topology, routes, facility state, incident verification, allowed actions, plan validity, task creation, or approval. Known IDs and action/team allow-lists are injected from authoritative domain data and checked after generation. Raw report text is treated as evidence; instruction-like patterns are flagged.

`GeminiProvider` currently implements only a credential gate and makes no network call. A production adapter still needs the official SDK, strict structured-output parsing, bounded retries, timeouts, quota/availability handling, call metadata, and contract tests. `GEMINI_API_KEY` must remain server-side.
