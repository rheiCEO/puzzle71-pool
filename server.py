#!/usr/bin/env python3
"""puzzle71-pool — serwer puli współdzielonej Puzzle #71."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web" / "index.html"
DB_PATH = ROOT / "pool.db"

PUZZLE_START = int(os.environ.get("PUZZLE71_RANGE_START", "0x40000000000000000"), 16)
PUZZLE_END = int(os.environ.get("PUZZLE71_RANGE_END", "0x7ffffffffffffffff"), 16)
MAP_BINS = int(os.environ.get("POOL_MAP_BINS", "2500"))  # 50x50
TARGET_H160 = "f6f5431d25bbf7b12e8add9af5e3475c44a0a5b8"
PUZZLE_ADDR = "1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU"
TREASURY = "1Ps8hoKzRjdZdDphFwBjm6qiAzDxFYXAFe"
FINDER_BTC = 3.0
TOTAL_REWARD_BTC = 7.1

_db_lock = threading.Lock()


def hex256(n: int) -> str:
    return format(n & ((1 << 256) - 1), "064x")


def bin_range(bin_id: int) -> tuple[int, int]:
    total = PUZZLE_END - PUZZLE_START + 1
    size = total // MAP_BINS
    s = PUZZLE_START + bin_id * size
    e = PUZZLE_END if bin_id == MAP_BINS - 1 else s + size - 1
    return s, e


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.executescript(
            """
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
            """
        )
        if con.execute("SELECT COUNT(*) FROM bins").fetchone()[0] == 0:
            rows = []
            for i in range(MAP_BINS):
                s, e = bin_range(i)
                rows.append((i, hex256(s), hex256(e), "free"))
            con.executemany(
                "INSERT INTO bins(id,start_hex,end_hex,status) VALUES(?,?,?,?)",
                rows,
            )
        con.execute(
            "INSERT OR IGNORE INTO meta(key,value) VALUES('initialized',?)",
            (str(time.time()),),
        )
        con.commit()


def get_found(con: sqlite3.Connection) -> dict | None:
    row = con.execute(
        "SELECT worker_id,payout_address,privkey,hash160,found_at FROM found ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    return {
        "worker": row[0],
        "payout_address": row[1],
        "privkey": row[2],
        "hash160": row[3],
        "at": row[4],
    }


def build_status() -> dict:
    with sqlite3.connect(DB_PATH) as con:
        counts = con.execute(
            "SELECT status, COUNT(*) FROM bins GROUP BY status"
        ).fetchall()
        stats = {k: v for k, v in counts}
        free = stats.get("free", 0)
        active = stats.get("active", 0)
        done = stats.get("done", 0)
        total_bins = MAP_BINS
        pct = (done / total_bins * 100) if total_bins else 0

        workers = [
            {
                "id": r[0],
                "name": r[1],
                "payout_address": r[2],
                "mode": r[3],
                "keys_done": r[4],
                "online": (time.time() - r[5]) < 180,
            }
            for r in con.execute(
                "SELECT id,name,payout_address,mode,keys_done,last_seen FROM workers ORDER BY keys_done DESC LIMIT 50"
            )
        ]

        map_status = [0] * MAP_BINS
        for bid, status in con.execute("SELECT id,status FROM bins"):
            if status == "done":
                map_status[bid] = 2
            elif status == "active":
                map_status[bid] = 1

        return {
            "ok": True,
            "puzzle_address": PUZZLE_ADDR,
            "target_hash160": TARGET_H160,
            "treasury_address": TREASURY,
            "finder_reward_btc": FINDER_BTC,
            "treasury_btc": TOTAL_REWARD_BTC - FINDER_BTC,
            "range_start_hex": hex256(PUZZLE_START),
            "range_end_hex": hex256(PUZZLE_END),
            "map_bins": MAP_BINS,
            "map_side": int(MAP_BINS ** 0.5),
            "bins_free": free,
            "bins_active": active,
            "bins_done": done,
            "progress_pct": round(pct, 6),
            "workers": workers,
            "map_status": map_status,
            "found": get_found(con),
        }


def register_worker(worker_id: str, name: str, payout_address: str, mode: str) -> dict:
    if not worker_id or not payout_address:
        return {"ok": False, "error": "worker_id i payout_address wymagane"}
    if mode not in ("gpu", "cpu"):
        mode = "gpu"
    with _db_lock:
        with sqlite3.connect(DB_PATH) as con:
            if get_found(con):
                return {"ok": False, "status": "found"}
            con.execute(
                "INSERT INTO workers(id,name,payout_address,mode,last_seen) VALUES(?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET name=excluded.name, payout_address=excluded.payout_address, "
                "mode=excluded.mode, last_seen=excluded.last_seen",
                (worker_id, name or worker_id, payout_address, mode, time.time()),
            )
            con.commit()
    return {"ok": True}


def claim_bin(worker_id: str, bin_id: int | None = None) -> dict:
    with _db_lock:
        with sqlite3.connect(DB_PATH) as con:
            if get_found(con):
                f = get_found(con)
                return {"status": "found", **f}

            w = con.execute(
                "SELECT payout_address FROM workers WHERE id=?", (worker_id,)
            ).fetchone()
            if not w:
                return {"ok": False, "error": "Najpierw zarejestruj worker (payout address)"}

            if bin_id is not None:
                row = con.execute(
                    "SELECT id,start_hex,end_hex,status FROM bins WHERE id=?",
                    (bin_id,),
                ).fetchone()
                if not row:
                    return {"ok": False, "error": "Nieprawidlowy bin"}
                if row[3] != "free":
                    return {"ok": False, "error": "Ten kwadracik juz zajety", "status": row[3]}
            else:
                row = con.execute(
                    "SELECT id,start_hex,end_hex,status FROM bins WHERE status='free' ORDER BY id LIMIT 1"
                ).fetchone()
                if not row:
                    return {"status": "exhausted", "message": "Calosc rozdana"}

            bid, start_hex, end_hex, _ = row
            now = time.time()
            con.execute(
                "UPDATE bins SET status='active', worker_id=?, claimed_at=? WHERE id=?",
                (worker_id, now, bid),
            )
            con.execute(
                "UPDATE workers SET last_seen=? WHERE id=?", (now, worker_id)
            )
            con.commit()
            return {
                "status": "ok",
                "bin_id": bid,
                "start": start_hex,
                "end": end_hex,
                "target": TARGET_H160,
                "payout_address": w[0],
            }


def update_progress(worker_id: str, bin_id: int, keys_done: int) -> dict:
    with _db_lock:
        with sqlite3.connect(DB_PATH) as con:
            con.execute(
                "UPDATE bins SET keys_done=? WHERE id=? AND worker_id=?",
                (keys_done, bin_id, worker_id),
            )
            con.execute(
                "UPDATE workers SET last_seen=?, keys_done=keys_done+? WHERE id=?",
                (time.time(), max(0, keys_done // 100), worker_id),
            )
            con.commit()
    return {"ok": True}


def complete_bin(worker_id: str, bin_id: int, keys_done: int) -> dict:
    with _db_lock:
        with sqlite3.connect(DB_PATH) as con:
            now = time.time()
            con.execute(
                "UPDATE bins SET status='done', keys_done=?, completed_at=? "
                "WHERE id=? AND worker_id=?",
                (keys_done, now, bin_id, worker_id),
            )
            con.execute(
                "UPDATE workers SET last_seen=? WHERE id=?", (now, worker_id)
            )
            con.commit()
    return {"ok": True}


def report_found(worker_id: str, privkey: str, hash160: str, payout_address: str) -> dict:
    with _db_lock:
        with sqlite3.connect(DB_PATH) as con:
            con.execute(
                "INSERT INTO found(worker_id,payout_address,privkey,hash160,found_at) VALUES(?,?,?,?,?)",
                (worker_id, payout_address, privkey, hash160, time.time()),
            )
            con.commit()
    return {
        "ok": True,
        "message": f"Trafienie! {FINDER_BTC} BTC -> {payout_address}, reszta -> {TREASURY}",
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json")

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length", 0))
        if n <= 0:
            return {}
        return json.loads(self.rfile.read(n))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            if WEB.exists():
                self._send(200, WEB.read_bytes(), "text/html; charset=utf-8")
            else:
                self._send(404, b"missing web/index.html", "text/plain")
        elif path in ("/api", "/api/status", "/status"):
            self._json(200, build_status())
        elif path == "/health":
            self._json(200, {"ok": True})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        data = self._read_json()

        if path == "/api/register":
            self._json(200, register_worker(
                str(data.get("worker_id", "")).strip(),
                str(data.get("name", "")).strip(),
                str(data.get("payout_address", "")).strip(),
                str(data.get("mode", "gpu")).strip().lower(),
            ))
        elif path == "/api/claim":
            bin_id = data.get("bin_id")
            self._json(200, claim_bin(
                str(data.get("worker_id", "")).strip(),
                int(bin_id) if bin_id is not None else None,
            ))
        elif path == "/api/progress":
            self._json(200, update_progress(
                str(data.get("worker_id", "")).strip(),
                int(data.get("bin_id", 0)),
                int(data.get("keys_done", 0)),
            ))
        elif path == "/api/complete":
            self._json(200, complete_bin(
                str(data.get("worker_id", "")).strip(),
                int(data.get("bin_id", 0)),
                int(data.get("keys_done", 0)),
            ))
        elif path == "/api/found":
            self._json(200, report_found(
                str(data.get("worker_id", "")).strip(),
                str(data.get("privkey", "")).strip(),
                str(data.get("hash160", TARGET_H160)).strip(),
                str(data.get("payout_address", "")).strip(),
            ))
        else:
            self._json(404, {"error": "not found"})


def main() -> None:
    ap = argparse.ArgumentParser(description="puzzle71-pool server")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8780")))
    args = ap.parse_args()

    init_db()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"puzzle71-pool: {url}")
    print(f"  puzzle:   {PUZZLE_ADDR}")
    print(f"  wypłata:  {FINDER_BTC} BTC znalazcy -> reszta {TREASURY}")
    print(f"  mapa:     {MAP_BINS} kwadracikow")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStop.")


if __name__ == "__main__":
    main()
