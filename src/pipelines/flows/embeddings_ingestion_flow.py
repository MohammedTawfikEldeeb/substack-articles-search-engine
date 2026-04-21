import argparse
import asyncio
from datetime import UTC

from dateutil import parser
from prefect import flow

from src.config import settings
from src.pipelines.tasks.ingest_embeddings import ingest_qdrant
from src.utils.logger_util import setup_logging


@flow(
    name="qdrant_ingest_flow",
    flow_run_name="qdrant_ingest_flow_run",
    description="Orchestrates SQL → Qdrant ingestion",
    retries=2,
    retry_delay_seconds=120,
)
async def qdrant_ingest_flow(from_date: str | None = None) -> None:
    """Prefect Flow: Orchestrates ingestion of articles from SQL into Qdrant.

    Determines the starting cutoff date for ingestion (user-provided date or
    configured default_start_date) and runs the Qdrant ingestion task.

    Args:
        from_date (str | None, optional): Start date in YYYY-MM-DD format. If None,
            falls back to configured default_start_date.

    Returns:
        None

    Raises:
        RuntimeError: If ingestion fails.
        Exception: For unexpected errors during execution.

    """
    logger = setup_logging()
    rss = settings.rss

    try:
        if from_date:
            # Parse user-provided date and assume UTC midnight
            from_date_dt = parser.parse(from_date).replace(tzinfo=UTC)
            logger.info(f"Using user-provided from_date: {from_date_dt}")
        else:
            # Fallback to configured default_start_date
            from_date_dt = parser.parse(rss.default_start_date).replace(tzinfo=UTC)
            logger.info(f"Using fallback from_date: {from_date_dt}")

        await ingest_qdrant(from_date=from_date_dt)

    except Exception as e:
        logger.error(f"Error during Qdrant ingestion flow: {e}")
        raise RuntimeError("Qdrant ingestion flow failed") from e


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--from-date",
        type=str,
        default=None,
        help="From date in YYYY-MM-DD format",
    )
    args = arg_parser.parse_args()

    asyncio.run(qdrant_ingest_flow(from_date=args.from_date))  # type: ignore[arg-type]
