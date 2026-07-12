import re

from app.domain.entities.document import DocumentChunk

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN.findall(text.lower()))


def rerank_chunks(
    query: str,
    chunks: list[DocumentChunk],
    *,
    top_k: int,
) -> list[DocumentChunk]:
    """Lightweight score-fusion rerank after hybrid retrieval."""
    if not chunks or len(chunks) <= 1:
        return chunks[:top_k]

    query_terms = _tokenize(query)
    if not query_terms:
        return chunks[:top_k]

    rescored: list[tuple[float, DocumentChunk]] = []
    for chunk in chunks:
        title_terms = _tokenize(chunk.title)
        content_terms = _tokenize(chunk.content[:500])
        title_overlap = len(query_terms & title_terms) / len(query_terms)
        content_overlap = len(query_terms & content_terms) / len(query_terms)
        hybrid = chunk.hybrid_score or 0.0
        fused = hybrid * 0.5 + title_overlap * 0.35 + content_overlap * 0.15
        rescored.append(
            (
                fused,
                DocumentChunk(
                    id=chunk.id,
                    document_id=chunk.document_id,
                    title=chunk.title,
                    content=chunk.content,
                    hybrid_score=fused,
                    metadata=chunk.metadata,
                ),
            )
        )

    rescored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in rescored[:top_k]]
