import { defineConfig } from "astro/config";

// Cloudflare Pages 部署（根路径）
export default defineConfig({
  site: "https://dimensionscosmos.pages.dev",
  base: "/",
  output: "static",
});
