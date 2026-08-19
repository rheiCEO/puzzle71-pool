# puzzle71-pool

Wspólna pula do Bitcoin Puzzle #71 — strona + serwer + lokalny worker (GPU/CPU).

## Nagrody (regulamin puli)

- Puzzle: `1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU` (~7.1 BTC)
- Przy trafieniu: **3 BTC** → adres znalazcy, reszta → `1Ps8hoKzRjdZdDphFwBjm6qiAzDxFYXAFe`
- Wypłata wymaga ręcznej/automatycznej obsługi klucza po znalezieniu (MVP: zapis + powiadomienie)

## Deploy strony (Cloudflare Pages)

Frontend + API na **pages.dev** — instrukcja: [DEPLOY-PAGES.md](DEPLOY-PAGES.md)

Po deploy worker łączy się z `https://puzzle71-pool.pages.dev` zamiast lokalnego serwera.

## Szybki start (Windows, lokalny serwer Python)

### 1. Serwer (jedna maszyna — VPS / vast / PC)

```bat
START-SERVER.bat
```

Otwórz: http://127.0.0.1:8780/

### 2. Worker GPU (u każdego uczestnika)

Wymaga `puzzle71-cuda` — zbuduj w `../puzzle71-cuda` albo ustaw:

```bat
set PUZZLE71_CUDA=C:\sciezka\do\puzzle71-cuda.exe
```

```bat
START-WORKER-GPU.bat TWOJ_ADRES_BTC http://IP_SERWERA:8780 Nick
```

### 3. Worker CPU (wolniejszy, bez karty)

```bat
pip install -r requirements-cpu.txt
START-WORKER-CPU.bat TWOJ_ADRES_BTC http://IP_SERWERA:8780 Nick
```

## Strona

- mapa **2500 kwadracików** (50×50) — cały zakres Puzzle #71
- kliknij wolny kwadracik → rezerwacja kawałka
- albo **Start** → kolejny wolny kawałek
- wszyscy widzą % postępu puli

## API

| Endpoint | Opis |
|----------|------|
| `GET /api/status` | postęp, mapa, workerzy |
| `POST /api/register` | `{worker_id, name, payout_address, mode}` |
| `POST /api/claim` | `{worker_id, bin_id?}` |
| `POST /api/complete` | `{worker_id, bin_id, keys_done}` |
| `POST /api/found` | zgłoszenie klucza |

## Linux / vast

```bash
python3 server.py --host 0.0.0.0 --port 8780
python3 worker.py http://IP:8780 bc1q... gpu nick
```

Tunel vast: Instance Portal → `http://localhost:8780`

## Powiązane

- Solver CUDA: [puzzle71-cuda](https://github.com/rheiCEO/puzzle71-cuda)
