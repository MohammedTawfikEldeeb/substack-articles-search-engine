from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from src.infrastructure.supabase.init_session import init_engine
from src.models.sql_models import Base, SubstackArticle
from src.utils.logger_util import setup_logging

logger = setup_logging()


def create_table() -> None:

    engine = init_engine()
    try:
        # Create an inspector to check existing tables
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        table_name = SubstackArticle.__tablename__

        # Check if the table already exists
        if table_name in existing_tables:
            logger.info(f"Table '{table_name}' already exists. No action needed.")
        else:
            logger.info(f"Table '{table_name}' does not exist. Creating...")
            # Create all tables defined in Base.metadata (includes SubstackArticle)
            Base.metadata.create_all(bind=engine)
            logger.info(f"Table '{table_name}' created successfully.")
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy error creating table '{table_name}': {e}")
        raise SQLAlchemyError(f"Failed to create table '{table_name}'") from e
    except Exception as e:
        logger.error(f"Unexpected error creating table '{table_name}': {e}")
        raise
    finally:
        # Dispose of the engine to release connections
        engine.dispose()
        logger.info("Database engine disposed.")


if __name__ == "__main__":
    create_table()
