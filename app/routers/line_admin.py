"""
LINEグループメンバーID管理ルーター

GET  /line-admin/groups/{group_id}/members
     → DBに蓄積されたメンバーIDを返す

POST /line-admin/groups/{group_id}/fetch-members
     → LINE APIで一括取得を試みてDBに保存（認証済みチャンネルのみ成功）

POST /line-admin/groups/{group_id}/prompt-members
     → グループに「個人IDを送って」とプッシュして受動収集を促す
"""
from datetime import datetime

from fastapi import APIRouter

from app.database import SessionLocal
from app.models.group_member import GroupMember
from app.services.notification_service import (
    fetch_group_member_ids,
    get_group_member_profile,
    _push_text,
)

router = APIRouter(prefix="/line-admin", tags=["line-admin"])


@router.get("/groups/{group_id}/members")
def list_group_members(group_id: str):
    """DBに保存済みのグループメンバーID一覧を返す"""
    db = SessionLocal()
    try:
        members = (
            db.query(GroupMember)
            .filter_by(group_id=group_id)
            .order_by(GroupMember.first_seen)
            .all()
        )
        return [
            {
                "line_user_id": m.line_user_id,
                "display_name": m.display_name,
                "first_seen": m.first_seen,
                "last_seen": m.last_seen,
            }
            for m in members
        ]
    finally:
        db.close()


@router.post("/groups/{group_id}/fetch-members")
def fetch_members_from_line_api(group_id: str):
    """
    LINE APIでグループメンバーIDを一括取得してDBに保存する。
    認証済みチャンネル（Verified/Premium）のみ成功する。
    未認証の場合は saved=0, error="requires_verified_channel" を返す。
    """
    ids = fetch_group_member_ids(group_id)
    if not ids:
        return {"saved": 0, "error": "requires_verified_channel"}

    db = SessionLocal()
    saved = 0
    try:
        for uid in ids:
            existing = (
                db.query(GroupMember)
                .filter_by(group_id=group_id, line_user_id=uid)
                .first()
            )
            if existing:
                existing.last_seen = datetime.utcnow()
            else:
                profile = get_group_member_profile(group_id, uid)
                display_name = profile.get("displayName") if profile else None
                db.add(GroupMember(
                    group_id=group_id,
                    line_user_id=uid,
                    display_name=display_name,
                ))
                saved += 1
        db.commit()
    finally:
        db.close()

    return {"saved": saved, "total_fetched": len(ids)}


@router.post("/groups/{group_id}/prompt-members")
def prompt_members_to_send_id(group_id: str):
    """
    グループに「個人IDを送ってください」とプッシュする。
    受動収集を促すための管理者操作用。
    """
    msg = (
        "【管理者からのお知らせ】\n"
        "メンバー登録のため、このトーク内に\n\n"
        "　個人ID\n\n"
        "と送信してください。\n"
        "あなたのLINE IDがボットから返信されます。"
    )
    _push_text(group_id, msg)
    return {"status": "sent"}
