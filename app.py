# Open with: python app.py
# Go to: http://localhost:5000

import asyncio
import json
import queue
import sys
import threading
import time
import urllib.request
from pathlib import Path

from flask import Flask, render_template, request, Response, stream_with_context
from dotenv import load_dotenv
import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import psycopg2
import psycopg2.extras
import MCP.rag as rag

import os
load_dotenv(Path(__file__).parent / ".env")

_VECTORDB_ENABLED = os.environ.get("VECTORDB_ENABLED", "").lower() in ("1", "true", "yes")
if _VECTORDB_ENABLED:
    from VectorDB.populate import populate as _populate_chroma

app = Flask(__name__)
async_client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
SERVER_SCRIPT = str(Path(__file__).parent / "MCP" / "server.py")
KNOWLEDGE_FILE = Path(__file__).parent / "MCP" / "knowledge.txt"
_BOSSES_JSON = Path(__file__).parent / "API" / "data" / "bosses.json"


def _seed_database() -> None:
    """Create the bosses table if needed and seed it from bosses.json when empty."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return
    try:
        from urllib.parse import urlparse
        p = urlparse(database_url)
        conn = psycopg2.connect(
            host=p.hostname, port=p.port or 5432,
            dbname=p.path.lstrip("/"), user=p.username, password=p.password,
        )
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS boss (
                    id          INTEGER PRIMARY KEY,
                    title       TEXT NOT NULL,
                    description TEXT,
                    runes       INTEGER
                )
            """)
            cur.execute("SELECT COUNT(*) FROM boss")
            if cur.fetchone()[0] == 0 and _BOSSES_JSON.exists():
                bosses = json.loads(_BOSSES_JSON.read_text(encoding="utf-8"))
                cur.executemany(
                    "INSERT INTO boss (id, title, description, runes) "
                    "VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
                    [(b["id"], b["name"], b.get("description"), b.get("runes")) for b in bosses],
                )
                print(f"Seeded {len(bosses)} bosses into the database.")
        conn.close()
    except Exception as exc:
        print(f"Warning: database seed skipped — {exc}")


_seed_database()

# Build the RAG index in a background thread so the server starts immediately
# and passes the deployment healthcheck while the model loads in parallel.
_rag_chunks: list = []
_rag_embeddings = None


def _build_rag_index() -> None:
    global _rag_chunks, _rag_embeddings
    # Delay heavy CPU work so gunicorn can pass the initial healthcheck first.
    time.sleep(30)
    knowledge_text = KNOWLEDGE_FILE.read_text(encoding="utf-8") if KNOWLEDGE_FILE.exists() else ""
    if knowledge_text:
        _rag_chunks, _rag_embeddings = rag.build_index(knowledge_text)
        print("RAG index ready.")
    if _VECTORDB_ENABLED:
        try:
            _populate_chroma()
        except Exception as exc:
            print(f"Warning: Chroma populate skipped — {exc}")
    else:
        print("VectorDB disabled. Set VECTORDB_ENABLED=1 to enable semantic search.")


threading.Thread(target=_build_rag_index, daemon=True, name="rag-builder").start()

_BASE_SYSTEM_PROMPT = """You are an Elden Ring assistant backed by a live database of Shadow of the Erdtree content. Your answers about game entities must come exclusively from tool calls — never from your training knowledge.

## Strict data rules

- **NEVER state facts about bosses, weapons, spells, skills, summons, items, NPCs, locations, dungeons, or remembrances from memory.** Your training data may be incomplete or wrong. All factual claims about game entities must come from a tool result.
- **Always call a tool before answering any data question**, even if you think you know the answer. If no tool returns a relevant result, say "I don't have that in my database" — do not fill in from memory.
- **Tool selection guide**:
  - Named entity (e.g. "Messmer", "Bloodfiend's Arm") → use the typed list tool (list_bosses, list_weapons, etc.) to find it by name, then the get_ tool for detail.
  - Descriptive or conceptual query (e.g. "intelligence-scaling weapons", "bosses weak to bleed") → use semantic_search first.
  - Unsure of type → use semantic_search across all entity types, then follow up with typed tools if needed.
- **Stay on topic**: Only answer questions about Elden Ring. Politely redirect anything else.

## Tone

Speak like an experienced player helping a friend — specific, confident, and encouraging. Supplement tool results with strategy advice from the injected knowledge context, but never invent stats or drop rates."""


def _build_system_prompt(query: str) -> str:
    """Retrieve the most relevant knowledge chunks for *query* and inject them."""
    if not _rag_chunks or _rag_embeddings is None:
        return _BASE_SYSTEM_PROMPT
    chunks = rag.retrieve(query, _rag_chunks, _rag_embeddings, k=2)
    context = "\n\n".join(chunks)
    return f"{_BASE_SYSTEM_PROMPT}\n\n## Relevant Knowledge\n\n{context}"


def _subprocess_env() -> dict:
    """Build an env dict that includes .pythonlibs so the MCP subprocess can find packages."""
    env = os.environ.copy()
    pythonlibs = str(Path(__file__).parent / ".pythonlibs" / "lib" / "python3.12" / "site-packages")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{pythonlibs}:{existing}" if existing else pythonlibs
    return env


async def _run_chat(messages: list, event_q: queue.Queue) -> None:
    """Full agentic loop: spawns server.py via stdio, discovers tools, calls Claude, handles tool use."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_SCRIPT],
        env=_subprocess_env(),
    )
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Discover tools from the MCP server — no hardcoding here
                tools_result = await session.list_tools()
                anthropic_tools = [
                    {
                        "name": t.name,
                        "description": t.description or "",
                        "input_schema": t.inputSchema,
                    }
                    for t in tools_result.tools
                ]

                current_messages = list(messages)
                query = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
                system_prompt = _build_system_prompt(query)

                while True:
                    tool_calls = []
                    active_tool = None
                    response_blocks = []
                    stop_reason = None

                    async with async_client.messages.stream(
                        model="claude-opus-4-8",
                        max_tokens=4096,
                        system=system_prompt,
                        tools=anthropic_tools,
                        messages=current_messages,
                    ) as stream:
                        async for event in stream:
                            etype = getattr(event, "type", None)

                            if etype == "content_block_start":
                                block = getattr(event, "content_block", None)
                                if block and block.type == "tool_use":
                                    active_tool = {
                                        "id": block.id,
                                        "name": block.name,
                                        "input_raw": "",
                                    }

                            elif etype == "content_block_delta":
                                delta = getattr(event, "delta", None)
                                if delta:
                                    if delta.type == "text_delta":
                                        event_q.put(json.dumps({"type": "text", "content": delta.text}))
                                    elif delta.type == "input_json_delta" and active_tool:
                                        active_tool["input_raw"] += delta.partial_json

                            elif etype == "content_block_stop":
                                if active_tool:
                                    try:
                                        parsed = json.loads(active_tool["input_raw"]) if active_tool["input_raw"] else {}
                                    except json.JSONDecodeError:
                                        parsed = {}
                                    tool_calls.append({
                                        "id": active_tool["id"],
                                        "name": active_tool["name"],
                                        "input": parsed,
                                    })
                                    active_tool = None

                        final_msg = await stream.get_final_message()
                        stop_reason = final_msg.stop_reason
                        response_blocks = final_msg.content

                    if stop_reason != "tool_use" or not tool_calls:
                        break

                    # Notify UI which tools are being called
                    for tc in tool_calls:
                        event_q.put(json.dumps({"type": "tool_use", "name": tc["name"]}))

                    # Add assistant turn (with tool_use blocks) to history.
                    # Build explicit dicts rather than model_dump() to avoid
                    # extra Pydantic fields that the API rejects on follow-up calls.
                    assistant_content = []
                    for b in response_blocks:
                        btype = getattr(b, "type", None)
                        if btype == "text":
                            assistant_content.append({"type": "text", "text": b.text})
                        elif btype == "tool_use":
                            assistant_content.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
                        elif btype == "thinking":
                            assistant_content.append({"type": "thinking", "thinking": b.thinking, "signature": getattr(b, "signature", "")})
                    current_messages.append({"role": "assistant", "content": assistant_content})

                    # Execute each tool via the MCP server and collect results
                    tool_results = []
                    for tc in tool_calls:
                        result = await session.call_tool(tc["name"], tc["input"])
                        content_str = "\n".join(
                            c.text for c in result.content if hasattr(c, "text")
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tc["id"],
                            "content": content_str or "{}",
                        })
                        event_q.put(json.dumps({"type": "tool_done", "name": tc["name"]}))

                    current_messages.append({"role": "user", "content": tool_results})

    except Exception as e:
        event_q.put(json.dumps({"type": "error", "message": str(e)}))
    finally:
        event_q.put(None)  # sentinel: tell the sync generator we're done


@app.route("/")
def index():
    return render_template("index.html")


def _log_user_prompt(content: str) -> None:
    try:
        payload = json.dumps({"content": content}).encode()
        req = urllib.request.Request(
            "http://localhost:3001/event",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=0.5)
    except Exception:
        pass


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    messages = data.get("messages", [])

    user_text = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    if user_text:
        threading.Thread(target=_log_user_prompt, args=(user_text,), daemon=True).start()

    def generate():
        event_q: queue.Queue = queue.Queue()

        # Run the async agentic loop in a background thread with its own event loop
        threading.Thread(
            target=lambda: asyncio.run(_run_chat(messages, event_q)),
            daemon=True,
        ).start()

        while True:
            item = event_q.get()
            if item is None:
                break
            yield f"data: {item}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
