from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from app.application.container import Container, build_container
from app.application.dto.chat import HealthResponse
from app.application.use_cases.health import HealthCheckUseCase
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.container = build_container()
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)


def get_container() -> Container:
    return app.state.container


@app.get(f"{settings.api_prefix}/health", response_model=HealthResponse)
async def health(container: Container = Depends(get_container)):
    return await container.health_use_case.execute()