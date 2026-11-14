#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then
  echo "Create the Python environment first using the setup steps in README.md."
  exit 1
fi
export OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:1.5b}"
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "${RAG_PORT:-8000}"
