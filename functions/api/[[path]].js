const PUZZLE_START = BigInt("0x40000000000000000");
const PUZZLE_END = BigInt("0x7ffffffffffffffff");
const MAP_BINS = 2500;
const TARGET_H160 = "f6f5431d25bbf7b12e8add9af5e3475c44a0a5b8";
const PUZZLE_ADDR = "1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU";
const TREASURY = "1Ps8hoKzRjdZdDphFwBjm6qiAzDxFYXAFe";
const FINDER_BTC = 3.0;
const TOTAL_REWARD_BTC = 7.1;

function hex256(n) {
  return n.toString(16).padStart(64, "0");
}

function binRange(binId) {
  const total = PUZZLE_END - PUZZLE_START + 1n;
  const size = total / BigInt(MAP_BINS);
  const s = PUZZLE_START + BigInt(binId) * size;
  const e = binId === MAP_BINS - 1 ? PUZZLE_END : s + size - 1n;
  return { s, e };
}

async function ensureBins(db) {
  const row = await db.prepare("SELECT COUNT(*) AS c FROM bins").first();
  if (row && row.c > 0) return;
  const stmts = [];
  for (let i = 0; i < MAP_BINS; i++) {
    const { s, e } = binRange(i);
    stmts.push(db.prepare("INSERT INTO bins(id,start_hex,end_hex,status) VALUES(?,?,?,?)")
      .bind(i, hex256(s), hex256(e), "free"));
  }
  await db.batch(stmts);
}

async function getFound(db) {
  const row = await db.prepare(
    "SELECT worker_id,payout_address,privkey,hash160,found_at FROM found ORDER BY id DESC LIMIT 1"
  ).first();
  if (!row) return null;
  return row;
}

async function buildStatus(db) {
  await ensureBins(db);
  const counts = await db.prepare("SELECT status, COUNT(*) AS c FROM bins GROUP BY status").all();
  const stats = {};
  for (const r of counts.results || []) stats[r.status] = r.c;
  const done = stats.done || 0;
  const active = stats.active || 0;
  const free = stats.free || 0;
  const pct = MAP_BINS ? (done / MAP_BINS * 100) : 0;

  const workers = await db.prepare(
    "SELECT id,name,payout_address,mode,keys_done,last_seen FROM workers ORDER BY keys_done DESC LIMIT 50"
  ).all();

  const bins = await db.prepare("SELECT id,status FROM bins ORDER BY id").all();
  const map_status = (bins.results || []).map(b => b.status === "done" ? 2 : b.status === "active" ? 1 : 0);

  const found = await getFound(db);

  return {
    ok: true,
    puzzle_address: PUZZLE_ADDR,
    target_hash160: TARGET_H160,
    treasury_address: TREASURY,
    finder_reward_btc: FINDER_BTC,
    treasury_btc: TOTAL_REWARD_BTC - FINDER_BTC,
    range_start_hex: hex256(PUZZLE_START),
    range_end_hex: hex256(PUZZLE_END),
    map_bins: MAP_BINS,
    map_side: Math.round(Math.sqrt(MAP_BINS)),
    bins_free: free,
    bins_active: active,
    bins_done: done,
    progress_pct: Math.round(pct * 1e6) / 1e6,
    workers: (workers.results || []).map(w => ({
      ...w,
      online: (Date.now() / 1000 - w.last_seen) < 180,
    })),
    map_status,
    found,
  };
}

async function registerWorker(db, data) {
  const worker_id = (data.worker_id || "").trim();
  const payout_address = (data.payout_address || "").trim();
  const name = (data.name || worker_id).trim();
  const mode = (data.mode || "gpu").toLowerCase();
  if (!worker_id || !payout_address) return { ok: false, error: "worker_id i payout_address wymagane" };
  await db.prepare(
    "INSERT INTO workers(id,name,payout_address,mode,last_seen) VALUES(?,?,?,?,?) "
    + "ON CONFLICT(id) DO UPDATE SET name=excluded.name, payout_address=excluded.payout_address, "
    + "mode=excluded.mode, last_seen=excluded.last_seen"
  ).bind(worker_id, name, payout_address, mode === "cpu" ? "cpu" : "gpu", Date.now() / 1000).run();
  return { ok: true };
}

async function claimBin(db, data) {
  const worker_id = (data.worker_id || "").trim();
  const bin_id = data.bin_id != null ? parseInt(data.bin_id, 10) : null;
  const found = await getFound(db);
  if (found) return { status: "found", ...found };

  const w = await db.prepare("SELECT payout_address FROM workers WHERE id=?").bind(worker_id).first();
  if (!w) return { ok: false, error: "Najpierw zarejestruj worker (payout address)" };

  let row;
  if (bin_id != null && !Number.isNaN(bin_id)) {
    row = await db.prepare("SELECT id,start_hex,end_hex,status FROM bins WHERE id=?").bind(bin_id).first();
    if (!row) return { ok: false, error: "Nieprawidlowy bin" };
    if (row.status !== "free") return { ok: false, error: "Ten kwadracik juz zajety", status: row.status };
  } else {
    row = await db.prepare("SELECT id,start_hex,end_hex,status FROM bins WHERE status='free' ORDER BY id LIMIT 1").first();
    if (!row) return { status: "exhausted", message: "Calosc rozdana" };
  }

  const now = Date.now() / 1000;
  await db.prepare("UPDATE bins SET status='active', worker_id=?, claimed_at=? WHERE id=?")
    .bind(worker_id, now, row.id).run();
  await db.prepare("UPDATE workers SET last_seen=? WHERE id=?").bind(now, worker_id).run();

  return {
    status: "ok",
    bin_id: row.id,
    start: row.start_hex,
    end: row.end_hex,
    target: TARGET_H160,
    payout_address: w.payout_address,
  };
}

async function completeBin(db, data) {
  const worker_id = (data.worker_id || "").trim();
  const bin_id = parseInt(data.bin_id, 10);
  const keys_done = parseInt(data.keys_done || 0, 10);
  const now = Date.now() / 1000;
  await db.prepare("UPDATE bins SET status='done', keys_done=?, completed_at=? WHERE id=? AND worker_id=?")
    .bind(keys_done, now, bin_id, worker_id).run();
  await db.prepare("UPDATE workers SET last_seen=? WHERE id=?").bind(now, worker_id).run();
  return { ok: true };
}

async function reportFound(db, data) {
  const worker_id = (data.worker_id || "").trim();
  const privkey = (data.privkey || "").trim();
  const hash160 = (data.hash160 || TARGET_H160).trim();
  const payout_address = (data.payout_address || "").trim();
  await db.prepare(
    "INSERT INTO found(worker_id,payout_address,privkey,hash160,found_at) VALUES(?,?,?,?,?)"
  ).bind(worker_id, payout_address, privkey, hash160, Date.now() / 1000).run();
  return {
    ok: true,
    message: `Trafienie! ${FINDER_BTC} BTC -> ${payout_address}, reszta -> ${TREASURY}`,
  };
}

function cors(json, status = 200) {
  return new Response(JSON.stringify(json), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store",
    },
  });
}

export async function onRequestOptions() {
  return new Response(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    },
  });
}

export async function onRequest(context) {
  const { request, env } = context;
  const db = env.DB;
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, "");

  try {
    if (request.method === "GET") {
      if (path === "/api/status" || path === "/api" || path === "/status") {
        return cors(await buildStatus(db));
      }
      if (path === "/api/health" || path === "/health") {
        return cors({ ok: true });
      }
      return cors({ error: "not found" }, 404);
    }

    if (request.method === "POST") {
      const data = await request.json().catch(() => ({}));
      if (path === "/api/register") return cors(await registerWorker(db, data));
      if (path === "/api/claim") return cors(await claimBin(db, data));
      if (path === "/api/complete") return cors(await completeBin(db, data));
      if (path === "/api/found") return cors(await reportFound(db, data));
      return cors({ error: "not found" }, 404);
    }

    return cors({ error: "method not allowed" }, 405);
  } catch (e) {
    return cors({ error: String(e) }, 500);
  }
}
