# Document Assistant with RAG

**Status: Planning / documentation only.** This repository currently contains a project specification and implementation roadmap. No working application, provider integration, deployment, or measured results are included yet.

A personal learning project by [Harshad Odakkal](https://github.com/harshadok), building on professional Flutter and mobile engineering experience while transitioning toward AI/mobile engineering.

## Problem and goal

Help users ask questions about their documents and receive answers grounded in retrieved passages with source references.

## Skills to practise

- Retrieval-Augmented Generation (RAG)
- Document processing and chunking
- Embeddings
- Vector databases
- Retrieval and source-grounded responses

## Planned end-to-end workflow

1. Upload a supported document and assign an owner and document ID.
2. Extract text and retain page or section metadata.
3. Split text into overlapping chunks and generate embeddings.
4. Store vectors and metadata in a vector database.
5. Embed a question and retrieve relevant chunks within the user’s document scope.
6. Generate an answer using retrieved context and show source passages; abstain when evidence is insufficient.

## Proposed architecture

Flutter client; Python API service; document parser; embedding and LLM provider adapters; vector database adapter.

The stack is a design proposal. Specific providers, libraries, model versions, and database products will be selected and documented during implementation.

## Planned API surface

- `POST /documents` — submit a document for processing
- `GET /documents/{id}/status` — inspect ingestion status
- `POST /questions` — ask a question over selected documents
- `DELETE /documents/{id}` — delete source text, metadata, and vectors

These endpoints are proposed contracts; they are not implemented.

## Core data model

Document(id, owner_id, filename, status); Chunk(id, document_id, page, text, embedding_ref); Answer(text, citations, retrieval_trace).

## Flutter/mobile experience

Document upload, ingestion progress, document library, chat screen, and tappable source citations.

## Evaluation and acceptance plan

- [ ] Test chunk boundaries and preservation of source metadata.
- [ ] Measure retrieval recall on a small hand-labelled question-and-passage dataset.
- [ ] Check answer grounding, citation correctness, and refusal for unanswerable questions.
- [ ] Verify one user cannot retrieve another user’s documents.
- [ ] Check that deletion removes source material and associated vectors.

No accuracy, latency, cost, or reliability results have been measured. Results will be added only after reproducible runs.

## Implementation roadmap

- [ ] **Milestone 1:** Build text extraction for one document format and inspect sample chunks.
- [ ] **Milestone 2:** Connect embeddings and vector storage; implement scoped similarity retrieval.
- [ ] **Milestone 3:** Add grounded generation and page-level citations.
- [ ] **Milestone 4:** Build the Flutter upload and question-answering screens.
- [ ] **Milestone 5:** Run a documented evaluation dataset and publish measured results.

## Planned demonstration

Upload a synthetic handbook, ask a question with a known answer, inspect the cited passage, then ask an unsupported question and show an evidence-insufficient response.

## Data and operational boundaries

Treat uploaded text as untrusted context, preserve document ownership filters, and do not put private document contents into logs.

## Getting started today

1. Read the proposed workflow and choose the first milestone.
2. Decide on providers and local development tools; record those decisions before implementation.
3. Add application code and a reproducible setup guide as the first milestone is built.
4. Use synthetic or public test data and keep credentials outside version control.

**There is no runnable quick start yet.** Installation and run commands will be added when code exists.

## Suggested future layout

```text
apps/mobile/        # Planned Flutter client
services/api/       # Planned application API
evals/              # Planned fixtures and evaluation runs
docs/               # Architecture decisions and demonstration notes
```

These directories describe the intended structure and have not been implemented.

## Portfolio context

This is an independent planned portfolio project, not client work or a production deployment. Its current scope is documentation; update the status and roadmap as working milestones are completed.
