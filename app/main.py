from fastapi import FastAPI
from api import endpoints
from middleware.logging import add_logging_middleware

app = FastAPI()


app.include_router(endpoints.router)

add_logging_middleware(app)
