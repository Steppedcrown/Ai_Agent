import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("elden-ring-mcp")
_API_BASE = "http://localhost:8000"


@mcp.tool()
def list_bosses(name: str = "") -> dict:
    """Return bosses from the Elden Ring API, optionally filtered by name.

    Args:
        name: Optional partial name to search for (case-insensitive). Leave empty to list all.
    Returns a dict with a 'data' list of boss objects, each containing id, title, description, and runes.
    """
    params = {}
    if name:
        params["name"] = name
    r = httpx.get(f"{_API_BASE}/bosses", params=params)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def get_boss(boss_id: int) -> dict:
    """Return detailed information about a single Elden Ring boss by ID.

    Args:
        boss_id: The numeric ID of the boss (use list_bosses to find IDs).
    Returns a dict with 'data' containing id, title, description, and runes reward.
    """
    r = httpx.get(f"{_API_BASE}/bosses/{boss_id}")
    r.raise_for_status()
    return r.json()


# --- Theme park tools (disabled) ---
# @mcp.tool()
# def list_parks() -> list:
#     """Return all theme parks with available queue times, grouped by park group."""
#     r = httpx.get("https://queue-times.com/parks.json")
#     r.raise_for_status()
#     return r.json()
#
# @mcp.tool()
# def get_queue_times(park_id: int) -> dict:
#     """Return live ride queue times for a theme park."""
#     r = httpx.get(f"https://queue-times.com/parks/{park_id}/queue_times.json")
#     r.raise_for_status()
#     return r.json()


if __name__ == "__main__":
    mcp.run()
