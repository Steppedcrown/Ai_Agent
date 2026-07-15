# ObservabilityTool

A Go reverse proxy that intercepts MCP traffic between the agent and the REST API, logging tool calls, system prompts, and latency as structured JSON.

## Why nothing shows up by default

The proxy has to sit **between** the MCP server and the REST API. Out of the box, `MCP/server.py` calls `http://localhost:8000` directly — the proxy is running but no traffic reaches it.

The correct traffic path is:

```
MCP/server.py → ObservabilityTool (:9001) → REST API (:8000)
```

## Setup (3 steps)

### 1. Configure the proxy

Edit `~/.myagent/mcp_config.json` (created automatically on first run):

```json
{
  "mcp_server_url": "http://localhost:8000",
  "listen_port": 9001,
  "flagged_terms": ["ignore previous instructions", "jailbreak"]
}
```

- `mcp_server_url` — where the proxy **forwards** to (your real REST API)
- `listen_port` — where the proxy **listens** (MCP server will point here)
- `flagged_terms` — strings to flag in system prompts

### 2. Start the proxy

```bash
cd ObservabilityTool
go run .
```

You should see:
```
ObservabilityTool starting...
Config loaded — target: http://localhost:8000  listen: :9001  flagged terms: [...]
Proxy listening on :9001 → http://localhost:8000
```

### 3. Route the MCP server through the proxy

Set the `MCP_API_URL` environment variable before starting the chatbot app so the MCP server sends its requests to the proxy instead of directly to port 8000.

**Windows (PowerShell):**
```powershell
$env:MCP_API_URL = "http://localhost:9001"
python app.py
```

**Windows (Command Prompt):**
```cmd
set MCP_API_URL=http://localhost:9001
python app.py
```

**macOS / Linux:**
```bash
MCP_API_URL=http://localhost:9001 python app.py
```

Or add it to your `.env` file:
```
MCP_API_URL=http://localhost:9001
```

## What you'll see

Every tool call the agent makes will print to the proxy shell. Example output:

```
[proxy] POST /weapons → http://localhost:8000
{
  "timestamp": "2025-01-15T10:23:44.123Z",
  "event_type": "tool_call",
  "path": "/weapons",
  "rpc_method": "tools/call",
  "tool_name": "list_weapons",
  "arguments": { "search": "greatsword" }
}
{
  "timestamp": "2025-01-15T10:23:44.341Z",
  "event_type": "completion",
  "path": "/weapons",
  "status_code": 200,
  "latency_ms": 218.4
}
```

If `flagged_terms` match anything in a system prompt, a `prompt_audit` event is also emitted with the matched terms highlighted.

## Live config reload

Edit `~/.myagent/mcp_config.json` while the proxy is running — changes are picked up instantly without restarting. The next request automatically uses the new target URL and flagged terms.

## Build a binary

```bash
cd ObservabilityTool
go build -o observability-tool .
./observability-tool
```
