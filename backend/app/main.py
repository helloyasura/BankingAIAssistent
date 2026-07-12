from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from app.api.dependencies import get_container
from app.api.routes import auth, chat
from app.application.container import build_container
from app.application.dto.chat import HealthResponse
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.container = build_container()
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}/health", response_model=HealthResponse)
async def health(container=Depends(get_container)):
    return await container.health_use_case.execute()