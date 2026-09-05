# 🔗 URL Shortener – FastAPI

A scalable and high-performance URL shortening service built with **FastAPI**, **SQLModel**, **PostgreSQL**, and **Alembic**, designed to handle high concurrency while keeping a maintainable and modular codebase.

This project is a fork of [mhhasani/url-shortener](https://github.com/mhhasani/url-shortener), extended with additional features for learning and resume purposes.

---

## 🧩 Features

* **Create short URLs** – `POST /shorten`(with optional custom alias and TTL expiration)
* **Redirect to original URLs** – `GET /r/{short_code}`(returns 410 Gone if expired)
* **Track visit statistics** – `GET /stats/{short_code}`
* **Async queue-based visit processing** for high concurrency
* **Connection pooling** for PostgreSQL
* **Custom async logging middleware** for observability
* **Flushable visit queue** for testing and shutdown safety

---

## 🚀 My Extensions

### Custom Alias Support
- Added optional `custom_alias` field to the shorten endpoint
- Pydantic validator enforces 3-20 char length and whitelist (letters, digits, hyphens, underscores)
- Database unique constraint + IntegrityError handling returns **409 Conflict** on collision
- Fully backward compatible: omit `custom_alias` to use auto-generation
- Covered by 5 new integration tests

### TTL Expiration
- Added optional `expires_in_days` field to the shorten endpoint
- Model adds nullable `expires_at` column (NULL = never expires)
- Expired URLs return **410 Gone** on redirect
- Alembic migration adds column + index on `expires_at`
- 5 new tests covering creation, expiration, default no-expiry, invalid input, stats still accessible

---

## ⚡ Scalability Highlights

* **Async Queue & Worker**
  Visits are enqueued and processed in batches to minimize DB writes and maintain atomic `total_visits` counts.

* **Connection Pooling**
  `SQLModel` async sessions with pooling prevent creating a new DB connection per request.

* **Background Logging**
  Logging is async; for very high traffic, logs can be redirected to Kafka or another scalable service.

* **Multi-instance Friendly**
  Visit workers and logging can be separated into dedicated services for horizontal scaling.

* **High Concurrency Ready**
  Batch updates, async DB, and rate-limiting strategies prevent service degradation under heavy traffic.

---

## 🚀 Getting Started

### 1️⃣ Clone the repository

```bash
git clone https://github.com/Songwenbo30/url-shortener.git
cd url-shortener
```

### 2️⃣ Create a virtual environment & install dependencies

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3️⃣ Configure environment

Copy the sample environment file and adjust DB credentials if needed:

```bash
cp sample.env .env
```
---

### 4️⃣ Run the database with Docker

```bash
docker compose up -d
```

---

### 5️⃣ Setup the database

```bash
alembic upgrade head
```

---

### 6️⃣ Run the application

Suppress FastAPI default logs to keep the output clean:

```bash
uvicorn app.main:app --reload --log-level critical
```

Open the interactive API docs at [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Running Tests

All tests are async-aware and flush the visit queue to ensure correct statistics:

```bash
pytest
```

Tests cover:

* URL creation and redirection
* Idempotent URL shortening
* **Custom alias creation, conflict (409), and validation (422)**
* **TTL expiration: 410 Gone on expired URLs, default no-expiry, invalid input (422)**
* Visit tracking under high concurrency
* Validation of invalid URLs

Total: **16 tests** (6 original + 5 custom alias + 5 TTL)

---

## 📁 Project Structure

```
app/
├── api/            # FastAPI routers
├── core/           # Configuration and settings
├── db/             # Models, async session, Alembic migrations
├── middleware/     # Logging middleware
├── utils/          # Visit queue, shortcode generator, background tasks
├── main.py         # FastAPI app entrypoint
```

---

## 🔧 Technical Details

### Visit Tracking

* Each redirect request calls `enqueue_visit(short_url_id, client_ip)`
* Background worker `visit_worker()` processes visits in batches (`BATCH_SIZE` / `BATCH_INTERVAL`)
* `_process_batch` inserts visit records and updates `ShortURL.total_visits` atomically

### Custom Alias

* Optional `custom_alias` field validated via Pydantic (length + character whitelist)
* Reuses existing `short_code` column and unique constraint — no schema change needed
* Conflict returns HTTP 409 instead of 500 for clear API semantics

### TTL Expiration

* Optional `expires_in_days` field validated via Pydantic (positive integer)
* Model adds nullable `expires_at` column — `NULL` means never expires
* Expired URLs return HTTP **410 Gone** on redirect (semantically correct: resource existed but is no longer available)
* Lazy cleanup: expiration is checked at access time; no background cleanup job needed for current scale
* Alembic migration adds column + index on `expires_at` for query efficiency

### Connection Pooling

* Async engine with pool size and overflow configured
* Avoids per-request DB connection creation, improving performance under load

### Logging

* Async logging middleware prevents blocking requests
* Logs can be offloaded to Kafka or other observability services under heavy traffic

---

## 📝 Notes

* Built with **async-first design** for high concurrency
* Visit counting is minimal; timestamps, user-agent, and geo-tracking can be added
* Focus on modularity and maintainability; background tasks handle heavy workloads
* Main request path is lightweight; batch processing, logging, and analytics happen in background tasks
* * Both extensions (custom alias and TTL) are purely additive — all existing behavior remains unchanged when optional fields are omitted
