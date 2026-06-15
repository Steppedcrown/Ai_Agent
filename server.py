# Test with: npx @modelcontextprotocol/inspector python server.py

import os
import anthropic
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("claude-mcp")
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


@mcp.tool()
def ask_claude(prompt: str, system: str = "") -> str:
    """Send a prompt to Claude and return the response."""
    messages = [{"role": "user", "content": prompt}]
    kwargs = {
        "model": "claude-opus-4-8",
        "max_tokens": 8096,
        "thinking": {"type": "adaptive"},
        "messages": messages,
    }
    if system:
        kwargs["system"] = system

    with client.messages.stream(**kwargs) as stream:
        return stream.get_final_message().content[0].text


@mcp.tool()
def ask_claude_with_history(
    messages: list[dict],
    system: str = "",
) -> str:
    """Send a multi-turn conversation to Claude and return the response.

    messages should be a list of {"role": "user"|"assistant", "content": str} dicts.
    """
    kwargs = {
        "model": "claude-opus-4-8",
        "max_tokens": 8096,
        "thinking": {"type": "adaptive"},
        "messages": messages,
    }
    if system:
        kwargs["system"] = system

    with client.messages.stream(**kwargs) as stream:
        return stream.get_final_message().content[0].text


if __name__ == "__main__":
    mcp.run()
