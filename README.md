<p align="center">
  <h1 align="center">persistent-agent-memory</h1>
  <p align="center">
    MCP server that gives AI agents persistent semantic memory across sessions.
  </p>
  <p align="center">
    <a href="#quick-start">Quick Start</a> &bull;
    <a href="#mcp-tools">Tools</a> &bull;
    <a href="#configuration">Config</a> &bull;
    <a href="#skills">Skills</a> &bull;
    <a href="#architecture">Architecture</a>
  </p>
</p>

---

**The problem:** Claude Code, Cursor, Windsurf, and other MCP-based agents forget everything between sessions. Every conversation starts from zero.

**The fix:** A single MCP server that stores memories as embeddings, recalls them via natural language, and orchestrates session handoffs -- so your agent picks up where it left off.

## Features

| | |
|---|---|
| **11 MCP tools** | remember, recall, forget, typed decisions/rules, bootstrap context, directory indexing |
| **Semantic search** | Memories are embedded and recalled via natural language -- not keyword matching |
| **Session continuity** | Handoff + bootstrap skills for structured session transitions |
| **Pluggable storage** | SQLite + sqlite-vec (default, zero-dependency) or PostgreSQL + pgvector |
| **Pluggable embeddings** | Any OpenAI-compatible API (Ollama, vLLM, OpenAI) or local sentence-transformers |
| **Directory indexer** | Semantic search over Markdown files and Obsidian vaults |
| **Multi-agent ready** | Source agent tracking, typed handoffs between agents and sessions |

## Quick Start

```bash
# Install
pip install persistent-agent-memory

# Start with Ollama for local embeddings (free, no API key needed)
ollama pull nomic-embed-text
pam serve --stdio
```

### Claude Code

Add to your project's `.mcp.json`:

```json
{
  "persistent-memory": {
    "command": "pam",
    "args": ["serve", "--stdio"]
  }
}
```

That's it. Your agent now has persistent memory across all sessions.

### Other MCP Clients

Any MCP-compatible client (Cursor, Windsurf, custom agents) can connect via stdio or SSE:

```bash
# stdio (for direct integration)
pam serve --stdio

# SSE (for network access)
pam serve  # defaults to 0.0.0.0:8765
```

### Docker (PostgreSQL backend)

```bash
docker compose up -d
```

## MCP Tools

### Core Memory

| Tool | Description |
|------|-------------|
| `remember` | Store a memory with content, category, tags, importance (1-5) |
| `recall` | Semantic search via natural language query |
| `forget` | Delete a memory by ID |
| `remember_decision` | Store an architecture decision with context + rationale |
| `remember_rule` | Store a rule/constraint that must be followed |

### Context & Search

| Tool | Description |
|------|-------------|
| `search_knowledge` | Extended search with threshold, filters, and time range |
| `get_context` | Load all relevant context for a topic |
| `get_session_summary` | Last N memories as a session briefing |
| `get_bootstrap_context` | Everything needed at session start (cached 1h) |

### Directory Indexer

| Tool | Description |
|------|-------------|
| `index_directory` | Scan .md files, chunk by heading, embed, store |
| `search_indexed` | Semantic search over indexed files |

The indexer chunks Markdown files by heading, tracks file modification times, and only re-indexes changed files.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Client                            │
│            (Claude Code, Cursor, custom)                 │
└───────────────────────┬─────────────────────────────────┘
                        │ stdio / SSE
┌───────────────────────▼─────────────────────────────────┐
│               persistent-agent-memory                    │
│                                                          │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ 11 MCP   │  │  Embedding   │  │     Storage       │  │
│  │  Tools   │  │  Provider    │  │     Backend       │  │
│  │          │  │              │  │                    │  │
│  │ remember │  │ OpenAI-compat│  │ SQLite + vec      │  │
│  │ recall   │  │  (default)   │  │  (default)        │  │
│  │ forget   │  │      OR      │  │      OR           │  │
│  │ decide   │  │ sentence-    │  │ PostgreSQL +      │  │
│  │ rule     │  │ transformers │  │  pgvector          │  │
│  │ search   │  │              │  │                    │  │
│  │ context  │  └──────────────┘  └──────────────────┘  │
│  │ summary  │                                           │
│  │ bootstrap│  ┌──────────────┐                         │
│  │ index    │  │  Directory   │                         │
│  │ search_ix│  │  Indexer     │                         │
│  └──────────┘  └──────────────┘                         │
└─────────────────────────────────────────────────────────┘
```

### Memory Model

```
Memory {
  id: UUID
  content: text
  embedding: vector           # semantic search
  category: enum              # general | decision | rule | context | handoff | project
  tags: string[]              # free-form filtering
  importance: 1-5             # prioritization
  source_agent: string        # who wrote this
  created_at / updated_at
  metadata: json              # extensible
}
```

**Category semantics:**
- `decision` -- prioritized in bootstrap context
- `rule` -- always loaded when topic matches
- `handoff` -- searched at session start for pending work
- `project` -- grouped by project tag

## Configuration

Copy `.env.example` to `.env`:

```bash
# Storage (pick one)
STORAGE_BACKEND=sqlite              # sqlite | postgres
SQLITE_PATH=./data/memory.db
# DATABASE_URL=postgresql://...     # only for postgres

# Embeddings (pick one)
EMBEDDING_PROVIDER=api              # api | local
EMBEDDING_API_URL=http://localhost:11434/v1
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSIONS=768
# EMBEDDING_API_KEY=sk-...          # only for cloud APIs

# Server
HOST=0.0.0.0
PORT=8765
BOOTSTRAP_CACHE_TTL=3600
```

### Embedding Providers

| Provider | Config | Best for |
|----------|--------|----------|
| **Ollama** (default) | `EMBEDDING_API_URL=http://localhost:11434/v1` | Local, free, no API key |
| **OpenAI** | `EMBEDDING_API_URL=https://api.openai.com/v1` + API key | Quality, hosted |
| **vLLM / LM Studio** | Any `/v1/embeddings` endpoint | Self-hosted GPU |
| **sentence-transformers** | `EMBEDDING_PROVIDER=local` | Direct GPU, no server |

## Skills

Skills are structured prompts that orchestrate tool usage. Install to your agent's skills directory:

### session-handoff

Structured handoff at session end:

```
SESSION-HANDOFF 2025-01-15
FROM: agent-a on desktop
PROJECT: auth-rewrite
STATUS: IN_PROGRESS

DONE:
- Implemented OAuth2 flow (commit abc123)

OPEN:
- Token refresh logic (P1)

ENTRY:
recall("auth-rewrite session-handoff")
```

### memory-bootstrap

Session start protocol:
1. Detect environment (hostname, IP, working directory)
2. `get_bootstrap_context()` -- loads decisions, rules, handoffs
3. `recall("session-handoff IN_PROGRESS OR BLOCKED")` -- find pending work
4. Summarize to user

### atlas-update (optional)

Infrastructure documentation pattern for multi-server setups.

## Development

```bash
git clone https://github.com/CytrexSGR/persistent-agent-memory.git
cd persistent-agent-memory
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

**50 tests**, covering config, models, embeddings, storage, service, indexer, and all MCP tools.

Optional test dependencies:
- `pip install -e ".[local]"` -- sentence-transformers tests
- `TEST_DATABASE_URL=postgresql://... pytest` -- PostgreSQL tests

## License

AGPL-3.0-or-later with commercial dual-licensing. For proprietary use without AGPL obligations, contact for a commercial license.
