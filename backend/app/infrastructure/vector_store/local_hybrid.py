import asyncio
import math
import re
from collections import Counter
from pathlib import Path
from rank_bm25 import BM25Okapi
from app.domain.entities.document import DocumentChunk
from app.domain.ports.vector_store_port import RetrievalQuery, VectorStorePort
from app.infrastructure.vector_store.reranker import rerank_chunks

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

    def _matches_filters(self, chunk: DocumentChunk, filters: dict[str, str]) -> bool:
        if not filters:
            return True
        return all(chunk.metadata.get(key) == value for key, value in filters.items())

    def _search_sync(self, query: RetrievalQuery) -> list[DocumentChunk]:
        if not self._chunks:
            self.load()
        candidates = [
            chunk
            for chunk in self._chunks
            if self._matches_filters(chunk, query.metadata_filters)
        ]
        if not candidates:
            return []
        candidate_indices = [self._chunks.index(chunk) for chunk in candidates]
        q_tokens = _tokenize(query.query)
        q_vec = Counter(q_tokens)
        bm25_scores = self._bm25.get_scores(q_tokens)
        ranked = []
        for i in candidate_indices:
            chunk = self._chunks[i]
            dense = _cosine(q_vec, self._vectors[i])
            sparse = float(bm25_scores[i]) / (max(bm25_scores) or 1.0)
            score = query.dense_weights * dense + query.sparse_weight * sparse
            ranked.append((score, DocumentChunk(
                id=chunk.id, document_id=chunk.document_id, title=chunk.title,
                content=chunk.content, hybrid_score=score, metadata=chunk.metadata,
            )))
        ranked.sort(key=lambda x: x[0], reverse=True)
        candidate_k = min(len(ranked), max(query.top_k * 2, query.top_k))
        candidates = [c for _, c in ranked[:candidate_k]]
        return rerank_chunks(query.query, candidates, top_k=query.top_k)

    async def upsert_documents(self, chunks: list[DocumentChunk]) -> int:
        self._chunks.extend(chunks)
        return len(chunks)

    async def health_check(self) -> bool:
        if not self._chunks:
            self.load()
        return len(self._chunks) > 0