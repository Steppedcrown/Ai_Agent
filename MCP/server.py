# Test with: npx @modelcontextprotocol/inspector python server.py

import httpx  # type: ignore
from mcp.server.fastmcp import FastMCP  # type: ignore

mcp = FastMCP("claude-mcp")
_queue_times_base = "https://queue-times.com"


@mcp.tool()
def list_parks() -> list:
    """Return all theme parks with available queue times, grouped by park group."""
    r = httpx.get(f"{_queue_times_base}/parks.json")
    r.raise_for_status()
    return r.json()


@mcp.tool()
def get_queue_times(park_id: int) -> dict:
    """Return live ride queue times for a theme park.

    Args:
        park_id: The numeric park ID from list_parks().
    Returns a dict with 'lands' (grouped rides) and 'rides' (ungrouped rides),
    each containing wait_time (minutes), is_open, and last_updated (UTC).
    """
    r = httpx.get(f"{_queue_times_base}/parks/{park_id}/queue_times.json")
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    mcp.run()
