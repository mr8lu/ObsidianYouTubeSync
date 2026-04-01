# Integrations (AI & Agents)

ObsidianYouTubeSync was built specifically for AI integration and downstream RAG operations. The produced dataset operates natively as an expansive Knowledge Graph.

## OpenClaw Skill (Recommended)

You can teach the [OpenClaw](https://openclaw.ai) Mac AI agent how to autonomously run your syncs and retag folders using a native `SKILL.md` file.

### Installation

1. Create a folder at `~/.openclaw/skills/obsidian-youtube-sync/`.
2. Drop in a `SKILL.md` file that explains how to execute `./run.sh` and `uv run retag_notes.py`. (A working template is provided upon request).

Once installed, you can simply ask OpenClaw: *"Sync my YouTube watch history and let me know what themes I learned about today."*

## Model Context Protocol (MCP) Server

You can expose the toolkit as an **MCP server** to clients like Claude Desktop or Cursor.

### Setup for Claude Desktop

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ObsidianYouTubeSync": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/ObsidianYouTubeSync",
        "run",
        "mcp_server.py"
      ]
    }
  }
}
```

*Note: Replace `/absolute/path/to/` with the actual path to the repository on your machine.*

## Knowledge Graph Engineering

### For GraphRAG (Microsoft GraphRAG / LlamaIndex)
1. Run `./run.sh --sync` to sync your complete YouTube history.
2. Point your GraphRAG pipeline at the `~/Documents/Obsidian Vault/YouTube/` folder.
3. The YAML frontmatter is parsed as node metadata; transcripts are chunked for retrieval; tags form the typed edge schema.

### For Vector Databases (Pinecone, Weaviate, Chroma)
- **Summaries**: Ideal for dense embedding because they are short, factual, and topic-rich.
- **Transcripts**: Can be chunked with metadata-aware splitters.
- **Tags**: Can be used as filters/facets for hybrid search queries.

### For LLM Fine-Tuning Datasets
You can generate instruction-response pairs from `(transcript) → summary` text pairs. You can also use the hierarchical tags as classification labels.
