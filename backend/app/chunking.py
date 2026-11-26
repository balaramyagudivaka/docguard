"""Split long text into small, overlapping chunks.

Why chunk? Embedding models work best on short passages, and when we answer a
question we want to hand the AI only the few relevant paragraphs, not whole files.

Why overlap? A sentence cut in half at a chunk boundary still appears whole in
the next chunk, so no idea is lost at the edges.
"""

CHUNK_WORDS = 200
OVERLAP_WORDS = 40


def chunk_text(text: str, chunk_words: int = CHUNK_WORDS, overlap: int = OVERLAP_WORDS) -> list[str]:
    """Return the text as a list of chunks of about `chunk_words` words each."""
    if overlap >= chunk_words:
        raise ValueError("overlap must be smaller than chunk_words")

    words = text.split()
    if not words:
        return []

    chunks = []
    step = chunk_words - overlap
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start:start + chunk_words]))
        if start + chunk_words >= len(words):
            break  # this chunk already reached the end of the text
    return chunks
