"""
Query-time retrieval over the RAG knowledge base.

Retrieval only — no LLM sits on top of this to generate a fabricated answer.
The frontend renders the retrieved passages directly, each with its source
file and a relevance score, because a scoped student project answering
"why did the image detector call this fake?" is safer and easier to trust
when it can show its receipts than when it silently paraphrases them.
"""

from rag.embeddings import embed_texts
from rag.store import get_collection

DEFAULT_TOP_K = 4


def query_knowledge_base(question: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    """
    Return up to `top_k` passages most relevant to `question`.

    Each result: {"text", "source", "chunk_index", "relevance"}. `relevance`
    is `1 - cosine_distance`, so it reads as a 0-1 similarity score (higher
    is more relevant) rather than Chroma's raw distance (lower is closer) —
    the inverted sense of "distance" is exactly the kind of thing that reads
    backwards to a user, so it's converted once here rather than in the API
    layer or the frontend.
    """
    collection = get_collection()
    count = collection.count()

    if count == 0:
        return []

    [query_embedding] = embed_texts([question])

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, count),
        include=["documents", "metadatas", "distances"],
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    passages = []
    for text, metadata, distance in zip(documents, metadatas, distances):
        passages.append(
            {
                "text": text,
                "source": metadata.get("source", "unknown"),
                "chunk_index": metadata.get("chunk_index", 0),
                "relevance": round(1 - distance, 4),
            }
        )

    return passages
