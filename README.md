
### 📄 `README.md`


# 🔗 URL Shortener – Python FastAPI Interview Task

This is a simple, scalable URL shortening service built with **FastAPI**, **SQLModel**, and **Alembic**.

This project is part of a technical interview process and is designed to showcase:
- Clean architecture & maintainable code
- Performance & scalability considerations
- Logging and observability practices
- Experience with SQLAlchemy / SQLModel, Alembic, and REST APIs

---

## 🧩 Features

- Create short URLs (`POST /shorten`)
- Redirect to original URL (`GET /{short_code}`)
- Track and view visit statistics (`GET /stats/{short_code}`)
- Custom logging with middleware
- Modular and scalable codebase structure

---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/mahdimmr/url-shortener.git
cd url-shortener
```

### 2. Create virtual environment & install dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```

### 3. Setup the database

> By default, it uses PostgreSQL, Look at in `sample.env` PG_DSN.

```bash
cp sample.env .env
alembic upgrade head
```

### 4. Run the app

```bash
uvicorn app.main:app --reload
```

Open your browser at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Running Tests

```bash
pytest
```

---

## 📁 Project Structure

```
app/
├── api/           # FastAPI routers
├── core/          # Configuration, shared utilities
├── db/            # Models, session, CRUD, migrations
├── middleware/    # Logging or custom middleware
├── main.py        # FastAPI app entrypoint
```

---

## 📌 Notes for Interviewers

- The implementation is scoped to take ~1 working day.
- Logging is implemented using a custom middleware.
- Visit tracking is minimal; can be extended to store timestamps/user-agent/etc.
- Add any modules, files, or dependencies you find necessary.
- In short: you’re free to treat this as a real project.
- For production: add rate limiting, background jobs for analytics, async DB access, etc.
- We're more interested in how you think and structure your work than in having one "correct" answer. Good luck, and
  enjoy the process!

---

## 🧠 Bonus Ideas (if you have time)

- Custom short code support
- Expiration time for URLs
- Admin dashboard to view top URLs
- Dockerfile & deployment configs

---
