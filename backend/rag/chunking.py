"""
Paragraph-aware text chunking for the RAG knowledge base.

Why not a fixed-size character slice? Cutting a document every N characters
routinely severs a sentence (or a whole idea) in half, and the retriever then
returns a passage that reads as a fragment. Splitting on paragraph
boundaries first keeps each chunk's text self-contained; only a single
paragraph that is itself too long gets hard-split, and even then on
whitespace rather than mid-word.

The sliding-window overlap (default 80 characters) exists so a fact sitting
right at a chunk boundary is not visible to only one side of the split —
without it, a question whose answer straddles the boundary can retrieve
neither half with enough context to make sense.
"""

DEFAULT_CHUNK_SIZE = 500
DEFAULT_OVERLAP = 80


def _hard_split(paragraph: str, chunk_size: int) -> list[str]:
    """
    Split a single paragraph that exceeds chunk_size, breaking on whitespace
    so a chunk never ends mid-word.
    """
    words = paragraph.split()
    pieces: list[str] = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > chunk_size and current:
            pieces.append(current)
            current = word
        else:
            current = candidate

    if current:
        pieces.append(current)

    return pieces


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """
    Split `text` into overlapping, paragraph-aware chunks of roughly
    `chunk_size` characters each.

    Algorithm:
      1. Split on blank lines ("\n\n") to get paragraphs.
      2. Any paragraph longer than chunk_size is hard-split on whitespace —
         this only happens for unusually long paragraphs; every source file
         in knowledge-sources/ is written in short paragraphs specifically
         to avoid this path.
      3. Paragraphs are packed into chunks greedily: keep appending until the
         next paragraph would exceed chunk_size, then close the chunk.
      4. Each new chunk (after the first) is seeded with the trailing
         `overlap` characters of the previous chunk, so context is not lost
         at the boundary.
    """
    if not text or not text.strip():
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    # Flatten any paragraph too long to fit in one chunk on its own.
    units: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            units.extend(_hard_split(paragraph, chunk_size))
        else:
            units.append(paragraph)

    chunks: list[str] = []
    current = ""

    for unit in units:
        candidate = f"{current}\n\n{unit}".strip() if current else unit

        if len(candidate) > chunk_size and current:
            chunks.append(current)
            # Seed the next chunk with the overlap tail of the one just closed.
            tail = current[-overlap:] if overlap > 0 else ""
            current = f"{tail}\n\n{unit}".strip() if tail else unit
        else:
            current = candidate

    if current:
        chunks.append(current)

    return chunks
