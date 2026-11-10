# Document Assistant with RAG

A personal AI/mobile engineering project by [Harshad Odakkal](https://github.com/harshadok).

**Current milestone: runnable local document retrieval API and Flutter client.** Upload a text document or text PDF, persist its semantic embeddings, ask a question, and inspect the retrieved passages with page references. Optional local LLM generation is integrated through Ollama. There is no cloud inference dependency or paid API key requirement.

## What is implemented

- UTF-8 TXT/Markdown and selectable-text PDF ingestion.
- Paragraph-aware, page-aware, tokenizer-aware chunks with overlap for long paragraphs and character offsets.
- Local `all-MiniLM-L6-v2` sentence embeddings.
- A persistent SQLite vector store with exact cosine search over normalized vectors using NumPy. This is a small-data implementation, not a dedicated approximate-nearest-neighbour engine.
- All-document or explicitly scoped retrieval, source text, page numbers, and request-local citation IDs.
- Flutter document upload, library, scope selection, questions, evidence cards, and deletion confirmation.
- Optional Ollama answer generation with JSON output validation and rejection of unknown citation IDs.
- Tests for persistence, document scoping, deletion, chunk coverage, input errors, embedding failures, and generation failures.
- A reproducible three-question synthetic retrieval evaluation using the real embedding model.

## Run the backend

Python 3.9+ is supported by the dependency ranges; this checkout was developed using Python 3.9.6. A newer supported Python release is preferable for ongoing work.

```sh
cd document-assistant-rag
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The first startup downloads the embedding model from Hugging Face. Model loading/inference happens on the backend computer, not on the phone. Subsequent runs can reuse the cached model; an uncached first run needs internet. Documents stay in `data/documents.sqlite3`, which is excluded from Git. Uploaded originals are not retained, but extracted text and embeddings are persisted.

On subsequent runs you can also start the server with `./scripts/start-backend.sh`. Set `RAG_PORT` to use a different port.

Open [interactive API docs](http://127.0.0.1:8000/docs) once the server reports that startup is complete.

### First document and question

In a second terminal, from the repository root:

```sh
curl -F 'file=@examples/handbook.txt' http://127.0.0.1:8000/documents
curl http://127.0.0.1:8000/documents
curl -X POST http://127.0.0.1:8000/questions \
  -H 'Content-Type: application/json' \
  -d '{"question":"How many paid vacation days do employees get?","generate":false}'
```

With `generate=false`, the API returns **retrieved passages**, not a synthesized answer. The response makes this explicit with `mode: retrieval_only` and `answer: null`.

To restrict a question to a document, include `"document_ids":["ID_RETURNED_BY_UPLOAD"]`. Omit the field or set it to `null` to search all documents; an empty list searches none. `min_score` defaults to `0.30` and is a retrieval heuristic, not a calibrated confidence score. No matching passages returns `mode: insufficient_evidence`.

## Run the Flutter client

```sh
cd mobile
flutter pub get
flutter run -d macos
```

The generated project includes macOS, Android, and iOS targets. The default backend address is `127.0.0.1:8000` for macOS/iOS Simulator and `10.0.2.2:8000` for Android Emulator. Debug Android builds permit local HTTP; release hosting should use HTTPS. The macOS entitlements allow outbound network access and user-selected read-only files.

For a different backend address:

```sh
flutter run --dart-define=API_BASE_URL=http://YOUR_SERVER:8000
```

A physical phone cannot use your computer's `127.0.0.1`. Physical-device LAN networking, signing, and file-picker behaviour still require device testing. This prototype is single-user and has no authentication: keep the backend bound to localhost during normal development. Do not expose it publicly or put private documents into a shared server.

## Optional local answer generation

Install Ollama separately, download a model suitable for your computer, and ensure its local server is running. Then start this API with the exact name of an installed model:

```sh
export OLLAMA_MODEL='YOUR_INSTALLED_MODEL_NAME'
# Optional; this is already the default:
export OLLAMA_BASE_URL='http://127.0.0.1:11434'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Turn on **Generate an answer with local AI** in the client, or pass `"generate":true` to `/questions`. No automatic model download is performed for Ollama. Without `OLLAMA_MODEL`, requesting generation returns a clear 503 error. Invalid model output or an unavailable local model returns 502.

The model is instructed to answer from source passages and return citation IDs. Citation validation only confirms that IDs exist; it does **not** prove that the answer is faithful. Review answers against the displayed evidence. Document prompt injection and hallucinations remain possible. No real Ollama inference result is claimed unless separately recorded in evaluation results.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Model name and generation configuration status |
| POST | `/documents` | Multipart file upload; extraction/embedding runs before `201 ready` |
| GET | `/documents` | List persisted documents and chunk counts |
| DELETE | `/documents/{id}` | Remove document text and its vectors |
| POST | `/questions` | Retrieve passages and optionally generate a local answer |

Uploads are synchronous in this milestone. There is no ingestion queue or separate upload-status endpoint yet.

## Tests and evaluation

```sh
source .venv/bin/activate
python -m pytest -q
python -m evals.run
cd mobile
flutter analyze
flutter test
```

The API tests use deterministic embedding doubles to isolate correctness. `python -m evals.run` uses the actual embedding model and writes `evals/latest-results.json`. Its three fictional handbook questions are only a retrieval smoke check, not a claim of production accuracy or generated answer quality. Flutter's widget test covers asking a question and showing source evidence without presenting it as generated text.

## Verified development results

- Backend test suite: **8 passed**.
- Real embedding model: **3/3 synthetic retrieval smoke cases passed** after paragraph-aware chunking; token-budget and text-coverage checks passed. See [recorded results](evals/latest-results.json).
- Flutter analysis: **no issues found**.
- Flutter evidence-view widget test: **passed**.
- Native macOS debug build: **succeeded**.
- Actual Ollama answer generation and physical mobile-device operation: **not tested in this session**.

These checks establish a working development baseline, not production readiness or a general accuracy benchmark.

## Architecture and source map

```text
Flutter upload/question interface
        |
        v
FastAPI -> extraction -> overlapping chunks -> local sentence embeddings
        |                                           |
        +---------------- SQLite text + vector store
        |
question -> embedding -> exact cosine retrieval -> source cards
                                      |
                                      +-> optional local Ollama -> validated citations
```

- `app/core.py`: parsing, chunking, embeddings, storage, retrieval, optional generation.
- `app/main.py`: input validation and HTTP endpoints.
- `mobile/lib/main.dart`: Flutter library, uploads, questions, and evidence view.
- `tests/`: backend correctness and failure-path tests.
- `examples/handbook.txt`: synthetic demo data.
- `evals/`: real-model retrieval smoke evaluation and results.
- `requirements.txt`: portable dependency ranges.
- `requirements-lock.txt`: installed versions from this development environment, when present.

## Current limits and next milestones

- 10 MB uploads, 100 PDF pages, 500,000 extracted characters. Scanned PDF OCR is not implemented. Empty, invalid, or encrypted PDFs are rejected.
- Chunking uses the embedding model's tokenizer budget with overlap to avoid silently truncating long passages. Retrieval quality still needs testing on diverse document types.
- Exact search loads matching vectors into memory, suitable for a small personal collection. Larger collections need indexing and pagination.
- SQLite storage is not encrypted by this app. Multi-user authentication, ownership enforcement, encrypted storage, background ingestion, and deployment are not implemented.
- Semantic similarity alone cannot reliably detect every unanswerable question. Threshold calibration, a broader held-out dataset, grounded-answer evaluation, and reranking are next milestones.
- Flutter analysis/widget tests and backend tests do not replace a native build or physical-device testing.

## Technical references

Implementation follows the primary documentation for [FastAPI file uploads](https://fastapi.tiangolo.com/tutorial/request-files/), [SentenceTransformer embeddings](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html), and [Ollama's chat API](https://github.com/ollama/ollama/blob/main/docs/api.md).
