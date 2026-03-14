# STS2 Tracker - CLAUDE.md

## プロジェクト概要
Slay the Spire 2の統計トラッカー。ローカルexeがセーブファイルを監視してSupabaseに送信、SvelteKitダッシュボードで統計を表示する。

## アーキテクチャ

### コンポーネント構成
- `src/` — SvelteKit フロントエンド（TypeScript + TailwindCSS）
- `backend/` — FastAPI バックエンド（Python）
- `local-agent/` — ローカル監視スクリプト（Python → exe配布）
- `supabase/` — DBマイグレーション・RLS設定

### データフロー
```
セーブファイル → local-agent（watchdog）→ FastAPI → Supabase
                                                        ↓
                                            SvelteKit ← Supabase直接クエリ（統計）
```

### 認証フロー
1. local-agent初回起動時にUUIDを生成してローカル保存（`~/.sts2tracker/config.json`）
2. FastAPI経由でSupabase匿名ユーザー作成
3. JWTをローカル保存・以降はそのJWTで認証
4. ブラウザ起動時はURLにJWTを付与して自動ログイン

## セーブファイル
- パス: `C:\Users\{username}\AppData\Roaming\SlayTheSpire2\steam\{steamID}\profile1\saves\history\`
- 形式: 読める平文JSON・難読化なし
- 検出: 新規ファイル追加をwatchdogで監視

## 重要な設計方針

### DB
- 生データを全部保存する（集計はクエリ時・統計追加に柔軟対応）
- RLSを有効にする：書き込みは本人のみ・読み取りは全員OK
- 個人特定情報は一切収集しない（Steam IDも収集しない）
- `uploaded_at`カラムで重複アップロード防止（ファイルhashはなし・run_idで一意性保証）

### セキュリティ
- UUIDで匿名認証（ユーザー登録不要）
- RLSで他人のデータを書き換え不可
- FastAPI側でレートリミット（slowapi使用）
- 全テーブルにuser_idを持たせてRLSポリシーを適用

### フロントエンド
- 未ログイン: 全ユーザーの集計統計のみ表示
- ログイン後: 個人統計 + 全体統計
- SSR不要なページはprerender=true（Cloudflare Pagesの静的配信を活かす）
- 重い統計クエリはSupabase RPCを使う

### ローカルエージェント
- 重複送信防止: 送信済みファイル名をローカルDBに記録（SQLite）
- オフライン対応: 送信失敗時はキューに積んで再試行
- exeはPyInstallerでビルド

## 技術スタック詳細
- フロントエンド: SvelteKit + TypeScript + TailwindCSS + Supabase JS Client
- バックエンド: FastAPI + Pydantic v2 + slowapi + supabase-py
- DB: Supabase（PostgreSQL）
- ローカル: Python + watchdog + SQLite（PyInstaller→exe）
- デプロイ: Cloudflare Pages（フロント）+ Fly.io or Render（FastAPI）

## ディレクトリ構成
```
sts2-tracker/
├── CLAUDE.md
├── src/                        # SvelteKit
│   ├── lib/
│   │   ├── supabase.ts         # Supabaseクライアント
│   │   ├── auth.ts             # 認証ユーティリティ
│   │   └── components/
│   └── routes/
│       ├── +layout.svelte
│       ├── +page.svelte        # トップ（全体統計）
│       ├── me/                 # 個人統計
│       └── runs/               # ラン詳細
├── backend/
│   ├── main.py
│   ├── routers/
│   │   ├── runs.py             # ランアップロードAPI
│   │   └── auth.py             # UUID認証
│   ├── models.py               # Pydanticモデル
│   ├── requirements.txt
│   └── venv/
├── local-agent/
│   ├── main.py                 # エントリポイント
│   ├── watcher.py              # ファイル監視
│   ├── uploader.py             # API送信
│   ├── config.py               # UUID管理
│   ├── queue.db                # SQLite（送信キュー・送信済み記録）
│   └── requirements.txt
└── supabase/
    ├── migrations/
    │   └── 001_initial.sql
    └── seed.sql
```

## コーディング規約
- Python: black + ruff・型ヒント必須
- TypeScript: strict mode
- コミットはfeat/fix/chore/docsプレフィックス
- テーブルカラムはsnake_case・TSはcamelCase（Supabase JSが自動変換）
