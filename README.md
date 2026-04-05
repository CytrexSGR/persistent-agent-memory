# persistent-agent-memory

MCP server that gives AI agents persistent semantic memory across sessions.

## Features

- **11 MCP tools** -- remember, recall, forget, typed decisions/rules, bootstrap context, directory indexing
- **Semantic search** -- memories are embedded and recalled via natural language
- **Session continuity** -- handoff + bootstrap skills for structured session transitions
- **Pluggable storage** -- SQLite + sqlite-vec (default, zero-dependency) or PostgreSQL + pgvector
- **Pluggable embeddings** -- any OpenAI-compatible API (Ollama, vLLM, OpenAI) or local sentence-transformers
- **Directory indexer** -- semantic search over Markdown files / Obsidian vaults

## Quick Start

```bash
# Install
pip install persistent-agent-memory

# Start with Ollama for local embeddings (free, no API key)
ollama pull nomic-embed-text
pam serve --stdio
```

### Claude Code Integration

Add to your `.mcp.json`:

```json
{
  "persistent-memory": {
    "command": "pam",
    "args": ["serve", "--stdio"]
  }
}
```

### With Docker (PostgreSQL backend)

```bash
docker compose up -d
```

## Configuration

Copy `.env.example` to `.env` and adjust:

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_BACKEND` | `sqlite` | `sqlite` or `postgres` |
| `SQLITE_PATH` | `./data/memory.db` | Path to SQLite database |
| `DATABASE_URL` | -- | PostgreSQL connection string |
| `EMBEDDING_PROVIDER` | `api` | `api` or `local` |
| `EMBEDDING_API_URL` | `http://localhost:11434/v1` | OpenAI-compatible embedding endpoint |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model name |
| `EMBEDDING_DIMENSIONS` | `768` | Vector dimensions |
| `BOOTSTRAP_CACHE_TTL` | `3600` | Bootstrap context cache (seconds) |

## MCP Tools

| Tool | Description |
|------|-------------|
| `remember` | Store a memory with content, category, tags, importance |
| `recall` | Semantic search via natural language query |
| `forget` | Delete a memory by ID |
| `remember_decision` | Store an architecture decision with context + rationale |
| `remember_rule` | Store a rule/constraint |
| `search_knowledge` | Extended search with threshold and filters |
| `get_context` | Load context for a topic |
| `get_session_summary` | Last N memories as briefing |
| `get_bootstrap_context` | Everything needed at session start (cached) |
| `index_directory` | Scan .md files, chunk, embed, store |
| `search_indexed` | Semantic search over indexed files |

## Skills

Install skills to your agent's skills directory for integration:

- **session-handoff** -- structured handoff at session end
- **memory-bootstrap** -- session start protocol (loads context + pending handoffs)
- **atlas-update** (optional) -- infrastructure documentation updates

## Development

```bash
git clone https://github.com/CytrexSGR/persistent-agent-memory.git
cd persistent-agent-memory
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## License

AGPL-3.0-or-later. Commercial license available -- contact for details.
