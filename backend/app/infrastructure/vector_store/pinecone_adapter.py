import asyncio

from app.config import Settings
from app.domain.entities.document import DocumentChunk
from app.domain.ports.vector_store_port import RetrievalQuery, VectorStorePort
from app.infrastructure.vector_store.local_hybrid import LocalHybridVectorStoreAdapter


class PineconeHybridAdapter(VectorStorePort):
    """Uses Pinecone when configured; otherwise delegates to local hybrid search."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._local = LocalHybridVectorStoreAdapter()
        self._local.load()
        self._index = None
        self._embeddings = None
        if settings.pinecone_api_key and settings.pinecone_index_name:
            self._init_pinecone()

    def _init_pinecone(self) -> None:
        try:
            from langchain_openai import OpenAIEmbeddings
            from pinecone import Pinecone

            client = Pinecone(api_key=self._settings.pinecone_api_key)
            self._index = client.Index(self._settings.pinecone_index_name)
            if self._settings.openai_api_key:
                self._embeddings = OpenAIEmbeddings(
                    api_key=self._settings.openai_api_key,
                    model=self._settings.openai_embedding_model,
                )
        except Exception:
            self._index = None
            self._embeddings = None

    async def hybrid_search(self, query: RetrievalQuery) -> list[DocumentChunk]:
        if self._index and self._embeddings:
            try:
                chunks = await asyncio.to_thread(self._pinecone_search_sync, query)
                if chunks:
                    return chunks
            except Exception:
                pass
        return await self._local.hybrid_search(query)

    def _to_pinecone_filter(self, metadata_filters: dict[str, str]) -> dict | None:
        if not metadata_filters:
            return None
        clauses = [{key: {"$eq": value}} for key, value in metadata_filters.items()]
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}

    def _pinecone_search_sync(self, query: RetrievalQuery) -> list[DocumentChunk]:
        vector = self._embeddings.embed_query(query.query)
        query_kwargs = {
            "vector": vector,
            "top_k": query.top_k,
            "include_metadata": True,
            "namespace": self._settings.pinecone_namespace,
        }
        if pinecone_filter := self._to_pinecone_filter(query.metadata_filters):
            query_kwargs["filter"] = pinecone_filter
        results = self._index.query(**query_kwargs)
        chunks: list[DocumentChunk] = []
        for match in results.get("matches", []):
            metadata = match.get("metadata") or {}
            chunks.append(
                DocumentChunk(
                    id=str(match["id"]),
                    document_id=str(metadata.get("document_id", match["id"])),
                    title=str(metadata.get("title", "")),
                    content=str(metadata.get("content", "")),
                    hybrid_score=float(match.get("score") or 0.0),
                    metadata={
                        key: str(value)
                        for key, value in metadata.items()
                        if key not in {"title", "content", "document_id"}
                    },
                )
            )
        return chunks

    async def upsert_documents(self, chunks: list[DocumentChunk]) -> int:
        count = await self._local.upsert_documents(chunks)
        if self._index and self._embeddings:
            try:
                await asyncio.to_thread(self._pinecone_upsert_sync, chunks)
            except Exception:
                pass
        return count

    def _pinecone_upsert_sync(self, chunks: list[DocumentChunk]) -> None:
        vectors = []
        for chunk in chunks:
            vectors.append(
                {
                    "id": chunk.id,
                    "values": self._embeddings.embed_query(chunk.content),
                    "metadata": {
                        "document_id": chunk.document_id,
                        "title": chunk.title,
                        "content": chunk.content,
                        **chunk.metadata,
                    },
                }
            )
        if vectors:
            self._index.upsert(
                vectors=vectors,
                namespace=self._settings.pinecone_namespace,
            )

    async def health_check(self) -> bool:
        local_ok = await self._local.health_check()
        if self._index is None:
            return local_ok
        try:
            stats = self._index.describe_index_stats()
            pinecone_ok = stats.get("total_vector_count", 0) > 0
            return local_ok or pinecone_ok
        except Exception:
            return local_ok
