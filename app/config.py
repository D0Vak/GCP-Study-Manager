from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # DB
    database_url: str = "sqlite:///./study_manager.db"
    db_ssl: bool = False

    # LINE Login（認証用チャンネル）
    line_login_channel_id: str = ""
    line_login_channel_secret: str = ""
    line_login_redirect_uri: str = "http://localhost:8000/auth/callback"

    # LINE Messaging API（通知用チャンネル）
    line_channel_access_token: str = ""

    # JWT
    jwt_secret_key: str = "change-me-with-openssl-rand-hex-32"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Cron
    cron_secret: str = "change-me"

    # CORS
    frontend_origin: str = "*"

    class Config:
        env_file = ".env"

    @property
    def auth_enabled(self) -> bool:
        return bool(self.line_login_channel_id and self.line_login_channel_secret)


settings = Settings()
