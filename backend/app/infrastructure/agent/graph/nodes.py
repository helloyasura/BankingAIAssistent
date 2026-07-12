from app.domain.entities.document import DocumentChunk
from app.domain.ports.llm_port import LLMPort
from app.domain.ports.mcp_port import MCPPort
from app.domain.ports.python_analysis_port import PythonAnalysisPort
from app.domain.ports.vector_store_port import RetrievalQuery, VectorStorePort
from app.domain.services.tool_authorization import ToolAuthorizationService
from app.domain.value_objects.role import ToolPremission
from app.infrastructure.agent.graph.state import GraphState

_RESEARCH_KEYWORDS = ("summarize", "recurring", "root cause", "all ", "analyze")
_MCP_KEYWORDS = (
    "on-call",
    "on call",
    "employee",
    "who is",
    "service catalog",
    "microservice",
    "inc-",
    "incident record",
)
_PYTHON_ANALYSIS_KEYWORDS = (
    "count",
    "recurring",
    "keyword",
    "frequency",
    "breakdown",
    "statistics",
    "root cause",
)


def _chunk_to_dict(chunk: DocumentChunk) -> dict:
    return {
        "id": chunk.id,
        "title": chunk.title,
        "content": chunk.content,
        "metadata": chunk.metadata,
    }


def _is_mcp_query(message: str) -> bool:
    lowered = message.lower()
    return any(keyword in lowered for keyword in _MCP_KEYWORDS)


def _is_python_analysis_query(message: str) -> bool:
    lowered = message.lower()
    return any(keyword in lowered for keyword in _PYTHON_ANALYSIS_KEYWORDS)


def _format_tool_result_item(item: dict) -> str:
    if "id" in item and "title" in item:
        parts = [f"{item['id']}: {item.get('title', 'Untitled')}"]
        if item.get("severity"):
            parts.append(f"({item['severity']})")
        if item.get("status"):
            parts.append(f"— {item['status']}")
        if item.get("root_cause"):
            parts.append(f"Root cause: {item['root_cause']}")
        return " ".join(parts)
    if "team" in item and "owner" in item:
        parts = [item.get("name", "Unknown service")]
        if item.get("team"):
            parts.append(f"({item['team']} team)")
        if item.get("owner"):
            parts.append(f"— owner: {item['owner']}")
        if item.get("status"):
            parts.append(f"— {item['status']}")
        return " ".join(parts)
    if item.get("name"):
        parts = [item["name"]]
        if item.get("role"):
            parts.append(f"({item['role']})")
        if item.get("department"):
            parts.append(f"— {item['department']} department")
        if item.get("email"):
            parts.append(f"— {item['email']}")
        return " ".join(parts)
    return str(item)


def _format_python_analysis_result(result: dict) -> str:
    sections: list[str] = []
    analysis_type = result.get("analysis_type", "general")

    if counts := result.get("root_cause_counts"):
        lines = [f"- {cause}: {count} incident(s)" for cause, count in counts.items()]
        sections.append("Count by root cause:\n" + "\n".join(lines))

    if keywords := result.get("recurring_keywords"):
        lines = [f"- {item['keyword']}: {item['count']}" for item in keywords[:10]]
        sections.append("Recurring keywords:\n" + "\n".join(lines))

    if summary := result.get("summary"):
        parts = [f"Analyzed {summary.get('chunk_count', 0)} document(s)."]
        if departments := summary.get("departments"):
            dept_lines = [f"- {dept}: {count}" for dept, count in departments.items()]
            parts.append("By department:\n" + "\n".join(dept_lines))
        if titles := summary.get("titles"):
            parts.append("Sample titles: " + ", ".join(titles))
        sections.append("\n".join(parts))

    if sections:
        header = f"Python analysis ({analysis_type}):"
        return header + "\n\n" + "\n\n".join(sections)
    return "No analysis results found."


def _format_tool_results_answer(tool_results: list[dict]) -> str:
    sections: list[str] = []
    for result in tool_results:
        if result.get("error"):
            sections.append(f"Tool error: {result['error']}")
            continue
        if "analysis_type" in result:
            sections.append(_format_python_analysis_result(result))
            continue
        tool = result.get("tool", result.get("inferred_tool", "tool"))
        results = result.get("results", [])
        if not results:
            sections.append(f"No results found from {tool}.")
            continue
        lines = [_format_tool_result_item(item) for item in results if isinstance(item, dict)]
        header = f"Found {len(lines)} result(s) from {tool}:"
        sections.append(header + "\n" + "\n".join(f"- {line}" for line in lines))
    return "\n\n".join(sections)


def _detect_analysis_type(message: str) -> str:
    lowered = message.lower()
    if "summarize" in lowered or ("recurring" in lowered and "root cause" in lowered):
        return "general"
    if "count" in lowered and "root cause" in lowered:
        return "root_cause"
    if "root cause" in lowered:
        return "root_cause"
    if "keyword" in lowered or "recurring" in lowered:
        return "keywords"
    if "metadata" in lowered or "department" in lowered:
        return "metadata"
    return "general"


def _should_include_mcp_incidents(message: str) -> bool:
    lowered = message.lower()
    return any(
        keyword in lowered
        for keyword in ("incident", "outage", "root cause", "recurring")
    )


def _incidents_to_chunks(incidents: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    for incident in incidents:
        content = (
            f"Incident {incident['id']}: {incident['title']}. "
            f"Severity {incident.get('severity', '')}. Status {incident.get('status', '')}. "
            f"Root Cause: {incident.get('root_cause', '')}. "
            f"Keywords: {', '.join(incident.get('keywords', []))}."
        )
        chunks.append(
            {
                "id": incident["id"],
                "title": incident["title"],
                "content": content,
                "metadata": {
                    "root_cause": incident.get("root_cause", ""),
                    "department": incident.get("department", ""),
                    "document_type": "incident",
                },
            }
        )
    return chunks


class GraphNodes:
    def __init__(
        self,
        vector_store: VectorStorePort,
        llm: LLMPort,
        mcp: MCPPort,
        python_analysis: PythonAnalysisPort,
        authorization: ToolAuthorizationService | None = None,
    ) -> None:
        self._vector_store = vector_store
        self._llm = llm
        self._mcp = mcp
        self._python_analysis = python_analysis
        self._authorization = authorization or ToolAuthorizationService()

    def _any_mcp_allowed(self, user_role: str) -> bool:
        return any(
            self._authorization.is_allowed(user_role, permission)
            for permission in (
                ToolPremission.MCP_EMPLOYEE_DIRECTORY,
                ToolPremission.MCP_SERVICE_CATALOG,
                ToolPremission.MCP_INCIDENT_RECORD,
            )
        )

    def _retrieval_query(self, state: GraphState, top_k: int = 5) -> RetrievalQuery:
        return RetrievalQuery(
            query=state["message"],
            top_k=top_k,
            metadata_filters=self._authorization.retrieval_metadata_filters(
                state.get("user_role", "viewer")
            ),
        )

    async def supervisor(self, state: GraphState) -> dict:
        message = state["message"].lower()
        user_role = state.get("user_role", "viewer")
        route = "retrieval"
        detail = "Routing to retrieval agent."

        if _is_mcp_query(message) and self._any_mcp_allowed(user_role):
            route = "mcp_tools"
            detail = "Routing to MCP tools."
        elif _is_python_analysis_query(message) and self._authorization.is_allowed(
            user_role, ToolPremission.PYTHON_ANALYSIS
        ):
            route = "python_analysis"
            detail = "Routing to python analysis."
        elif any(keyword in message for keyword in _RESEARCH_KEYWORDS):
            route = "research"
            detail = "Routing to research agent."

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
        chunks = await self._vector_store.hybrid_search(self._retrieval_query(state))
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
            self._retrieval_query(state, top_k=10)
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

    async def mcp_tools(self, state: GraphState) -> dict:
        user_role = state.get("user_role", "viewer")
        result = await self._mcp.infer_and_call(state["message"])
        tool_name = result.get("inferred_tool", "employee_directory")
        permission = self._authorization.required_permission_for_mcp_tool(tool_name)

        if not self._authorization.is_allowed(user_role, permission):
            return {
                "tool_results": [],
                "activities": state.get("activities", [])
                + [
                    {
                        "node": "mcp_tools",
                        "status": "blocked",
                        "detail": (
                            f"Role '{user_role}' is not permitted to use MCP tool "
                            f"'{tool_name}'."
                        ),
                        "metadata": {"tool": tool_name, "permission": permission.value},
                    }
                ],
            }

        return {
            "tool_results": [result],
            "activities": state.get("activities", [])
            + [
                {
                    "node": "mcp_tools",
                    "status": "completed",
                    "detail": (
                        f"MCP tool '{tool_name}' returned {result.get('count', 0)} results."
                    ),
                    "metadata": {"tool": tool_name},
                }
            ],
        }

    async def python_analysis(self, state: GraphState) -> dict:
        user_role = state.get("user_role", "viewer")
        if not self._authorization.is_allowed(user_role, ToolPremission.PYTHON_ANALYSIS):
            return {
                "tool_results": [],
                "activities": state.get("activities", [])
                + [
                    {
                        "node": "python_analysis",
                        "status": "blocked",
                        "detail": (
                            f"Role '{user_role}' is not permitted to run python analysis."
                        ),
                    }
                ],
            }

        chunks = await self._vector_store.hybrid_search(
            self._retrieval_query(state, top_k=10)
        )
        chunk_dicts = [_chunk_to_dict(chunk) for chunk in chunks]
        if _should_include_mcp_incidents(state["message"]) and self._authorization.is_allowed(
            user_role, ToolPremission.MCP_INCIDENT_RECORD
        ):
            mcp_result = await self._mcp.call_tool("incident_records", {})
            incident_chunks = _incidents_to_chunks(mcp_result.get("results", []))
            incident_ids = {chunk.get("id") for chunk in incident_chunks}
            chunk_dicts = incident_chunks + [
                chunk
                for chunk in chunk_dicts
                if not any(
                    str(chunk.get("id", "")).startswith(incident_id)
                    for incident_id in incident_ids
                )
            ]
        analysis_type = _detect_analysis_type(state["message"])
        analysis = self._python_analysis.analyze_chunks(chunk_dicts, analysis_type)
        return {
            "retrieved_chunks": chunk_dicts,
            "tool_results": [analysis],
            "activities": state.get("activities", [])
            + [
                {
                    "node": "python_analysis",
                    "status": "completed",
                    "detail": f"Completed {analysis_type} analysis on {len(chunk_dicts)} chunks.",
                    "metadata": {"analysis_type": analysis_type},
                }
            ],
        }

    async def response(self, state: GraphState) -> dict:
        tool_results = state.get("tool_results", [])
        blocked = any(
            activity.get("status") == "blocked"
            for activity in state.get("activities", [])
            if activity.get("node") in {"mcp_tools", "python_analysis"}
        )
        if blocked:
            blocked_activity = next(
                activity
                for activity in reversed(state.get("activities", []))
                if activity.get("status") == "blocked"
            )
            return {
                "final_answer": blocked_activity["detail"],
                "validation_passed": False,
                "activities": state.get("activities", [])
                + [
                    {
                        "node": "response",
                        "status": "completed",
                        "detail": "Returned authorization message.",
                    }
                ],
            }

        findings = state.get("research_findings", [])
        if tool_results:
            answer = _format_tool_results_answer(tool_results)
            return {
                "final_answer": answer,
                "validation_passed": True,
                "activities": state.get("activities", [])
                + [
                    {
                        "node": "response",
                        "status": "completed",
                        "detail": "Answer generated from tool results.",
                    }
                ],
            }
        elif findings:
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
