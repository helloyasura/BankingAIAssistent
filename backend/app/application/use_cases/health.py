
from app.application.dto.chat import HealthResponse
from app.config import Settings
from app.domain.ports.vector_store_port import VectorStorePort


class HealthCheckUseCase: 
    def __init__(self, setting:Settings, vector_store: VectorStorePort) -> None: 
        self.setting = setting
        self.vector_store = vector_store
    
    async def execute(self) -> HealthResponse: 
        vector_ok = await self.vector_store.health_check()
        return HealthResponse(
            status="healthy" if vector_ok else "degraded",
            version=self.setting.app_version,
            environment=self.setting.environment,
            dependencies={"vector_store": "healthy" if vector_ok else "degraded"}
        )