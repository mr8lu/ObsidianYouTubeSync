# YouTube History Sync Tool

This tool automatically fetches your YouTube watch history and synchronizes it into your Obsidian Vault. It extracts the video transcription, summarizes the video, generates tags using Google Gemini API, and saves standard Markdown files tailored for Obsidian.

## Prerequisites

1. Python 3: Make sure you have Python 3 installed.
2. Google Gemini API Key: You'll need to obtain a free Gemini API key to run processing.

## Setup

First, activate a virtual environment and install the required dependencies.

```bash
# 1. Create a virtual environment (if not already created)
python3 -m venv venv

# 2. Activate the virtual environment
source venv/bin/activate

# 3. Install requirements
pip install -r requirements.txt
```

*(Note: `run.sh` automatically attempts to activate `venv/bin/activate` in the script directory.)*

## Configuration

1. **API Key**: Create a `.env` file in the root directory and add your Google Gemini API key:
   ```bash
   echo "GEMINI_API_KEY=your_actual_key_here" > .env
   ```
   Alternatively, copy the example file: `cp .env.example .env` and fill in your key.

2. **Vault Path**: Ensure `OBSIDIAN_VAULT_PATH` in `sync.py` and `retag_notes.py` points to your local Obsidian Vault.

## Usage

### Syncing YouTube History
Run the script via `run.sh`. Ensure you have Chrome cookies logged into YouTube for `yt-dlp` to fetch history.

**Incremental Sync (Typical Use):**
```bash
./run.sh --incremental
```

**Full Initialization:**
```bash
./run.sh --init
```

**Re-tagging existing YouTube notes (Taxonomy update):**
```bash
./run.sh --retag
```

### Re-tagging Other Folders (Apple Notes, etc.)
Use `retag_notes.py` to apply the global taxonomy/keywords to any folder in your vault.

```bash
# Preview changes (Dry Run)
python3 retag_notes.py --dry-run

# Process default (Apple Notes)
python3 retag_notes.py

# Process specific folder
python3 retag_notes.py --folder "/Users/[user name]/Documents/Obsidian Vault/Books"
```

## Features
- **Global Taxonomy**: Shared consistent tagging across different content types.
- **Multi-threading**: Fast parallel processing using `ThreadPoolExecutor`.
- **Shorts Detection**: Automatically skips YouTube Shorts to focus on standard videos.
- **Orphan Support**: Injects frontmatter into notes that don't have it.
- **Keyword Extraction**: LLM-driven informative keywords merged into tag properties.

## Permissions

The tool tests write access to your `OBSIDIAN_VAULT_PATH` early on. On macOS, ensure your Terminal app has "Full Disk Access" or access to your "Documents" folder.
