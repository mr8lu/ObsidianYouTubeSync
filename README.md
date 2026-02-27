# 📺 Obsidian YouTube Sync: AI-Powered PKM Automation

[![Obsidian](https://img.shields.io/badge/Made%20for-Obsidian-8b6cef?logo=obsidian)](https://obsidian.md)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Turn your YouTube watch history into a structured personal knowledge base.** 

This tool automatically synchronizes your YouTube activity into your **Obsidian Vault**, extracting transcripts, generating AI-driven summaries, and applying a consistent hierarchical taxonomy using Google Gemini.

> **Keywords:** *youtube, download, sync, history, transcript, caption, summary, genai, llm, organize, categorized*
---

## ✨ Key Features

- **🧠 AI-Driven Summarization**: Uses Google Gemini to generate high-quality summaries of every video.
- **🏷️ Smart Hierarchical Taxonomy**: Automatically applies hierarchical tags (e.g., `Technology/AI/LLM`) to keep your vault organized.
- **📜 Full Transcript Extraction**: Pulls full video transcripts and saves them directly in your notes for deep searchability.
- **🔗 Link Extraction**: Automatically extracts and lists all URLs found in the video description.
- **⚡ Parallel Processing**: Built with multi-threading to sync hundreds of videos in seconds.
- **🛠️ Retagging Engine**: Includes a standalone script to apply your global taxonomy to *any* folder in your vault (like Apple Notes or Kindle highlights).
- **🚫 Shorts Detection**: Automatically identifies and skips YouTube Shorts to maintain a high-signal knowledge base.

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.10+** installed on your system.
- **Google Gemini API Key**: Get a free key from the [Google AI Studio](https://aistudio.google.com/).
- **Chrome/Safari/Firefox**: Logged into YouTube (used by `yt-dlp` to fetch your private history).

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/[user name]/YouTubeSyncTool.git
cd YouTubeSyncTool

# Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration
1. **API Key**: Create a `.env` file:
   ```bash
   cp .env.example .env
   ```
   Then fill in your values:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here

   # Optional: Webshare proxy (see below)
   WEBSHARE_PROXY_USER=your_proxy_user
   WEBSHARE_PROXY_PASS=your_proxy_password
   ```

2. **Vault Path**: Open `sync.py` and `retag_notes.py` and ensure `OBSIDIAN_VAULT_PATH` points to your vault (default is `~/Documents/Obsidian Vault`).

3. **(Optional) Webshare Proxy**: The tool uses a [Webshare](https://www.webshare.io/) rotating proxy to avoid IP blocks and rate limits when fetching transcripts and video details via `yt-dlp` and the YouTube Transcript API.
   - Sign up for a free or paid plan at [webshare.io](https://www.webshare.io/).
   - Copy your **Proxy Username** and **Proxy Password** from the Webshare dashboard.
   - Add them to your `.env` file as `WEBSHARE_PROXY_USER` and `WEBSHARE_PROXY_PASS`.
   - If these are not set, the tool will attempt to connect directly (which may result in throttling or blocks for large syncs).

---

## 🛠️ Usage

### Syncing YouTube History
Run the script via `run.sh` to start pulling your recent watch history.

```bash
# Typical daily sync (incremental)
./run.sh --incremental

# First-time setup (sync last 500 videos)
./run.sh --init

# Re-process and re-tag existing notes
./run.sh --retag
```

### Re-tagging Existing Notes (The "Retag" Engine)
You can use the built-in logic to clean up *any* folder in your Obsidian vault with your global AI taxonomy.

```bash
# Preview changes (Dry Run)
python3 retag_notes.py --folder "~/Documents/Obsidian Vault/Apple Notes" --dry-run

# Run live updates
python3 retag_notes.py --folder "~/Documents/Obsidian Vault/Apple Notes"
```

## 🤖 MCP Server Integration (For AI Agents)

This toolkit includes a native **Model Context Protocol (MCP)** server, allowing AI assistants (like Claude Desktop, Cursor, or other MCP-compatible clients) to autonomously trigger syncs or retag your vault.

### Exposed Tools
- `sync_youtube_history(mode)`: Triggers the main sync engine (supports `incremental`, `init`, `retag`, or `test` modes).
- `retag_obsidian_notes(folder, dry_run)`: Triggers the retag engine against any local folder.

### Setup for Claude Desktop
Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "YouTubeSyncTool": {
      "command": "/absolute/path/to/YouTubeSyncTool/venv/bin/python3",
      "args": [
        "/absolute/path/to/YouTubeSyncTool/mcp_server.py"
      ]
    }
  }
}
```
*Note: Ensure you replace `/absolute/path/to/` with the actual path to the repository on your machine.*

---

## 🏗️ Why this works for Obsidian
This tool is designed specifically for the **Obsidian/PKM** workflow:
- **Native Properties**: Uses standard YAML Frontmatter (`tags:`, `url:`, `summary:`) that Obsidian recognizes instantly as [Properties](https://help.obsidian.md/Editing+and+formatting/Properties).
- **Hierarchical Tags**: Generates tags in the `Parent/Child` format, allowing you to browse your knowledge tree in the Obsidian Tag Pane.
- **Metadata-Rich**: Every note includes the uploader name, sync date, and source link for easy Dataview queries.

---

## 📄 Sample Output Note

Every synced video becomes a beautifully structured Obsidian note:

```markdown
---
url: https://www.youtube.com/watch?v=dQw4w9WgXcQ
channel: "Veritasium"
date_synced: 2026-02-27
summary: "An exploration of how the brain forms long-term memories and the role of sleep in memory consolidation..."
tags:
  - Science
  - Science/Neuroscience
  - Science/Neuroscience/Memory
  - Health/Sleep
  - Person/MatthewWalker
  - NeuralPlasticity
  - SleepScience
  - CognitivePsychology
---

# Why Your Brain Needs Sleep to Learn

## Extracted Links
- https://www.sleepfoundation.org

## Description
In this video, we explore the science of memory...

## Raw Transcript
The hippocampus acts as a temporary storage buffer...
```

---

## 🗺️ Roadmap

| Feature | Status |
|---|---|
| YouTube History Sync (incremental & full) | ✅ Done |
| AI Summarization + Hierarchical Tags | ✅ Done |
| Full Transcript Extraction | ✅ Done |
| Parallel Processing | ✅ Done |
| Vault-wide Retagging Engine | ✅ Done |
| Proxy / Rate-limit support | ✅ Done |
| Obsidian Community Plugin | 🔜 Planned |
| Support for Notion / Logseq export | 🔜 Planned |
| Local LLM support (Ollama) | 💡 Considering |
| YouTube Playlist sync | 💡 Considering |

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for how to get started.

If you find this useful, please ⭐ **star the repo** — it helps more Obsidian users discover it.

---

## 🔒 Permissions & Privacy
- **Local-First**: Your notes are stored locally on your machine.
- **No Private Data Uploads**: Only video titles, descriptions, and transcripts are sent to the Gemini API for summarization; no personal account data is ever shared.
- **Permissions**: Ensure your Terminal app has "Full Disk Access" or permission to access your "Documents" folder on macOS.

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

---

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.
