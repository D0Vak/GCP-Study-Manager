"""
外部 cron サービス（cron-job.org など）から呼ばれるエンドポイント。
Render の無料プランはアイドル時にスリープするため、APScheduler の代わりにこれを使う。

設定例（cron-job.org）:
  URL:    POST https://your-app.onrender.com/cron/daily-reminder
  Header: X-Cron-Secret: <CRON_SECRET>
  Schedule: 毎日 09:00 JST (00:00 UTC)
"""
import logging

from fastapi import APIRouter, Header, HTTPException

from app.config import settings
from app.services.notification_service import run_daily_reminders

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cron", tags=["cron"])


def _check_secret(x_cron_secret: str | None) -> None:
    if not x_cron_secret or x_cron_secret != settings.cron_secret:
        raise HTTPException(status_code=403, detail="Invalid cron secret")


@router.post("/daily-reminder")
def daily_reminder(x_cron_secret: str | None = Header(default=None)):
    """前日リマインドを手動または外部 cron から実行する"""
    _check_secret(x_cron_secret)
    logger.info("Cron: daily-reminder triggered")
    run_daily_reminders()
    return {"message": "Daily reminders sent"}
