# Contributing to YouTubeSyncTool

Thank you for your interest in contributing! This project is designed to work for the Obsidian/PKM community — all contributions that improve the experience are welcome.

## Getting Started

1. **Fork** the repository and clone your fork locally.
2. **Create a virtual environment** and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Create a `.env` file** with your API key:
   ```bash
   cp .env.example .env
   # Then fill in your GEMINI_API_KEY
   ```
4. **Test the tool**:
   ```bash
   ./run.sh --test
   ```

## How to Contribute

- **Bug Fixes**: Open an issue first describing the bug, then submit a PR referencing it.
- **New Features**: Open a feature request issue first to discuss the idea before writing code.
- **Taxonomy Improvements**: Edit `taxonomy.py` and open a PR — community input on the tag hierarchy is especially welcome.
- **Documentation**: Improving the README or adding examples is always appreciated.

## Pull Request Guidelines

- Keep PRs focused on a single change.
- Update `CHANGELOG.md` under `[Unreleased]` with a short description of your change.
- Ensure Python code is compatible with Python 3.10+.

## Code Style

- Standard Python conventions (PEP 8).
- Use f-strings, type hints, and Pydantic models where applicable.

## Community

- Obsidian Discord: [join here](https://discord.gg/obsidianmd)
- r/ObsidianMD: [reddit.com/r/ObsidianMD](https://reddit.com/r/ObsidianMD)
