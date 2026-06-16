"""Diagnose local-document retrieval. Run from the project root:

    python diagnose_docs.py
"""
import os, glob, importlib.util
from collections import Counter

docs = os.environ.get("DOCS_DIR", "docs")
print("=" * 60)
print("cwd:            ", os.getcwd())
print("DOCS_DIR:       ", docs, "->", os.path.abspath(docs))
print("docs exists:    ", os.path.isdir(docs))
print("pypdf installed:", importlib.util.find_spec("pypdf") is not None)
print("rank_bm25:      ", importlib.util.find_spec("rank_bm25") is not None)
print("=" * 60)

print("Files in docs/:")
for p in glob.glob(os.path.join(docs, "**", "*"), recursive=True):
    if os.path.isfile(p):
        print(f"  - {p}  ({os.path.getsize(p)} bytes)")

from competitor_agent.tools import _read_text_from_file, _collect_chunks, search_local_docs

print("\nPDF text extraction:")
for p in glob.glob(os.path.join(docs, "**", "*.pdf"), recursive=True):
    t = _read_text_from_file(p)
    flag = "OK" if len(t) > 50 else "EMPTY  <-- scanned image or unreadable"
    print(f"  {os.path.basename(p)}: {len(t)} chars [{flag}]")
    if t:
        print(f"     sample: {t[:120]!r}")

chunks = _collect_chunks(docs)
print(f"\nTotal passages (README excluded): {len(chunks)}")
print("Passages by file:", dict(Counter(s for s, _ in chunks)))

r = search_local_docs.invoke({"query": "Samsung Apple pricing features positioning"})
print("\nRetrieval test (query = 'Samsung Apple pricing features positioning'):")
print("  note:     ", r["note"])
print("  retrieved:", [c["source"] for c in r["chunks"]])
print("=" * 60)
