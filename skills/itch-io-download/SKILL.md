---
name: itch-io-download
description: "Use when downloading a game or file from itch.io (free or owned uploads) with curl/script, especially when the download returns an HTML 'thanks for downloading' interstitial instead of the archive, or when download_url gives a token URL that never yields the file."
---

# itch.io download

## Core principle

**`download_url` is a decoy.** `POST /<slug>/download_url` returns a token URL
(`/<slug>/download/<token>`) that only renders the *"thanks for downloading"* HTML
interstitial — it never serves the file, no matter what headers/cookies you add.
The real, signed CDN URL comes from a **different endpoint**:

```
POST /<slug>/file/<upload_id>?source=view_game&as_props=1&after_download_lightbox=true
```

Its JSON response has a top-level `url` field: a short-lived (~60 s) signed
Cloudflare R2 link (`itchio-mirror.*.r2.cloudflarestorage.com/...`). Fetch that
URL directly — no cookies needed — to get the actual archive.

## When to use

- Downloading a free itch.io game/tool for analysis, RE, or archiving.
- `curl .../download_url` then following the returned URL gives HTML, not a zip.
- You need a scriptable, browser-free download (CI, subagents, headless boxes).

## Recipe (verified 2026-11-23, pure curl, no browser)

1. **GET the game page** with a cookie jar. This sets the `itchio_token` session
   cookie and exposes two values in the HTML:
   - `<meta name="csrf_token" value="...">` — the CSRF token (equals the cookie).
   - `data-upload_id="NNNN"` on each download button — one per upload/file.
2. **POST the file endpoint** (same jar) with form body `csrf_token=<token>`:
   `POST <page-url>/file/<upload_id>?source=view_game&as_props=1&after_download_lightbox=true`
   headers `X-Requested-With: XMLHttpRequest` + `Referer: <page-url>`.
   Response JSON: `{ "url": "<signed R2 URL>", "external": ..., "lightbox": ... }`.
3. **GET the `url`** immediately (it expires in ~60 s). The bytes are the real
   archive (ZIP magic `50 4b 03 04`).

Just run the bundled script — it does all three steps:

```bash
bash scripts/itch-download.sh https://gingerenslaver.itch.io/ashtreelane ./AshTreeLane.zip
# choose a specific upload when a page has several:
bash scripts/itch-download.sh <page-url> <out-file> <upload_id>
```

## Quick reference

| Goal | Endpoint / field |
|---|---|
| Session cookie + CSRF + upload ids | `GET <page-url>` → `itchio_token` cookie, `csrf_token` meta, `data-upload_id` |
| **Real file URL** | `POST <page-url>/file/<upload_id>?source=view_game&as_props=1&after_download_lightbox=true` → JSON `url` |
| Decoy (HTML interstitial) | `POST <page-url>/download_url` → token URL → `GET` returns HTML, **not** the file |
| File host | `itchio-mirror.*.r2.cloudflarestorage.com` (signed, ~60 s TTL) |

## Common mistakes

- **Following the `download_url` token and expecting a redirect.** It returns
  `200 text/html` (the interstitial) for every header combo (`Sec-Fetch-*`,
  browser UA, cookies). Stop retrying it; call the **file** endpoint instead.
- **Reusing a stale CSRF/cookie.** The CSRF must match the `itchio_token` cookie
  from the *same* jar/session. Fetch the page and POST the file endpoint in one
  continuous session.
- **Sitting on the signed URL.** It expires in ~60 s; download immediately.
- **Multiple uploads.** A page can list several files (Windows/Mac/Linux, demos).
  Each has its own `data-upload_id`; pass the right one as arg 3.
- **Paid / owned uploads.** The file endpoint only returns a `url` for free
  uploads or ones the session owns. For purchased games, log in via a browser,
  export the `itchio_token` cookie, and point `ITCH_COOKIE_JAR` at a Netscape
  cookie file containing it.
- **Name-your-own-price pages.** NYOP pages (a `buy_btn`, even at a $0 minimum)
  expose **no `data-upload_id`** in the static HTML — the id lives behind the
  purchase flow, so the script exits "no upload id found". Pass the id explicitly
  as arg 3 if known, or complete the $0 download in a browser to reveal it.

## Scope / limits

- Verified for **direct-download free** Windows uploads (no login): ashtreelane
  (253 MB) and Dead Sight (34.7 MB), byte-identical across runs. Owned-upload and
  name-your-own-price paths are not automated; see Common mistakes.
- This downloads the shipped artifact only. It does not bypass paywalls or DRM.