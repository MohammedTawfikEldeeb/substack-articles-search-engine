from pathlib import Path
from typing import ClassVar

import yaml
from pydantic import BaseModel, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from src.models.article_models import FeedItem


class SupabaseDBSettings(BaseModel):
    table_name: str = Field(
        default="substack_articles", description="supabase table name"
    )
    host: str = Field(default="localhost", description="supabase db host")
    port: int = Field(default=6543, description="supabase db port")
    user: str = Field(default="postgres", description="supabase db user")
    password: SecretStr = Field(
        default=SecretStr("password"),
        description="supabase db password",
    )
    name: str = Field(default="postgres", description="supabase db name")


class QdrantSettings(BaseModel):
    url: str = Field(default="", description="Qdrant API URL")
    api_key: str = Field(default="", description="Qdrant API key")
    collection_name: str = Field(
        default="substack_collection", description="Qdrant collection name"
    )
    dense_model_name: str = Field(
        default="BAAI/bge-base-en", description="Dense model name"
    )
    sparse_model_name: str = Field(
        default="Qdrant/bm25", description="Sparse model name"
    )  # prithivida/Splade_PP_en_v1 (larger)
    vector_dim: int = Field(
        default=768,
        description="Vector dimension",
    )
    article_batch_size: int = Field(
        default=5, description="Number of articles to parse and ingest in a batch"
    )
    sparse_batch_size: int = Field(default=32, description="Sparse batch size")
    embed_batch_size: int = Field(default=50, description="Dense embedding batch")
    upsert_batch_size: int = Field(
        default=50, description="Batch size for Qdrant upsert"
    )
    max_concurrent: int = Field(
        default=2, description="Maximum number of concurrent tasks"
    )


class RSSSettings(BaseModel):
    feeds: list[FeedItem] = Field(
        default_factory=list[FeedItem], description="List of RSS feed items"
    )
    default_start_date: str = Field(
        default="2025-09-15", description="Default cutoff date"
    )
    request_timeout_seconds: int = Field(
        default=15, description="HTTP timeout for RSS feed requests in seconds"
    )
    max_description_length: int = Field(
        default=10000, description="Maximum RSS description/content length to keep"
    )
    batch_size: int = Field(
        default=5, description="Number of articles to parse and ingest in a batch"
    )


class TextSplitterSettings(BaseModel):
    chunk_size: int = Field(default=4000, description="Size of text chunks")
    chunk_overlap: int = Field(default=200, description="Size of text chunks")
    separators: list[str] = Field(
        default_factory=lambda: [
            "\n---\n",
            "\n\n",
            "\n```\n",
            "\n## ",
            "\n# ",
            "\n**",
            "\n",
            ". ",
            "! ",
            "? ",
            " ",
            "",
        ],
        description="List of separators for text splitting. The order or separators matter",
    )


class HuggingFaceSettings(BaseModel):
    api_key: str = Field(default="", description="Hugging Face API key")
    model: str = Field(
        default="BAAI/bge-base-en-v1.5", description="Hugging Face model name"
    )


class OpenRouterSettings(BaseModel):
    api_key: str = Field(default="", description="OpenRouter API key")
    api_url: str = Field(
        default="https://openrouter.ai/api/v1", description="OpenRouter API URL"
    )


class OpikObservabilitySettings(BaseModel):
    api_key: str = Field(default="", description="Opik Observability API key")
    project_name: str = Field(
        default="substack-pipeline", description="Opik project name"
    )


class Settings(BaseSettings):
    supabase_db: SupabaseDBSettings = Field(default_factory=SupabaseDBSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    rss: RSSSettings = Field(default_factory=RSSSettings)
    hugging_face: HuggingFaceSettings = Field(default_factory=HuggingFaceSettings)
    text_splitter: TextSplitterSettings = Field(default_factory=TextSplitterSettings)
    openrouter: OpenRouterSettings = Field(default_factory=OpenRouterSettings)
    opik: OpikObservabilitySettings = Field(default_factory=OpikObservabilitySettings)
    rss_config_yaml_path: str = "src/configs/feeds_rss.yaml"
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=[".env"],
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
        case_sensitive=False,
        frozen=True,
    )

    @model_validator(mode="after")
    def hydrate_rss_settings(self) -> "Settings":
        config_path = Path(self.rss_config_yaml_path)
        if not config_path.exists():
            return self

        with config_path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}

        if not isinstance(raw, dict):
            raise ValueError("RSS config YAML must contain a mapping at the top level")

        rss_settings = RSSSettings(
            batch_size=raw.get("batch_size", self.rss.batch_size),
            request_timeout_seconds=raw.get(
                "request_timeout_seconds",
                self.rss.request_timeout_seconds,
            ),
            max_description_length=raw.get(
                "max_description_length",
                self.rss.max_description_length,
            ),
            feeds=raw.get("feeds", []),
        )
        object.__setattr__(self, "rss", rss_settings)
        return self


settings = Settings()
