from datacalasses import dataclass
from app.application.use_cases.health import HealthCheckUseCase
from app.config import Settings, get_settings
from app.domain.ports.auth_port import AuthPort
from app.domain.ports.vector_store_port import VectorStorePort

@dataclass(slots=True)
class Container:
    settings: Settings
    auth_port: AuthPort
    vector_store_port: VectorStorePort
    health_check_use_case: HealthCheckUseCase

def build_container(settings:Settings | None = None) -> Container:
    raise NotImplementedError("Wire stabling of dependencies is not implemented yet. Please implement the build_container function to wire up the dependencies.")