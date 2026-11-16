# 法务三页下线归档（2026-11-17）

## 归档对象

| 页面 | 原路径 | 归档路径 |
| --- | --- | --- |
| 隐私政策 | `src/pages/privacy.astro` | `archive/legal-pages-2026-11-17/src/pages/privacy.astro` |
| 服务条款 | `src/pages/terms.astro` | `archive/legal-pages-2026-11-17/src/pages/terms.astro` |
| 退款说明 | `src/pages/refund.astro` | `archive/legal-pages-2026-11-17/src/pages/refund.astro` |

## 下线原因

1. 三页内容围绕付费解锁、购买、退款构建（面包多 / Gumroad 等外部支付渠道），与站点当前「全站免费、`PAY_ENABLED=false`、`commerce.ts` 已冻结」的实际状态直接矛盾，对外构成错误承诺。
2. 运营主体、联系邮箱等要素长期为占位值，页面不具法律效力，反而构成合规风险。
3. 站点唯一合法定位为「浇灌自由生长的文明」，法务页承载的付费叙事与该定位冲突。

## 同步改动

- `src/layouts/BaseLayout.astro`：页脚移除 `/terms`、`/refund`、`/privacy` 三链接，仅保留 `/about`。
- `src/components/AboutView.astro`：移除「相关条款」整条列表项及三链接。
- `src/i18n/pages/about.ts`：清理 `labelDocs` / `docTerms` / `docRefund` / `docPrivacy` 四个字段（四语言），已无渲染引用。
- `scripts/check-design-consistency.mjs`：从基线清单移除已不存在的 `privacy.astro`、`terms.astro`。

## 后期债务（未结清，恢复收费前必须处理）

付费服务恢复时，以下工作必须重做，不得直接复用本归档文件：

1. 补齐真实运营主体、联系邮箱（`src/config/commerce.ts`）。
2. 重新撰写与真实收费模式一致的条款/隐私/退款文本，并做法律审阅。
3. 重新接入页脚与 About 页入口，同时评估备案与增值服务合规要求。

## 恢复方式

将三个页面文件移回 `src/pages/`，并恢复上述四处引用改动即可；注意恢复前先完成「后期债务」第 1、2 项。
