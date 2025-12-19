from fastapi import FastAPI
import asyncio
from app.api import endpoints
from app.middleware.logging import add_logging_middleware
from app.utils.visit_queue import visit_worker, flush_queue

app = FastAPI()


@app.on_event("startup")
async def start_visit_worker():
    asyncio.create_task(visit_worker())


@app.on_event("shutdown")
async def flush_visits_on_shutdown():
    await flush_queue()


app.include_router(endpoints.router)

add_logging_middleware(app)
