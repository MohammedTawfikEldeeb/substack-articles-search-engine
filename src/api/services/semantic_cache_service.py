import time
import uuid
from dataclasses import dataclass

import opik
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, models

from src.api.models.api_models import AskRequest, SearchResult
from src.config import settings
from src.infrastructure.qdrant.qdrant_vectorstore import AsyncQdrantVectorStore
from src.utils.logger_util import setup_logging

logger = setup_logging()


def _normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().split())


def _build_filter_signature(ask: AskRequest) -> str:
    parts = [
        f"feed_author={ask.feed_author or ''}",
        f"feed_name={ask.feed_name or ''}",
        f"title_keywords={(ask.title_keywords or '').strip().lower()}",
        f"provider={ask.provider}",
        f"model={ask.model or ''}",
        f"limit={ask.limit}",
    ]
    return "|".join(parts)


def _compact_source(source: SearchResult) -> dict:
    # Keep source metadata small for cache payload safety.
    return {
        "title": source.title,
        "feed_author": source.feed_author,
        "feed_name": source.feed_name,
        "article_author": source.article_author,
        "url": source.url,
        "score": source.score,
    }


@dataclass(slots=True)
class SemanticCacheHit:
    answer: str
    sources: list[SearchResult]
    model: str | None
    finish_reason: str | None
    score: float


class SemanticCacheService:
    def __init__(self, vectorstore: AsyncQdrantVectorStore):
        self.vectorstore = vectorstore
        self.client = vectorstore.client
        self.collection_name = settings.qdrant.semantic_cache_collection_name
        self.similarity_threshold = settings.qdrant.semantic_cache_similarity_threshold
        self.ttl_seconds = settings.qdrant.semantic_cache_ttl_seconds
        self.content_version = settings.qdrant.semantic_cache_content_version
        self.embedding_size = settings.qdrant.vector_dim

    def _update_lookup_span(
        self,
        *,
        hit: bool,
        reason: str,
        score: float | None = None,
    ) -> None:
        try:
            opik.update_current_span(
                metadata={
                    "cache.hit": hit,
                    "cache.reason": reason,
                    "cache.score": score,
                    "cache.threshold": self.similarity_threshold,
                    "cache.content_version": self.content_version,
                    "cache.ttl_seconds": self.ttl_seconds,
                    "cache.collection": self.collection_name,
                }
            )
        except Exception:
            # Never let observability break serving path.
            pass

    def _update_save_span(
        self,
        *,
        write_success: bool,
        reason: str,
        source_count: int,
    ) -> None:
        try:
            opik.update_current_span(
                metadata={
                    "cache.write_success": write_success,
                    "cache.write_reason": reason,
                    "cache.source_count": source_count,
                    "cache.content_version": self.content_version,
                    "cache.ttl_seconds": self.ttl_seconds,
                    "cache.collection": self.collection_name,
                }
            )
        except Exception:
            # Never let observability break serving path.
            pass

    async def ensure_collection(self) -> None:
        try:
            await self.client.get_collection(collection_name=self.collection_name)
            logger.info(
                f"Semantic cache collection '{self.collection_name}' already exists."
            )
            return
        except UnexpectedResponse as e:
            if e.status_code != 404:
                logger.warning(
                    f"Unable to check semantic cache collection '{self.collection_name}': {e}"
                )
                return

        try:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.embedding_size,
                    distance=Distance.COSINE,
                ),
            )
            await self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="filter_signature",
                field_schema=models.KeywordIndexParams(
                    type=models.KeywordIndexType.KEYWORD
                ),
            )
            await self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="content_version",
                field_schema=models.KeywordIndexParams(
                    type=models.KeywordIndexType.KEYWORD
                ),
            )
            logger.info(
                f"Semantic cache collection '{self.collection_name}' created successfully."
            )
        except Exception as e:
            logger.warning(
                f"Failed to create semantic cache collection '{self.collection_name}': {e}"
            )

    @opik.track(name="semantic_cache_lookup")
    async def try_get(self, ask: AskRequest) -> SemanticCacheHit | None:
        normalized_query = _normalize_query(ask.query_text)
        if not normalized_query:
            self._update_lookup_span(hit=False, reason="miss_empty_query")
            return None

        filter_signature = _build_filter_signature(ask)
        dense_vector = self.vectorstore.dense_vectors([normalized_query])[0]

        try:
            response = await self.client.query_points(
                collection_name=self.collection_name,
                query=dense_vector,
                limit=1,
                with_payload=True,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="filter_signature",
                            match=MatchValue(value=filter_signature),
                        )
                    ]
                ),
            )
        except Exception as e:
            logger.warning(f"Semantic cache lookup failed: {e}")
            self._update_lookup_span(hit=False, reason="miss_error")
            return None

        if not response.points:
            self._update_lookup_span(hit=False, reason="miss_no_candidate")
            return None

        point = response.points[0]
        score = float(point.score or 0.0)
        if score < self.similarity_threshold:
            self._update_lookup_span(
                hit=False,
                reason="miss_low_similarity",
                score=score,
            )
            return None

        payload = point.payload or {}
        now = int(time.time())
        expires_at = int(payload.get("expires_at", 0))
        cached_version = payload.get("content_version")

        if expires_at <= now:
            self._update_lookup_span(hit=False, reason="miss_expired", score=score)
            return None

        if cached_version != self.content_version:
            self._update_lookup_span(
                hit=False,
                reason="miss_version_mismatch",
                score=score,
            )
            return None

        raw_sources = payload.get("sources", [])
        sources = [SearchResult.model_validate(item) for item in raw_sources]
        self._update_lookup_span(hit=True, reason="hit", score=score)

        return SemanticCacheHit(
            answer=str(payload.get("answer", "")),
            sources=sources,
            model=payload.get("model"),
            finish_reason=payload.get("finish_reason"),
            score=score,
        )

    @opik.track(name="semantic_cache_save")
    async def save(
        self,
        ask: AskRequest,
        answer: str,
        sources: list[SearchResult],
        model: str | None,
        finish_reason: str | None,
    ) -> None:
        normalized_query = _normalize_query(ask.query_text)
        if not normalized_query:
            self._update_save_span(
                write_success=False,
                reason="skip_empty_query",
                source_count=len(sources),
            )
            return

        now = int(time.time())
        expires_at = now + self.ttl_seconds
        filter_signature = _build_filter_signature(ask)
        dense_vector = self.vectorstore.dense_vectors([normalized_query])[0]
        source_urls = [s.url for s in sources if s.url]

        point_id = str(uuid.uuid4())
        payload = {
            "normalized_query": normalized_query,
            "original_query": ask.query_text,
            "filter_signature": filter_signature,
            "answer": answer,
            "sources": [_compact_source(s) for s in sources],
            "retrieved_doc_ids": source_urls,
            "top_k": ask.limit,
            "model": model,
            "finish_reason": finish_reason,
            "created_at": now,
            "expires_at": expires_at,
            "content_version": self.content_version,
        }

        try:
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=dense_vector,
                        payload=payload,
                    )
                ],
                wait=True,
            )
            logger.info(
                f"Semantic cache saved point_id={point_id} query='{normalized_query[:80]}'"
            )
            self._update_save_span(
                write_success=True,
                reason="stored",
                source_count=len(sources),
            )
        except Exception as e:
            logger.warning(f"Semantic cache rich write failed: {e}")

            # Retry with a minimal payload to avoid losing cache writes due payload limits.
            try:
                minimal_payload = {
                    "normalized_query": normalized_query,
                    "original_query": ask.query_text,
                    "filter_signature": filter_signature,
                    "answer": answer,
                    "retrieved_doc_ids": source_urls,
                    "top_k": ask.limit,
                    "model": model,
                    "finish_reason": finish_reason,
                    "created_at": now,
                    "expires_at": expires_at,
                    "content_version": self.content_version,
                }
                fallback_point_id = str(uuid.uuid4())
                await self.client.upsert(
                    collection_name=self.collection_name,
                    points=[
                        models.PointStruct(
                            id=fallback_point_id,
                            vector=dense_vector,
                            payload=minimal_payload,
                        )
                    ],
                    wait=True,
                )
                logger.info(
                    f"Semantic cache saved with minimal payload point_id={fallback_point_id} query='{normalized_query[:80]}'"
                )
                self._update_save_span(
                    write_success=True,
                    reason="stored_minimal_payload",
                    source_count=len(sources),
                )
            except Exception as retry_error:
                logger.warning(f"Semantic cache write retry failed: {retry_error}")
                self._update_save_span(
                    write_success=False,
                    reason="write_error",
                    source_count=len(sources),
                )
