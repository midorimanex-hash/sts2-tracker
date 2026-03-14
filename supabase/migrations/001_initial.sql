-- ============================================================
-- STS2 Tracker - Initial Schema
-- ============================================================
-- 方針:
--   - 生データを全保存（集計はクエリ時に行う）
--   - RLS有効: 書き込みは本人のみ・読み取りは全員OK
--   - 個人特定情報は収集しない
-- ============================================================

-- ============================================================
-- EXTENSION
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE users (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- RUNS（ランの基本情報）
-- ============================================================
CREATE TABLE runs (
  id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id              UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  -- 識別
  source_filename      TEXT NOT NULL,  -- セーブファイル名（重複アップロード防止）

  -- キャラ・設定
  character            TEXT NOT NULL,  -- e.g. "IRONCLAD", "SILENT"
  ascension            INT  NOT NULL DEFAULT 0,

  -- 勝敗
  win                  BOOLEAN NOT NULL,
  was_abandoned        BOOLEAN NOT NULL DEFAULT FALSE,
  killed_by_encounter  TEXT,           -- 死因（nullなら生存またはabandon）

  -- アクト構成（生JSON）
  acts                 JSONB,

  -- タイムスタンプ
  run_timestamp        TIMESTAMPTZ,    -- セーブファイル内のタイムスタンプ（あれば）
  uploaded_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (user_id, source_filename)    -- 同一ユーザーの重複アップロード防止
);

CREATE INDEX idx_runs_user_id   ON runs(user_id);
CREATE INDEX idx_runs_character ON runs(character);
CREATE INDEX idx_runs_win       ON runs(win);
CREATE INDEX idx_runs_ascension ON runs(ascension);

-- ============================================================
-- FLOOR_EVENTS（フロアごとの部屋・エンカウンター情報）
-- ============================================================
CREATE TABLE floor_events (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_id       UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,  -- RLS用

  floor        INT  NOT NULL,
  act          INT  NOT NULL,
  room_type    TEXT NOT NULL,  -- e.g. "MONSTER", "ELITE", "BOSS", "SHOP", "REST", "EVENT", "TREASURE"
  encounter_id TEXT,           -- エンカウンターID（あれば）
  event_id     TEXT            -- イベントID（あれば）
);

CREATE INDEX idx_floor_events_run_id ON floor_events(run_id);
CREATE INDEX idx_floor_events_user_id ON floor_events(user_id);

-- ============================================================
-- FLOOR_STATS（フロアごとのHP・ゴールド状態）
-- ============================================================
CREATE TABLE floor_stats (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_id       UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  floor        INT NOT NULL,
  current_hp   INT NOT NULL,
  max_hp       INT NOT NULL,
  gold         INT NOT NULL
);

CREATE INDEX idx_floor_stats_run_id ON floor_stats(run_id);
CREATE INDEX idx_floor_stats_user_id ON floor_stats(user_id);

-- ============================================================
-- CARD_CHOICES（カード選択履歴）
-- ============================================================
CREATE TABLE card_choices (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_id       UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  floor        INT  NOT NULL,
  picked       TEXT,              -- 選んだカードID（nullはスキップ）
  skipped      BOOLEAN NOT NULL DEFAULT FALSE,
  not_picked   TEXT[]  NOT NULL DEFAULT '{}'  -- 選ばなかったカードIDの配列
);

CREATE INDEX idx_card_choices_run_id  ON card_choices(run_id);
CREATE INDEX idx_card_choices_user_id ON card_choices(user_id);
CREATE INDEX idx_card_choices_picked  ON card_choices(picked);

-- ============================================================
-- RELIC_CHOICES（レリック選択履歴）
-- ============================================================
CREATE TABLE relic_choices (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_id       UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  floor        INT  NOT NULL,
  source       TEXT NOT NULL,    -- e.g. "BOSS", "ELITE", "SHOP", "EVENT"
  picked       TEXT,             -- 選んだレリックID
  not_picked   TEXT[] NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_relic_choices_run_id  ON relic_choices(run_id);
CREATE INDEX idx_relic_choices_user_id ON relic_choices(user_id);

-- ============================================================
-- POTION_CHOICES（ポーション選択履歴）
-- ============================================================
CREATE TABLE potion_choices (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_id       UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  floor        INT  NOT NULL,
  picked       TEXT,
  not_picked   TEXT[] NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_potion_choices_run_id  ON potion_choices(run_id);
CREATE INDEX idx_potion_choices_user_id ON potion_choices(user_id);

-- ============================================================
-- POTION_EVENTS（ポーション使用・破棄履歴）
-- ============================================================
CREATE TABLE potion_events (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_id       UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  floor        INT  NOT NULL,
  potion_id    TEXT NOT NULL,
  action       TEXT NOT NULL     -- e.g. "USE", "DISCARD"
);

CREATE INDEX idx_potion_events_run_id  ON potion_events(run_id);
CREATE INDEX idx_potion_events_user_id ON potion_events(user_id);

-- ============================================================
-- REST_SITE_CHOICES（焚き火選択履歴）
-- ============================================================
CREATE TABLE rest_site_choices (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_id       UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  floor        INT  NOT NULL,
  action       TEXT NOT NULL,    -- e.g. "REST", "SMITH", "LIFT", "DIG", "RECALL", "TOKE"
  card_upgraded TEXT             -- SMITHの場合の対象カード
);

CREATE INDEX idx_rest_site_choices_run_id  ON rest_site_choices(run_id);
CREATE INDEX idx_rest_site_choices_user_id ON rest_site_choices(user_id);

-- ============================================================
-- ANCIENT_CHOICES（古代の選択履歴）
-- ============================================================
CREATE TABLE ancient_choices (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_id       UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  floor        INT  NOT NULL,
  ancient_id   TEXT NOT NULL,
  picked       TEXT NOT NULL,    -- 選んだボーナスID
  not_picked   TEXT[] NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_ancient_choices_run_id  ON ancient_choices(run_id);
CREATE INDEX idx_ancient_choices_user_id ON ancient_choices(user_id);

-- ============================================================
-- EVENT_CHOICES（イベント選択履歴）
-- ============================================================
CREATE TABLE event_choices (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_id       UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  floor        INT  NOT NULL,
  event_id     TEXT NOT NULL,
  option_chosen TEXT NOT NULL,
  -- イベントの結果（ゴールド増減・HP増減など生データ）
  result       JSONB
);

CREATE INDEX idx_event_choices_run_id  ON event_choices(run_id);
CREATE INDEX idx_event_choices_user_id ON event_choices(user_id);

-- ============================================================
-- SHOP_EVENTS（ショップ購入・除去履歴）
-- ============================================================
CREATE TABLE shop_events (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_id       UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  floor        INT  NOT NULL,
  action       TEXT NOT NULL,    -- e.g. "BUY_CARD", "BUY_RELIC", "BUY_POTION", "PURGE_CARD"
  item_id      TEXT NOT NULL,
  cost         INT  NOT NULL DEFAULT 0
);

CREATE INDEX idx_shop_events_run_id  ON shop_events(run_id);
CREATE INDEX idx_shop_events_user_id ON shop_events(user_id);

-- ============================================================
-- CARD_ENCHANTMENTS（カードエンチャント履歴）
-- ============================================================
CREATE TABLE card_enchantments (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_id         UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  floor          INT  NOT NULL,
  card_id        TEXT NOT NULL,
  enchantment    TEXT NOT NULL,  -- e.g. "UPGRADE", "TRANSFORM", "DUPLICATE"
  source         TEXT            -- エンチャント元（レリック名・イベント名など）
);

CREATE INDEX idx_card_enchantments_run_id  ON card_enchantments(run_id);
CREATE INDEX idx_card_enchantments_user_id ON card_enchantments(user_id);

-- ============================================================
-- DECK_CARDS（最終デッキ）
-- ============================================================
CREATE TABLE deck_cards (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_id      UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  card_id     TEXT NOT NULL,
  upgraded    BOOLEAN NOT NULL DEFAULT FALSE,
  count       INT NOT NULL DEFAULT 1  -- 同名カードのまとめ（複数枚の場合）
);

CREATE INDEX idx_deck_cards_run_id  ON deck_cards(run_id);
CREATE INDEX idx_deck_cards_user_id ON deck_cards(user_id);
CREATE INDEX idx_deck_cards_card_id ON deck_cards(card_id);

-- ============================================================
-- FINAL_RELICS（最終所持レリック）
-- ============================================================
CREATE TABLE final_relics (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_id     UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  relic_id   TEXT NOT NULL,
  slot       INT              -- 取得順（あれば）
);

CREATE INDEX idx_final_relics_run_id   ON final_relics(run_id);
CREATE INDEX idx_final_relics_user_id  ON final_relics(user_id);
CREATE INDEX idx_final_relics_relic_id ON final_relics(relic_id);

-- ============================================================
-- FINAL_POTIONS（最終所持ポーション）
-- ============================================================
CREATE TABLE final_potions (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_id     UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  potion_id  TEXT NOT NULL,
  slot       INT              -- スロット番号
);

CREATE INDEX idx_final_potions_run_id   ON final_potions(run_id);
CREATE INDEX idx_final_potions_user_id  ON final_potions(user_id);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

-- 全テーブルでRLSを有効化
ALTER TABLE users            ENABLE ROW LEVEL SECURITY;
ALTER TABLE runs             ENABLE ROW LEVEL SECURITY;
ALTER TABLE floor_events     ENABLE ROW LEVEL SECURITY;
ALTER TABLE floor_stats      ENABLE ROW LEVEL SECURITY;
ALTER TABLE card_choices     ENABLE ROW LEVEL SECURITY;
ALTER TABLE relic_choices    ENABLE ROW LEVEL SECURITY;
ALTER TABLE potion_choices   ENABLE ROW LEVEL SECURITY;
ALTER TABLE potion_events    ENABLE ROW LEVEL SECURITY;
ALTER TABLE rest_site_choices ENABLE ROW LEVEL SECURITY;
ALTER TABLE ancient_choices  ENABLE ROW LEVEL SECURITY;
ALTER TABLE event_choices    ENABLE ROW LEVEL SECURITY;
ALTER TABLE shop_events      ENABLE ROW LEVEL SECURITY;
ALTER TABLE card_enchantments ENABLE ROW LEVEL SECURITY;
ALTER TABLE deck_cards       ENABLE ROW LEVEL SECURITY;
ALTER TABLE final_relics     ENABLE ROW LEVEL SECURITY;
ALTER TABLE final_potions    ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- RLS POLICIES - users テーブル
-- ============================================================
-- 自分のレコードのみ参照可
CREATE POLICY "users: select own" ON users
  FOR SELECT USING (id = auth.uid());

-- 自分自身の作成のみ（匿名認証でauth.uid()と一致するIDのみ）
CREATE POLICY "users: insert own" ON users
  FOR INSERT WITH CHECK (id = auth.uid());

-- ============================================================
-- RLS POLICIES - runs テーブル
-- ============================================================
-- 全員読み取りOK（統計用）
CREATE POLICY "runs: select all" ON runs
  FOR SELECT USING (true);

-- 書き込みは本人のみ
CREATE POLICY "runs: insert own" ON runs
  FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY "runs: update own" ON runs
  FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY "runs: delete own" ON runs
  FOR DELETE USING (user_id = auth.uid());

-- ============================================================
-- RLS POLICIES - 子テーブル（runs以外の全テーブル）
-- ============================================================
-- マクロ的にまとめて定義
-- floor_events
CREATE POLICY "floor_events: select all" ON floor_events FOR SELECT USING (true);
CREATE POLICY "floor_events: insert own" ON floor_events FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "floor_events: delete own" ON floor_events FOR DELETE USING (user_id = auth.uid());

-- floor_stats
CREATE POLICY "floor_stats: select all" ON floor_stats FOR SELECT USING (true);
CREATE POLICY "floor_stats: insert own" ON floor_stats FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "floor_stats: delete own" ON floor_stats FOR DELETE USING (user_id = auth.uid());

-- card_choices
CREATE POLICY "card_choices: select all" ON card_choices FOR SELECT USING (true);
CREATE POLICY "card_choices: insert own" ON card_choices FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "card_choices: delete own" ON card_choices FOR DELETE USING (user_id = auth.uid());

-- relic_choices
CREATE POLICY "relic_choices: select all" ON relic_choices FOR SELECT USING (true);
CREATE POLICY "relic_choices: insert own" ON relic_choices FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "relic_choices: delete own" ON relic_choices FOR DELETE USING (user_id = auth.uid());

-- potion_choices
CREATE POLICY "potion_choices: select all" ON potion_choices FOR SELECT USING (true);
CREATE POLICY "potion_choices: insert own" ON potion_choices FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "potion_choices: delete own" ON potion_choices FOR DELETE USING (user_id = auth.uid());

-- potion_events
CREATE POLICY "potion_events: select all" ON potion_events FOR SELECT USING (true);
CREATE POLICY "potion_events: insert own" ON potion_events FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "potion_events: delete own" ON potion_events FOR DELETE USING (user_id = auth.uid());

-- rest_site_choices
CREATE POLICY "rest_site_choices: select all" ON rest_site_choices FOR SELECT USING (true);
CREATE POLICY "rest_site_choices: insert own" ON rest_site_choices FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "rest_site_choices: delete own" ON rest_site_choices FOR DELETE USING (user_id = auth.uid());

-- ancient_choices
CREATE POLICY "ancient_choices: select all" ON ancient_choices FOR SELECT USING (true);
CREATE POLICY "ancient_choices: insert own" ON ancient_choices FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "ancient_choices: delete own" ON ancient_choices FOR DELETE USING (user_id = auth.uid());

-- event_choices
CREATE POLICY "event_choices: select all" ON event_choices FOR SELECT USING (true);
CREATE POLICY "event_choices: insert own" ON event_choices FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "event_choices: delete own" ON event_choices FOR DELETE USING (user_id = auth.uid());

-- shop_events
CREATE POLICY "shop_events: select all" ON shop_events FOR SELECT USING (true);
CREATE POLICY "shop_events: insert own" ON shop_events FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "shop_events: delete own" ON shop_events FOR DELETE USING (user_id = auth.uid());

-- card_enchantments
CREATE POLICY "card_enchantments: select all" ON card_enchantments FOR SELECT USING (true);
CREATE POLICY "card_enchantments: insert own" ON card_enchantments FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "card_enchantments: delete own" ON card_enchantments FOR DELETE USING (user_id = auth.uid());

-- deck_cards
CREATE POLICY "deck_cards: select all" ON deck_cards FOR SELECT USING (true);
CREATE POLICY "deck_cards: insert own" ON deck_cards FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "deck_cards: delete own" ON deck_cards FOR DELETE USING (user_id = auth.uid());

-- final_relics
CREATE POLICY "final_relics: select all" ON final_relics FOR SELECT USING (true);
CREATE POLICY "final_relics: insert own" ON final_relics FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "final_relics: delete own" ON final_relics FOR DELETE USING (user_id = auth.uid());

-- final_potions
CREATE POLICY "final_potions: select all" ON final_potions FOR SELECT USING (true);
CREATE POLICY "final_potions: insert own" ON final_potions FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "final_potions: delete own" ON final_potions FOR DELETE USING (user_id = auth.uid());
