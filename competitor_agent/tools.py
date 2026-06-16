"""Research tools available to the agent.

Two kinds of retrieval are provided:
  • web_search        — live web search via Tavily.
  • fetch_document    — read a single web page or PDF in full by URL.
  • search_local_docs — retrieve relevant passages from local files (.txt/.md/.pdf)
                        in DOCS_DIR (default: ./docs).

This satisfies "web search AND document retrieval tools". Engineers can register
additional LangChain tools or custom MCP integrations by appending to RESEARCH_TOOLS.
"""
from __future__ import annotations

import glob
import io
import os
import pathlib
import re
from typing import List

from langchain_core.tools import tool

try:
    from tavily import TavilyClient
except Exception:  # pragma: no cover
    TavilyClient = None


# --------------------------------------------------------------------------- #
# Web search (Tavily)
# --------------------------------------------------------------------------- #
def _client() -> "TavilyClient":
    if TavilyClient is None:
        raise RuntimeError("tavily-python is not installed. `pip install tavily-python`.")
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        raise RuntimeError("TAVILY_API_KEY is not set. Add it to your environment/.env.")
    return TavilyClient(api_key=key)


@tool
def web_search(query: str, max_results: int = 5) -> dict:
    """Search the web for recent, factual information.

    Returns a dict with an `answer` (Tavily's synthesized summary) and a list of
    `results`, each with title, url and a content snippet. Use this to find pricing,
    features, positioning and recent news about a company or product.
    """
    client = _client()
    resp = client.search(query=query, max_results=max_results,
                          search_depth="advanced", include_answer=True)
    results = [
        {"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")}
        for r in resp.get("results", [])
    ]
    return {"answer": resp.get("answer", ""), "results": results}


# --------------------------------------------------------------------------- #
# Document retrieval: fetch a single document by URL
# --------------------------------------------------------------------------- #
@tool
def fetch_document(url: str, max_chars: int = 6000) -> dict:
    """Fetch a web page or PDF by URL and return its extracted plain text.

    Use this to read a specific source document (article, datasheet, SEC filing,
    pricing page) in full, rather than relying on a short search snippet.
    """
    try:
        import requests
        resp = requests.get(url, timeout=20,
                            headers={"User-Agent": "Mozilla/5.0 (competitor-research-agent)"})
        resp.raise_for_status()
    except Exception as e:
        return {"url": url, "text": "", "error": str(e)}

    ctype = resp.headers.get("content-type", "").lower()
    if "pdf" in ctype or url.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(resp.content))
            text = "\n".join((pg.extract_text() or "") for pg in reader.pages)
        except Exception as e:
            return {"url": url, "text": "", "error": f"pdf parse failed: {e}"}
    else:
        text = resp.text
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
        except Exception:
            text = re.sub(r"<[^>]+>", " ", text)  # crude fallback if bs4 missing

    text = re.sub(r"\s+", " ", text).strip()
    return {"url": url, "text": text[:max_chars]}


# --------------------------------------------------------------------------- #
# Document retrieval: lexical search over local files
# --------------------------------------------------------------------------- #
def _read_text_from_file(path: str) -> str:
    ext = pathlib.Path(path).suffix.lower()
    if ext in (".txt", ".md"):
        try:
            return pathlib.Path(path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(path)
            return "\n".join((pg.extract_text() or "") for pg in reader.pages)
        except Exception:
            return ""
    return ""


def _tokenize(text: str) -> list:
    return [t for t in re.findall(r"\w+", text.lower()) if len(t) > 1]


def _collect_chunks(docs_dir: str):
    """Read every file in docs_dir and split into (source, text) passages.

    The folder's own instructional README is skipped so it doesn't compete with
    real reference material during retrieval.
    """
    chunks = []
    for path in glob.glob(os.path.join(docs_dir, "**", "*"), recursive=True):
        if not os.path.isfile(path):
            continue
        if os.path.basename(path).lower() in ("readme.md", "readme.txt", "readme"):
            continue
        text = _read_text_from_file(path)
        if not text:
            continue
        for chunk in re.split(r"\n\s*\n", text):
            chunk = chunk.strip()
            if len(chunk) >= 40:
                chunks.append((os.path.basename(path), chunk))
    return chunks


@tool
def search_local_docs(query: str, max_chunks: int = 4) -> dict:
    """Retrieve the most relevant passages from local documents in DOCS_DIR (./docs).

    Reads .txt, .md and .pdf files, splits them into passages, and ranks them against
    the query with BM25 (a standard relevance model: rare query terms weigh more and
    passage length is normalized). Falls back to keyword-frequency scoring if the
    rank-bm25 package is unavailable. Use this to ground the analysis in user-provided
    files such as analyst reports, datasheets, or prior research.
    """
    docs_dir = os.environ.get("DOCS_DIR", "docs")
    if not os.path.isdir(docs_dir):
        return {"chunks": [], "note": f"no docs directory at '{docs_dir}'", "ranker": "none"}

    chunks = _collect_chunks(docs_dir)
    if not chunks:
        return {"chunks": [], "note": f"no readable passages in '{docs_dir}'", "ranker": "none"}

    q_tokens = _tokenize(query)
    qset = set(q_tokens)
    corpus = [_tokenize(text) for _, text in chunks]
    ranker = "bm25"
    try:
        from rank_bm25 import BM25Okapi
        bm25 = BM25Okapi(corpus)
        scores = list(bm25.get_scores(q_tokens))
    except Exception:
        ranker = "keyword-frequency (rank-bm25 not installed)"
        terms = [t for t in q_tokens if len(t) > 2]
        scores = [sum(text.lower().count(t) for t in terms) for _, text in chunks]

    # Rank passages that share at least one query term. (Overlap filter, not a
    # positive-score cutoff: BM25 IDF can go negative on a very small corpus.)
    cand = [(sc, src, text) for sc, (src, text), toks in zip(scores, chunks, corpus)
            if qset & set(toks)]
    cand.sort(key=lambda x: x[0], reverse=True)
    top = [(src, text) for _, src, text in cand][:max_chunks]
    return {
        "chunks": [{"source": s, "text": c[:800]} for s, c in top],
        "note": f"{len(top)} of {len(chunks)} passage(s) from '{docs_dir}' via {ranker}",
        "ranker": ranker,
    }


# Engineers: append custom MCP-backed or API-backed tools here.
RESEARCH_TOOLS: List = [web_search, fetch_document, search_local_docs]
