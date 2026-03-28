#!/bin/bash

# GEMINI_API_KEY is now loaded from .env automatically by the scripts.
# See .env.example for setup.

# Run the sync script using uv (automatically handles virtual environment and dependencies)
uv run "$(dirname "$0")/sync.py" "$@"