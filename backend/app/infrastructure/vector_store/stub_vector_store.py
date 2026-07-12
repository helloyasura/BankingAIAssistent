from app.domain.entities.document import DocumentChunk
from app.domain.ports.vector_store_port import RetrievalQuery , VectorStorePort

class StubVectorStoreAdapter(VectorStorePort):
    async def hybrid_search(self, query: RetrievalQuery) -> list[DocumentChunk]:
        return []
    async def upsert_documents(self, documents: list[DocumentChunk]) -> int:
        return 0
    async def health_check(self) -> bool:
        return True