# Deploy na Cloudflare Pages (pages.dev)

Strona + API (Functions + D1) — bez własnego VPS.

## 1. Cloudflare — token

1. https://dash.cloudflare.com/profile/api-tokens
2. **Create Token** → template **Edit Cloudflare Workers**
3. Skopiuj token

PowerShell:
```powershell
$env:CLOUDFLARE_API_TOKEN="twój-token"
```

## 2. D1 (baza mapy)

```powershell
cd puzzle71-pool
npx wrangler d1 create puzzle71-pool
```

Skopiuj `database_id` do `wrangler.toml` (zamiast `REPLACE_AFTER_D1_CREATE`).

```powershell
npx wrangler d1 execute puzzle71-pool --remote --file=migrations/0001_init.sql
```

## 3. Deploy

```powershell
npx wrangler pages project create puzzle71-pool --production-branch master
npx wrangler pages deploy web --project-name puzzle71-pool --branch master
```

D1 binding (jeśli deploy nie podłączy automatycznie):
- Cloudflare Dashboard → **Workers & Pages** → **puzzle71-pool** → **Settings** → **Bindings**
- Add **D1** → name `DB` → database `puzzle71-pool`

## 4. Adres

Po deploy: `https://puzzle71-pool.pages.dev` (lub custom domain).

Strona sama woła API pod `/api/*` na tej samej domenie.

## 5. Worker lokalny (u użytkowników)

```bat
python worker.py https://puzzle71-pool.pages.dev bc1q... gpu Nick
```

GPU liczy lokalnie, mapa aktualizuje się centralnie na Pages.

## Alternatywa: GitHub → Pages (bez wrangler)

1. https://dash.cloudflare.com → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**
2. Repo: `rheiCEO/puzzle71-pool`
3. **Build output directory:** `web`
4. **Root directory:** `/`
5. Bindings → D1 `DB` → `puzzle71-pool`
6. Deploy

Po pierwszym deploy uruchom migrację D1 (krok 2).
