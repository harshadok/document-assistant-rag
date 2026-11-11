"""Lesson 1: turn a document's bytes into readable, page-labelled text.

Run from the repository root:
    python -m lessons.document_processing
    python -m lessons.document_processing /absolute/path/to/a/document.pdf
"""
import argparse
from pathlib import Path

from app.core import extract_pages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", type=Path, default=Path("examples/handbook.txt"))
    args = parser.parse_args()

    # 1. A file is raw bytes before we interpret its contents.
    try:
        content = args.file.read_bytes()
        # 2. Reuse our app's parser to decode text or extract text from PDF pages.
        pages = extract_pages(args.file.name, content)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Could not process document: {error}\n")

    # 3. Preserve page numbers so later answers can point back to their source.
    print(f"File: {args.file.name}")
    print(f"Bytes read: {len(content)}")
    print(f"Pages: {len(pages)}")
    for number, text in pages:
        print(f"\n--- Page {number}: {len(text)} characters ---")
        print(text)


if __name__ == "__main__":
    main()
