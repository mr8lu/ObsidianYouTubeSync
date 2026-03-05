# 📺 ObsidianYouTubeSync — YouTube History Downloader, Transcript Extractor & AI Knowledge Graph Builder

[![Obsidian](https://img.shields.io/badge/Made%20for-Obsidian-8b6cef?logo=obsidian)](https://obsidian.md)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-5c3d9e?logo=anthropic)](https://modelcontextprotocol.io)

**Download, sync, and organize your entire YouTube watch history into a structured, AI-tagged knowledge graph — ready for Obsidian, OpenClaw, and GraphRAG pipelines.**

This tool automates the full pipeline: it downloads YouTube video metadata, extracts captions and transcripts, generates LLM-powered summaries using Google Gemini (GenAI), and saves each video as a richly categorized Markdown note with a consistent hierarchical taxonomy. Built for users with **large YouTube watch libraries** who want to transform passive viewing history into an active, searchable, and connectable dataset.

> **Use cases:** Personal knowledge management (PKM), YouTube history cataloging, knowledge graph construction, transcript dataset preparation, GraphRAG ingestion, OpenClaw/LLM agent tooling, personal AI training data, second brain building.

---

## ✨ Why ObsidianYouTubeSync?

If you have hundreds or thousands of videos in your YouTube history, finding insights buried in that content is nearly impossible without structure. This tool solves that by:

- **Downloading** your full YouTube watch history (incremental or bulk) using `yt-dlp`
- **Extracting** full captions and transcripts for every video (with fallback to auto-generated captions)
- **Summarizing** each video using Google Gemini LLM (GenAI) — concise, searchable summaries
- **Categorizing** content with a shared hierarchical taxonomy (e.g., `Technology/ArtificialIntelligence`, `Science/Neuroscience`) using AI classification
- **Organizing** notes into Obsidian with clean YAML frontmatter (tags, url, channel, date, summary) — queryable via Dataview
- **Enabling** downstream pipelines: export structured notes as a knowledge graph dataset for **GraphRAG**, **OpenClaw**, vector databases, or LLM fine-tuning

---

## 🧠 Key Features

| Feature | Details |
|---|---|
| **LLM Summarization** | Google Gemini (GenAI) generates concise, high-quality summaries for every video |
| **Full Transcript Download** | Pulls captions/transcripts (manual + auto-generated) from YouTube |
| **Hierarchical AI Tagging** | CamelCase taxonomy tags like `Technology/AI/LLM`, `Person/ElonMusk` |
| **History Sync** | Download & sync your entire YouTube watch history via browser cookies + `yt-dlp` |
| **Incremental Updates** | Smart detection — only processes new videos, skips already-synced ones |
| **YouTube Shorts Skip** | Automatically detects and skips Shorts to keep your knowledge base high-signal |
| **Vault-wide Retagging** | Retag any folder (Apple Notes, Books, etc.) using the same global AI taxonomy |
| **Parallel Processing** | `ThreadPoolExecutor` with configurable pool — syncs 100s of videos in minutes |
| **MCP Server** | Native [Model Context Protocol](https://modelcontextprotocol.io) server for AI agent integration |
| **GraphRAG-Ready Output** | Structured Markdown with rich metadata nodes for knowledge graph pipelines |

---

## 🗂️ Output Format — GraphRAG & Knowledge Graph Ready

Each YouTube video becomes a structured Markdown node with rich metadata. This format is directly ingestible by **OpenClaw**, **GraphRAG**, LlamaIndex, LangChain, or any knowledge graph pipeline:

```markdown
---
url: https://www.youtube.com/watch?v=VIDEO_ID
channel: "Lex Fridman"
date_synced: 2026-02-27
summary: "A deep conversation on the nature of intelligence and the trajectory of AGI development, exploring consciousness, Gödel's theorems, and the limits of computation."
tags:
  - Technology
  - Technology/ArtificialIntelligence
  - Technology/ArtificialIntelligence/LLM
  - Science/CognitiveScience
  - Person/LexFridman
  - Person/JohnCarmack
  - AGI
  - ConsciousnessDebate
  - ComputationalLimits
---

# The Future of AGI with John Carmack

## Extracted Links
- https://en.wikipedia.org/wiki/Gödel%27s_incompleteness_theorems

## Description
In this episode, Lex Fridman sits down with John Carmack to discuss...

## Raw Transcript
[Full verbatim transcript for semantic search, embedding, and RAG ingestion]
```

### Why this structure matters for GraphRAG / OpenClaw:
- **Entities** (`Person/`, `Company/`, `Location/`) form graph nodes
- **Taxonomy tags** form typed edges between concepts
- **Summaries** are ideal embedding targets for semantic similarity
- **Transcripts** provide raw text for chunking, dense retrieval, and fine-tuning
- **Dates + channels** enable temporal and source-based graph traversals

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.10+**
- **Google Gemini API Key** — free tier available at [Google AI Studio](https://aistudio.google.com/)
- **Chrome, Safari, or Firefox** logged into YouTube (for `yt-dlp` history access)
- **Obsidian** (optional but recommended for visualization and Dataview queries)

### Installation

```bash
# Clone the repository
git clone https://github.com/mr8lu/ObsidianYouTubeSync.git
cd ObsidianYouTubeSync

# Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration

```bash
# Copy the example environment file
cp .env.example .env
```

Edit `.env` with your credentials:
```env
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Webshare rotating proxy (recommended for large history syncs)
WEBSHARE_PROXY_USER=your_proxy_user
WEBSHARE_PROXY_PASS=your_proxy_password
```

> **Vault Path**: The default is `~/Documents/Obsidian Vault`. Update `OBSIDIAN_VAULT_PATH` in `sync.py` and `retag_notes.py` if your vault lives elsewhere.

---

## 🛠️ Usage

### Sync Your YouTube Watch History

```bash
# First-time full sync (downloads your complete watch history)
./run.sh --init

# Incremental daily sync (only processes new videos)
./run.sh --incremental

# Re-tag and re-categorize all existing notes with the latest taxonomy
./run.sh --retag
```

### Retag Any Folder with the Global AI Taxonomy

Apply consistent LLM-powered categorization to *any* existing notes folder:

```bash
# Dry-run preview (no files modified)
python3 retag_notes.py --folder "~/Documents/Obsidian Vault/Apple Notes" --dry-run

# Live retag
python3 retag_notes.py --folder "~/Documents/Obsidian Vault/Books"

# Control parallelism
python3 retag_notes.py --folder "~/Documents/Obsidian Vault/Books" --workers 10
```

---

## 🤖 AI Agent Integrations (OpenClaw & MCP)

This toolkit is designed to be fully manageable by local-first AI agents. There are two primary integration paths:

### 1. OpenClaw Skill (Recommended)
You can teach the [OpenClaw](https://openclaw.ai) Mac AI agent how to autonomously run your syncs and retag folders using a native `SKILL.md` file.

**Installation:**
Create a folder at `~/.openclaw/skills/obsidian-youtube-sync/` and drop in a `SKILL.md` file that explains how to execute `./run.sh` and `retag_notes.py`. (A working template is provided upon request).
Once installed, you can simply ask OpenClaw: *"Sync my YouTube watch history and let me know what themes I learned about today."*

### 2. Model Context Protocol (MCP) Server
Alternatively, you can expose the toolkit as an **MCP server** to Claude Desktop, Cursor, or other MCP clients.
> *Note: The `mcp_server.py` file is currently parked on the `dev/v1.0.1` branch.*

**Setup for Claude Desktop (when using `dev/v1.0.1`):**
Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ObsidianYouTubeSync": {
      "command": "/absolute/path/to/ObsidianYouTubeSync/venv/bin/python3",
      "args": [
        "/absolute/path/to/ObsidianYouTubeSync/mcp_server.py"
      ]
    }
  }
}
```
*Note: Ensure you replace `/absolute/path/to/` with the actual path to the repository on your machine.*

---

## 📊 Building a Knowledge Graph with Your YouTube History

This tool is purpose-built as a **data pipeline** for knowledge graph construction. Here's how to plug it into downstream systems:

### For GraphRAG (Microsoft GraphRAG / LlamaIndex)
1. Run `./run.sh --init` to sync your complete YouTube history
2. Point your GraphRAG pipeline at the `~/Documents/Obsidian Vault/YouTube/` folder
3. The YAML frontmatter is parsed as node metadata; transcripts are chunked for retrieval; tags form the typed edge schema

### For OpenClaw
- Each note file is a self-contained document node with entity tags (`Person/`, `Company/`, `Location/`) pre-extracted
- The taxonomy hierarchy (`Technology/ArtificialIntelligence/LLM`) maps directly to ontological class trees
- Channel metadata provides provenance edges in the graph

### For Vector Databases (Pinecone, Weaviate, Chroma)
- Summaries are ideal for dense embedding (short, factual, topic-rich)
- Transcripts can be chunked with metadata-aware splitters
- Tags can be used as filters/facets for hybrid search

### For LLM Fine-Tuning Datasets
- Generate instruction-response pairs from `(transcript) → summary` pairs
- Use hierarchical tags as classification labels
- Export with a simple Python script reading the YAML frontmatter

---

## 🗺️ Roadmap

| Feature | Status |
|---|---|
| YouTube History Sync (incremental & full) | ✅ Done |
| AI Summarization via Google Gemini (GenAI) | ✅ Done |
| Full Transcript / Caption Extraction | ✅ Done |
| Hierarchical AI Taxonomy Tagging | ✅ Done |
| Parallel Processing (ThreadPoolExecutor) | ✅ Done |
| Vault-wide Retagging Engine | ✅ Done |
| Proxy / Rate-limit Support | ✅ Done |
| MCP Server for AI Agent Integration | ✅ Done |
| GraphRAG Export Helper Script | 🔜 Planned |
| Obsidian Community Plugin | 🔜 Planned |
| Notion / Logseq Export | 🔜 Planned |
| Local LLM Support (Ollama) | 💡 Considering |
| YouTube Playlist Sync | 💡 Considering |
| OpenClaw Native Connector | 💡 Considering |

---

## 🏗️ How It Works with Obsidian

- **Native YAML Properties**: `tags:`, `url:`, `summary:`, `channel:`, `date_synced` — all recognized by Obsidian natively
- **Hierarchical Tags**: `Parent/Child` tags map to Obsidian's Tag Pane tree view
- **Dataview Queries**: Query your entire watch history like a database
- **Graph View**: Entity tags create visual connections between videos sharing people, companies, or concepts

---

## 🔒 Privacy & Security

- **Local-First**: All notes live on your machine. No cloud sync.
- **No Account Data**: Only public video metadata (title, description, transcript) is sent to Gemini for summarization. Your YouTube account credentials are never accessed or stored.
- **Credential Security**: API keys loaded via `.env` (excluded from git). Proxy credentials stored locally only.
- **macOS Permissions**: Ensure Terminal has "Full Disk Access" in System Settings → Privacy & Security.

---

## ⚙️ Compatibility

| Environment | Supported |
|---|---|
| macOS (Intel & Apple Silicon) | ✅ |
| Linux | ✅ |
| Windows (WSL) | ⚠️ Untested |
| Python 3.10+ | ✅ |
| Obsidian 1.0+ | ✅ |
| Chrome / Safari / Firefox cookies | ✅ |
| Claude Desktop (MCP) | ✅ |
| GraphRAG / LlamaIndex | ✅ |
| OpenClaw | ✅ |

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for how to get started.

If you find this useful, please ⭐ **star the repo** — it helps more researchers, PKM enthusiasts, and knowledge graph builders discover it.

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
