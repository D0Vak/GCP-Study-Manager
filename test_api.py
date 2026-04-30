"""
Integration test — run while server is up: python test_api.py
"""
import time
import httpx

base = "http://localhost:8000"
ts = int(time.time())


def main():
    # Users
    u1 = httpx.post(f"{base}/users", json={"name": f"Alice-{ts}", "line_id": "U_alice"}).json()
    u2 = httpx.post(f"{base}/users", json={"name": f"Bob-{ts}"}).json()
    print("Users:", u1["id"], u1["name"], "/", u2["id"], u2["name"])

    # Team
    t = httpx.post(f"{base}/teams", json={"name": f"Team-{ts}", "line_group_id": "Cgrp"}).json()
    print("Team:", t)

    # Members
    httpx.post(f"{base}/teams/{t['id']}/members", json={"user_id": u1["id"]})
    httpx.post(f"{base}/teams/{t['id']}/members", json={"user_id": u2["id"]})
    members = httpx.get(f"{base}/teams/{t['id']}/members").json()
    print("Members:", [m["name"] for m in members])

    # Event (no Attendance pre-generated)
    ev = httpx.post(f"{base}/events", json={
        "team_id": t["id"], "title": "Python Study #1", "scheduled_at": "2026-05-10T19:00:00"
    }).json()
    print("Event:", ev)

    # Attendance — all should be pending (no DB records)
    att_init = httpx.get(f"{base}/events/{ev['id']}/attendance").json()
    print("[initial]", [(a["user"]["name"], a["status"]) for a in att_init])
    assert all(a["status"] == "pending" for a in att_init), "Expected all pending"

    # Upsert: Alice → yes
    httpx.put(f"{base}/events/{ev['id']}/attendance", json={"user_id": u1["id"], "status": "yes"})
    att_after = httpx.get(f"{base}/events/{ev['id']}/attendance").json()
    print("[after yes]", [(a["user"]["name"], a["status"]) for a in att_after])

    # No-response — only Bob
    no_resp = httpx.get(f"{base}/events/{ev['id']}/attendance/no-response").json()
    print("[no-resp]", [u["name"] for u in no_resp])
    assert len(no_resp) == 1 and no_resp[0]["name"] == "Bob"

    # Next event
    nxt = httpx.get(f"{base}/events/next?team_id={t['id']}").json()
    print("[next]", nxt["title"] if nxt else None)

    # Status update
    httpx.patch(f"{base}/events/{ev['id']}/status", json={"status": "done"})
    nxt_after = httpx.get(f"{base}/events/next?team_id={t['id']}").json()
    print("[next after done]", nxt_after)
    assert nxt_after is None, "No next event after marking done"

    # Notifications (log-only since no LINE token)
    sumr = httpx.post(f"{base}/events/{ev['id']}/notify/summary").json()
    print("[summary notify]", sumr)

    print("\n✓ All checks passed")


if __name__ == "__main__":
    main()
