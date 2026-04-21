import os
import tempfile
from contextlib import asynccontextmanager

import dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client.http.exceptions import UnexpectedResponse

from src.api.exceptions.exception_handlers import (
    general_exception_handler,
    qdrant_exception_handler,
    validation_exception_handler,
)
from src.api.middleware.logging_middleware import LoggingMiddleware
from src.api.routes.health_routes import router as health_router
from src.api.routes.search_routes import router as search_router
from src.api.services.semantic_cache_service import SemanticCacheService
from src.infrastructure.qdrant.qdrant_vectorstore import AsyncQdrantVectorStore
from src.utils.logger_util import setup_logging

dotenv.load_dotenv()

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache_dir = os.getenv("FASTEMBED_CACHE_DIR") or os.path.join(
        tempfile.gettempdir(), "fastembed_cache"
    )
    os.makedirs(cache_dir, exist_ok=True)
    logger.info(f"HF_HOME: {os.environ.get('HF_HOME', 'Not set')}")
    logger.info(f"Cache dir: {cache_dir}, Writable: {os.access(cache_dir, os.W_OK)}")
    cache_contents = os.listdir(cache_dir) if os.path.exists(cache_dir) else "Empty"
    logger.info(f"Cache contents before: {cache_contents}")
    try:
        # creates Qdrant client internally
        app.state.vectorstore = AsyncQdrantVectorStore(cache_dir=cache_dir)
        app.state.semantic_cache = SemanticCacheService(app.state.vectorstore)
        await app.state.semantic_cache.ensure_collection()
    except Exception as e:
        logger.exception("Failed to initialize QdrantVectorStore")
        raise e
    yield
    try:
        await app.state.vectorstore.client.close()
    except Exception:
        logger.exception("Failed to close Qdrant client")


app = FastAPI(
    title="Substack RAG API",
    version="1.0",
    description="API for Substack Retrieval-Augmented Generation (RAG) system",
    lifespan=lifespan,
)


allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # ["*"],  # allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # only the methods the app uses
    allow_headers=["Authorization", "Content-Type"],  # only headers needed
)

app.add_middleware(LoggingMiddleware)


app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(UnexpectedResponse, qdrant_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


app.include_router(search_router, prefix="/search", tags=["search"])
app.include_router(health_router, tags=["health"])

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=True,
    )
