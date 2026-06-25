#!/usr/bin/env python3
"""Extract text from an earnings/report PDF for equity research preflight."""

from __future__ import annotations

import argparse
import sys
import tempfile
import urllib.request
from pathlib import Path


def load_pdf(source: str) -> Path:
    if source.startswith(("http://", "https://")):
        handle = tempfile.NamedTemporaryFile(prefix="wser-pdf-", suffix=".pdf", delete=False)
        handle.close()
        req = urllib.request.Request(source, headers={"User-Agent": "wall-street-equity-research/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp, open(handle.name, "wb") as out:
            out.write(resp.read())
        return Path(handle.name)
    path = Path(source).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    return path


def extract_with_pypdf(path: Path, max_pages: int | None) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = reader.pages[:max_pages] if max_pages else reader.pages
    return "\n\n".join((page.extract_text() or "").strip() for page in pages).strip()


def extract_with_pdfplumber(path: Path, max_pages: int | None) -> str:
    import pdfplumber

    chunks: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        pages = pdf.pages[:max_pages] if max_pages else pdf.pages
        for page in pages:
            chunks.append((page.extract_text() or "").strip())
    return "\n\n".join(chunks).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract text from a local or remote PDF.")
    parser.add_argument("pdf", help="Local PDF path or HTTP(S) URL")
    parser.add_argument("--max-pages", type=int, default=None, help="Optional page limit")
    args = parser.parse_args()

    path = load_pdf(args.pdf)
    errors: list[str] = []
    for name, extractor in (("pypdf", extract_with_pypdf), ("pdfplumber", extract_with_pdfplumber)):
        try:
            text = extractor(path, args.max_pages)
            if text:
                print(text)
                print(f"\n[extracted_with={name} source={path}]", file=sys.stderr)
                return 0
            errors.append(f"{name}: extracted empty text")
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    print("PDF text extraction failed.", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
