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

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models.group_member import GroupMember
from app.models.team import Team
from app.models.user import User
from app.services.notification_service import (
    _push_text,
    _push_with_quick_reply,
    fetch_group_member_ids,
    get_group_member_profile,
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


@router.get("/groups/{group_id}/members-status")
def group_members_status(group_id: str, db: Session = Depends(get_db)):
    """
    グループIDを元に：
    - DBに蓄積されたLINEメンバーIDと、それに紐付くユーザー情報
    - そのグループを持つチームのメンバーのうちLINE ID未設定のユーザー
    を返す。
    """
    # このgroup_idを持つチームを検索
    team = db.query(Team).filter(Team.line_group_id == group_id).first()

    # DBに蓄積されたグループメンバー
    group_members = (
        db.query(GroupMember)
        .filter_by(group_id=group_id)
        .order_by(GroupMember.first_seen)
        .all()
    )

    # LINE IDでユーザーを逆引きするマップ
    all_users = db.query(User).all()
    line_id_to_user = {u.line_id: u for u in all_users if u.line_id}

    members_result = []
    for gm in group_members:
        matched = line_id_to_user.get(gm.line_user_id)
        members_result.append({
            "line_user_id": gm.line_user_id,
            "display_name": gm.display_name,
            "last_seen": gm.last_seen,
            "matched_user": {"id": matched.id, "name": matched.name} if matched else None,
        })

    # チームメンバーのうちLINE ID未設定のユーザー
    no_line_id_users = []
    if team:
        from app.models.team import TeamMember
        team_user_ids = {m.user_id for m in db.query(TeamMember).filter_by(team_id=team.id).all()}
        no_line_id_users = [
            {"id": u.id, "name": u.name}
            for u in all_users
            if u.id in team_user_ids and not u.line_id
        ]

    return {
        "group_id": group_id,
        "team": {"id": team.id, "name": team.name} if team else None,
        "line_members": members_result,
        "no_line_id_users": no_line_id_users,
    }


@router.post("/groups/{group_id}/prompt-members")
def prompt_members_to_send_id(group_id: str):
    """
    グループにクイックリプライ付きメッセージをプッシュする。
    メンバーはボタンをタップするだけでLINE IDを取得できる。
    """
    msg = "【管理者からのお知らせ】\nメンバー登録のため、下のボタンをタップしてください。\nLINE IDがあなたのトークに個別に届きます（グループには表示されません）。"
    quick_reply_items = [
        {
            "type": "action",
            "action": {
                # postback型はタップしてもグループに何も表示されない
                "type": "postback",
                "label": "自分のLINE IDを確認する",
                "data": f"action=get_line_id&group_id={group_id}",
                # displayText を省略することでグループ履歴に何も残らない
            },
        }
    ]
    _push_with_quick_reply(group_id, msg, quick_reply_items)
    return {"status": "sent"}
