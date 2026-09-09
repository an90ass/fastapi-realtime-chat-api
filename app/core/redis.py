import json
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config import settings


class RedisClient:
    """Singleton-style Redis manager utilizing an async connection pool."""

    _pool: Optional[aioredis.ConnectionPool] = None
    _client: Optional[aioredis.Redis] = None

    @classmethod
    async def init_pool(cls) -> None:
        """Initialize Redis connection pool on application startup."""
        if cls._pool is None:
            cls._pool = aioredis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_POOL_MAX_CONNECTIONS,
                decode_responses=True,
            )
            cls._client = aioredis.Redis(connection_pool=cls._pool)

    @classmethod
    async def close_pool(cls) -> None:
        """Gracefully close Redis pool on application shutdown."""
        if cls._client:
            if hasattr(cls._client, "aclose"):
                await cls._client.aclose()
            else:
                await cls._client.close()
        if cls._pool:
            if hasattr(cls._pool, "adisconnect"):
                await cls._pool.adisconnect()
            else:
                await cls._pool.disconnect()
        cls._client = None
        cls._pool = None

    @classmethod
    def get_client(cls) -> aioredis.Redis:
        """Returns the active Redis client instance."""
        if cls._client is None:
            # Fallback initialization if accessed before lifespan
            cls._pool = aioredis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_POOL_MAX_CONNECTIONS,
                decode_responses=True,
            )
            cls._client = aioredis.Redis(connection_pool=cls._pool)
        return cls._client

    @classmethod
    async def publish(cls, channel: str, message: Any) -> int:
        """Serializes and publishes a message to a channel using pooled connection."""
        client = cls.get_client()
        serialized = json.dumps(message) if isinstance(message, (dict, list)) else str(message)
        return await client.publish(channel, serialized)

    @classmethod
    def get_pubsub(cls) -> aioredis.client.PubSub:
        """Creates a PubSub instance from the connection pool."""
        client = cls.get_client()
        return client.pubsub()

    @classmethod
    async def ping(cls) -> bool:
        """Ping check for health endpoint."""
        try:
            client = cls.get_client()
            return await client.ping()
        except Exception:
            return False


redis_client = RedisClient
