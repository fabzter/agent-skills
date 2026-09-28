---
name: gog-oauth-refresh-token-expiry
description: Diagnose and fix gog CLI logins that expire every ~7 days. Detects Google External+Testing 7-day refresh tokens via the token endpoint response, then makes them long-lived by completing OAuth branding (homepage + privacy policy) and publishing the app to In production, followed by a mandatory --force-consent re-auth.
---

# gog OAuth refresh-token expiry (weekly re-login) — diagnose & fix

## Symptom

`gog` (gogcli) forces a full re-login roughly every 7 days. Access tokens refresh fine in between; then the refresh token itself dies (`invalid_grant`) and only `gog auth add --force-consent` recovers.

## Root cause

The GCP project owning gog's OAuth client has consent screen **User type = External, Publishing status = Testing**. Google issues **7-day refresh tokens** for External+Testing apps that request user-data scopes. gog's own docs call this "weekly reauthorization".

## Definitive detection (no console access needed)

Exchange the stored refresh token and inspect the response **keys**:

1. Read the refresh token from the OS keychain: `security find-generic-password -s gogcli -a "token:default:<email>" -w` (macOS; the value is a JSON blob with a `refresh_token` field).
2. Read `client_id` / `client_secret` from `~/Library/Application Support/gogcli/credentials.json`.
3. POST `grant_type=refresh_token` to `https://oauth2.googleapis.com/token`.
4. Interpret:
   - **`refresh_token_expires_in` PRESENT** (value ≈ 604800 minus the token's age) ⇒ consent screen is in **Testing** status; the refresh token is 7-day-limited.
   - **`refresh_token_expires_in` ABSENT** ⇒ **In production**; the refresh token is long-lived. This field is only returned for Testing-status external apps, so its presence/absence is the definitive signal.

Never print tokens or the client secret; report only key names, HTTP status, and expiry values.

## Fix

1. **Complete Branding** (`https://console.cloud.google.com/auth/branding?project=<project-id>`): app name, user support email and developer contact are usually already set. The blockers are **Application home page** and **Application privacy policy link** — both are *required* for external production apps — plus the **Authorized domains** entry that becomes required once they are set. A minimal static site (an `index.html` homepage and a `privacy.html` policy page, e.g. on GitHub Pages) satisfies both; register its domain as an authorized domain. Save and confirm the "Branding changes saved!" toast. **Without homepage + privacy policy the "Publish app" button stays greyed out** ("complete your configuration on the Branding page").
2. **Publish** (`https://console.cloud.google.com/auth/audience?project=<project-id>`): click **Publish app → Confirm** (Testing → In production). Reversible via "Back to testing". Google **verification is NOT required** to stop the 7-day clock; verification only affects name/logo display and >100-user or restricted-scope cases. Org-less personal projects cannot use "Make internal" (Internal requires a Cloud Organization).
3. **Mandatory re-consent**: refresh tokens minted while in Testing **keep** their 7-day expiry even after publishing. Re-run `gog auth add <email> --services <same list> --force-consent`. Preserve the existing service list (read it from `gog auth list`). Use `--timeout=10m`: the default authorization timeout (~2 min) is too short for a human to click through the consent screen.
4. **Verify**: repeat the detection POST — `refresh_token_expires_in` must now be **absent**; `gog auth doctor` should report `status ok`.

## Driving the Google Cloud console from a live logged-in browser

The console is an Angular Material SPA; use the local CDP relay against the user's real logged-in Chrome (see the `chrome-relay-live-tab` skill) rather than a fresh browser, which would lack the Google session.

- Ignore `chrome-devtools`-style MCP tab lists that show only `about:blank` (that is an isolated browser); use the raw relay target list.
- The relay's browser-level websocket rejects connections that send an `Origin` header — connect with the origin suppressed (e.g. `websocket.create_connection(..., suppress_origin=True)` with python `websocket-client`).
- Use `Target.createTarget` / `Target.closeTarget` / `Target.activateTarget` for scratch tabs; attach per target with `flatten:true`.
- Fill Angular Material inputs with real CDP input: focus via JS (`input.focus(); input.select()`), type with `Input.insertText`, commit with a real `Tab`/`Enter` `Input.dispatchKeyEvent` (no `text` prop). The "Add domain" control reveals an inline input (placeholder `example.com`). The **Save** button only enables once the form is valid *and* dirty.
- The OAuth consent screen for an unverified production app shows "Google hasn't verified this app"; a **human must** click Advanced → Continue → Allow. Surface the consent tab (`Target.activateTarget`) and use a long `--timeout` so the human can finish.

## Post-production token kill conditions (still apply)

User revokes access; 6 months of non-use; password change while holding Gmail scopes; the 100-refresh-tokens-per-account-per-client cap (oldest silently invalidated); Workspace admin block/limit. Unverified production apps show the "unverified app" warning and carry a 100-new-user lifetime cap — harmless for single-owner use. Being (or adding) a **test user does NOT extend the 7-day limit**.
