import json
from pathlib import Path

from app.domain.entities.document import DocumentChunk

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_DATA_DIR = _PROJECT_ROOT / "data" / "mock_documents"


def load_document_chunks(data_dir: Path | None = None) -> list[DocumentChunk]:
    directory = data_dir or _DEFAULT_DATA_DIR
    chunks: list[DocumentChunk] = []

    for path in sorted(directory.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        doc_id = payload["id"]
        chunks.append(
            DocumentChunk(
                id=f"{doc_id}-chunk-0",
                document_id=doc_id,
                title=payload["title"],
                content=payload["content"],
                metadata={
                    "document_type": payload.get("document_type", ""),
                    "department": payload.get("department", ""),
                    "access_level": payload.get("access_level", ""),
                    "tags": ",".join(payload.get("tags", [])),
                },
            )
        )

    return chunks
