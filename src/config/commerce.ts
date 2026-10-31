// 商业化配置：所有收款/主体信息集中在此，避免散落在页面里被误当成真实链路上线。
//
// 上线前必须确认的三项（当前为待填状态，缺失时站点自动降级为「暂未开放销售」，
// 不会渲染任何无效收款链接，避免用户点击后付款失败）：
//   1) PAY_ENABLED —— 是否已具备真实收款与发货能力
//   2) BUY_LINK    —— 真实商品页地址（面包多 / Gumroad / 自有收银台）
//   3) OPERATOR    —— 运营主体与联系方式（条款、退款页、页脚统一引用）
export const PAY_ENABLED = false;

// 每个付费方法对应的真实商品链接；未配置则视为未上架
export const BUY_LINKS: Record<string, string> = {
  // 例：adler: "https://mbd.pub/o/xxxxx",
};

// 统一兜底链接（配了它就所有未单独配置的方法都走这里）
export const BUY_LINK_FALLBACK = "";

export const OPERATOR = {
  name: "维点图书馆 DimensionsCosmos",
  // 待填：个体工商户/公司全称，或明确标注个人开发者
  legalName: "（待补充运营主体信息）",
  email: "（待补充联系邮箱）",
  repo: "https://github.com/aidulibrary/DimensionsCosmos",
  region: "中国大陆",
};

export const getBuyLink = (methodId: string): string =>
  PAY_ENABLED ? BUY_LINKS[methodId] || BUY_LINK_FALLBACK || "" : "";
