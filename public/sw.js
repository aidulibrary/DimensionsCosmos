/*!
 * 维点图书馆 DimensionsCosmos · Service Worker
 * 目标：离线可读、秒开、可安装（PWA / MSIX 打包基础）
 *
 * 策略总览
 *   页面导航      有缓存先用缓存并后台更新；无缓存等网络（8s）→ 缓存页 → /books/ → / → offline.html
 *   章节/书目数据  stale-while-revalidate（读过的永远离线可读）
 *   静态资源      cache-first（/_astro/ 带内容哈希，可长期缓存）
 *   Web 字体      cache-first（跨域，仅 fonts.*）
 *   站外链接      不拦截（面包多 / Gumroad 支付跳转必须走真实网络）
 *   非 GET 请求   不拦截（预留未来 AI 接口 POST）
 */

const VERSION = 'v1.0.0';
const SHELL_CACHE = `dc-shell-${VERSION}`;
const PAGE_CACHE = `dc-page-${VERSION}`;
const DATA_CACHE = `dc-data-${VERSION}`;
const ASSET_CACHE = `dc-asset-${VERSION}`;
const FONT_CACHE = `dc-font-${VERSION}`;

const KEEP_CACHES = [SHELL_CACHE, PAGE_CACHE, DATA_CACHE, ASSET_CACHE, FONT_CACHE];

/** 安装时预缓存。全部带尾斜杠，与 Astro 的目录式输出一致。 */
const PRECACHE_URLS = [
  '/',
  '/books/',
  '/methods/',
  '/pricing/',
  '/offline.html',
  '/manifest.webmanifest',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/icons/icon-512-maskable.png',
  '/icons/apple-touch-icon-180.png',
  '/favicon.ico',
];

/** 无缓存时才等网络，给到 8 秒，避免把「慢」误判成「断网」 */
const NAV_TIMEOUT_MS = 8000;

/* ------------------------------------------------------------------ 安装 */

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(SHELL_CACHE);
      // 逐个缓存：任何单条失败都不应让整次安装失败
      await Promise.all(
        PRECACHE_URLS.map(async (url) => {
          try {
            const res = await fetch(new Request(url, { cache: 'reload' }));
            if (res && (res.ok || res.type === 'opaque')) {
              await cache.put(url, res);
            }
          } catch (err) {
            console.warn('[SW] 预缓存跳过', url, err);
          }
        })
      );
      await self.skipWaiting();
    })()
  );
});

/* -------------------------------------------------------------- 激活清理 */

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys.map((key) => (KEEP_CACHES.includes(key) ? null : caches.delete(key)))
      );
      await self.clients.claim();
    })()
  );
});

/* ---------------------------------------------------------------- 消息 */

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

/* ---------------------------------------------------------------- 分流 */

self.addEventListener('fetch', (event) => {
  const req = event.request;

  if (req.method !== 'GET') return;

  let url;
  try {
    url = new URL(req.url);
  } catch {
    return;
  }

  /* 跨域 */
  if (url.origin !== self.location.origin) {
    if (/(^|\.)fonts\.(googleapis|gstatic)\.com$/.test(url.hostname)) {
      event.respondWith(cacheFirst(req, FONT_CACHE));
    }
    // 其余跨域（支付、外链、统计）一律交给浏览器，不缓存、不拦截
    return;
  }

  /* 预留：未来 AI 接口不做缓存，避免读到陈旧解读 */
  if (url.pathname.startsWith('/api/')) return;

  /* 页面导航 */
  if (req.mode === 'navigate') {
    event.respondWith(handleNavigation(req));
    return;
  }

  /* 数据：/data/ch/123.json、/data/book-13.json、/data/index.json 等 */
  if (/^\/data\/.*\.json$/.test(url.pathname)) {
    event.respondWith(staleWhileRevalidate(req, DATA_CACHE));
    return;
  }

  /* 构建产物与图标 */
  if (
    url.pathname.startsWith('/_astro/') ||
    url.pathname.startsWith('/icons/') ||
    url.pathname.startsWith('/fonts/') ||
    /\/favicon\.(ico|png)$/.test(url.pathname)
  ) {
    event.respondWith(cacheFirst(req, ASSET_CACHE));
    return;
  }

  /* 其余同源 GET：SWR 兜底 */
  event.respondWith(staleWhileRevalidate(req, ASSET_CACHE));
});

/* ------------------------------------------------------------ 策略实现 */

/**
 * 页面导航。
 * 有缓存 → 立即返回缓存（秒开），同时后台静默更新；
 * 无缓存 → 等网络，最多 8 秒；仍失败才走离线兜底。
 *
 * 不用「网络优先 + 短超时」，是因为国内网络首包很容易超过 4 秒，
 * 那样会把「慢」误判成「断网」，用户明明有网却被丢到离线页。
 */
async function handleNavigation(req) {
  const pageCache = await caches.open(PAGE_CACHE);
  const cached = await matchLoose(pageCache, req);

  // 永不 reject：失败时返回 null，由下面的兜底逻辑处理，避免 unhandled rejection
  const networkPromise = fetch(req)
    .then((res) => {
      if (res && res.ok) {
        pageCache.put(req, res.clone()).catch(() => {});
      }
      return res;
    })
    .catch(() => null);

  if (cached) {
    // 有缓存：立即可用，网络在后台静默更新
    return cached;
  }

  try {
    const fresh = await withTimeout(networkPromise, NAV_TIMEOUT_MS);
    if (fresh) return fresh;
  } catch (err) {
    /* 8 秒仍未拿到首包，当作不可达 */
  }

  return await offlineFallback(req, pageCache);
}

async function offlineFallback(req, pageCache) {
  // 1) 同 URL 缓存（可能刚好在等待期间写入）
  const exact = await matchLoose(pageCache, req);
  if (exact) return exact;

  // 2) 书库 / 首页兜底
  const shellCache = await caches.open(SHELL_CACHE);
  for (const fallback of ['/books/', '/']) {
    const hit =
      (await pageCache.match(fallback, { ignoreSearch: true })) ||
      (await shellCache.match(fallback, { ignoreSearch: true }));
    if (hit) return hit;
  }

  // 3) 离线说明页
  const offline = await shellCache.match('/offline.html');
  if (offline) return offline;

  return new Response('当前离线，且该页面尚未缓存。', {
    status: 503,
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
}

async function staleWhileRevalidate(req, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(req);

  const networkPromise = fetch(req)
    .then((res) => {
      if (res && res.ok) cache.put(req, res.clone()).catch(() => {});
      return res;
    })
    .catch(() => null);

  if (cached) return cached;

  const fresh = await networkPromise;
  if (fresh) return fresh;

  return new Response('{"offline":true}', {
    status: 503,
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
}

async function cacheFirst(req, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(req);
  if (cached) return cached;

  try {
    const res = await fetch(req);
    if (res && res.ok) cache.put(req, res.clone()).catch(() => {});
    return res;
  } catch {
    return new Response('', {
      status: 503,
      statusText: 'Offline and not cached',
    });
  }
}

/**
 * 缓存查找，容忍尾斜杠差异。
 * 站内导航链接是 `/books`（无斜杠），而预缓存清单与 manifest 的 start_url 是 `/books/`，
 * 两者在 Cache 里是不同 key。这里互相兜一次，避免「明明预缓存过却离线打不开」。
 */
async function matchLoose(cache, req) {
  const hit = await cache.match(req, { ignoreSearch: true });
  if (hit) return hit;

  let url;
  try {
    url = new URL(typeof req === 'string' ? req : req.url);
  } catch {
    return undefined;
  }

  const alt = url.pathname.endsWith('/')
    ? url.pathname.slice(0, -1) || '/'
    : url.pathname + '/';

  return await cache.match(alt + url.search, { ignoreSearch: true });
}

function withTimeout(promise, ms) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`timeout ${ms}ms`)), ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}
