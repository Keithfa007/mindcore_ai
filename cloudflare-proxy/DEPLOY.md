# MindCore proxy — deploy runbook

This Cloudflare Worker holds your OpenAI and ElevenLabs keys server-side. The
app will call it with a signed-in user's Firebase token instead of an API key,
so no key ever ships inside a build again.

Do this on your PC. It does NOT touch the app yet — nothing breaks while you set
this up. When it is deployed and tested, send me the Worker URL and I will swap
the app's call sites and strip the keys.

## 0. One-time prerequisites
- Node.js installed (you already have it for Flutter tooling).
- A free Cloudflare account: https://dash.cloudflare.com/sign-up (no card needed for the Workers free tier).

## 1. Install dependencies
```
cd cloudflare-proxy
npm install
```

## 2. Log in to Cloudflare
```
npx wrangler login
```
This opens a browser to authorise. Approve it.

## 3. Set the two secrets (this is where the NEW keys go — server-side only)
```
npx wrangler secret put OPENAI_API_KEY
```
Paste your NEW OpenAI key when prompted (create a fresh one at platform.openai.com; do NOT reuse the revoked one).
```
npx wrangler secret put ELEVENLABS_API_KEY
```
Paste your ElevenLabs key.

These are stored encrypted at Cloudflare. They are never in the repo, never in the app.

## 4. Deploy
```
npx wrangler deploy
```
At the end it prints a URL like:
```
https://mindcore-proxy.<your-subdomain>.workers.dev
```
Copy that URL. That is what you send me for the next step.

## 5. Test it (proves the deploy + the auth gate work)
Health check (should print `{"ok":true}`):
```
curl https://mindcore-proxy.<your-subdomain>.workers.dev/health
```
Auth gate — a chat call with no token MUST be rejected (should print `{"error":"missing bearer token"}` with HTTP 401):
```
curl -i -X POST https://mindcore-proxy.<your-subdomain>.workers.dev/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"hi"}]}'
```
If health returns ok and the chat call returns 401, the proxy is live and locked
down correctly. (A full end-to-end chat test happens once the app points at it,
or by pasting a real Firebase ID token from `flutter run` into the `Authorization:
Bearer <token>` header.)

## 6. Send me the Worker URL
Reply with the `https://mindcore-proxy.<...>.workers.dev` URL. I will then:
- point all 13 OpenAI call sites and 3 ElevenLabs call sites at it,
- delete `OPENAI_API_KEY` and `ELEVENLABS_API_KEY` from `lib/env/env.dart` and your `.env`,
- and give you the build command for the new version.

## What the proxy enforces (so it can't become the next abuse vector)
- Requires a valid Firebase ID token from your project (`mindcore-ai`). Random callers are rejected.
- Only allows the `gpt-4o-mini` model. Any attempt to run gpt-4o / o1 / etc. is refused.
- Caps `max_tokens` (2048) and ElevenLabs text length (5000 chars).

## Later enhancement (optional)
Add a Cloudflare rate-limit rule, or have the Worker read the caller's Firestore
`isPremium` flag, to enforce your subscription gate server-side too. Not required
for v1 — the auth + model whitelist already close the leak-abuse hole.
