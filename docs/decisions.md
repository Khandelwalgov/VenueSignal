# Architecture Decision Log

- **Choice of synthetic stadium**: A synthetic stadium (Unity Stadium) is used to satisfy the project's requirement to remain demoable without accessing proprietary FIFA data or real stadium blueprints.
- **Choice of Next.js + FastAPI**: Next.js provides a robust, fast frontend with good accessibility primitives. FastAPI provides excellent Python typing via Pydantic which aligns well with graph/node/edge data validation.
- **Graph as operational truth**: The visual SVG map is strictly a presentation layer. All routing and status data belongs to a separate structured JSON graph.
- **Human approval for consequential actions**: All generated AI plans are reviewed and approved by the Venue Operations Controller before work is created.
- **No AI routing**: Deterministic weighted Dijkstra owns pathfinding and produces reproducible accessibility-constraint results.
- **Repository-size strategy**: Binary files are banned. Next.js cache and python cache are ignored. A script strictly ensures the repository remains under the 10 MB limit.
- **One-primary-persona strategy**: We focus deeply on the Venue Operations Controller rather than creating a shallow super-app for fans, organizers, and volunteers simultaneously.
- **Versioned overlay strategy**: Canonical topology stays immutable. Runtime failures and crowd changes are stored in a separate overlay so scenario resets cannot corrupt venue truth.
- **Provider strategy**: The credential-free provider exercises the same schemas and approval boundaries without pretending to call Gemini; the official Gemini adapter is selected only with server credentials.
- **Repository strategy**: Memory supports isolated tests, SQLite supports durable single-process use, and Firestore is mandatory in production. Canonical topology remains version-controlled JSON.
- **Production safety profile**: Production startup requires Firebase auth, Firestore, a non-loopback CORS allow-list, and disabled demo reset; unsafe production configuration fails startup.
- **Idempotent evidence identity**: Normalized report fingerprints produce deterministic report identifiers so repeated evidence converges across application instances.
