from mcp.server.fastmcp import FastMCP

from mcp_memory.repository import fetch_memory, init_db, save_memory, search_memories

mcp = FastMCP("memory")


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
