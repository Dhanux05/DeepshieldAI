"""
Synchronise backend/knowledge-sources/ into the ChromaDB collection.

Design: every file's content is hashed (SHA-256). On each sync run, a file
whose hash matches what's already stored is skipped entirely — re-embedding
unchanged text on every restart would waste startup time for no benefit. A
file whose hash has changed has its old chunks deleted and replaced. A file
that existed in the collection but is no longer on disk has its chunks
removed too, so deleting a knowledge-source file actually removes it from
retrieval instead of leaving stale chunks behind forever.
"""

import hashlib
from pathlib import Path
from typing import Any

from rag.chunking import chunk_text
from rag.embeddings import embed_texts
from rag.store import get_collection

SOURCE_DIR = Path(__file__).resolve().parent.parent / "knowledge-sources"


def _file_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _existing_hash(collection: Any, source_name: str) -> str | None:
    """
    The content_hash of a previously-indexed source file, or None if it has
    never been indexed. Every chunk of a file carries the same hash, so
    limit=1 is enough — we only need to know whether it changed.
    """
    result = collection.get(where={"source": source_name}, limit=1)
    metadatas = result.get("metadatas") or []
    if not metadatas:
        return None
    return metadatas[0].get("content_hash")


def _index_file(collection: Any, path: Path, content: str, content_hash: str) -> int:
    chunks = chunk_text(content)
    if not chunks:
        return 0

    embeddings = embed_texts(chunks)
    ids = [f"{path.name}::{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "source": path.name,
            "chunk_index": i,
            "content_hash": content_hash,
        }
        for i in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )
    return len(chunks)


def sync_knowledge_base() -> dict:
    """
    Sync every .md file in knowledge-sources/ into ChromaDB.

    Returns a summary dict — {"synced": [...], "skipped": [...],
    "removed_stale": [...]} — so both the FastAPI startup log and the manual
    /api/rag/sync endpoint can report exactly what happened without
    duplicating this logic.
    """
    collection = get_collection()

    synced: list[str] = []
    skipped: list[str] = []
    removed_stale: list[str] = []

    if not SOURCE_DIR.exists():
        return {"synced": synced, "skipped": skipped, "removed_stale": removed_stale}

    source_files = sorted(SOURCE_DIR.glob("*.md"))
    current_names = {path.name for path in source_files}

    for path in source_files:
        content = path.read_text(encoding="utf-8")
        content_hash = _file_hash(content)

        if _existing_hash(collection, path.name) == content_hash:
            skipped.append(path.name)
            continue

        # Either never indexed, or changed — clear any stale chunks first.
        collection.delete(where={"source": path.name})
        _index_file(collection, path, content, content_hash)
        synced.append(path.name)

    # Purge chunks for any source file that was indexed previously but is
    # gone from disk now, so a deleted knowledge-source file actually stops
    # being retrievable instead of lingering forever.
    indexed_sources = {
        metadata.get("source")
        for metadata in (collection.get(include=["metadatas"]).get("metadatas") or [])
        if metadata.get("source")
    }
    for stale_name in indexed_sources - current_names:
        collection.delete(where={"source": stale_name})
        removed_stale.append(stale_name)

    return {"synced": synced, "skipped": skipped, "removed_stale": removed_stale}
