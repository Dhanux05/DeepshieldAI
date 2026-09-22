"""
Manually sync backend/knowledge-sources/ into the RAG vector store.

The FastAPI app already does this automatically on every startup (see the
lifespan hook in app/main.py) — this script exists for the times that isn't
enough: re-running the sync without restarting the whole API, or checking
what a sync would do from a plain shell during development.

Usage (from the `backend/` directory, with the venv active):

    python -m scripts.sync_knowledge_base
"""

import sys

from rag.ingest import sync_knowledge_base


def main() -> None:
    summary = sync_knowledge_base()

    print(f"Synced:        {len(summary['synced'])} file(s) — {summary['synced']}")
    print(f"Skipped:       {len(summary['skipped'])} file(s) — {summary['skipped']}")
    print(f"Removed stale: {len(summary['removed_stale'])} file(s) — {summary['removed_stale']}")


if __name__ == "__main__":
    sys.exit(main())
