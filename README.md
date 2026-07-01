# Elden Ring AI Assistant

An AI-powered chatbot that acts as a knowledgeable Elden Ring player. Ask it about boss strategies, lore, rune rewards, and Shadow of the Erdtree content. It uses Claude (via the Anthropic API) combined with the Model Context Protocol (MCP) to look up live boss data from a local REST API backed by PostgreSQL.

**Live demo:** https://ai-agent--AidenThomas3.replit.app
> The app is password protected. Reach out if you'd like access and I'll send you the password.

---

## What it does

- **Conversational AI** — streams responses from Claude with a typing effect in the browser
- **MCP tool use** — the assistant can call `list_bosses` and `get_boss` tools to fetch accurate data mid-conversation rather than hallucinating
- **RAG knowledge base** — a local `knowledge.txt` file is semantically searched at query time and injected into the system prompt, giving Claude grounded, detailed strategy notes
- **REST API** — a standalone FastAPI service exposes the boss database over HTTP; the MCP server calls this API to serve the chatbot
- **PostgreSQL database** — boss data is stored in a real database (seeded from the original JSON files)

---

## Architecture

```
Browser
  └── Flask app (port 5000)
        ├── RAG (sentence-transformers, knowledge.txt)
        ├── Anthropic Claude API (streaming)
        └── MCP client → MCP server subprocess (per request)
                              └── Elden Ring API (port 8000, FastAPI + PostgreSQL)
```

Three processes run independently:

| Process | Command | Port |
|---|---|---|
| Flask chat app | `python app.py` | 5000 |
| Elden Ring REST API | `cd API && uvicorn main:app --host localhost --port 8000` | 8000 |
| MCP server | spawned automatically per chat request | — |

---

## Setup

### Prerequisites

- Python 3.12+
- A PostgreSQL database (Replit provides one automatically via `DATABASE_URL`)
- An [Anthropic API key](https://console.anthropic.com/)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment variables

Create a `.env` file in the project root (or set these as environment secrets):

```
ANTHROPIC_API_KEY=your-api-key-here
```

The database connection is read from `DATABASE_URL` (set automatically on Replit, or configure it yourself for local development).

#### Enabling semantic / vector search (optional)

Vector search uses [ChromaDB](https://www.trychroma.com/) and is **disabled by default**. To enable it:

1. Install chromadb:
   ```bash
   pip install chromadb
   ```
2. Set the environment variable:
   ```
   VECTORDB_ENABLED=1
   ```

When enabled, the app embeds all game entities into a local Chroma collection on startup and the `semantic_search` MCP tool becomes available for conceptual queries (e.g. "intelligence-scaling weapons", "bosses weak to bleed"). Without it, all other tools work normally.

### 3. Seed the database

The boss table needs to exist before the API will work. Connect to your PostgreSQL database and run:

```sql
CREATE TABLE IF NOT EXISTS bosses (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    runes       INTEGER
);
```

Then insert the boss records from `API/data/bosses.json`, or run the app and use the API to verify the table is populated.

### 4. Run the services

Start the Elden Ring API first, then the Flask app:

```bash
# Terminal 1 — REST API
cd API && uvicorn main:app --host localhost --port 8000

# Terminal 2 — Chat app
python app.py
```

Then open `http://localhost:5000` in your browser.

---

## Project structure

```
├── app.py                  # Flask app — agentic loop, SSE streaming, RAG
├── requirements.txt
├── templates/
│   └── index.html          # Chat UI (vanilla JS, marked.js for markdown)
├── MCP/
│   ├── server.py           # MCP server — exposes list_bosses / get_boss tools
│   ├── rag.py              # Semantic search over knowledge.txt
│   └── knowledge.txt       # Boss strategy & lore knowledge base
└── API/
    ├── main.py             # FastAPI entry point
    ├── data/
    │   └── bosses.json     # Original seed data
    ├── db/
    │   ├── loader.py       # PostgreSQL connection (psycopg2)
    │   └── driver.py       # Query builder (JSONDriver)
    └── routers/
        └── _base.py        # Generic router factory (list + detail endpoints)
```

---

## API endpoints

The Elden Ring API runs on `localhost:8000`. Interactive docs are available at `http://localhost:8000/docs`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/bosses` | List bosses — supports `?name=`, `?page=`, `?limit=` |
| `GET` | `/bosses/{id}` | Get a single boss by ID |

### Example

```bash
curl http://localhost:8000/bosses?name=messmer
curl http://localhost:8000/bosses/3
```

---

## Adding more bosses or data models

1. Add rows to the `bosses` table (or create a new table for a new model)
2. Register the new model in `API/main.py`:
   ```python
   app.include_router(make_router("weapons"))
   ```
3. Add a new MCP tool in `MCP/server.py` that calls the new endpoint
4. Update `MCP/knowledge.txt` with relevant knowledge for the new data
