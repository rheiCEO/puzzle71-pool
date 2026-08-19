# Deploy na Render.com (FREE)

## Najszybciej — 1 klik (Ty)

**Nie da się zdeployować bez Twojego konta Render** — ale to dosłownie jeden klik:

👉 **[Otwórz Blueprint → Apply](https://dashboard.render.com/blueprint/new?repo=https://github.com/rheiCEO/puzzle71-pool)**

1. Zaloguj przez GitHub (jeśli trzeba)
2. **Apply**
3. Poczekaj ~2–3 min → status **Live**
4. URL: `https://puzzle71-pool.onrender.com`

---

## Krok po kroku (alternatywa)

1. Wejdź na https://render.com
2. **Get Started** → zaloguj przez **GitHub**
3. Zezwól na dostęp do repozytoriów

## Krok 2 — Blueprint (automatycznie z repo)

1. Dashboard → **New +** → **Blueprint**
2. Połącz repo: **`rheiCEO/puzzle71-pool`**
3. Render wczyta `render.yaml` — kliknij **Apply**
4. Poczekaj ~2–3 min (status **Live**)

Dostaniesz URL typu:
```text
https://puzzle71-pool.onrender.com
```

## Krok 3 — sprawdź

Otwórz w przeglądarce:
```text
https://puzzle71-pool.onrender.com/
https://puzzle71-pool.onrender.com/health
```

Powinno być: strona z mapą + `{"ok": true}` na `/health`.

> **Uwaga:** plan free „śpi” po ~15 min bez ruchu. Pierwsze wejście może trwać **20–60 s** — to normalne.

## Krok 4 — worker u Ciebie (GPU)

```bat
set PUZZLE71_CUDA=C:\Users\micha\NEW_PROGRAMING\puzzle71-cuda\bin\puzzle71-cuda.exe
python worker.py https://puzzle71-pool.onrender.com TWOJ_ADRES_BTC gpu TwojNick
```

Albo na stronie: wpisz adres → **Start** → skopiuj komendę.

## Krok 5 — znajomi

1. Wchodzą na `https://puzzle71-pool.onrender.com`
2. Wpisują swój adres BTC
3. Klikają kwadracik / Start
4. Odpalają u siebie `worker.py` z linkiem Render

---

## Ręczny deploy (gdy Blueprint nie działa)

**New +** → **Web Service** → repo `puzzle71-pool`:

| Pole | Wartość |
|------|---------|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python server.py --host 0.0.0.0 --port $PORT` |
| Plan | **Free** |

## Backup mapy

Baza `pool.db` na Render free **resetuje się przy redeploy**.  
Na MVP to OK — mapa odtwarza się od zera. Później można dodać płatny dysk Render.

## Problemy

| Problem | Rozwiązanie |
|---------|-------------|
| Strona wolno startuje | Free tier — poczekaj 30–60 s |
| Worker nie łączy | Sprawdź URL (https, bez `/` na końcu) |
| Brak GPU | Ustaw `PUZZLE71_CUDA` lub tryb `cpu` |
