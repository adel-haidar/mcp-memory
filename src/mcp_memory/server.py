from mcp.server.fastmcp import FastMCP

from mcp.server.auth.provider import TokenVerifier, AccessToken
from mcp_memory.auth import validate_token as check_token
from mcp_memory.repository import fetch_memory, init_db, save_memory, search_memories


class PostgresTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        client_id = check_token(token)
        if not client_id:
            return None
        return AccessToken(client_id=client_id, scopes=[])


mcp = FastMCP("memory", token_verifier=PostgresTokenVerifier())


@mcp.tool()
def save(title: str, content: str, tags: list[str] | None = None) -> str:
    """Saving memory with title: {} and tags: {}"""
    memory = save_memory(title, content, tags)
    return f"Saved memory '{memory.title}' with id {memory.memory_id}"


@mcp.tool()
def fetch(memory_id: str) -> str:
    """Fetching Memory with ID '{memory_id}'"""
    memory = fetch_memory(memory_id)
    if memory is None:
        return f"No memory found with ID {memory_id}"
    return f"[{memory.memory_id}] {memory.title}\n{memory.content}\nTags: {', '.join(memory.tags)}"


@mcp.tool()
def search(query: str) -> str:
    """Search memories by keyword. Matches against title, content, and tags."""
    results = search_memories(query)
    if not results:
        return f"No memories found for query: {query}"
    lines = [f"- [{m.memory_id}] {m.title}" for m in results]
    return f"Found {len(results)} memories:\n" + "\n".join(lines)


init_db()

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
