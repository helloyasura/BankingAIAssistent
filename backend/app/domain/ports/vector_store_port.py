from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from app.domain.entities.document import DocumentChunk

@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    query: str
    top_k: int = 5
    metadata_filters: dict[str, str]  = field(default_factory=dict)
    dense_weights: float = 0.6
    sparse_weight:float = 0.4

class VectorStorePort(ABC):
    @abstractmethod
    async def hybrid_search(self, query:RetrievalQuery) -> list[DocumentChunk]: ...

    @abstractmethod
    async def upsert_documents(self, documents:list[DocumentChunk]) -> int: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
