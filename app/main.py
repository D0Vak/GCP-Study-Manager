import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import settings
from app.database import Base, engine
from app.routers import auth, cron, events, notify, teams, users, webhook

logging.basicConfig(level=logging.INFO)

Base.metadata.create_all(bind=engine)

# スキーママイグレーション: 既存DBに新カラムを安全に追加
_migrations = [
    # TeamMember.is_admin (デフォルト0=False、既存行は全員管理者扱いになる→後方互換)
    "ALTER TABLE team_members ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0",
]

with engine.connect() as _conn:
    for _sql in _migrations:
        try:
            _conn.execute(text(_sql))
            _conn.commit()
        except Exception:
            pass  # カラムが既に存在する場合など

app = FastAPI(
    title="GCP Event Manager",
    description="GCPイベント管理システム",
    version="4.0.0",
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
app.include_router(notify.router)
app.include_router(webhook.router)

app.mount("/", StaticFiles(directory="static", html=True), name="static")
