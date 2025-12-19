"""
This module implements an asynchronous visit tracking system for short URLs using
a queue-based batch processing mechanism. Its primary purpose is to efficiently
record URL visits and update visit counts in the database while minimizing
database write load and ensuring data integrity under high concurrency.

Rationale:

1. Asynchronous Queueing:
   - Each redirect request enqueues a visit event containing the `short_url_id`
     and the `client_ip`.
   - Enqueuing is fast and non-blocking, ensuring the redirect response remains
     low-latency even under heavy traffic.

2. Batch Processing:
   - Visits are processed in batches of up to `BATCH_SIZE` or after
     `BATCH_INTERVAL` seconds, whichever comes first.
   - This reduces the number of database transactions by aggregating multiple
     visits into a single commit.

3. Atomic Visit Count Updates:
   - The `_process_batch` function inserts all `URLVisit` records in the batch
     and updates the `total_visits` field in the `ShortURL` table in one
     transactional context.
   - Aggregating visit counts in Python ensures atomic updates and prevents
     race conditions under concurrent redirects.

4. Flush on Shutdown / Testing:
   - The `flush_queue` function ensures that any remaining visits in the queue
     are written to the database.
   - This is critical for testing scenarios and application shutdown,
     guaranteeing that no visit data is lost.

5. Asynchronous Logging:
   - Each batch processed or flushed is logged asynchronously using `log_async`.
   - This provides observability without blocking the event loop or slowing
     down visit processing.

Usage:

- `enqueue_visit(short_url_id, client_ip)`:
    Called whenever a URL is accessed to enqueue a visit event.
- `visit_worker()`:
    Long-running coroutine that continuously processes visit events in batches.
    Should be started as a background task during application startup.
- `flush_queue()`:
    Flushes any remaining visits from the queue, typically called on shutdown
    or in test teardown to ensure all visits are persisted.
"""

import asyncio
import time
import logging
from sqlmodel import update
from app.db.models import URLVisit, ShortURL
from app.db.session import create_async_session
from app.middleware.logging import log_async

VISIT_QUEUE = asyncio.Queue()
BATCH_SIZE = 1000
BATCH_INTERVAL = 5  # seconds


async def enqueue_visit(short_url_id: int, client_ip: str):
    await VISIT_QUEUE.put({"short_url_id": short_url_id, "client_ip": client_ip})


async def _process_batch(batch: list[dict]):
    if not batch:
        return 0

    session_factory = create_async_session()
    async with session_factory() as session:
        async with session.begin():
            for visit in batch:
                session.add(URLVisit(**visit))

            counts = {}
            for visit in batch:
                counts[visit["short_url_id"]] = counts.get(visit["short_url_id"], 0) + 1
            for short_url_id, count in counts.items():
                stmt = (
                    update(ShortURL)
                    .where(ShortURL.id == short_url_id)
                    .values(total_visits=ShortURL.total_visits + count)
                )
                await session.exec(stmt)

    return len(batch)


async def visit_worker():
    total_processed = 0

    while True:
        batch = []
        start_time = time.perf_counter()

        try:
            while len(batch) < BATCH_SIZE:
                visit = await asyncio.wait_for(VISIT_QUEUE.get(), timeout=BATCH_INTERVAL)
                batch.append(visit)
        except asyncio.TimeoutError:
            pass

        processed = await _process_batch(batch)
        total_processed += processed

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if processed:
            await log_async(
                level=logging.INFO,
                message="Processed visit batch",
                extra={
                    "batch_size": processed,
                    "duration_ms": duration_ms,
                    "total_processed": total_processed,
                },
            )


async def flush_queue():
    total_flushed = 0

    batch = []
    while not VISIT_QUEUE.empty():
        batch.append(await VISIT_QUEUE.get())
        if len(batch) >= BATCH_SIZE:
            processed = await _process_batch(batch)
            total_flushed += processed
            batch = []

    if batch:
        processed = await _process_batch(batch)
        total_flushed += processed

    await log_async(
        level=logging.INFO,
        message="Flushed remaining visits from queue",
        extra={"total_flushed": total_flushed},
    )
