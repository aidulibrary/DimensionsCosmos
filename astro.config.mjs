import { defineConfig } from 'astro/config';

// GitHub Pages 部署：base 路径必须匹配仓库名
export default defineConfig({
  site: 'https://aidulibrary.github.io',
  base: '/DimensionsCosmos/',
  output: 'static',
});
