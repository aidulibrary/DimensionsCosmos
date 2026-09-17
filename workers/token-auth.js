/**
 * DimensionsCosmos Token Auth Worker
 *
 * 路径：
 *   POST /generate  → 生成解锁 token（供 webhook 调用）
 *   GET  /verify?token=xxx&book=slug&method=id → 验证 token
 *
 * Token 格式：base64(JSON({b: bookSlug, m: methodId, ts: timestamp, sig: hmac}))
 *   前端解析 base64 → 取 b/m → localStorage 存储 → 页面刷新自动解锁
 */

const SECRET_KEY =
  typeof WORKER_SECRET !== "undefined"
    ? WORKER_SECRET
    : "dimensions-cosmos-secret-change-me";

function base64url(str) {
  return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function unbase64url(str) {
  str = str.replace(/-/g, "+").replace(/_/g, "/");
  while (str.length % 4) str += "=";
  return atob(str);
}

async function hmacSign(data, key) {
  const enc = new TextEncoder();
  const algo = { name: "HMAC", hash: "SHA-256" };
  const k = await crypto.subtle.importKey("raw", enc.encode(key), algo, false, [
    "sign",
  ]);
  const sig = await crypto.subtle.sign(algo, k, enc.encode(data));
  return btoa(String.fromCharCode(...new Uint8Array(sig)));
}

async function generateToken(book, method) {
  const ts = Date.now();
  const payload = JSON.stringify({ b: book, m: method, ts });
  const sig = await hmacSign(payload, SECRET_KEY);
  const token = base64url(payload + "|" + sig);
  return token;
}

async function verifyToken(token) {
  try {
    const raw = unbase64url(token);
    const [payload, sig] = raw.split("|");
    if (!payload || !sig) return null;
    const expected = await hmacSign(payload, SECRET_KEY);
    if (expected !== sig) return null;
    return JSON.parse(payload);
  } catch {
    return null;
  }
}

// ---- Request Handler ----

async function handleRequest(req) {
  const url = new URL(req.url);
  const path = url.pathname;

  // CORS headers
  const headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };

  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers });
  }

  // POST /generate — 生成 token（需带简单鉴权）
  if (path === "/generate" && req.method === "POST") {
    const auth = req.headers.get("Authorization");
    if (auth !== `Bearer ${SECRET_KEY.substring(0, 12)}`) {
      return new Response(JSON.stringify({ error: "unauthorized" }), {
        status: 401,
        headers: { ...headers, "Content-Type": "application/json" },
      });
    }

    const body = await req.json().catch(() => ({}));
    const { book, method } = body;
    if (!book || !method) {
      return new Response(
        JSON.stringify({ error: "book and method required" }),
        {
          status: 400,
          headers: { ...headers, "Content-Type": "application/json" },
        },
      );
    }

    const token = await generateToken(book, method);
    return new Response(JSON.stringify({ token, book, method }), {
      status: 200,
      headers: { ...headers, "Content-Type": "application/json" },
    });
  }

  // GET /verify?token=xxx&book=slug&method=id
  if (path === "/verify" && req.method === "GET") {
    const token = url.searchParams.get("token");
    const book = url.searchParams.get("book");
    const method = url.searchParams.get("method");

    if (!token) {
      return new Response(
        JSON.stringify({ valid: false, reason: "missing token" }),
        {
          status: 400,
          headers: { ...headers, "Content-Type": "application/json" },
        },
      );
    }

    const payload = await verifyToken(token);
    if (!payload) {
      return new Response(
        JSON.stringify({ valid: false, reason: "invalid token" }),
        {
          status: 403,
          headers: { ...headers, "Content-Type": "application/json" },
        },
      );
    }

    // 可选：验证 book/method 与 token 匹配
    if (book && payload.b !== book) {
      return new Response(
        JSON.stringify({ valid: false, reason: "book mismatch" }),
        {
          status: 403,
          headers: { ...headers, "Content-Type": "application/json" },
        },
      );
    }
    if (method && payload.m !== method) {
      return new Response(
        JSON.stringify({ valid: false, reason: "method mismatch" }),
        {
          status: 403,
          headers: { ...headers, "Content-Type": "application/json" },
        },
      );
    }

    return new Response(
      JSON.stringify({ valid: true, book: payload.b, method: payload.m }),
      {
        status: 200,
        headers: { ...headers, "Content-Type": "application/json" },
      },
    );
  }

  return new Response("DimensionsCosmos Token API", { status: 200, headers });
}

// ---- Cloudflare Workers entry ----
export default {
  async fetch(req, env) {
    // Inject secret from environment
    if (env.WORKER_SECRET) {
      globalThis.WORKER_SECRET = env.WORKER_SECRET;
    }
    return handleRequest(req);
  },
};
