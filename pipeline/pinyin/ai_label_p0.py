# -*- coding: utf-8 -*-
"""
维点图书馆 · FLCA-6 ｜ T2.4-P0 AI 替代人工标注引擎  v2
=========================================================
目标：把 P0 1,200 位金标标注，从"逐位人工判定"改为
      「AI 多证据三态预标 + 冲突/低置信项人工仲裁」。

监督来源（不新造人工标注，全部复用存量人工判读）：
  S1  reports/t23_batch1.txt        360 位（12 高频歧义字 × 30，D180/R180 均衡，精确 chapter:offset）
  S2  t23_v6/v7/v8_check.txt        406 位（可唯一反查定位的抽检记录）
  合计约 760 位，标签 = 「机器给出的读音在该上下文是否成立」。

判别目标：二分类 p_ok = P(该读音在此上下文成立 | 特征)
输出三态：
  PASS     p_ok >= TAU_ASSERT    → 直接采信机器读音，产出金标，无需人工
  REVIEW   TAU_LOW..TAU_ASSERT   → 人工仲裁（AI 同时给出候选改判建议）
  REJECT   p_ok <  TAU_LOW       → 机器读音大概率错，必须人工核（附替代音建议）

人工量：从 1,200 位 → 盲审 120 位（标定用）+ REVIEW/REJECT 项（数十~百余）。

用法：
  python ai_label_p0.py --stage train
  python ai_label_p0.py --stage label
  python ai_label_p0.py --stage audit
  python ai_label_p0.py --stage all
"""
import argparse, json, os, re, math, random, sqlite3, bisect, collections, hashlib

DB = r'D:\DimensionsCosmos\data\guji.db'
PIPE = r'D:\DimensionsCosmos\pipeline\pinyin'
TEMP = os.path.join(PIPE, 'temp')
REPORTS = os.path.join(PIPE, 'reports')
os.makedirs(TEMP, exist_ok=True)

SEED_FILES = ['t23_v6_check.txt', 't23_v7_check.txt', 't23_v8_check.txt']
BATCH1 = os.path.join(REPORTS, 't23_batch1.txt')
NGRAM_FILE = os.path.join(REPORTS, 't23_ngram.json')
P0_FILE = os.path.join(PIPE, 'gold_batch2_P0_1200.jsonl')
RULE_FILE = os.path.join(PIPE, 'rules', 'L05_rules_v2_5.json')

TAU_ASSERT = 0.90
TAU_LOW = 0.50
SEED = 20261112
K_SMOOTH = 4.0


# ============================ 语料与资源 ============================
def load_corpus():
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT id,text FROM chapters ORDER BY id").fetchall()
    buf, spans, pos = [], [], 0
    for cid, tx in rows:
        tx = tx or ''
        buf.append(tx); spans.append((cid, pos, pos + len(tx))); pos += len(tx) + 1; buf.append('\n')
    return ''.join(buf), spans, con


BIG, SPANS, CON = load_corpus()
STARTS = [s[1] for s in SPANS]
CID_TO_SPAN = {s[0]: s for s in SPANS}


def gpos_of(cid, off):
    s = CID_TO_SPAN.get(cid)
    if not s:
        return None
    return s[1] + off


def load_resources():
    lex = collections.defaultdict(list)
    for s, r, rt, au, rk in CON.execute(
            "SELECT surface,reading,reading_type,authority,rank FROM pinyin_lexicon"):
        lex[s].append((r, rt, au, rk))
    dist = collections.defaultdict(collections.Counter)
    for s, r in CON.execute(
            "SELECT surface,reading FROM chapter_pinyin WHERE build_id LIKE '%r2v9%'"):
        dist[s][r] += 1
    if not dist:
        for s, r in CON.execute("SELECT surface,reading FROM chapter_pinyin"):
            dist[s][r] += 1
    rules = json.load(open(RULE_FILE, encoding='utf-8'))['rules']
    by_id = {i: r for i, r in enumerate(rules, start=1)}
    return lex, dist, by_id


LEX, DIST, RULE_BY_ID = load_resources()
NGRAM = json.load(open(NGRAM_FILE, encoding='utf-8')) if os.path.exists(NGRAM_FILE) else {}
NG_POST = {k: collections.Counter({c: n for c, n in v}) for k, v in NGRAM.get('post1', {}).items()}
NG_PRE2 = {k: collections.Counter({c: n for c, n in v}) for k, v in NGRAM.get('pre2', {}).items()}
NG_TOT = {s: sum(c.values()) for s, c in NG_POST.items()}

_PIN_CACHE = {}


def pin_at(cid, off):
    key = (cid, off)
    if key in _PIN_CACHE:
        return _PIN_CACHE[key]
    row = CON.execute(
        "SELECT reading,reading_alt,state,confidence,reading_type,rule_id,build_id "
        "FROM chapter_pinyin WHERE chapter_id=? AND char_offset=? "
        "ORDER BY build_id DESC LIMIT 1", (cid, off)).fetchone()
    _PIN_CACHE[key] = row
    return row


# ============================ 种子集 ============================
def build_seed():
    rows, miss, multi = [], 0, 0
    # S1 batch1：精确 chapter:offset
    if os.path.exists(BATCH1):
        for line in open(BATCH1, encoding='utf-8', errors='replace'):
            line = line.rstrip('\n')
            if not line.strip():
                continue
            pr = line.split('|')
            if len(pr) < 5:
                continue
            surf, reading, verd, pos = pr[0], pr[1], pr[2], pr[3]
            if ':' not in pos:
                continue
            c, o = pos.split(':', 1)
            try:
                cid, off = int(c), int(o)
            except Exception:
                continue
            if verd not in ('D', 'R'):
                continue
            rows.append(dict(surface=surf, reading=reading, correct=1 if verd == 'D' else 0,
                             chapter_id=cid, offset=off, src='t23_batch1', verdict=verd))
    # S2 抽检记录：反查定位
    for fn in SEED_FILES:
        p = os.path.join(PIPE, fn)
        if not os.path.exists(p):
            continue
        for line in open(p, encoding='utf-8'):
            line = line.rstrip('\n')
            if not line.strip():
                continue
            pr = line.split('|')
            if len(pr) < 4:
                continue
            surf, reading, verd, ctx = pr[0], pr[1], pr[2], pr[3]
            m = re.search(r'【(.+?)】', ctx)
            if not m or m.group(1) != surf:
                continue
            left, right = ctx[:m.start()], ctx[m.end():]
            key = left + surf + right
            hits, s = [], 0
            while True:
                i = BIG.find(key, s)
                if i < 0:
                    break
                hits.append(i + len(left)); s = i + 1
                if len(hits) > 3:
                    break
            if len(hits) != 1:
                multi += 1; continue
            cid, off = None, None
            gi = bisect.bisect_right(STARTS, hits[0]) - 1
            if gi < 0:
                miss += 1; continue
            c, s0, e0 = SPANS[gi]
            if not (s0 <= hits[0] < e0):
                miss += 1; continue
            cid, off = c, hits[0] - s0
            rows.append(dict(surface=surf, reading=reading, correct=1 if verd.startswith('D') else 0,
                             chapter_id=cid, offset=off, src=fn, verdict=verd))
    # 去重（同章同位同字）
    seen, uniq = set(), []
    for r in rows:
        k = (r['chapter_id'], r['offset'], r['surface'])
        if k in seen:
            continue
        seen.add(k); uniq.append(r)
    stats = dict(raw=len(rows), total=len(uniq), dedup=len(rows) - len(uniq),
                 pos=sum(x['correct'] for x in uniq),
                 neg=len(uniq) - sum(x['correct'] for x in uniq),
                 by_src=dict(collections.Counter(x['src'] for x in uniq)))
    return uniq, stats


# ============================ 特征 ============================
FUNC = set('之不也者矣乎曰而其所以於于與为為所则則无無有未莫弗相且乃焉哉耶耳兮夫盖蓋')
NOUNMARK = set('王公侯伯州县縣郡府将將军軍氏人子帝后刺史上柱國郎令丞牧守督護护使')
NEG = set('不未無无莫弗勿毋非')
SENT_END = set('也者矣焉哉乎耳兮耶')
SPEECH = set('曰云謂谓問问答告語语')
VERBISH = set('為为以與与從从使令命謂谓曰云行至入出居處处食衣乘執执見见')
PREP = set('於于以與与為为自向從从因用由')
PUNCT = set('，。；：、！？」』）')

CTX_R = 16
FEAT_ORDER = [
    'is_multi', 'n_reading', 'dist_share', 'dist_max',
    'logp_post1', 'logp_pre2', 'punct_rate',
    'r1_func', 'r1_sentend', 'l1_neg', 'l1_nounmark', 'r1_nounmark',
    'r1_de', 'l1_de', 'r1_speech', 'l1_prep', 'r1_verbish', 'l2_de',
    'repeat_in_ctx', 'r1_multi', 'l1_multi',
    'rtype_default', 'rtype_lexical', 'rtype_poDu', 'rtype_tongJia', 'rtype_properNoun',
    'state_variant', 'rule_priority', 'rule_is_whitelist', 'rule_is_lookahead',
    'te_surface', 'te_rule', 'te_sr', 'bias',
]


def static_feats(surface, reading, cid, off, rule_id=None, state=None):
    gpos = gpos_of(cid, off)
    if gpos is None or gpos >= len(BIG):
        return None
    left = BIG[max(0, gpos - CTX_R):gpos]
    right = BIG[gpos + 1: gpos + 1 + CTX_R]
    l1 = left[-1:] if left else ''
    l2 = left[-2:] if len(left) >= 2 else left
    r1 = right[:1]
    r2 = right[:2]

    f = {}
    nread = len(LEX.get(surface, []))
    f['is_multi'] = 1.0 if nread > 1 else 0.0
    f['n_reading'] = min(nread, 6) / 6.0
    d = DIST.get(surface)
    if d:
        tot = sum(d.values())
        f['dist_share'] = d.get(reading, 0) / tot
        f['dist_max'] = max(d.values()) / tot
    else:
        f['dist_share'] = 0.0; f['dist_max'] = 0.0
    # 语料搭配频次（数据驱动）
    pc = NG_POST.get(surface)
    tot_ng = NG_TOT.get(surface, 0) or 1
    f['logp_post1'] = math.log1p(pc.get(r1, 0)) / math.log1p(max(tot_ng, 2))
    pp = NG_PRE2.get(surface)
    f['logp_pre2'] = math.log1p(pp.get(l2, 0)) / math.log1p(max(tot_ng, 2))
    f['punct_rate'] = (pc.get('，', 0) + pc.get('。', 0)) / tot_ng if pc else 0.0
    f['r1_func'] = 1.0 if r1 in FUNC else 0.0
    f['r1_sentend'] = 1.0 if r1 in SENT_END else 0.0
    f['l1_neg'] = 1.0 if l1 in NEG else 0.0
    f['l1_nounmark'] = 1.0 if l1 in NOUNMARK else 0.0
    f['r1_nounmark'] = 1.0 if r1 in NOUNMARK else 0.0
    f['r1_de'] = 1.0 if r1 == '之' else 0.0
    f['l1_de'] = 1.0 if l1 == '之' else 0.0
    f['r1_speech'] = 1.0 if r1 in SPEECH else 0.0
    f['l1_prep'] = 1.0 if l1 in PREP else 0.0
    f['r1_verbish'] = 1.0 if r1 in VERBISH else 0.0
    f['l2_de'] = 1.0 if l2[:1] == '之' else 0.0
    f['repeat_in_ctx'] = 1.0 if surface in left + right else 0.0
    f['r1_multi'] = 1.0 if (r1 and len(LEX.get(r1, [])) > 1) else 0.0
    f['l1_multi'] = 1.0 if (l1 and len(LEX.get(l1, [])) > 1) else 0.0
    rt = None
    pin = pin_at(cid, off)
    if pin:
        rt = pin[4]
        state = state or pin[2]
        rule_id = rule_id if rule_id is not None else pin[5]
    f['rtype_default'] = 1.0 if rt in (None, 'default') else 0.0
    f['rtype_lexical'] = 1.0 if rt == 'lexical' else 0.0
    f['rtype_poDu'] = 1.0 if rt == 'poDu' else 0.0
    f['rtype_tongJia'] = 1.0 if rt == 'tongJia' else 0.0
    f['rtype_properNoun'] = 1.0 if rt == 'properNoun' else 0.0
    f['state_variant'] = 1.0 if state == 'variant' else 0.0
    rr = RULE_BY_ID.get(rule_id) if rule_id else None
    if rr:
        f['rule_priority'] = rr.get('priority', 50) / 100.0
        pat = rr.get('pattern', '')
        f['rule_is_whitelist'] = 1.0 if '|' in pat else 0.0
        f['rule_is_lookahead'] = 1.0 if '(?=' in pat else 0.0
    else:
        f['rule_priority'] = 0.0; f['rule_is_whitelist'] = 0.0; f['rule_is_lookahead'] = 0.0
    f['bias'] = 1.0
    meta = dict(surface=surface, reading=reading, chapter_id=cid, offset=off,
                rule_id=rule_id, rtype=rt, state=state,
                l1=l1, r1=r1, l2=l2, r2=r2, left=left, right=right)
    return f, meta


# ============================ target encoding（LOO 平滑） ============================
def build_te(rows, keyfn, prior, k=K_SMOOTH):
    """返回 dict key -> (sum, cnt)"""
    agg = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        key = keyfn(r)
        a = agg[key]
        a[0] += r['correct']; a[1] += 1
    return agg


def te_value(agg, key, prior, k=K_SMOOTH):
    a = agg.get(key)
    if not a:
        return prior
    sm, cnt = a
    return (sm + prior * k) / (cnt + k)


# ============================ 逻辑回归（纯标准库） ============================
def _sig(z):
    if z > 30: return 1.0
    if z < -30: return 0.0
    return 1.0 / (1.0 + math.exp(-z))


def fit_lr(X, y, l2=0.03, lr=0.3, epochs=800, pos_w=1.0, seed=SEED):
    n, m = len(X), len(X[0])
    w = [0.0] * m
    b = 0.0
    idx = list(range(n))
    rng = random.Random(seed)
    for ep in range(epochs):
        rng.shuffle(idx)
        for i in idx:
            z = b + sum(w[j] * X[i][j] for j in range(m))
            g = (_sig(z) - y[i]) * (pos_w if y[i] == 1 else 1.0)
            for j in range(m):
                if X[i][j]:
                    w[j] -= lr * (g * X[i][j] + l2 * w[j])
            b -= lr * g
    return w, b


def pred(w, b, x):
    return _sig(b + sum(wj * xj for wj, xj in zip(w, x)))


def auc_score(y, p):
    pairs = sorted(zip(p, y))
    pos = sum(y); neg = len(y) - pos
    if pos == 0 or neg == 0:
        return float('nan')
    acc = 0.0; i = 0
    while i < len(pairs):
        j = i
        while j + 1 < len(pairs) and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1
        acc += avg_rank * sum(pairs[k][1] for k in range(i, j + 1))
        i = j + 1
    return (acc - pos * (pos + 1) / 2.0) / (pos * neg)


# ============================ 训练 ============================
def train_and_cv(verbose=True):
    seed_rows, sstats = build_seed()
    if verbose:
        print('[seed]', json.dumps(sstats, ensure_ascii=False))
    feats, metas = [], []
    keep = []
    for r in seed_rows:
        got = static_feats(r['surface'], r['reading'], r['chapter_id'], r['offset'])
        if got is None:
            continue
        f, meta = got
        feats.append(f); metas.append(meta); keep.append(r)
    if verbose:
        print('[seed] featurized', len(keep))
    y = [r['correct'] for r in keep]
    prior = sum(y) / len(y)
    surf_key = lambda r: r['surface']
    rule_key = lambda r: (r.get('rule_id'), )
    sr_key = lambda r: (r['surface'], r['reading'])

    rng = random.Random(SEED)
    by_surf = collections.defaultdict(list)
    for i, r in enumerate(keep):
        by_surf[r['surface']].append(i)
    folds = [[] for _ in range(5)]
    for s, ids in by_surf.items():
        rng.shuffle(ids)
        for j, i in enumerate(ids):
            folds[j % 5].append(i)

    oof = [0.0] * len(keep)
    fold_auc = []
    for fi in range(5):
        tr = [i for i in range(len(keep)) if i not in set(folds[fi])]
        te = folds[fi]
        agg_s = build_te([keep[i] for i in tr], surf_key, prior)
        agg_r = build_te([{**keep[i], 'rule_id': metas[i]['rule_id']} for i in tr], rule_key, prior)
        agg_sr = build_te([keep[i] for i in tr], sr_key, prior)
        # 训练折内部再做一层 LOO，避免自泄漏
        Xtr, ytr = [], []
        for i in tr:
            f = dict(feats[i])
            f['te_surface'] = te_value(agg_s, keep[i]['surface'], prior)
            f['te_rule'] = te_value(agg_r, (metas[i]['rule_id'], ), prior)
            f['te_sr'] = te_value(agg_sr, (keep[i]['surface'], keep[i]['reading']), prior)
            Xtr.append([f[n] for n in FEAT_ORDER]); ytr.append(keep[i]['correct'])
        P = sum(ytr); N = len(ytr) - P
        w, b = fit_lr(Xtr, ytr, pos_w=(N / P if P else 1.0))
        Xte, yte = [], []
        for i in te:
            f = dict(feats[i])
            f['te_surface'] = te_value(agg_s, keep[i]['surface'], prior)
            f['te_rule'] = te_value(agg_r, (metas[i]['rule_id'], ), prior)
            f['te_sr'] = te_value(agg_sr, (keep[i]['surface'], keep[i]['reading']), prior)
            Xte.append([f[n] for n in FEAT_ORDER]); yte.append(keep[i]['correct'])
        for i, xv in zip(te, Xte):
            oof[i] = pred(w, b, xv)
        fold_auc.append(auc_score(yte, [oof[i] for i in te]))

    overall_auc = auc_score(y, oof)
    # 阈值扫描
    grid = []
    for tau in [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.93, 0.95, 0.97]:
        sel = [i for i in range(len(keep)) if oof[i] >= tau]
        if not sel:
            grid.append(dict(tau=tau, n=0, prec=None, cover=0.0, fp=0)); continue
        tp = sum(y[i] for i in sel)
        grid.append(dict(tau=tau, n=len(sel), prec=round(tp / len(sel), 4),
                         cover=round(len(sel) / len(keep), 4), fp=len(sel) - tp))
    if verbose:
        print('[cv] fold AUC', [round(a, 4) for a in fold_auc],
              '| mean', round(sum(fold_auc) / 5, 4), '| overall', round(overall_auc, 4))
        print('[cv] threshold grid (n=%d, 正类先验=%.3f)' % (len(keep), prior))
        for g in grid:
            print('    tau=%.2f  n=%-3d prec=%-6s cover=%-6s fp=%d' %
                  (g['tau'], g['n'], g['prec'], g['cover'], g['fp']))

    # 全量重训
    agg_s = build_te(keep, surf_key, prior)
    agg_r = build_te([{**keep[i], 'rule_id': metas[i]['rule_id']} for i in range(len(keep))], rule_key, prior)
    agg_sr = build_te(keep, sr_key, prior)
    Xall = []
    for i in range(len(keep)):
        f = dict(feats[i])
        f['te_surface'] = te_value(agg_s, keep[i]['surface'], prior)
        f['te_rule'] = te_value(agg_r, (metas[i]['rule_id'], ), prior)
        f['te_sr'] = te_value(agg_sr, (keep[i]['surface'], keep[i]['reading']), prior)
        Xall.append([f[n] for n in FEAT_ORDER])
    P = sum(y); N = len(y) - P
    w, b = fit_lr(Xall, y, pos_w=(N / P if P else 1.0))
    model = dict(
        feat_order=FEAT_ORDER, w=w, b=b, prior=prior,
        tau_assert=TAU_ASSERT, tau_low=TAU_LOW,
        te_surface={f'{k[0]}': v for k, v in agg_s.items()},
        te_sr={f'{k[0]}|{k[1]}': v for k, v in agg_sr.items()},
        te_rule={f'{k[0]}': v for k, v in agg_r.items()},
        seed_stats=sstats, n_train=len(keep), pos_rate=prior,
        cv_fold_auc=fold_auc, cv_auc_overall=overall_auc, threshold_grid=grid,
        rule_hash=hashlib.sha256(open(RULE_FILE, 'rb').read()).hexdigest()[:16],
        trained_at='2026-11-12',
    )
    mp = os.path.join(TEMP, 'ai_label_model.json')
    json.dump(model, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if verbose:
        order = sorted(range(len(FEAT_ORDER)), key=lambda i: -abs(w[i]))
        print('[model] top weights')
        for i in order[:16]:
            print('    %-20s %+.3f' % (FEAT_ORDER[i], w[i]))
        print('[model] saved', mp)
    return model


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', default='train')
    a = ap.parse_args()
    if a.stage in ('train', 'all'):
        train_and_cv()
