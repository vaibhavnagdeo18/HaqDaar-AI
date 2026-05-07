import redis.asyncio as redis
from core.config import settings

# Redis client for caching and session management
redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)

async def get_redis():
    return redis_client
