import redis.asyncio as aioredis
from app.core.setting import settings

redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
)

redis_client = aioredis.Redis(connection_pool=redis_pool)

KEY_PREFIX = "short:url:"

async def get_cached_url(short_code: str) -> str | None:
    """从 Redis 获取 short_code 对应的 original_url。未命中返回 None"""
    key = KEY_PREFIX + short_code
    return await redis_client.get(key)

async def set_cached_url(short_code: str, original_url: str, ttl: int = 300) -> None:
    """
        将 short_code → original_url 写入 Redis。
        ttl 默认 300 秒（5 分钟），生产环境可根据 expires_at 动态计算
    """
    key = KEY_PREFIX + short_code
    await redis_client.set(key, original_url, ex=ttl)

async def delete_cached_url(short_code: str) -> None:
    """删除缓存（用于短链过期或更新时主动失效）"""
    key = KEY_PREFIX + short_code
    await redis_client.delete(key)

async def close_redis() -> None:
    """应用关闭时调用，释放连接池资源"""
    await redis_client.aclose()

async def reset_redis_pool():
    """测试用：关闭并重建连接池"""
    global redis_pool, redis_client
    await redis_client.aclose()
    redis_pool = aioredis.ConnectionPool.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    redis_client = aioredis.Redis(connection_pool=redis_pool)