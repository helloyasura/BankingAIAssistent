from dataclasses import dataclass
from app.application.use_cases.health import HealthCheckUseCase
from app.config import Settings, get_settings
from app.domain.ports.agent_port import AgentOrchestratorPort
from app.domain.ports.auth_port import AuthPort
from app.domain.ports.memory_port import MemoryPort
from app.domain.ports.vector_store_port import VectorStorePort
from backend.infrastructure.agent.stub_orchestrator import StubAgentOrchestrator
from backend.infrastructure.auth.hardcoded_auth import HardcodedAuth
from backend.infrastructure.memory.in_memory import InMemoryMemoryAdapter
from backend.infrastructure.vector_store.stub_vector_store import StubVectorStoreAdapter



@dataclass(slots=True)
class Container:
    settings: Settings
    auth_port: AuthPort
    memory_port: MemoryPort
    vector_store_port: VectorStorePort
    agent_port: AgentOrchestratorPort
    health_use_case: HealthCheckUseCase


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    auth = HardcodedAuth()
    memory = InMemoryMemoryAdapter()
    vector_store = StubVectorStoreAdapter()
    agent = StubAgentOrchestrator()
    return Container(
        settings=settings, 
        auth_port=auth,
        memory_port=memory,
        vector_store_port=vector_store,
        agent_port=agent,
        health_use_case=HealthCheckUseCase(settings, vector_store),
    )