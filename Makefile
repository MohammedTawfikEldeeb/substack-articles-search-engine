export PATH := $(CURDIR)\.venv\Scripts;$(PATH)

## supabase
supabase-create: 
	@echo "Creating Supabase database..."
	uv run python -m src.infrastructure.supabase.create_db

supabase-delete: 
	@echo "Deleting Supabase database..."
	uv run python -m src.infrastructure.supabase.delete_db

ingest-rss-articles-flow: 
	@echo "Running RSS ingestion locally (no scheduler)..."
	uv run -m src.pipelines.flows.rss_ingestion_flow

ingest-embeddings-flow: 
	@echo "Running embeddings ingestion locally (no scheduler)..."
	uv run -m src.pipelines.flows.embeddings_ingestion_flow

qdrant-create-collection: ## Create Qdrant collection
	@echo "Creating Qdrant collection..."
	uv run python -m src.infrastructure.qdrant.create_collection

qdrant-delete-collection: ## Delete Qdrant collection
	@echo "Deleting Qdrant collection..."
	uv run python -m src.infrastructure.qdrant.delete_collection

qdrant-create-indexes: ## Create Qdrant index
	@echo "Updating HNSW and creating Qdrant indexes..."
	uv run python -m src.infrastructure.qdrant.create_indexes

qdrant-ingest-from-sql: ## Ingest data from SQL to Qdrant
	@echo "Ingesting data from SQL to Qdrant..."
	uv run python -m src.infrastructure.qdrant.ingest_from_sql
	@echo "Data ingestion complete."

run-api: ## Run FastAPI application
	@echo "Starting FastAPI application..."
	uv run -m src.api.main
	@echo "FastAPI application stopped."

clean-fastembed-cache: ## Clear potentially corrupted fastembed cache
	@echo "Clearing fastembed cache..."
	uv run python -c "import os, shutil, tempfile; paths=['/tmp/fastembed_cache', os.path.join(tempfile.gettempdir(), 'fastembed_cache')]; [shutil.rmtree(p, ignore_errors=True) for p in paths if os.path.isdir(p)]; print('Cleared:', paths)"
	@echo "Fastembed cache clear complete."

run-react: ## Run React frontend
	@echo "Starting React frontend..."
	cd frontend && npm install && npm run dev
	@echo "React frontend stopped."