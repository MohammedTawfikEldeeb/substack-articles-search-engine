from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from src.infrastructure.supabase.init_session import init_engine
from src.models.sql_models import Base
from src.utils.logger_util import setup_logging

logger = setup_logging()


def delete_all_tables() -> None:
    engine = init_engine()
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        if not existing_tables:
            logger.info("No tables found in the database. Nothing to delete.")
            return

        confirm = input(
            f"Are you sure you want to DROP ALL tables? {existing_tables}\n"
            "Type 'YES' to confirm or any other key to cancel: "
        )
        if confirm != "YES":
            logger.info("Operation canceled by user.")
            return

        logger.info(f"Dropping all tables: {existing_tables}")
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped successfully.")

    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy error dropping tables: {e}")
        raise SQLAlchemyError("Failed to drop tables from the database") from e
    except Exception as e:
        logger.error(f"Unexpected error dropping tables: {e}")
        raise
    finally:
        engine.dispose()
        logger.info("Database engine disposed.")


if __name__ == "__main__":
    delete_all_tables()
