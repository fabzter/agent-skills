#!/usr/bin/env bash
# itch-download.sh — download a free (or owned) itch.io upload as its real archive.
#
# Why this exists: POST /<slug>/download_url returns a token URL that only renders
# the "thanks for downloading" HTML interstitial — never the file. The actual
# signed CDN URL comes from POST /<slug>/file/<upload_id> (JSON field "url").
#
# Usage:
#   bash itch-download.sh <game-page-url> <out-file> [upload_id]
# Example:
#   bash itch-download.sh https://gingerenslaver.itch.io/ashtreelane ./AshTreeLane.zip
#
# Free uploads need no login. Owned/paid uploads need a logged-in itchio_token
# cookie in the jar (log in via a browser first, export cookies, point JAR at them).
set -euo pipefail

PAGE_URL="${1:?usage: itch-download.sh <game-page-url> <out-file> [upload_id]}"
OUT="${2:?usage: itch-download.sh <game-page-url> <out-file> [upload_id]}"
UPLOAD_ID="${3:-}"

UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
JAR="${ITCH_COOKIE_JAR:-$(mktemp)}"
[ -n "${ITCH_COOKIE_JAR:-}" ] || trap 'rm -f "$JAR"' EXIT

BASE="${PAGE_URL%%\?*}"          # strip query string
BASE="${BASE%/}"                 # strip trailing slash

# 1) Load the game page: sets the itchio_token session cookie, exposes CSRF + upload ids.
PAGE="$(curl -fsSL -c "$JAR" -A "$UA" "$PAGE_URL")"

CSRF="$(printf '%s' "$PAGE" | python3 -c 'import sys,re;m=re.search(r"name=\"csrf_token\" value=\"([^\"]+)\"",sys.stdin.read());print(m.group(1) if m else "")')"
[ -n "$CSRF" ] || { echo "error: no csrf_token found (page blocked or login required?)" >&2; exit 1; }

if [ -z "$UPLOAD_ID" ]; then
  UPLOAD_ID="$(printf '%s' "$PAGE" | python3 -c 'import sys,re;m=re.search(r"data-upload_id=\"(\d+)\"",sys.stdin.read());print(m.group(1) if m else "")')"
fi
[ -n "$UPLOAD_ID" ] || { echo "error: no data-upload_id in page HTML (name-your-own-price pages hide it behind the buy flow). Pass the upload id explicitly as arg 3, or complete the \$0 download in a browser to reveal it." >&2; exit 1; }

# 2) Ask the FILE endpoint for the real signed CDN URL (NOT download_url).
RESP="$(curl -fsS -b "$JAR" -c "$JAR" -A "$UA" \
  -H 'X-Requested-With: XMLHttpRequest' -H "Referer: $PAGE_URL" \
  --data-urlencode "csrf_token=$CSRF" \
  "${BASE}/file/${UPLOAD_ID}?source=view_game&as_props=1&after_download_lightbox=true")"

FILE_URL="$(printf '%s' "$RESP" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("url",""))')"
[ -n "$FILE_URL" ] || { echo "error: file endpoint returned no url (paid/owned upload needs a logged-in cookie): $RESP" >&2; exit 1; }

# 3) Fetch the signed URL directly (no cookies needed; ~60s expiry — use immediately).
curl -fSL -A "$UA" "$FILE_URL" -o "$OUT"
echo "saved: $OUT"
file "$OUT" 2>/dev/null || true