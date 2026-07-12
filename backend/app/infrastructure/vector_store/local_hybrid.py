import asyncio
import math
import re
from collections import Counter
from pathlib import Path
from rank_bm25 import BM25Okapi
from app.domain.entities.document import DocumentChunk
from app.domain.ports.vector_store_port import RetrievalQuery, VectorStorePort

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[t] * b.get(t, 0) for t in a)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


class LocalHybridVectorStoreAdapter(VectorStorePort):
    def __init__(self, data_dir: Path | None = None) -> None:
        self._chunks: list[DocumentChunk] = []
        self._bm25 = None
        self._vectors: list[Counter] = []
        self._data_dir = data_dir

    def load(self) -> int:
        # Use document_loader.py to read JSON files → split into chunks
        from app.infrastructure.vector_store.document_loader import load_document_chunks
        self._chunks = load_document_chunks(self._data_dir)
        corpus = [_tokenize(c.content) for c in self._chunks]
        self._bm25 = BM25Okapi(corpus) if corpus else None
        self._vectors = [Counter(t) for t in corpus]
        return len(self._chunks)

    async def hybrid_search(self, query: RetrievalQuery) -> list[DocumentChunk]:
        return await asyncio.to_thread(self._search_sync, query)

    def _search_sync(self, query: RetrievalQuery) -> list[DocumentChunk]:
        if not self._chunks:
            self.load()
        q_tokens = _tokenize(query.query)
        q_vec = Counter(q_tokens)
        bm25_scores = self._bm25.get_scores(q_tokens)
        ranked = []
        for i, chunk in enumerate(self._chunks):
            dense = _cosine(q_vec, self._vectors[i])
            sparse = float(bm25_scores[i]) / (max(bm25_scores) or 1.0)
            score = query.dense_weight * dense + query.sparse_weight * sparse
            ranked.append((score, DocumentChunk(
                id=chunk.id, document_id=chunk.document_id, title=chunk.title,
                content=chunk.content, hybrid_score=score, metadata=chunk.metadata,
            )))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in ranked[: query.top_k]]

    async def upsert_documents(self, chunks: list[DocumentChunk]) -> int:
        self._chunks.extend(chunks)
        return len(chunks)

    async def health_check(self) -> bool:
        if not self._chunks:
            self.load()
        return len(self._chunks) > 0