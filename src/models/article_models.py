from datetime import datetime

from pydantic import BaseModel, Field


class FeedItem(BaseModel):
    name: str
    author: str = ""
    url: str


class ArticleItem(BaseModel):
    feed_name: str
    feed_author: str
    title: str
    url: str
    content: str
    article_authors: list[str] = Field(default_factory=list)
    published_at: datetime | None = None
