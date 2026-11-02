/**
 * 稳定引用短链边缘重定向（REF-SPEC v1 · A+B 方案 B 部分）
 *
 *   /Q276015/c002  →  302  /books/1-论语/read/#dc:Q276015/c002
 *
 * 为什么用函数而不是静态页：
 *   Cloudflare Pages 单次部署上限 20000 文件，9874 个短链静态页 + 9874 个章节 JSON
 *   会直接撑爆配额（Pages only supports up to 20,000 files in a deployment）。
 *   改为边缘 302 后，短链占用 0 个部署文件，且不必为每章预渲染 HTML。
 *
 * 覆盖范围：public/_routes.json 的 include 已限定为 /*\/c*，只有短链形态的请求会进函数，
 *           其余静态页面与资源完全不经过 Functions，不改变现有访问路径的性能与行为。
 *
 * 索引来源：构建期由 scripts/postbuild-ref-routes.mjs 输出到 dist/data/ref-index/works.json
 *           （workKey → slug，约百条量级），此处惰性读取并常驻实例内存。
 */
const REF_RE = /^\/([A-Za-z0-9_-]{1,64})\/c(\d{3,})\/?$/;
const INDEX_PATH = "/data/ref-index/works.json";

// 模块级缓存：同一函数实例内只读一次索引
let cachedMap = null;

async function loadIndex(context) {
  if (cachedMap) return cachedMap;
  try {
    const url = new URL(context.request.url);
    const target = new URL(INDEX_PATH, url);
    const res = await context.next(new Request(target.toString(), { method: "GET" }));
    if (!res || !res.ok) {
      console.warn("[ref-route] 索引读取失败", res && res.status, INDEX_PATH);
      return null;
    }
    const map = await res.json();
    if (!map || typeof map !== "object") return null;
    cachedMap = map;
    return cachedMap;
  } catch (err) {
    console.error("[ref-route] 索引异常", String(err));
    return null;
  }
}

export async function onRequest(context) {
  const { request } = context;
  const method = request.method.toUpperCase();
  if (method !== "GET" && method !== "HEAD") return context.next();

  const url = new URL(request.url);
  const m = REF_RE.exec(url.pathname);
  if (!m) return context.next();

  const workKey = m[1];
  const chapNo = m[2];

  const map = await loadIndex(context);
  const slug = map && typeof map[workKey] === "string" ? map[workKey] : null;

  // 索引缺失或该 workKey 不在库内：交回静态层（由 404 页面接管），不伪造跳转
  if (!slug) return context.next();

  // 书名 slug 含中文，HTTP 头只允许 Latin-1，必须整体百分号编码后再写入 Location
  const location = encodeURI(`/books/${slug}/read/#dc:${workKey}/c${chapNo}`);
  return new Response(null, {
    status: 302,
    headers: {
      Location: location,
      "Cache-Control": "public, max-age=600",
      "Referrer-Policy": "no-referrer-when-downgrade",
      "X-Ref-Route": "dynamic",
    },
  });
}
