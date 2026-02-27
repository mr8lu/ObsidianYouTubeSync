#!/bin/bash

# GEMINI_API_KEY is now loaded from .env automatically by the scripts.
# See .env.example for setup.

# Activate virtual environment
source "$(dirname "$0")/venv/bin/activate"

# Run the sync script with any provided arguments (e.g., --init or --incremental)
python3 "$(dirname "$0")/sync.py" "$@"
