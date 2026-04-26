from contextlib import asynccontextmanager
from fastapi import FastAPI


def create_app() -> FastAPI:

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        print("Open Server...")
        yield
        print("Close server")

    application = FastAPI(
        title="Qalix CLI API",
        version="0.1.0",
        description="Qalix CLI API for create unit test cases and integration test cases to CD/CI pipelines",
        lifespan=lifespan,
    )

    # How use Routers
    #application.include_router(users.router, prefix="/api/v1")

    @application.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok"}

    return application


# Instancia global que usa uvicorn
app = create_app()