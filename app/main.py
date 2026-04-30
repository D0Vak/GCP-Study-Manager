import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.routers import auth, cron, events, teams, users

logging.basicConfig(level=logging.INFO)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Study Manager",
    description="勉強会スケジュール管理システム",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin] if settings.frontend_origin != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(cron.router)
app.include_router(users.router)
app.include_router(teams.router)
app.include_router(events.router)

app.mount("/", StaticFiles(directory="static", html=True), name="static")
