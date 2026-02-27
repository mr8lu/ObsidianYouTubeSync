# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
- Updated `run.sh` to remove hardcoded API keys in favor of `.env` files.
- Optimized tag generation prompts to focus on broad-to-specific hierarchical classification.
