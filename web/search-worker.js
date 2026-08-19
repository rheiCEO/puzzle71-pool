import { sha256 } from "https://esm.sh/@noble/hashes@1.4.0/sha256";
import { ripemd160 } from "https://esm.sh/@noble/hashes@1.4.0/ripemd160";
import * as secp from "https://esm.sh/@noble/secp256k1@2.1.0";

function hexToBigInt(h) {
  return BigInt("0x" + h.replace(/^0x/, ""));
}

function bigintTo32Bytes(n) {
  const hex = n.toString(16).padStart(64, "0");
  const out = new Uint8Array(32);
  for (let i = 0; i < 32; i++) out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  return out;
}

function bytesToHex(b) {
  return Array.from(b).map(x => x.toString(16).padStart(2, "0")).join("");
}

function hash160Compressed(privBytes) {
  const pub = secp.getPublicKey(privBytes, true);
  return bytesToHex(ripemd160(sha256(pub)));
}

let stop = false;

self.onmessage = (ev) => {
  const msg = ev.data;
  if (msg.cmd === "stop") {
    stop = true;
    return;
  }
  if (msg.cmd !== "start") return;

  stop = false;
  const start = hexToBigInt(msg.start);
  const end = hexToBigInt(msg.end);
  const target = (msg.target || "").toLowerCase();
  const maxKeys = msg.maxKeys || 500000;
  let k = start;
  let checked = 0;
  const t0 = performance.now();
  let lastReport = t0;

  (async () => {
    while (!stop && k <= end && checked < maxKeys) {
      const priv = bigintTo32Bytes(k);
      const h = hash160Compressed(priv);
      if (h === target) {
        self.postMessage({
          type: "found",
          privkey: k.toString(16).padStart(64, "0"),
          hash160: h,
          checked,
        });
        return;
      }
      k += 1n;
      checked += 1;
      const now = performance.now();
      if (now - lastReport > 500) {
        const speed = checked / ((now - t0) / 1000);
        self.postMessage({ type: "progress", checked, speed, current: k.toString(16) });
        lastReport = now;
      }
    }
    self.postMessage({ type: "done", checked, stopped: stop });
  })();
};
