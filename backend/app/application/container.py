from dataclasses import dataclass

from app.application.use_cases.chat import ChatUseCase
from app.application.use_cases.feedback import FeedbackUseCase
from app.application.use_cases.health import HealthCheckUseCase
from app.application.use_cases.login import LoginUseCase
from app.config import Settings, get_settings
from app.domain.ports.agent_port import AgentOrchestratorPort
from app.domain.ports.auth_port import AuthPort
from app.domain.ports.memory_port import MemoryPort
from app.domain.ports.mcp_port import MCPPort
from app.domain.ports.python_analysis_port import PythonAnalysisPort
from app.domain.ports.vector_store_port import VectorStorePort
from app.domain.services.approval_gate import ApprovalGateService
from app.domain.services.guardrails import GuardrailService
from app.domain.services.tool_authorization import ToolAuthorizationService
from app.infrastructure.agent.langgraph_orchestrator import LangGraphOrchestrator
from app.infrastructure.auth.hardcoded_auth import HardcodedAuth
from app.infrastructure.auth.jwt_service import JwtService
from app.infrastructure.feedback.feedback_store import FeedbackStore
from app.infrastructure.llm.openai_adapter import OpenAIAdapter
from app.infrastructure.mcp.enterprise_mcp_adapter import EnterpriseMcpAdapter
from app.infrastructure.memory.composite_memory import CompositeMemoryAdapter
from app.infrastructure.memory.sqlite_long_term import SqliteLongTermMemoryStore
from app.infrastructure.tools.python_analysis import PythonAnalysisAdapter
from app.infrastructure.vector_store.local_hybrid import LocalHybridVectorStoreAdapter
from app.infrastructure.vector_store.pinecone_adapter import PineconeHybridAdapter
from app.infrastructure.observerbility.langsmith_adapter import (
    LangSmithObservabilityAdapter,
    NoOpObservabilityAdapter,
)


@dataclass(slots=True)
class Container:
    settings: Settings
    auth_port: AuthPort
    memory_port: MemoryPort
    vector_store_port: VectorStorePort
    mcp_port: MCPPort
    python_analysis_port: PythonAnalysisPort
    agent_port: AgentOrchestratorPort
    jwt_service: JwtService
    approval_gate: ApprovalGateService
    health_use_case: HealthCheckUseCase
    login_use_case: LoginUseCase
    chat_use_case: ChatUseCase
    feedback_use_case: FeedbackUseCase


def _build_observability(settings: Settings):
    if settings.langchain_api_key and settings.langchain_tracing_v2:
        return LangSmithObservabilityAdapter(settings)
    return NoOpObservabilityAdapter()


def _build_vector_store(settings: Settings) -> VectorStorePort:
    if settings.pinecone_api_key:
        return PineconeHybridAdapter(settings)
    store = LocalHybridVectorStoreAdapter()
    store.load()
    return store


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    auth = HardcodedAuth()
    long_term = SqliteLongTermMemoryStore(settings.long_term_memory_db)
    memory = CompositeMemoryAdapter(long_term=long_term)
    vector_store = _build_vector_store(settings)
    llm = OpenAIAdapter(settings)
    mcp = EnterpriseMcpAdapter()
    python_analysis = PythonAnalysisAdapter()
    authorization = ToolAuthorizationService()
    approval_gate = ApprovalGateService(auto_approve=settings.hitl_auto_approve)
    agent = LangGraphOrchestrator(
        vector_store,
        llm,
        mcp,
        python_analysis,
        authorization=authorization,
        approval_gate=approval_gate,
    )
    jwt_service = JwtService(settings)
    observability = _build_observability(settings)
    feedback_store = FeedbackStore(settings.feedback_db)
    return Container(
        settings=settings,
        auth_port=auth,
        memory_port=memory,
        vector_store_port=vector_store,
        mcp_port=mcp,
        python_analysis_port=python_analysis,
        agent_port=agent,
        jwt_service=jwt_service,
        approval_gate=approval_gate,
        health_use_case=HealthCheckUseCase(settings, vector_store),
        login_use_case=LoginUseCase(auth, jwt_service),
        chat_use_case=ChatUseCase(agent, memory, GuardrailService(), observability),
        feedback_use_case=FeedbackUseCase(feedback_store, observability),
    )
