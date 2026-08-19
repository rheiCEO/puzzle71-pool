#!/usr/bin/env python3
"""Worker puli — lokalne GPU (puzzle71-cuda) lub CPU."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FOUND_RE = re.compile(r"Klucz:\s*([0-9a-fA-F]+)", re.I)
H160_RE = re.compile(r"Hash160:\s*([0-9a-fA-F]+)", re.I)


def find_solver() -> Path | None:
    candidates = [
        ROOT / "bin" / "puzzle71-cuda.exe",
        ROOT / "bin" / "puzzle71-cuda",
        ROOT.parent / "puzzle71-cuda" / "bin" / "puzzle71-cuda.exe",
        ROOT.parent / "puzzle71-cuda" / "bin" / "puzzle71-cuda",
    ]
    env = os.environ.get("PUZZLE71_CUDA")
    if env:
        candidates.insert(0, Path(env))
    for p in candidates:
        if p.exists():
            return p
    return None


def api(base: str, path: str, data: dict | None = None) -> dict:
    url = base.rstrip("/") + path
    if data is None:
        req = urllib.request.Request(url, method="GET")
    else:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_gpu(solver: Path, claim: dict, ckpt: Path) -> tuple[bool, str | None, str | None, int]:
    cmd = [
        str(solver), "--mode", "sequential",
        "--start", claim["start"],
        "--end", claim["end"],
        "--target", claim.get("target", "f6f5431d25bbf7b12e8add9af5e3475c44a0a5b8"),
        "--checkpoint", str(ckpt),
        "--work-scale", os.environ.get("WORK_SCALE", "16"),
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    assert proc.stdout
    lines = []
    for line in proc.stdout:
        print(line, end="")
        lines.append(line)
    proc.wait()
    full = "".join(lines)
    if "ZNALEZIONO" in full:
        km = FOUND_RE.search(full)
        hm = H160_RE.search(full)
        return True, km.group(1) if km else None, hm.group(1) if hm else None, 0
    start_i = int(claim["start"], 16)
    end_i = int(claim["end"], 16)
    return False, None, None, end_i - start_i + 1


def run_cpu(claim: dict) -> tuple[bool, str | None, str | None, int]:
    from cpu_search import search_range
    start_i = int(claim["start"], 16)
    end_i = int(claim["end"], 16)
    target = claim.get("target", "f6f5431d25bbf7b12e8add9af5e3475c44a0a5b8")

    def progress(n: int) -> None:
        if n % 50000 == 0:
            print(f"CPU: {n} kluczy...", end="\r")

    hit = search_range(start_i, end_i, target, progress_cb=progress, max_keys=500000)
    if hit:
        return True, hit["privkey"], hit["hash160"], hit["checked"]
    return False, None, None, min(500000, end_i - start_i + 1)


def main() -> None:
    if len(sys.argv) < 4:
        print("Uzycie: python worker.py URL ADRES_BTC [gpu|cpu] [nick]")
        print("Przyklad: python worker.py http://127.0.0.1:8780 bc1q... gpu Kuba")
        sys.exit(1)

    base = sys.argv[1].rstrip("/")
    payout = sys.argv[2].strip()
    mode = sys.argv[3].strip().lower() if len(sys.argv) > 3 else "gpu"
    nick = sys.argv[4].strip() if len(sys.argv) > 4 else "miner"
    worker_id = re.sub(r"[^a-zA-Z0-9_-]", "_", nick)[:32] or "worker"

    solver = find_solver()
    if mode == "gpu" and not solver:
        print("Brak puzzle71-cuda — ustaw PUZZLE71_CUDA lub zbuduj ../puzzle71-cuda")
        print("Albo uzyj trybu cpu")
        sys.exit(1)

    print(f"Pool worker: {nick} ({worker_id})")
    print(f"Serwer: {base}")
    print(f"Wypłata: {payout}")
    print(f"Tryb: {mode}\n")

    api(base, "/api/register", {
        "worker_id": worker_id,
        "name": nick,
        "payout_address": payout,
        "mode": mode,
    })

    while True:
        try:
            st = api(base, "/api/status")
            if st.get("found"):
                print("\n*** JUZ ZNALEZIONO ***")
                break

            claim = api(base, "/api/claim", {"worker_id": worker_id})
            if claim.get("status") == "found":
                print("\n*** JUZ ZNALEZIONO ***")
                break
            if claim.get("status") == "exhausted":
                print("\nCalosc rozdana.")
                break
            if claim.get("status") != "ok":
                print("Czekam...", claim.get("error", claim))
                time.sleep(5)
                continue

            bid = claim["bin_id"]
            print(f"\n>>> Kwadracik #{bid}: {claim['start'][:16]}... .. {claim['end'][:16]}...")

            ckpt = ROOT / f"pool_{worker_id}_{bid}.progress"
            if mode == "gpu":
                found, priv, h160, keys = run_gpu(solver, claim, ckpt)
            else:
                found, priv, h160, keys = run_cpu(claim)

            if found and priv:
                api(base, "/api/found", {
                    "worker_id": worker_id,
                    "privkey": priv,
                    "hash160": h160 or claim.get("target"),
                    "payout_address": payout,
                })
                print(f"\n*** TRAFIENIE! Klucz: {priv} ***")
                break

            api(base, "/api/complete", {
                "worker_id": worker_id,
                "bin_id": bid,
                "keys_done": keys or 0,
            })
            print(f"\nKwadracik #{bid} done.")

        except urllib.error.URLError as e:
            print(f"Blad polaczenia: {e} — retry 10s")
            time.sleep(10)
        except KeyboardInterrupt:
            print("\nStop.")
            break


if __name__ == "__main__":
    main()
