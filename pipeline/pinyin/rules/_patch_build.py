import pathlib
p = pathlib.Path(r'D:\DimensionsCosmos\pipeline\pinyin\build_pinyin.py')
s = p.read_text(encoding='utf-8')
reps = [
 ('        offsets, readings, states, metas = [], [], [], {}',
  '        offsets, readings, states, metas, confs = [], [], [], {}, []'),
 ('            offsets.append(i)\n            readings.append(rd or "")',
  '            offsets.append(i)\n            confs.append(conf)\n            readings.append(rd or "")'),
 ('                    0.88 if m else (0.80 if states[k] == "a" else 0.45),',
  '                    confs[k],'),
 ('                "engine": "L0.5-rule-v1", "len": len(raw),',
  '                "engine": engine, "len": len(raw),'),
 ('        (build_id, time.strftime("%Y-%m-%d %H:%M:%S"), "L0.5-rule-v1", None,',
  '        (build_id, time.strftime("%Y-%m-%d %H:%M:%S"), engine, None,'),
 ('    cfg = {"engine": "L0.5-rule-v1", "window": WINDOW, "limit": args.limit,',
  '    cfg = {"engine": engine, "window": WINDOW, "limit": args.limit,'),
]
for a, b in reps:
    if a not in s:
        print('MISS:', a[:70])
        continue
    s = s.replace(a, b, 1)
    print('OK  :', a[:50].replace('\n', '|'))
p.write_text(s, encoding='utf-8')
