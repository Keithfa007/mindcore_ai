// MindCore AI - key-holding proxy (Cloudflare Worker)
// ---------------------------------------------------
// Holds the OpenAI and ElevenLabs keys server-side so they never ship inside
// the app. The app calls this Worker with the signed-in user's Firebase ID
// token instead of an API key. The Worker:
//   1. verifies the Firebase token (only real, signed-in app users get through),
//   2. whitelists the model (only gpt-4o-mini) and caps token counts,
//   3. forwards to OpenAI / ElevenLabs with the real key and streams the reply.
//
// Routes:
//   POST /chat            -> https://api.openai.com/v1/chat/completions
//   POST /tts/<rest>      -> https://api.elevenlabs.io/v1/text-to-speech/<rest>
//
// Secrets (set with `wrangler secret put`): OPENAI_API_KEY, ELEVENLABS_API_KEY
// Vars (wrangler.toml): FIREBASE_PROJECT_ID

import { importX509, jwtVerify } from 'jose';

const ALLOWED_MODELS = new Set(['gpt-4o-mini']);
const MAX_OUTPUT_TOKENS = 2048;   // hard cap on OpenAI max_tokens
const TTS_MAX_CHARS = 5000;       // hard cap on ElevenLabs text length

// Google's public x509 certs for Firebase ID tokens, cached in-isolate.
const CERT_URL =
  'https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com';
let _certCache = { keys: null, exp: 0 };

async function getFirebaseCerts() {
  const now = Date.now();
  if (_certCache.keys && now < _certCache.exp) return _certCache.keys;
  const res = await fetch(CERT_URL);
  if (!res.ok) throw new Error('cert fetch failed');
  const keys = await res.json(); // { "<kid>": "-----BEGIN CERTIFICATE-----..." }
  const cc = res.headers.get('cache-control') || '';
  const m = cc.match(/max-age=(\d+)/);
  const ttlMs = (m ? parseInt(m[1], 10) : 3600) * 1000;
  _certCache = { keys, exp: now + ttlMs };
  return keys;
}

// Verify a Firebase ID token and return its payload, or throw.
async function verifyFirebaseToken(token, projectId) {
  const certs = await getFirebaseCerts();
  const { payload } = await jwtVerify(
    token,
    async (header) => {
      const pem = certs[header.kid];
      if (!pem) throw new Error('unknown key id');
      return importX509(pem, 'RS256');
    },
    {
      issuer: `https://securetoken.google.com/${projectId}`,
      audience: projectId,
    }
  );
  if (!payload.sub) throw new Error('token has no subject');
  return payload;
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

async function handleChat(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'invalid JSON body' }, 400);
  }

  if (!ALLOWED_MODELS.has(body.model)) {
    return json({ error: `model not allowed: ${body.model}` }, 403);
  }
  if (typeof body.max_tokens === 'number' && body.max_tokens > MAX_OUTPUT_TOKENS) {
    body.max_tokens = MAX_OUTPUT_TOKENS;
  }

  const upstream = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.OPENAI_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  // Pass the response body straight through. When the app asked for
  // stream:true this transparently relays the SSE stream (typewriter effect).
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      'Content-Type':
        upstream.headers.get('Content-Type') || 'application/json',
    },
  });
}

async function handleTts(request, env, rest, search) {
  // Guard payload size without blocking the passthrough for other fields.
  try {
    const clone = request.clone();
    const peek = await clone.json();
    if (peek && typeof peek.text === 'string' && peek.text.length > TTS_MAX_CHARS) {
      return json({ error: 'text too long' }, 413);
    }
  } catch {
    // Non-JSON or unreadable body: let ElevenLabs validate it.
  }

  const target = `https://api.elevenlabs.io/v1/text-to-speech/${rest}${search}`;
  const upstream = await fetch(target, {
    method: 'POST',
    headers: {
      'xi-api-key': env.ELEVENLABS_API_KEY,
      'Content-Type':
        request.headers.get('Content-Type') || 'application/json',
      Accept: request.headers.get('Accept') || 'audio/mpeg',
    },
    body: request.body,
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      'Content-Type':
        upstream.headers.get('Content-Type') || 'audio/mpeg',
    },
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === 'GET' && url.pathname === '/health') {
      return json({ ok: true });
    }
    if (request.method !== 'POST') {
      return json({ error: 'method not allowed' }, 405);
    }

    // --- Auth: require a valid Firebase ID token ---
    const authz = request.headers.get('Authorization') || '';
    const token = authz.startsWith('Bearer ') ? authz.slice(7) : '';
    if (!token) return json({ error: 'missing bearer token' }, 401);

    const projectId = env.FIREBASE_PROJECT_ID || 'mindcore-ai';
    try {
      await verifyFirebaseToken(token, projectId);
    } catch {
      return json({ error: 'invalid or expired token' }, 401);
    }

    // --- Routing ---
    if (url.pathname === '/chat') {
      return handleChat(request, env);
    }
    if (url.pathname.startsWith('/tts/')) {
      const rest = url.pathname.slice('/tts/'.length); // voiceId[/stream][/...]
      return handleTts(request, env, rest, url.search);
    }
    return json({ error: 'not found' }, 404);
  },
};
