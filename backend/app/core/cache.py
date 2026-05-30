import json
import redis.asyncio as redis
from app.config.settings import REDIS_URL

CACHE_TTL = 3600  # 1 hour in seconds

_redis: redis.Redis | None = None


async def connect_redis():
    global _redis
    _redis = redis.from_url(REDIS_URL, decode_responses=True)
    # Test connection
    await _redis.ping()
    print("Redis connected")


async def disconnect_redis():
    global _redis
    if _redis:
        await _redis.close()
        print("Redis disconnected")


async def get_cache(key: str) -> dict | None:
    if not _redis:
        return None
    data = await _redis.get(key)
    if data:
        return json.loads(data)
    return None


async def set_cache(key: str, value: dict, ttl: int = CACHE_TTL):
    if not _redis:
        return
    await _redis.set(key, json.dumps(value, default=str), ex=ttl)


async def delete_cache(key: str):
    if not _redis:
        return
    await _redis.delete(key)
