# Study Manager

勉強会スケジュール管理システム — **完全無料構成**

```
[ ブラウザ ]
     ↓
[ Render (FastAPI) — 無料 ]
     ↓
[ Neon PostgreSQL — 無料・永続 ]
     ↓
[ LINE API — 通知専用 ]

[ Google OAuth — 無料 ]  ← 認証だけに使用
[ cron-job.org — 無料 ]  ← 毎日 09:00 にリマインド自動実行
```

---

## ローカル開発（ゼロ設定で起動）

```bash
cd GCP-Study-Manager
pip install -r requirements.txt
cp .env.example .env
python run.py
# → http://localhost:8000/   (Dev Mode: 認証なし)
# → http://localhost:8000/docs
```

`GOOGLE_CLIENT_ID` を空のまま起動すると認証なしの **Dev Mode** で動きます。

---

## Render へのデプロイ手順

### 1. Neon で無料 PostgreSQL を作成

1. [neon.tech](https://neon.tech) でアカウント作成（無料・カード不要）
2. プロジェクト作成 → 「Connection string」をコピー
3. 形式: `postgresql://user:password@ep-xxx.region.aws.neon.tech/neondb`
4. pg8000 用に先頭を変更: `postgresql+pg8000://...`

### 2. Google OAuth 設定（無料）

1. [Google Cloud Console](https://console.cloud.google.com/apis/credentials) でプロジェクト作成
2. 「OAuth 2.0 クライアント ID」作成 → 種類: Webアプリ
3. 承認済みリダイレクト URI に追加:
   ```
   https://your-app.onrender.com/auth/callback
   ```
4. クライアント ID・シークレットをメモ

> Google OAuth は無料。Cloud Run や Cloud SQL は **使わない**。

### 3. Render でデプロイ

1. [render.com](https://render.com) でアカウント作成（無料）
2. 「New Web Service」→ GitHub リポジトリを接続
3. Render が `render.yaml` を自動検出
4. 「Environment」タブで以下を設定:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | `postgresql+pg8000://...` (Neon の接続文字列) |
| `DB_SSL` | `true` |
| `GOOGLE_CLIENT_ID` | Google Console から |
| `GOOGLE_CLIENT_SECRET` | Google Console から |
| `GOOGLE_REDIRECT_URI` | `https://your-app.onrender.com/auth/callback` |
| `CRON_SECRET` | 任意のランダム文字列 |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Developers から（任意） |

5. 「Deploy」ボタンを押す

### 4. cron-job.org でリマインド自動化（無料）

1. [cron-job.org](https://cron-job.org) でアカウント作成（無料）
2. 新しい Cron Job を作成:
   - **URL**: `https://your-app.onrender.com/cron/daily-reminder`
   - **Method**: POST
   - **Header**: `X-Cron-Secret: <CRON_SECRETの値>`
   - **Schedule**: 毎日 09:00 (UTC+9 = JST の場合は 00:00 UTC)

> Render 無料プランはアイドル15分でスリープします。cron-job.org が毎日 ping することで
> アプリが起動し、前日リマインドが実行されます。

---

## API 一覧

### 認証（公開）
| Method | Path | 説明 |
|--------|------|------|
| GET | /auth/mode | Dev Mode か判定 |
| GET | /auth/google | Google ログイン開始 |
| GET | /auth/callback | OAuth コールバック |
| GET | /auth/me | 現在のユーザー情報 |

### Cron（X-Cron-Secret ヘッダー必須）
| Method | Path | 説明 |
|--------|------|------|
| POST | /cron/daily-reminder | 翌日イベントにリマインド送信 |

### 以下は JWT 必須（Dev Mode は不要）

| Method | Path | 説明 |
|--------|------|------|
| POST/GET | /users | ユーザー作成・一覧 |
| POST/GET | /teams | チーム作成・一覧 |
| POST/GET | /teams/{id}/members | メンバー追加・一覧 |
| POST/GET | /events | 勉強会作成・一覧 |
| GET | /events/next?team_id=N | 次の勉強会 |
| PATCH | /events/{id}/status | 状態更新 |
| PUT/GET | /events/{id}/attendance | 出欠登録・一覧 |
| GET | /events/{id}/attendance/no-response | 未回答者 |
| POST | /events/{id}/notify/* | 通知送信 |

---

## 無料枠まとめ

| サービス | 無料枠 | 制限 |
|---------|--------|------|
| Render Web | 750時間/月 | 15分アイドルでスリープ |
| Neon PostgreSQL | 0.5GB, 無期限 | コンピュート時間に上限あり |
| Google OAuth | 無制限 | Google アカウントが必要 |
| cron-job.org | 無制限 | 最短5分間隔 |
| LINE Messaging API | 200通/月 | 超過は有料 |
