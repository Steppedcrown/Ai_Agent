---
name: RAG startup CPU starvation
description: SentenceTransformer model loaded at import time in MCP/rag.py blocks gunicorn worker from ever responding, causing healthcheck timeouts on deployment.
---

# RAG import-time model load blocks gunicorn healthchecks

## The rule
`MCP/rag.py` originally had `_model = SentenceTransformer("all-MiniLM-L6-v2")` at module level. When gunicorn imports `app.py`, which does `import MCP.rag as rag`, it triggers this synchronous model load (~60-80s) before the worker can handle any HTTP request — so every healthcheck times out and deployment fails.

**Why:** Module-level code in any imported module runs synchronously during worker boot. Heavy IO/CPU at import time directly delays the worker's ability to serve requests.

**How to apply:** In `MCP/rag.py`, `_model` is now `None` at module level and loaded lazily via `_get_model()` on first call to `build_index()` or `retrieve()`. Combined with a `time.sleep(30)` at the start of the background RAG builder thread in `app.py`, the worker boots instantly, passes healthchecks, and the model loads quietly in the background 30 seconds later.

**Key lesson:** Any heavy import (sentence_transformers, torch, tensorflow, etc.) in a transitively-imported module will block gunicorn worker startup. Always lazy-load these inside functions, never at module level.
