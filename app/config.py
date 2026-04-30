from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # DB
    database_url: str = "sqlite:///./study_manager.db"
    db_ssl: bool = False  # Neon / Supabase など外部 PostgreSQL は True に

    # LINE
    line_channel_access_token: str = ""

    # Google OAuth (空 = Dev Mode)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/callback"

    # JWT
    jwt_secret_key: str = "change-me-with-openssl-rand-hex-32"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Cron endpoint protection
    cron_secret: str = "change-me"

    # CORS
    frontend_origin: str = "*"

    class Config:
        env_file = ".env"

    @property
    def auth_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)


settings = Settings()
