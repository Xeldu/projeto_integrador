import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from .database import engine, Base
from .routes import router
from .simulator import simulate_readings


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    task = asyncio.create_task(simulate_readings())
    yield
    task.cancel()


app = FastAPI(
    title="Temperature Logger API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)
