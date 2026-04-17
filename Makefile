## supabase
supabase-create: 
	@echo "Creating Supabase database..."
	uv run python -m src.infrastructure.supabase.create_db