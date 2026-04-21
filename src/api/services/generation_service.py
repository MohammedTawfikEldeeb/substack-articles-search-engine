from collections.abc import AsyncGenerator, Callable

import opik

from src.api.models.api_models import SearchResult
from src.api.models.provider_models import MODEL_REGISTRY
from src.api.services.providers.openrouter_service import (
    generate_openrouter,
    stream_openrouter,
)
from src.api.services.providers.utils.evaluation_metrics import evaluate_metrics
from src.api.services.providers.utils.prompts import build_research_prompt
from src.utils.logger_util import setup_logging

logger = setup_logging()


# -----------------------
# Non-streaming answer generator
# -----------------------
@opik.track(name="generate_answer")
async def generate_answer(
    query: str,
    contexts: list[SearchResult],
    provider: str = "openrouter",
    selected_model: str | None = None,
) -> dict:
    """Generate a non-streaming answer using OpenRouter.

    Args:
        query (str): The user's research query.
        contexts (list[SearchResult]): List of context documents with metadata.
        provider (str): The LLM provider to use (must be "openrouter").

    Returns:
        dict: {"answer": str, "sources": list[str], "model": Optional[str]}

    """
    prompt = build_research_prompt(contexts, query=query)
    model_used: str | None = None
    finish_reason: str | None = None

    provider_lower = provider.lower()
    if provider_lower != "openrouter":
        raise ValueError(
            f"Unknown provider: {provider}. Only 'openrouter' is supported."
        )

    config = MODEL_REGISTRY.get_config(provider_lower)

    try:
        answer, model_used, finish_reason = await generate_openrouter(
            prompt, config=config, selected_model=selected_model
        )
        metrics_results = await evaluate_metrics(answer, prompt)
        logger.info(f"G-Eval Faithfulness → {metrics_results}")
    except Exception as e:
        logger.error(
            f"Error occurred while generating answer from {provider_lower}: {e}"
        )
        raise

    return {
        "answer": answer,
        "sources": [r.url for r in contexts],
        "model": model_used,
        "finish_reason": finish_reason,
    }


# -----------------------
# Streaming answer generator
# -----------------------
@opik.track(name="get_streaming_function")
def get_streaming_function(
    provider: str,
    query: str,
    contexts: list[SearchResult],
    selected_model: str | None = None,
) -> Callable[[], AsyncGenerator[str, None]]:
    """Get a streaming function for OpenRouter.

    Args:
        provider (str): The LLM provider to use (must be "openrouter").
        query (str): The user's research query.
        contexts (list[SearchResult]): List of context documents with metadata.

    Returns:
        Callable[[], AsyncGenerator[str, None]]: A function that returns an async generator yielding
        response chunks.

    """
    prompt = build_research_prompt(contexts, query=query)
    provider_lower = provider.lower()
    if provider_lower != "openrouter":
        raise ValueError(
            f"Unknown provider: {provider}. Only 'openrouter' is supported."
        )

    config = MODEL_REGISTRY.get_config(provider_lower)
    logger.info(f"Using model config: {config}")

    async def stream_gen() -> AsyncGenerator[str, None]:
        """Asynchronous generator that streams response chunks from OpenRouter.

        Yields:
            str: The next chunk of the response.

        """
        buffer = []  # collect textual chunks for evaluation only

        def is_control_chunk(chunk: str) -> bool:
            return chunk.startswith("__model_used__:") or chunk == "__truncated__"

        try:
            async for chunk in stream_openrouter(
                prompt, config=config, selected_model=selected_model
            ):
                if not is_control_chunk(chunk):
                    buffer.append(chunk)
                yield chunk

            full_output = "".join(buffer)
            metrics_results = await evaluate_metrics(full_output, prompt)
            logger.info(f"Metrics results: {metrics_results}")

        except Exception as e:
            logger.error(f"Error occurred while streaming from {provider}: {e}")
            yield "__error__"

    return stream_gen
