# Architecture Decision Log

- **Choice of synthetic stadium**: A synthetic stadium (Unity Stadium) is used to satisfy the project's requirement to remain demoable without accessing proprietary FIFA data or real stadium blueprints.
- **Choice of Next.js + FastAPI**: Next.js provides a robust, fast frontend with good accessibility primitives. FastAPI provides excellent Python typing via Pydantic which aligns well with graph/node/edge data validation.
- **Graph as operational truth**: The visual SVG map is strictly a presentation layer. All routing and status data belongs to a separate structured JSON graph.
- **Human approval for future consequential actions**: All generated AI plans must be reviewed and approved by the Venue Operations Controller.
- **No AI routing**: GenAI cannot reason reliably about complex graph traversal in real-time. Deterministic algorithms (Dijkstra) will be used for pathfinding, ensuring guaranteed results for accessibility constraints.
- **Repository-size strategy**: Binary files are banned. Next.js cache and python cache are ignored. A script strictly ensures the repository remains under the 10 MB limit.
- **One-primary-persona strategy**: We focus deeply on the Venue Operations Controller rather than creating a shallow super-app for fans, organizers, and volunteers simultaneously.
