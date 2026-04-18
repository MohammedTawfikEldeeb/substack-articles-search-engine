export PATH := $(CURDIR)\.venv\Scripts;$(PATH)

## supabase
supabase-create: 
	@echo "Creating Supabase database..."
	uv run python -m src.infrastructure.supabase.create_db

ingest-rss-articles-flow: 
	@echo "Running RSS ingestion locally (no scheduler)..."
	uv run -m src.pipelines.flows.rss_ingestion_flow
