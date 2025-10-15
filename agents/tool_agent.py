# agents/tool_agent.py
import asyncio
from typing import Optional, Dict, Any
from utils.mcp_adapter import fetch_external_context

def fetch_external_data(query: str, provider: str = "mock", api_key: str = None) -> str:
    """
    Synchronous wrapper returning string summary (for backward compatibility).
    """
    result = fetch_external_context(query, provider=provider, api_key=api_key)
    return result.get("summary", "") if isinstance(result, dict) else str(result)

async def fetch_external_data_async(query: str, provider: str = "mock", limit: int = 3) -> Dict[str, Any]:
    """
    Async wrapper that runs the MCP adapter in a thread.
    """
    return await asyncio.to_thread(fetch_external_context, query, provider, limit, None)
