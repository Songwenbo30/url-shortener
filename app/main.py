from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncio

from app.api import endpoints
from app.middleware.logging import add_logging_middleware
from app.utils.visit_queue import visit_worker, flush_queue
from app.core.redis import close_redis  # 新增


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    # 启动后台访问统计 Worker
    asyncio.create_task(visit_worker())

    yield  # 应用运行期间停在这里

    # 关闭时
    # 1. 先刷完剩余的访问统计，确保数据不丢
    await flush_queue()
    # 2. 释放 Redis 连接池
    await close_redis()


app = FastAPI(lifespan=lifespan)

app.include_router(endpoints.router)

add_logging_middleware(app)
