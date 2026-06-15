# Test with: npx @modelcontextprotocol/inspector python server.py

import os
import anthropic  # type: ignore
import httpx  # type: ignore
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP  # type: ignore

load_dotenv()

mcp = FastMCP("claude-mcp")
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
_aviation_key = os.environ.get("AVIATIONSTACK_API_KEY")
_aviation_base = "https://api.aviationstack.com/v1"


@mcp.tool()
def search_flights(
    dep_iata: str = "",
    arr_iata: str = "",
    flight_iata: str = "",
    airline_iata: str = "",
    flight_status: str = "",
    limit: int = 10,
) -> dict:
    """Search real-time flights from the AviationStack API.

    Args:
        dep_iata: Departure airport IATA code (e.g. 'SFO').
        arr_iata: Arrival airport IATA code (e.g. 'JFK').
        flight_iata: Specific flight number (e.g. 'AA100').
        airline_iata: Airline IATA code (e.g. 'AA' for American).
        flight_status: One of scheduled, active, landed, cancelled, incident, diverted.
        limit: Max results to return (default 10).
    """
    params: dict = {"access_key": _aviation_key, "limit": limit}
    if dep_iata:
        params["dep_iata"] = dep_iata
    if arr_iata:
        params["arr_iata"] = arr_iata
    if flight_iata:
        params["flight_iata"] = flight_iata
    if airline_iata:
        params["airline_iata"] = airline_iata
    if flight_status:
        params["flight_status"] = flight_status

    r = httpx.get(f"{_aviation_base}/flights", params=params)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def get_airport(iata_code: str) -> dict:
    """Look up an airport by its IATA code (e.g. 'LAX', 'LHR')."""
    params = {"access_key": _aviation_key, "iata_code": iata_code}
    r = httpx.get(f"{_aviation_base}/airports", params=params)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def get_airline(iata_code: str) -> dict:
    """Look up an airline by its IATA code (e.g. 'AA', 'UA', 'DL')."""
    params = {"access_key": _aviation_key, "iata_code": iata_code}
    r = httpx.get(f"{_aviation_base}/airlines", params=params)
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    mcp.run()
