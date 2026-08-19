# Alternatywy deploy (bez Cloudflare)

Cloudflare Pages wymaga tokena + D1 — poniżej prostsze opcje.

---

## Opcja A — vast.ai (najszybsza u Ciebie)

Masz już instancję GPU i tunel Cloudflare z vast. **Zero nowych kont.**

```bash
cd /workspace
git clone https://github.com/rheiCEO/puzzle71-pool.git
cd puzzle71-pool
python3 server.py --host 0.0.0.0 --port 8780
```

Instance Portal → **Create new tunnel** → `http://localhost:8780`

Worker u uczestników:
```bash
python3 worker.py https://TWOJ-TUNEL.trycloudflare.com bc1q... gpu Nick
```

**Plus:** masz już GPU obok, możesz też sam liczyć.  
**Minus:** jak zatrzymasz instancję, strona pada (backup: `pool.db`).

---

## Opcja B — Render.com (darmowy, stały URL)

1. https://render.com → Sign up (GitHub)
2. **New** → **Blueprint** → repo `rheiCEO/puzzle71-pool`
3. Deploy — dostaniesz URL typu `https://puzzle71-pool.onrender.com`

Worker:
```bash
python worker.py https://puzzle71-pool.onrender.com ADRES gpu Nick
```

**Plus:** stały link, bez vast, darmowy tier.  
**Minus:** free tier „śpi” po bezczynności (~30 s pierwsze wejście).

Plik `render.yaml` jest już w repo.

---

## Opcja C — GitHub Pages + API gdzie indziej

- Frontend: GitHub Pages (tylko HTML — branch `gh-pages` lub folder `web/`)
- API: vast **albo** Render (URL wpisujesz w polu „URL serwera” na stronie)

Strona już ma pole `serverUrl` — wystarczy hostować `web/index.html` i podać adres API.

---

## Opcja D — u siebie na PC + tunel

```bat
START-SERVER.bat
```

W drugim oknie (ngrok / cloudflared):
```bash
cloudflared tunnel --url http://127.0.0.1:8780
```

Dajesz znajomym link z tunelu. Działa bez VPS.

---

## Co polecam

| Sytuacja | Wybór |
|----------|--------|
| Już płacisz za vast | **A** — 1 terminal, tunel 8780 |
| Chcesz stały link 24/7 za darmo | **B** — Render |
| Chcesz tylko pokazać mapę znajomym z domu | **D** — tunel z PC |

**GPU zawsze lokalnie u każdego** — serwer tylko koordynuje mapę i przydziela kawałki, nie liczy kluczy.

---

## Backup postępu puli

Skopiuj plik `pool.db` (SQLite) przed wyłączeniem serwera — to cała mapa i rezerwacje.
