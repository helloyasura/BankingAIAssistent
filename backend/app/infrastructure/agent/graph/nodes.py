from app.domain.entities.document import DocumentChunk
from app.domain.ports.llm_port import LLMPort
from app.domain.ports.vector_store_port import RetrievalQuery, VectorStorePort
from app.infrastructure.agent.graph.state import GraphState

_RESEARCH_KEYWORDS = ("summarize", "recurring", "root cause", "all ", "analyze")


def _chunk_to_dict(chunk: DocumentChunk) -> dict:
    return {"id": chunk.id, "title": chunk.title, "content": chunk.content}


class GraphNodes:
    def __init__(self, vector_store: VectorStorePort, llm: LLMPort) -> None:
        self._vector_store = vector_store
        self._llm = llm

    async def supervisor(self, state: GraphState) -> dict:
        message = state["message"].lower()
        route = "research" if any(k in message for k in _RESEARCH_KEYWORDS) else "retrieval"
        detail = (
            "Routing to research agent."
            if route == "research"
            else "Routing to retrieval agent."
        )
        return {
            "route": route,
            "activities": state.get("activities", [])
            + [
                {
                    "node": "supervisor",
                    "status": "completed",
                    "detail": detail,
                }
            ],
        }

    async def retrieval(self, state: GraphState) -> dict:
        chunks = await self._vector_store.hybrid_search(
            RetrievalQuery(query=state["message"], top_k=5)
        )
        return {
            "retrieved_chunks": [_chunk_to_dict(c) for c in chunks],
            "activities": state.get("activities", [])
            + [
                {
                    "node": "retrieval",
                    "status": "completed",
                    "detail": f"Retrieved {len(chunks)} chunks.",
                }
            ],
        }

    async def research(self, state: GraphState) -> dict:
        chunks = await self._vector_store.hybrid_search(
            RetrievalQuery(query=state["message"], top_k=10)
        )
        batches = [chunks[i : i + 2] for i in range(0, len(chunks), 2)]
        findings: list[str] = []
        for batch in batches:
            batch_text = "\n\n".join(
                f"[{c.id}] {c.title}: {c.content[:400]}" for c in batch
            )
            summary = await self._llm.generate(f"Summarize themes in:\n{batch_text}")
            findings.append(summary)
        return {
            "research_findings": findings,
            "retrieved_chunks": [_chunk_to_dict(c) for c in chunks],
            "activities": state.get("activities", [])
            + [
                {
                    "node": "research",
                    "status": "completed",
                    "detail": f"Analyzed {len(chunks)} chunks in {len(batches)} batches.",
                }
            ],
        }

    async def response(self, state: GraphState) -> dict:
        findings = state.get("research_findings", [])
        if findings:
            context = "\n\n".join(findings)
            prompt = (
                "Synthesize a final answer from these research findings. "
                "Cite doc IDs in [ID] format when relevant.\n\n"
                f"Findings:\n{context}\n\nQuestion: {state['message']}"
            )
        else:
            context = "\n\n".join(
                c["content"][:500] for c in state.get("retrieved_chunks", [])[:3]
            )
            prompt = (
                "Answer using only this context. Cite doc IDs in [ID] format.\n\n"
                f"Context:\n{context}\n\nQuestion: {state['message']}"
            )
        answer = await self._llm.generate(prompt)
        return {
            "final_answer": answer,
            "validation_passed": True,
            "activities": state.get("activities", [])
            + [
                {
                    "node": "response",
                    "status": "completed",
                    "detail": "Answer generated.",
                }
            ],
        }
