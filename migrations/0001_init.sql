CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS workers (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  payout_address TEXT NOT NULL,
  mode TEXT NOT NULL DEFAULT 'gpu',
  last_seen REAL NOT NULL,
  keys_done INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS bins (
  id INTEGER PRIMARY KEY,
  start_hex TEXT NOT NULL,
  end_hex TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'free',
  worker_id TEXT,
  keys_done INTEGER NOT NULL DEFAULT 0,
  claimed_at REAL,
  completed_at REAL
);
CREATE TABLE IF NOT EXISTS found (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  worker_id TEXT,
  payout_address TEXT,
  privkey TEXT NOT NULL,
  hash160 TEXT,
  found_at REAL NOT NULL
);
