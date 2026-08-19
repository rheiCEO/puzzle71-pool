#!/usr/bin/env python3
"""Prosty CPU search — demo / fallback bez CUDA."""
from __future__ import annotations

import hashlib
from typing import Callable


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _ripemd160(data: bytes) -> bytes:
    try:
        from Crypto.Hash import RIPEMD160
        h = RIPEMD160.new()
        h.update(data)
        return h.digest()
    except ImportError:
        pass
    # minimal RIPEMD160 fallback via hashlib if available (py3.12+ no ripemd160 by default)
    import struct
    # Use coincurve path instead if no RIPEMD — caller should install pycryptodome
    raise ImportError("pip install pycryptodome  (dla CPU search)")


def pubkey_compressed(priv_int: int):
    from coincurve import PrivateKey
    pk = PrivateKey(priv_int.to_bytes(32, "big"))
    return pk.public_key.format(compressed=True)


def hash160_pubkey(pub: bytes) -> str:
    h1 = _sha256(pub)
    h2 = _ripemd160(h1)
    return h2.hex()


def search_range(
    start: int,
    end: int,
    target_h160: str,
    progress_cb: Callable[[int], None] | None = None,
    max_keys: int = 1_000_000,
) -> dict | None:
    try:
        import coincurve  # noqa: F401
    except ImportError as e:
        raise ImportError("CPU search wymaga: pip install coincurve pycryptodome") from e

    target = target_h160.lower().strip()
    checked = 0
    for k in range(start, min(end, start + max_keys - 1) + 1):
        checked += 1
        if progress_cb and checked % 10000 == 0:
            progress_cb(checked)
        try:
            pub = pubkey_compressed(k)
            h = hash160_pubkey(pub)
            if h == target:
                return {"privkey": format(k, "064x"), "hash160": h, "checked": checked}
        except Exception:
            continue
    return None
