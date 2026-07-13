"""
Local RAG knowledge base — sentence-transformers embeddings + Chroma vector store.

Standalone by design: this module does NOT import assistant.py, so ingesting a
folder of PDFs never spins up Whisper / Claude / ElevenLabs. The embedding model
and Chroma client are lazy-loaded on first use.

Pipeline: extract text (PDF page-by-page for exact attribution, or .txt/.md whole)
→ token-aware chunking with overlap → bge embeddings (cosine) → Chroma collection
with per-chunk metadata (title, source file, page) for source attribution.
"""

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).parent
CONFIG_FILE = PROJECT_DIR / "config.json"

# bge-*-en-v1.5 wants this instruction prepended to *queries* only (not passages).
_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

_DEFAULTS = {
    "kb_dir": str(PROJECT_DIR / "knowledge"),
    "kb_store_dir": str(PROJECT_DIR / "kb_store"),
    "kb_collection": "knowledge",
    "kb_embedding_model": "BAAI/bge-base-en-v1.5",
    "kb_chunk_tokens": 400,      # bge-base max seq len is 512 — stay under it
    "kb_chunk_overlap": 60,
    "kb_top_k": 4,
}


def get_config() -> Dict:
    """Read only the kb_* settings from config.json, falling back to defaults."""
    cfg = dict(_DEFAULTS)
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            for k in _DEFAULTS:
                if k in data:
                    cfg[k] = data[k]
        except Exception as e:
            logger.warning(f"Could not read kb config, using defaults: {e}")
    cfg["kb_dir"] = str(Path(cfg["kb_dir"]).expanduser())
    cfg["kb_store_dir"] = str(Path(cfg["kb_store_dir"]).expanduser())
    return cfg


# -----------------------------
# Lazy singletons
# -----------------------------
_embedder = None
_collection = None


def get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        cfg = get_config()
        logger.info(f"Loading embedding model: {cfg['kb_embedding_model']} (once)")
        _embedder = SentenceTransformer(cfg["kb_embedding_model"])
    return _embedder


def get_collection(reset: bool = False):
    global _collection
    if _collection is not None and not reset:
        return _collection
    import chromadb
    cfg = get_config()
    client = chromadb.PersistentClient(path=cfg["kb_store_dir"])
    name = cfg["kb_collection"]
    if reset:
        try:
            client.delete_collection(name)
        except Exception:
            pass
    # Cosine space to match normalized bge embeddings.
    _collection = client.get_or_create_collection(
        name=name, metadata={"hnsw:space": "cosine"}
    )
    return _collection


def _embed(texts: List[str], is_query: bool = False) -> List[List[float]]:
    if is_query:
        texts = [_QUERY_INSTRUCTION + t for t in texts]
    embs = get_embedder().encode(
        texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False
    )
    return embs.tolist()


# -----------------------------
# Text extraction
# -----------------------------
def _extract_pdf(path: Path) -> Tuple[str, List[Tuple[int, str]]]:
    """Return (title, [(page_number, page_text), ...]). Page numbers are 1-based."""
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    title = ""
    try:
        if reader.metadata and reader.metadata.title:
            title = reader.metadata.title.strip()
    except Exception:
        pass
    # arXiv/LaTeX PDFs often carry a figure filename or the arXiv id as the "title".
    # Reject those and fall back to the (descriptive) filename stem.
    low = title.lower()
    if (not title or len(title) < 4 or low.startswith("arxiv:")
            or low.endswith((".eps", ".ps", ".dvi", ".tex", ".pdf", ".fig"))):
        title = ""
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            logger.warning(f"{path.name} p.{i}: extract failed ({e})")
            text = ""
        if text.strip():
            pages.append((i, text))
    return (title or path.stem), pages


def extract_documents(path: Path) -> Tuple[str, List[Tuple[int, str]]]:
    """Dispatch by extension. Non-PDF files are returned as a single page (-1)."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix in (".txt", ".md", ".markdown", ".rst"):
        return path.stem, [(-1, path.read_text(errors="replace"))]
    raise ValueError(f"Unsupported file type: {path.name}")


SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md", ".markdown", ".rst"}


# -----------------------------
# Chunking (token-aware, sentence-boundary preserving)
# -----------------------------
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n{2,}")


def _split_sentences(text: str) -> List[str]:
    text = re.sub(r"[ \t]+", " ", text)
    parts = [s.strip() for s in _SENTENCE_SPLIT.split(text)]
    return [p for p in parts if p]


def _chunk_text(text: str, target_tokens: int, overlap_tokens: int) -> List[str]:
    """Pack sentences into ~target_tokens chunks with token overlap between them."""
    tok = get_embedder().tokenizer

    def ntok(s: str) -> int:
        return len(tok.encode(s, add_special_tokens=False))

    sentences = _split_sentences(text)
    chunks: List[str] = []
    cur: List[str] = []
    cur_tokens = 0

    def flush() -> None:
        nonlocal cur, cur_tokens
        if cur:
            chunks.append(" ".join(cur).strip())

    for sent in sentences:
        n = ntok(sent)
        # A single oversized sentence: flush, then hard-split it by tokens.
        if n > target_tokens:
            flush()
            cur, cur_tokens = [], 0
            ids = tok.encode(sent, add_special_tokens=False)
            step = max(1, target_tokens - overlap_tokens)
            for start in range(0, len(ids), step):
                piece = tok.decode(ids[start:start + target_tokens])
                if piece.strip():
                    chunks.append(piece.strip())
            continue
        if cur_tokens + n > target_tokens and cur:
            flush()
            # Carry a tail of sentences worth ~overlap_tokens into the next chunk.
            tail: List[str] = []
            tail_tokens = 0
            for s in reversed(cur):
                st = ntok(s)
                if tail_tokens + st > overlap_tokens:
                    break
                tail.insert(0, s)
                tail_tokens += st
            cur, cur_tokens = tail, tail_tokens
        cur.append(sent)
        cur_tokens += n

    flush()
    return [c for c in chunks if c.strip()]


# -----------------------------
# Ingest
# -----------------------------
def _file_hash(path: Path) -> str:
    h = hashlib.sha1()
    h.update(path.read_bytes())
    return h.hexdigest()


def ingest_file(path: Path, collection=None) -> Dict:
    """Index one file. Incremental: skips unchanged files, re-indexes changed ones."""
    cfg = get_config()
    collection = collection or get_collection()
    abspath = str(path.resolve())
    fhash = _file_hash(path)

    existing = collection.get(where={"path": abspath})
    existing_ids = existing.get("ids", [])
    if existing_ids:
        metas = existing.get("metadatas", [])
        if metas and all(m.get("file_hash") == fhash for m in metas):
            return {"file": path.name, "status": "up-to-date", "chunks": len(existing_ids)}
        collection.delete(ids=existing_ids)  # changed — drop stale chunks

    title, pages = extract_documents(path)

    ids, docs, metadatas = [], [], []
    chunk_i = 0
    for page_no, page_text in pages:
        for chunk in _chunk_text(page_text, cfg["kb_chunk_tokens"], cfg["kb_chunk_overlap"]):
            ids.append(f"{fhash[:12]}:{chunk_i}")
            docs.append(chunk)
            metadatas.append({
                "path": abspath,
                "source": path.name,
                "title": title,
                "page": int(page_no),   # -1 for non-paginated files
                "file_hash": fhash,
                "chunk_index": chunk_i,
            })
            chunk_i += 1

    if not docs:
        return {"file": path.name, "status": "empty", "chunks": 0}

    embeddings = _embed(docs, is_query=False)
    collection.add(ids=ids, documents=docs, embeddings=embeddings, metadatas=metadatas)
    return {"file": path.name, "status": "indexed", "chunks": len(docs)}


def ingest_path(path: Optional[str] = None, reset: bool = False) -> List[Dict]:
    """Ingest a file or (recursively) every supported file in a folder."""
    cfg = get_config()
    target = Path(path).expanduser() if path else Path(cfg["kb_dir"])
    collection = get_collection(reset=reset)

    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = sorted(p for p in target.rglob("*") if p.suffix.lower() in SUPPORTED_SUFFIXES)
    else:
        raise FileNotFoundError(f"Not found: {target}")

    results = []
    for f in files:
        try:
            res = ingest_file(f, collection)
        except Exception as e:
            logger.error(f"Failed to ingest {f.name}: {e}")
            res = {"file": f.name, "status": f"error: {e}", "chunks": 0}
        results.append(res)
        logger.info(f"ingest {res['status']}: {f.name} ({res['chunks']} chunks)")
    return results


# -----------------------------
# Retrieval
# -----------------------------
def search(query: str, top_k: Optional[int] = None) -> List[Dict]:
    """Return the top-k passages with source attribution, best first."""
    cfg = get_config()
    k = top_k or cfg["kb_top_k"]
    collection = get_collection()
    if collection.count() == 0:
        return []

    q_emb = _embed([query], is_query=True)
    res = collection.query(
        query_embeddings=q_emb,
        n_results=min(k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]

    hits = []
    for rank, (doc, meta, dist) in enumerate(zip(docs, metas, dists), start=1):
        hits.append({
            "rank": rank,
            "text": doc,
            "title": meta.get("title", ""),
            "source": meta.get("source", ""),
            "page": meta.get("page", -1),
            "score": round(1.0 - float(dist), 4),   # cosine distance → similarity
        })
    return hits


def stats() -> Dict:
    """Summary of what's indexed, grouped by source file."""
    collection = get_collection()
    total = collection.count()
    got = collection.get(include=["metadatas"]) if total else {"metadatas": []}
    by_source: Dict[str, Dict] = {}
    for m in got.get("metadatas", []):
        src = m.get("source", "?")
        entry = by_source.setdefault(src, {"title": m.get("title", ""), "chunks": 0})
        entry["chunks"] += 1
    return {"total_chunks": total, "sources": by_source}
