from pydantic import BaseModel , Field , SecretStr , model_validator
from pydantic_settings import BaseSettings , SettingsConfigDict
from typing import ClassVar

class SupabaseDBSettings(BaseModel):
    table_name : str = Field(default="substack_articles" , description="supabase table name")
    host: str = Field(default="localhost" , description="supabase db host")
    port: int = Field(default=6543 , description="supabase db port")
    user: str = Field(default="postgres" , description="supabase db user")
    password: SecretStr = Field(default=SecretStr("password") , description="sipabase db password")
    name: str = Field(default="postgres" , description="supabase db name")


class QdrantSettings(BaseModel):
    pass

class RSSSettings(BaseSettings):
    pass

class Settings(BaseSettings):
    supabase_db: SupabaseDBSettings = Field(default_factory=SupabaseDBSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    rss: RSSSettings = Field(default_factory=RSSSettings)
    
    rss_config_yaml_path: str = "src/configs/feeds_rss.yaml"
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=[".env"],
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
        case_sensitive=False,
        frozen=True,
    )


settings = Settings()