from dataclasses import dataclass , field
from datetime import date

@dataclass(frozen=True, slots=True)
class Document:
    id: str
    title: str
    content: str
    document_type: str
    department: str
    access_level: str
    create_date: date
    metadata:dict[str, str] = field(default_factory=dict)
@dataclass(frozen=True, slots=True)
class DocumentMetadata:
    id:str
    document_id:str
    title:str
    content:str
    dense_score:float | None =None
    sparse_score:float | None =None
    hybrid_score:float | None =None
    metadata:dict[str, str] = field(default_factory=dict)

DocumentChunk = DocumentMetadata