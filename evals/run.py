"""Run the real embedding model against a tiny synthetic retrieval dataset."""
import json
import tempfile
from pathlib import Path

from app.core import DocumentService, SemanticEmbedder


def main():
    root = Path(__file__).resolve().parents[1]
    cases = json.loads((root / "evals/cases.json").read_text())
    with tempfile.TemporaryDirectory() as directory:
        service = DocumentService(Path(directory) / "evaluation.sqlite3", SemanticEmbedder())
        service.ingest("handbook.txt", (root / "examples/handbook.txt").read_bytes())
        probe = "A document has several sections with searchable information. " * 100
        chunks = service.embedder.chunks([(1, probe)])
        covered = set()
        for chunk in chunks:
            token_count = len(service.embedder.model.tokenizer.encode(chunk["text"]))
            assert token_count <= service.embedder.model.max_seq_length
            covered.update(range(chunk["start"], chunk["end"]))
        assert covered == set(range(len(probe)))
        results = []
        for case in cases:
            sources = service.retrieve(case["question"], None, top_k=2)
            found = any(case["expected_text"] in source["text"] for source in sources)
            results.append({"question": case["question"], "expected_text_found_in_top_2": found,
                            "scores": [round(source["score"], 4) for source in sources]})
        report = {"model": service.embedder.name, "cases": results,
                  "pass_count": sum(item["expected_text_found_in_top_2"] for item in results),
                  "total": len(results), "token_budget_and_coverage_check": "passed", "scope": "Tiny synthetic retrieval smoke evaluation; not an answer-quality benchmark."}
        output = root / "evals/latest-results.json"
        output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        if report["pass_count"] != report["total"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
