# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Created `mcp_server.py` implementing a native Model Context Protocol (MCP) server via `FastMCP` to allow agentic systems to autonomously run the sync and retagging tools.
- Added `mcp` SDK to dependencies.
- Added `CONTRIBUTING.md` with setup instructions, contribution guidelines, and PR etiquette.
- Added `.github/ISSUE_TEMPLATE/bug_report.md` structured bug report template.
- Added `.github/ISSUE_TEMPLATE/feature_request.md` structured feature request template.
- Added **Sample Output Note** section to `README.md` showing a real example of a generated Obsidian note.
- Added **Roadmap** table to `README.md` listing completed and upcoming features.
- Added **Compatibility** table to `README.md` covering macOS, Linux, Python, and browser support.
- Added `python-dotenv`, `tenacity`, and `requests` to `requirements.txt` (were used in code but missing from the manifest).

### Changed
- Revamped `README.md` with improved SEO-focused title, badges, and structured sections targeting the Obsidian/PKM community.
- Updated `.gitignore` to explicitly allow `.github/ISSUE_TEMPLATE/` and `CONTRIBUTING.md` while keeping `PROMOTION.md` local-only.

## [1.0.0] - 2026-02-27
### Added
- Added GitHub Dependabot configuration (`.github/dependabot.yml`) for automated dependency updates.
- Created `retag_notes.py` script to apply taxonomy-consistent tagging to any Obsidian folder (e.g., Apple Notes).
- Added multi-threading support to both `sync.py` and `retag_notes.py` using `ThreadPoolExecutor`.
- Added configurable `THREAD_POOL_SIZE` for parallel processing.
- Integrated `python-dotenv` for secure environment variable management via `.env` file.
- Added YouTube Shorts detection in `sync.py` using lightweight HEAD requests to skip non-video content.
- Added free-form `keywords` generation to Gemini prompts, which are merged into the Obsidian `tags:` property for enhanced searchability.
- Added `.gitignore` to exclude sensitive data, environment files, and junk.
- Initialized Git repository.

### Fixed
- Fixed taxonomy normalizer to support CJK characters in dynamic entity tags (e.g., `Person/查尼`).
- Fixed "bare entity" bug where root prefixes like `Person` or `Company` were incorrectly categorized as `Other/Uncategorized`.
- Improved keyword sanitizer to correctly handle word boundaries and CamelCase conversion (e.g., "neural network" -> "NeuralNetwork").

### Changed
- Refactored absolute file paths to use dynamic relative paths (`os.path.expanduser('~')`) for improved portability across different environments.
- Scrubbed hardcoded system username occurrences from repository files and history.
- Updated `run.sh` to remove hardcoded API keys in favor of `.env` files.
- Optimized tag generation prompts to focus on broad-to-specific hierarchical classification.
