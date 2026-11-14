# Verification — 14 November 2026

## Automated checks

- Python backend suite: **10 passed** in the local development environment.
- `python -m pip check`: no broken requirements for the installed project environment.
- Deterministic tests isolate provider failures using doubles; the real-provider checks below are separate evidence.
- GitHub Actions runs the backend suite on Python 3.11 without requiring model weights or credentials.

## Real-provider checks

- Real all-MiniLM-L6-v2 embeddings: 3/3 synthetic retrieval smoke cases passed.
- Token-budget and complete-text-coverage checks passed.
- Real Ollama Qwen2.5 1.5B: returned “24 days” for the synthetic leave-policy question, with a citation and exact source quote validated by code.
- Flutter analysis, evidence-view widget test, and native macOS debug build previously passed; backend changes retain that API contract.

## Scope

This is a runnable single-user local portfolio implementation. Smoke checks on synthetic/public data are not a production-readiness claim, a general quality benchmark, or proof that an AI output is always correct. See README for supported formats, runtime dependencies and operational boundaries.
