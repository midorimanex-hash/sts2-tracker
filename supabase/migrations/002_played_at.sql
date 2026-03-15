-- run_timestamp を played_at にリネームし、NOT NULL + DEFAULT NOW() に変更
ALTER TABLE runs RENAME COLUMN run_timestamp TO played_at;

-- 既存の NULL を現在時刻で埋める
UPDATE runs SET played_at = NOW() WHERE played_at IS NULL;

-- DEFAULT と NOT NULL を設定（以降は必ず値が入る）
ALTER TABLE runs ALTER COLUMN played_at SET DEFAULT NOW();
ALTER TABLE runs ALTER COLUMN played_at SET NOT NULL;

-- 日付順のクエリ用インデックス
CREATE INDEX IF NOT EXISTS idx_runs_played_at ON runs(played_at DESC);
