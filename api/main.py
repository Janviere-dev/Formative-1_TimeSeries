from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.config import settings
from api.db import engine, get_readings_collection
from api.models import Base
from api.routers import health, mongo_readings, sql_readings


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.init_on_startup:
        Base.metadata.create_all(bind=engine)
        get_readings_collection().create_index("date_time")
    yield


app = FastAPI(title="Metro Interstate Traffic Volume API", lifespan=lifespan)
app.include_router(sql_readings.router)
app.include_router(mongo_readings.router)
app.include_router(health.router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "sql_readings": "/sql/readings",
        "mongo_readings": "/mongo/readings",
    }
