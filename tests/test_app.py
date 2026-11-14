import json
import re
from unittest.mock import patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core import DocumentService, chunk_pages, extract_pages, generate_with_ollama
from app.main import create_app


class TestEmbedder:
    """Deterministic test double; semantic model behaviour is checked separately by evals/run.py."""
    __test__ = False
    name = "test-word-vectors-v1"

    def encode(self, texts):
        vocab = ["leave", "equipment", "remote", "approval"]
        vectors = []
        for text in texts:
            words = re.findall(r"\w+", text.lower())
            vector = np.array([words.count(word) for word in vocab], dtype=np.float32)
            vectors.append(vector / (np.linalg.norm(vector) or 1))
        return np.array(vectors)


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "test.sqlite3", TestEmbedder())) as client:
        yield client


def upload(client, text, filename="policy.txt"):
    result = client.post("/documents", files={"file": (filename, text.encode(), "text/plain")})
    assert result.status_code == 201, result.text
    return result.json()["id"]


def test_upload_scope_retrieve_delete_and_persistence(client, tmp_path):
    first = upload(client, "Annual leave is 24 days. Leave requires approval.")
    second = upload(client, "Equipment allowance requires approval.")
    response = client.post("/questions", json={"question": "leave", "document_ids": [first]}).json()
    assert response["mode"] == "retrieval_only"
    assert response["answer"] is None
    assert response["sources"][0]["document_id"] == first
    assert response["sources"][0]["page"] == 1
    assert response["sources"][0]["citation_id"] == "S1"
    assert client.post("/questions", json={"question": "leave", "document_ids": [second]}).json()["sources"] == []
    assert client.post("/questions", json={"question": "leave", "document_ids": []}).json()["sources"] == []
    # A newly constructed service reads the same committed records.
    service = DocumentService(tmp_path / "test.sqlite3", TestEmbedder())
    assert len(service.documents()) == 2
    assert client.delete("/documents/" + first).status_code == 200
    assert service.retrieve("leave", [first]) == []
    with service.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM chunks WHERE document_id=?", (first,)).fetchone()[0] == 0
    assert client.delete("/documents/" + first).status_code == 404


def test_refusal_and_validation(client, monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    upload(client, "leave policy")
    assert client.post("/questions", json={"question": "volcano"}).json()["mode"] == "insufficient_evidence"
    assert client.post("/questions", json={"question": "leave", "generate": True}).status_code == 503
    assert client.post("/questions", json={"question": "   "}).status_code == 422
    assert client.post("/questions", json={"question": "leave", "top_k": 0}).status_code == 422
    assert client.post("/documents", files={"file": ("bad.exe", b"hello")}).status_code == 422
    assert client.post("/documents", files={"file": ("empty.txt", b" ")}).status_code == 422
    assert client.post("/documents", files={"file": ("binary.txt", b"\xff")}).status_code == 422
    assert client.post("/documents", files={"file": ("bad.pdf", b"not a PDF")}).status_code == 422


def test_chunk_coverage_and_page_metadata():
    text = "abc def " * 300
    chunks = chunk_pages([(7, text)], size=120, overlap=20)
    covered = set()
    for chunk in chunks:
        assert chunk["page"] == 7
        assert text[chunk["start"]:chunk["end"]] == chunk["text"]
        covered.update(range(chunk["start"], chunk["end"]))
    assert covered == set(range(len(text)))
    with pytest.raises(ValueError):
        chunk_pages([(1, text)], size=10, overlap=10)


def test_file_size_and_model_mismatch(tmp_path):
    with pytest.raises(ValueError):
        extract_pages("big.txt", b"a" * (10 * 1024 * 1024 + 1))
    db = tmp_path / "index.sqlite3"
    DocumentService(db, TestEmbedder())
    other = TestEmbedder()
    other.name = "a-different-model"
    with pytest.raises(ValueError, match="Embedding model differs"):
        DocumentService(db, other)


def test_embedding_failure_does_not_store_partial_document(tmp_path):
    embedder = TestEmbedder()
    service = DocumentService(tmp_path / "index.sqlite3", embedder)
    with patch.object(embedder, "encode", side_effect=RuntimeError("provider down")):
        with pytest.raises(RuntimeError):
            service.ingest("policy.txt", b"leave policy")
    assert service.documents() == []


def test_unknown_generated_citations_rejected():
    from io import BytesIO

    fake = {"message": {"content": json.dumps({"answer": "Invented", "citations": ["S99"]})}}
    with patch("urllib.request.urlopen", return_value=BytesIO(json.dumps(fake).encode())):
        with pytest.raises(ValueError, match="unknown citations"):
            generate_with_ollama("leave?", [{"citation_id": "S1", "text": "24 days"}], "fake", "http://localhost")


def test_pdf_extraction_preserves_real_page_reference(client):
    from io import BytesIO
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

    writer = PdfWriter()
    writer.add_blank_page(width=600, height=800)
    page = writer.add_blank_page(width=600, height=800)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                             NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 50 700 Td (Annual leave is 24 days.) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = BytesIO()
    writer.write(buffer)
    response = client.post("/documents", files={"file": ("policy.pdf", buffer.getvalue(), "application/pdf")})
    assert response.status_code == 201
    result = client.post("/questions", json={"question": "leave"}).json()
    assert result["sources"][0]["page"] == 2
    assert "24 days" in result["sources"][0]["text"]


def test_generated_answer_and_model_failure(client, monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "test-model")
    upload(client, "Annual leave is 24 days.")
    with patch("app.main.generate_with_ollama", return_value={"answer": "24 days", "citations": ["S1"]}):
        response = client.post("/questions", json={"question": "leave", "generate": True})
        assert response.status_code == 200
        assert response.json()["mode"] == "generated"
    with patch("app.main.generate_with_ollama", side_effect=OSError("offline")):
        assert client.post("/questions", json={"question": "leave", "generate": True}).status_code == 502


def test_fabricated_evidence_is_rejected():
    from io import BytesIO
    fake = {'message': {'content': json.dumps({'answer': '24 days', 'citations': ['S1'], 'evidence': [{'source_id': 'S1', 'quote': 'A fabricated supporting passage'}]})}}
    with patch('urllib.request.urlopen', return_value=BytesIO(json.dumps(fake).encode())):
        with pytest.raises(ValueError, match='does not occur'):
            generate_with_ollama('leave?', [{'citation_id': 'S1', 'text': 'Annual leave is 24 days.'}], 'fake', 'http://localhost')


def test_valid_generated_evidence_passes():
    from io import BytesIO
    fake = {'message': {'content': json.dumps({'answer': '24 days', 'citations': ['S1'], 'evidence': [{'source_id': 'S1', 'quote': 'Annual leave is 24 days.'}]})}}
    with patch('urllib.request.urlopen', return_value=BytesIO(json.dumps(fake).encode())):
        result = generate_with_ollama('leave?', [{'citation_id': 'S1', 'text': 'Annual leave is 24 days.'}], 'fake', 'http://localhost')
        assert result['citations'] == ['S1']
