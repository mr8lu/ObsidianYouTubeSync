# Setup Guide

This guide will walk you through the process of setting up ObsidianYouTubeSync on your machine.

## Prerequisites

Before starting, ensure you have the following installed:

1. **Python 3.10+**: Requires a modern Python environment.
2. **uv**: We recommend using `uv` (Fast Python Package Manager) to manage dependencies. [Installation Guide](https://docs.astral.sh/uv/getting-started/installation/)
3. **Google Gemini API Key**: Free tier available at [Google AI Studio](https://aistudio.google.com/).
4. **Browser logged into YouTube**: Chrome, Safari, or Firefox needs to be logged in, allowing `yt-dlp` to access your watch history.
5. **Obsidian** (Optional): Highly recommended for visualizing and using Dataview queries.

## Installation

1. **Clone the repository**

```bash
git clone https://github.com/mr8lu/ObsidianYouTubeSync.git
cd ObsidianYouTubeSync
```

2. **Set up the Python environment using `uv`**

```bash
uv sync
```

## Configuration

1. **Copy the example environment file:**

```bash
cp .env.example .env
```

2. **Edit `.env` with your credentials:**

Add your Gemini API Key. You can also optionally configure Webshare rotating proxies if you are planning on doing extremely large history syncs.

```env title=".env"
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Webshare rotating proxy
WEBSHARE_PROXY_USER=your_proxy_user
WEBSHARE_PROXY_PASS=your_proxy_password
```

!!! warning "Important — Vault Path"
    The default target directory for output is `~/Documents/Obsidian Vault`. **You must update `OBSIDIAN_VAULT_PATH` in `sync.py` and `retag_notes.py` if your vault lives elsewhere** before running any syncs.

## Verifying the Setup

You are now ready to start using the tools! Proceed to the [Usage Guide](usage.md).
