from dataclasses import dataclass
from pathlib import Path

from app.application.use_cases.chat import ChatUseCase
from app.application.use_cases.health import HealthCheckUseCase
from app.application.use_cases.login import LoginUseCase
from app.config import Settings, get_settings
from app.domain.ports.agent_port import AgentOrchestratorPort
from app.domain.ports.auth_port import AuthPort
from app.domain.ports.memory_port import MemoryPort
from app.domain.ports.vector_store_port import VectorStorePort
from app.domain.services.guardrails import GuardrailService
from app.infrastructure.agent.langgraph_orchestrator import LangGraphOrchestrator
from app.infrastructure.auth.hardcoded_auth import HardcodedAuth
from app.infrastructure.auth.jwt_service import JwtService
from app.infrastructure.llm.openai_adapter import OpenAIAdapter
from app.infrastructure.memory.in_memory import InMemoryMemoryAdapter
from app.infrastructure.vector_store.local_hybrid import LocalHybridVectorStoreAdapter


@dataclass(slots=True)
class Container:
    settings: Settings
    auth_port: AuthPort
    memory_port: MemoryPort
    vector_store_port: VectorStorePort
    agent_port: AgentOrchestratorPort
    jwt_service: JwtService
    health_use_case: HealthCheckUseCase
    login_use_case: LoginUseCase
    chat_use_case: ChatUseCase


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    auth = HardcodedAuth()
    memory = InMemoryMemoryAdapter()
    vector_store = LocalHybridVectorStoreAdapter()
    vector_store.load()
    llm = OpenAIAdapter(settings)
    agent = LangGraphOrchestrator(vector_store, llm)
    jwt_service = JwtService(settings)
    return Container(
        settings=settings,
        auth_port=auth,
        memory_port=memory,
        vector_store_port=vector_store,
        agent_port=agent,
        jwt_service=jwt_service,
        health_use_case=HealthCheckUseCase(settings, vector_store),
        login_use_case=LoginUseCase(auth, jwt_service),
        chat_use_case=ChatUseCase(agent, memory, GuardrailService()),
    )
