from fastapi import FastAPI

from .config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version)


@app.get(f"{settings.api_prefix}/health")
async def health():
    return {"status": "healthy", "version": settings.app_version}