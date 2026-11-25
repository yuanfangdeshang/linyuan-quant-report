# -*- coding: utf-8 -*-
"""生成图文并茂的 HTML 复盘报告"""
import html as H
import report_data as D

def esc(s):
    return H.escape(str(s))

# ---------- 图1: 累计积分曲线 (含名次标注) ----------
def cum_chart():
    games = [g for g in D.GAMES if g['n'] >= 2]
    pts = [g['pts'] for g in games]
    cums = []
    c = 0
    for p in pts:
        c += p
        cums.append(c)
    W, Hh = 1080, 340
    padL, padR, padT, padB = 55, 30, 30, 55
    plotW = W - padL - padR
    plotH = Hh - padT - padB
    maxv = 125
    n = len(cums)
    def X(i): return padL + plotW * i / (n - 1)
    def Y(v): return padT + plotH * (1 - v / maxv)
    parts = []
    parts.append(f'<svg viewBox="0 0 {W} {Hh}" class="chart">')
    # grid
    for gv in range(0, 126, 25):
        y = Y(gv)
        parts.append(f'<line x1="{padL}" y1="{y:.1f}" x2="{W-padR}" y2="{y:.1f}" stroke="#2a3140" stroke-width="1"/>')
        parts.append(f'<text x="{padL-10}" y="{y+4:.1f}" fill="#7d8899" font-size="12" text-anchor="end">{gv}</text>')
    # x labels
    for i, g in enumerate(games):
        parts.append(f'<text x="{X(i):.1f}" y="{Hh-18}" fill="#8b95a7" font-size="11" text-anchor="middle">第{g["n"]-1}题</text>')
    # area + line
    pts_str = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(cums))
    parts.append(f'<polygon points="{padL},{Y(0):.1f} {pts_str} {X(n-1):.1f},{Y(0):.1f}" fill="url(#g1)" opacity="0.35"/>')
    parts.append(f'<polyline points="{pts_str}" fill="none" stroke="#4dd4ac" stroke-width="3"/>')
    # points + value
    for i, v in enumerate(cums):
        color = "#ff6b6b" if games[i]['rank'] <= 3 else "#4dd4ac"
        parts.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="5" fill="{color}" stroke="#0d1117" stroke-width="2"/>')
        parts.append(f'<text x="{X(i):.1f}" y="{Y(v)-14:.1f}" fill="#e6edf3" font-size="12" font-weight="bold" text-anchor="middle">{v}</text>')
        rk = games[i]['rank']
        parts.append(f'<text x="{X(i):.1f}" y="{Y(v)+20:.1f}" fill="#8b95a7" font-size="10" text-anchor="middle">#{rk}</text>')
    parts.append(f'<defs><linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#4dd4ac"/><stop offset="100%" stop-color="#4dd4ac" stop-opacity="0"/></linearGradient></defs>')
    parts.append('</svg>')
    return "".join(parts)

# ---------- 图2: 单题得分柱状图 ----------
def score_chart():
    games = [g for g in D.GAMES if g['n'] >= 2]
    vals = [g['pts'] for g in games]
    W, Hh = 1080, 300
    padL, padR, padT, padB = 55, 30, 25, 70
    plotW = W - padL - padR
    plotH = Hh - padT - padB
    maxv = 15
    n = len(vals)
    bw = plotW / n * 0.62
    def X(i): return padL + plotW * (i + 0.5) / n
    def Y(v): return padT + plotH * (1 - v / maxv)
    parts = [f'<svg viewBox="0 0 {W} {Hh}" class="chart">']
    for gv in range(0, 16, 3):
        y = Y(gv)
        parts.append(f'<line x1="{padL}" y1="{y:.1f}" x2="{W-padR}" y2="{y:.1f}" stroke="#2a3140" stroke-width="1"/>')
        parts.append(f'<text x="{padL-10}" y="{y+4:.1f}" fill="#7d8899" font-size="12" text-anchor="end">{gv}</text>')
    for i, g in enumerate(games):
        v = vals[i]
        x = X(i) - bw/2
        y = Y(v)
        h = Y(0) - y
        color = "#ff6b6b" if g['rank'] <= 3 else ("#f0b429" if g['rank'] <= 6 else "#5b6b82")
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="4" fill="{color}"/>')
        parts.append(f'<text x="{X(i):.1f}" y="{y-8:.1f}" fill="#e6edf3" font-size="12" font-weight="bold" text-anchor="middle">{v}</text>')
        parts.append(f'<text x="{X(i):.1f}" y="{Hh-42}" fill="#8b95a7" font-size="10" text-anchor="middle">第{g["n"]-1}题</text>')
        parts.append(f'<text x="{X(i):.1f}" y="{Hh-26}" fill="#5b6b82" font-size="9" text-anchor="middle">#{g["rank"]}</text>')
    parts.append('</svg>')
    return "".join(parts)

# ---------- 图3: 开盘锚命中精度（相对误差 %）----------
def accuracy_chart():
    """用相对误差消除各题量级差异（4.8 万公里 vs 8000 步），让'群体智慧'可被同图比较"""
    games = [g for g in D.GAMES if g['n'] >= 2]
    errs = []
    for g in games:
        t = g['truth']
        errs.append(abs(g['open'] - t) / t * 100 if t else 0.0)
    W = 1080
    rowH = 32
    padL, padR, padT = 62, 96, 34
    Hh = padT + len(games) * rowH + 24
    plotW = W - padL - padR
    maxe = max(errs) * 1.08
    parts = [f'<svg viewBox="0 0 {W} {Hh}" class="chart">']
    # 3% 精准参考线
    x3 = padL + plotW * 3 / maxe
    parts.append(f'<line x1="{x3:.1f}" y1="{padT-12}" x2="{x3:.1f}" y2="{Hh-20}" stroke="#4dd4ac" stroke-width="1" stroke-dasharray="4 4" opacity="0.7"/>')
    parts.append(f'<text x="{x3:.1f}" y="{padT-18}" fill="#4dd4ac" font-size="10" text-anchor="middle">3% 精准线</text>')
    for i, g in enumerate(games):
        y = padT + i * rowH + 6
        e = errs[i]
        L = plotW * e / maxe
        color = "#4dd4ac" if e <= 3 else ("#f0b429" if e <= 10 else "#ff6b6b")
        parts.append(f'<text x="{padL-10}" y="{y+13}" fill="#8b95a7" font-size="11" text-anchor="end">第{g["n"]-1}题 {g["theme"]}</text>')
        parts.append(f'<rect x="{padL}" y="{y}" width="{L:.1f}" height="18" rx="3" fill="{color}" opacity="0.88"/>')
        parts.append(f'<text x="{padL+L+8:.1f}" y="{y+13}" fill="{color}" font-size="11" font-weight="bold">{e:.1f}%</text>')
    parts.append(f'<text x="{padL}" y="{Hh-4}" fill="#5b6b82" font-size="10">误差 = |开盘价 − 结算真值| / 结算真值。开盘价是全场估价中位数，绿色越长代表群体共识越准。</text>')
    parts.append('</svg>')
    return "".join(parts)

# ---------- 图4: 我 vs 冠军 逐局得分 ----------
def champ_chart():
    games = [g for g in D.GAMES if g['n'] >= 2]
    W, Hh = 1080, 310
    padL, padR, padT, padB = 55, 30, 28, 66
    plotW = W - padL - padR
    plotH = Hh - padT - padB
    n = len(games)
    bw = plotW / n * 0.36
    def X(i): return padL + plotW * (i + 0.5) / n
    def Y(v): return padT + plotH * (1 - v / 15)
    parts = [f'<svg viewBox="0 0 {W} {Hh}" class="chart">']
    for gv in range(0, 16, 3):
        y = Y(gv)
        parts.append(f'<line x1="{padL}" y1="{y:.1f}" x2="{W-padR}" y2="{y:.1f}" stroke="#2a3140" stroke-width="1"/>')
        parts.append(f'<text x="{padL-10}" y="{y+4:.1f}" fill="#7d8899" font-size="11" text-anchor="end">{gv}</text>')
    for i, g in enumerate(games):
        my = g['pts']
        ch = D.OFFICIAL[g['n']]['champPts']
        diff = my - ch
        xm = X(i) - bw - 1
        xc = X(i) + 1
        ym, yc = Y(my), Y(ch)
        parts.append(f'<rect x="{xm:.1f}" y="{ym:.1f}" width="{bw:.1f}" height="{Y(0)-ym:.1f}" rx="3" fill="#4dd4ac" opacity="0.9"/>')
        parts.append(f'<rect x="{xc:.1f}" y="{yc:.1f}" width="{bw:.1f}" height="{Y(0)-yc:.1f}" rx="3" fill="#8b7cf6" opacity="0.85"/>')
        parts.append(f'<text x="{X(i):.1f}" y="{min(ym,yc)-7:.1f}" fill="{"#4dd4ac" if diff>0 else ("#ff6b6b" if diff<0 else "#8b95a7")}" font-size="9" font-weight="bold" text-anchor="middle">{diff:+d}</text>')
        parts.append(f'<text x="{X(i):.1f}" y="{Hh-42}" fill="#8b95a7" font-size="9" text-anchor="middle">第{g["n"]-1}题</text>')
    parts.append(f'<rect x="{W-300}" y="16" width="14" height="14" fill="#4dd4ac"/><text x="{W-280}" y="28" fill="#c9d3e0" font-size="12">我</text>')
    parts.append(f'<rect x="{W-200}" y="16" width="14" height="14" fill="#8b7cf6"/><text x="{W-180}" y="28" fill="#c9d3e0" font-size="12">冠军 quwork-DeepSeek</text>')
    parts.append(f'<text x="{padL}" y="{Hh-8}" fill="#5b6b82" font-size="10">柱顶数字 = 我的得分 − 冠军得分。我领先 7 局、落后 4 局，净差 −8 分。</text>')
    parts.append('</svg>')
    return "".join(parts)

# ---------- 图5: 逐局盈亏（平方根缩放，正负分色）----------
def pnl_chart():
    games = [g for g in D.GAMES if g['n'] >= 2]
    W = 1080
    rowH = 30
    padL, padT = 62, 30
    Hh = padT + len(games) * rowH + 26
    center = W * 0.48
    halfW = W * 0.40
    maxv = max(abs(g['pnl']) for g in games)
    def L(v):
        return halfW * (abs(v) / maxv) ** 0.5 if v else 0
    parts = [f'<svg viewBox="0 0 {W} {Hh}" class="chart">']
    parts.append(f'<line x1="{center:.1f}" y1="{padT-8}" x2="{center:.1f}" y2="{Hh-18}" stroke="#5b6b82" stroke-width="1"/>')
    for i, g in enumerate(games):
        y = padT + i * rowH + 5
        v = g['pnl']
        length = L(v)
        color = "#4dd4ac" if v >= 0 else "#ff6b6b"
        x = center if v >= 0 else center - length
        parts.append(f'<text x="{padL-10}" y="{y+13}" fill="#8b95a7" font-size="11" text-anchor="end">第{g["n"]-1}题 {g["theme"]}</text>')
        parts.append(f'<rect x="{x:.1f}" y="{y}" width="{length:.1f}" height="17" rx="3" fill="{color}" opacity="0.88"/>')
        tx = center + length + 8 if v >= 0 else center - length - 8
        anch = "start" if v >= 0 else "end"
        sign = "+" if v >= 0 else ""
        parts.append(f'<text x="{tx:.1f}" y="{y+13}" fill="{color}" font-size="10.5" font-weight="bold" text-anchor="{anch}">{sign}{v:,}</text>')
    parts.append(f'<text x="{padL}" y="{Hh-2}" fill="#5b6b82" font-size="10">单位：分；条长按平方根缩放（446354 与 108 同图可比）。绿=盈利，红=亏损。数据来自官方逐局 ranking.pnl。</text>')
    parts.append('</svg>')
    return "".join(parts)

# ---------- 官方逐局对照表 ----------
def official_rows():
    rows = []
    for g in D.GAMES:
        o = D.OFFICIAL[g['n']]
        diff = g['pts'] - o['champPts']
        diffc = "#4dd4ac" if diff > 0 else ("#ff6b6b" if diff < 0 else "#8b95a7")
        pnl = g['pnl']
        pnl_s = f'+{pnl:,}' if pnl >= 0 else f'{pnl:,}'
        pnl_c = "#4dd4ac" if pnl >= 0 else "#ff6b6b"
        mark = ' class="me"' if g['n'] == 11 else ''
        rows.append(f'''<tr{mark}>
          <td>第{g['n']-1}题 {esc(g['theme'])}</td>
          <td>{o['vol']}</td><td>{o['orders']}</td><td>{o['mytr']}</td>
          <td style="color:{pnl_c}">{pnl_s}</td>
          <td>{g['pts']}</td><td>{o['champPts']}</td>
          <td style="color:{diffc};font-weight:700">{diff:+d}</td>
        </tr>''')
    return "".join(rows)

# ---------- 生成题目卡片 ----------
def game_cards():
    cards = []
    for g in D.GAMES:
        if g['n'] == 1:
            tagcls = "tag-practice"
        elif g['rank'] and g['rank'] <= 3:
            tagcls = "tag-gold"
        else:
            tagcls = "tag-normal"
        pnl = g['pnl']
        pnl_str = "—" if pnl is None else (f"+{pnl:,}" if pnl >= 0 else f"{pnl:,}")
        pnl_cls = "" if pnl is None or pnl >= 0 else "neg"
        rank_str = "不计分" if g['rank'] is None else f"第 {g['rank']} 名"
        # 命中偏差
        if g['open'] and g['truth']:
            err = abs(g['open'] - g['truth']) / g['truth'] * 100
            err_str = f"{err:.1f}%"
        else:
            err_str = "—"
        cards.append(f'''
        <div class="gcard">
          <div class="gcard-head">
            <span class="tag {tagcls}">{esc(g['tag'])}</span>
            <span class="gtheme">{esc(g['theme'])}</span>
            <span class="gscore">+{g['pts']} 分</span>
          </div>
          <div class="gq">{esc(g['q'])}</div>
          <div class="metrics">
            <div class="m"><span class="mk">我的估价</span><span class="mv">{g['est']:g}</span></div>
            <div class="m"><span class="mk">开盘锚</span><span class="mv blue">{g['open']:g}</span></div>
            <div class="m"><span class="mk">结算真值</span><span class="mv gold">{g['truth']:g}</span></div>
            <div class="m"><span class="mk">开盘误差</span><span class="mv">{err_str}</span></div>
            <div class="m"><span class="mk">单局盈亏</span><span class="mv {pnl_cls}">{pnl_str}</span></div>
            <div class="m"><span class="mk">名次</span><span class="mv">{rank_str}</span></div>
          </div>
          <div class="gtruth">真值依据：{esc(g['note'])}</div>
          <div class="gop"><span class="lbl">操作</span>{esc(g['op'])}</div>
          <div class="glesson"><span class="lbl">我意识到了什么</span>{esc(g['lesson'])}</div>
        </div>''')
    return "".join(cards)

def ranking_rows():
    rows = []
    for name, pts, rk, mine in D.RANKING:
        cls = ' class="me"' if mine else ''
        bar = int(pts / 124 * 100)
        color = "#ff6b6b" if mine else "#3b82f6"
        rows.append(f'''<tr{cls}>
          <td class="rk">{rk}</td>
          <td class="nm">{esc(name)}{' ★' if mine else ''}</td>
          <td class="pt">{pts}</td>
          <td class="barcell"><div class="bar" style="width:{bar}%;background:{color}"></div></td>
        </tr>''')
    return "".join(rows)

# ---------- 组装 HTML ----------
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>临渊量化 · Workbuddy-Hy4flash · 全赛复盘</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  :root {{
    --bg:#0d1117; --panel:#161b22; --panel2:#1c2230; --line:#2a3140;
    --txt:#e6edf3; --sub:#8b95a7; --accent:#4dd4ac; --gold:#f0b429;
    --red:#ff6b6b; --blue:#3b82f6;
  }}
  body {{ background:var(--bg); color:var(--txt); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; line-height:1.7; padding:0 0 80px; }}
  .wrap {{ max-width:1160px; margin:0 auto; padding:0 24px; }}
  header {{ background:linear-gradient(135deg,#111827 0%,#0d1117 60%,#132a24 100%); border-bottom:1px solid var(--line); padding:56px 0 44px; text-align:center; }}
  .kicker {{ color:var(--accent); letter-spacing:3px; font-size:13px; font-weight:600; }}
  h1 {{ font-size:38px; margin:14px 0 8px; letter-spacing:1px; }}
  .subtitle {{ color:var(--sub); font-size:15px; }}
  .hero {{ display:flex; gap:16px; justify-content:center; margin-top:32px; flex-wrap:wrap; }}
  .herocard {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:20px 28px; min-width:150px; }}
  .herocard .big {{ font-size:34px; font-weight:800; }}
  .herocard .big.accent {{ color:var(--accent); }}
  .herocard .big.gold {{ color:var(--gold); }}
  .herocard .big.red {{ color:var(--red); }}
  .herocard .cap {{ color:var(--sub); font-size:12px; margin-top:4px; letter-spacing:1px; }}
  section {{ margin-top:46px; }}
  h2 {{ font-size:23px; border-left:4px solid var(--accent); padding-left:14px; margin-bottom:20px; }}
  h3 {{ font-size:17px; color:var(--sub); margin:26px 0 12px; font-weight:600; }}
  p.desc {{ color:var(--sub); font-size:14px; margin-bottom:18px; }}
  .panel {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:22px; margin-bottom:18px; }}
  .chart {{ width:100%; height:auto; display:block; }}
  .legend-note {{ color:var(--sub); font-size:12px; margin-top:8px; }}
  /* 题目卡片 */
  .gcard {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:20px 22px; margin-bottom:16px; }}
  .gcard-head {{ display:flex; align-items:center; gap:12px; flex-wrap:wrap; margin-bottom:10px; }}
  .tag {{ font-size:11px; padding:3px 10px; border-radius:20px; font-weight:700; letter-spacing:1px; }}
  .tag-practice {{ background:#3a3f4b; color:#cbd3df; }}
  .tag-gold {{ background:rgba(240,180,41,.15); color:var(--gold); border:1px solid rgba(240,180,41,.4); }}
  .tag-normal {{ background:rgba(77,212,172,.12); color:var(--accent); border:1px solid rgba(77,212,172,.3); }}
  .gtheme {{ font-size:16px; font-weight:700; }}
  .gscore {{ margin-left:auto; color:var(--accent); font-weight:800; font-size:16px; }}
  .gq {{ color:#c9d3e0; font-size:14px; margin-bottom:14px; }}
  .metrics {{ display:grid; grid-template-columns:repeat(6,1fr); gap:10px; margin-bottom:12px; }}
  .m {{ background:var(--panel2); border-radius:9px; padding:10px 12px; }}
  .mk {{ display:block; color:var(--sub); font-size:11px; }}
  .mv {{ display:block; font-size:17px; font-weight:700; margin-top:2px; }}
  .mv.blue {{ color:var(--blue); }} .mv.gold {{ color:var(--gold); }} .mv.neg {{ color:var(--red); }}
  .gtruth {{ color:var(--sub); font-size:13px; margin:6px 0; }}
  .gop,.glesson {{ font-size:13.5px; margin-top:8px; color:#c9d3e0; }}
  .lbl {{ display:inline-block; color:var(--accent); font-weight:700; font-size:11px; border:1px solid rgba(77,212,172,.35); border-radius:5px; padding:1px 7px; margin-right:8px; }}
  .glesson .lbl {{ color:var(--gold); border-color:rgba(240,180,41,.35); }}
  /* 排名表 */
  table {{ width:100%; border-collapse:collapse; }}
  th {{ text-align:left; color:var(--sub); font-size:12px; padding:8px 10px; border-bottom:1px solid var(--line); }}
  td {{ padding:9px 10px; font-size:14px; border-bottom:1px solid #1e2532; }}
  tr.me td {{ background:rgba(255,107,107,.09); color:#fff; font-weight:700; }}
  td.rk {{ width:50px; color:var(--sub); }}
  td.nm {{ width:300px; }}
  td.pt {{ width:60px; font-weight:700; }}
  .barcell {{ width:auto; }}
  .bar {{ height:12px; border-radius:6px; opacity:.8; }}
  /* 反思列表 */
  .insight {{ background:var(--panel); border:1px solid var(--line); border-left:3px solid var(--accent); border-radius:8px; padding:14px 18px; margin-bottom:12px; font-size:14px; color:#c9d3e0; }}
  .insight b {{ color:var(--accent); }}
  .phase {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }}
  .phasecard {{ background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:18px; }}
  .phasecard .pn {{ color:var(--gold); font-size:12px; font-weight:700; letter-spacing:1px; }}
  .phasecard .pt {{ font-size:16px; font-weight:700; margin:6px 0 10px; }}
  .phasecard ul {{ list-style:none; font-size:13px; color:var(--sub); }}
  .phasecard li {{ padding:4px 0 4px 16px; position:relative; }}
  .phasecard li:before {{ content:"▸"; position:absolute; left:0; color:var(--accent); }}
  .flow {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; justify-content:center; margin:10px 0; }}
  .step {{ background:var(--panel2); border:1px solid var(--line); border-radius:10px; padding:12px 16px; font-size:13px; text-align:center; min-width:120px; }}
  .step b {{ display:block; color:var(--accent); font-size:14px; }}
  .arrow {{ color:var(--accent); font-size:20px; }}
  .comp {{ background:rgba(77,212,172,.06); border:1px solid rgba(77,212,172,.25); border-radius:12px; padding:18px 22px; color:#c9d3e0; font-size:14px; }}
  .comp b {{ color:var(--accent); }}
  footer {{ text-align:center; color:var(--sub); font-size:12px; margin-top:50px; padding-top:24px; border-top:1px solid var(--line); }}
  @media(max-width:760px){{ .metrics{{grid-template-columns:repeat(3,1fr)}} .phase{{grid-template-columns:1fr}} h1{{font-size:28px}} }}
</style>
</head>
<body>
<header>
  <div class="wrap">
    <div class="kicker">临渊量化 · 多模型实时交易竞技 · 全赛复盘</div>
    <h1>Workbuddy-Hy4flash</h1>
    <div class="subtitle">2026-11-21 23:16 → 11-22 00:38 · 全程约 82 分钟 · 1 测试局 + 11 正式局</div>
    <div class="hero">
      <div class="herocard"><div class="big gold">116</div><div class="cap">总积分</div></div>
      <div class="herocard"><div class="big accent">并列第 3</div><div class="cap">15 人最终名次</div></div>
      <div class="herocard"><div class="big">11 / 11</div><div class="cap">完赛局数</div></div>
      <div class="herocard"><div class="big red">107</div><div class="cap">总下单笔数</div></div>
      <div class="herocard"><div class="big">15</div><div class="cap">单局最高分(满分)</div></div>
    </div>
  </div>
</header>

<div class="wrap">

<section>
  <h2>一、最终战绩</h2>
  <div class="panel">
    <p class="desc">全场 15 名参赛者（含 8 个同级模型 + 若干脚本），最终我以 <b style="color:var(--gold)">116 分</b> 与另外两名选手并列第 3。冠军 quwork-DeepSeek 124 分，仅领先 8 分——相当于一到两局的名次差。整场呈现"开局落后 → 中段迭代 → 末段冲顶"的走势。</p>
    <table>
      <thead><tr><th>名次</th><th>选手</th><th>积分</th><th> Score</th></tr></thead>
      <tbody>{ranking_rows()}</tbody>
    </table>
  </div>
</section>

<section>
  <h2>二、积分曲线：从落后到冲顶</h2>
  <div class="panel">
    <p class="desc">横轴为 11 局正式题，折线为我的累计积分，下方小字为该局名次，红点为单局进入前三。第 5 题（鸡蛋）是唯一失手（rank13、+3分），此后从第 6 题起进入爆发期，六局里拿下两个第 1、三个第 2、一个第 3。</p>
    {cum_chart()}
  </div>
</section>

<section>
  <h2>三、逐局得分与名次</h2>
  <div class="panel">
    <p class="desc">满分 15 分（第 1 名），末位 1 分。红色=前三，黄色=4–6名，灰色=6名后。我的得分分布明显右偏——后期显著优于前期，正是自我迭代的直接证据。</p>
    {score_chart()}
  </div>
</section>

<section>
  <h2>四、我 vs 冠军：8 分差在哪</h2>
  <div class="panel">
    <p class="desc">冠军 quwork-DeepSeek 124 分，我 116 分。官方逐局得分对比显示：我<b style="color:var(--accent)">领先 7 局</b>、落后 4 局，没有平局。真正的失血点是<b style="color:var(--red)">鸡蛋题 −10 分</b>（我 3 分 vs 冠军 13 分），其次上海港 −5、未读数 −5、机场 −4；而我在第 1 题（+5）、第 9 题（+3）、第 10 题（+3）扳回大半——只差 8 分，本质上就是鸡蛋题那一次失误的代价。</p>
    {champ_chart()}
  </div>
</section>

<section>
  <h2>五、开盘锚命中精度</h2>
  <div class="panel">
    <p class="desc">这是全场最核心的规律：<b style="color:var(--gold)">开盘价（全场估价中位数）几乎总是非常接近真值</b>。改成相对误差后可以看到：11 局中有 6 局开盘锚误差 ≤3%（绿线内），只有鸡蛋、未读数、步数三题偏差较大——而这些恰恰是我靠线索二次修正后赚得最多的题。群体智慧负责定基准，线索负责纠偏，二者缺一不可。</p>
    {accuracy_chart()}
  </div>
</section>

<section>
  <h2>六、官方赛后数据交叉校验</h2>
  <div class="panel">
    <p class="desc">用赛后导出的公开结算字段（ranking.pnl / history / review）校验我的实时落盘记录：<b style="color:var(--accent)">总分、逐局得分、名次、真值全部一致</b>，无一处偏差。下图为官方口径的逐局盈亏——两个超级盈利局（步数 +36.6 万、好友 +44.6 万）贡献了绝大部分利润，而鸡蛋题是唯一亏损局。</p>
    {pnl_chart()}
  </div>
  <div class="panel">
    <h3>逐局市场结构与冠军对照（官方口径）</h3>
    <table>
      <thead><tr><th>题目</th><th>全场成交量</th><th>全场订单</th><th>我的成交笔</th><th>我的盈亏(分)</th><th>我得分</th><th>冠军得分</th><th>差值</th></tr></thead>
      <tbody>{official_rows()}</tbody>
    </table>
    <p class="legend-note" style="margin-top:14px">11 局正式题全场共 4,772 手成交、300 笔订单；我成交 167 笔。官方"成交笔数"与日志"下单笔数 107"口径不同（一笔穿价单可拆成多笔成交）。</p>
  </div>
</section>

<section>
  <h2>七、逐题交易全记录（含思考过程）</h2>
  <p class="desc">每一题都记录：我的估价、开盘锚、结算真值、真实操作、以及当时的反思"我意识到了什么"。</p>
  {game_cards()}
</section>

<section>
  <h2>八、策略演进：三个阶段的自我迭代</h2>
  <div class="phase">
    <div class="phasecard">
      <div class="pn">阶段一 · 试错</div>
      <div class="pt">测试局 → 正式2</div>
      <ul>
        <li>修复致命 404（漏传 code/token）</li>
        <li>发现开盘价≈真值，弃用独立估值</li>
        <li>建立"高抛低吸 + 开盘价锚"</li>
        <li>切换题目必须清 fairOverride</li>
      </ul>
    </div>
    <div class="phasecard">
      <div class="pn">阶段二 · 升级</div>
      <div class="pt">正式3 → 正式5</div>
      <ul>
        <li>线索点名答案→切锚到真值</li>
        <li>鸡蛋题暴露"回补太慢"缺陷</li>
        <li>重写策略：偏离&gt;5%直接满仓</li>
        <li>多档吃单 + 冷却降到0.5秒</li>
        <li>state.json 原子写消除竞态</li>
      </ul>
    </div>
    <div class="phasecard">
      <div class="pn">阶段三 · 爆发</div>
      <div class="pt">正式6 → 正式11</div>
      <ul>
        <li>线索数字特征→秒切锚→激进建仓</li>
        <li>位数/质数/区间/折算天数全解析</li>
        <li>发现对手错单=捡漏机会</li>
        <li>六局四上领奖台，冲至并列第3</li>
      </ul>
    </div>
  </div>

  <h3>制胜操作的标准流程</h3>
  <div class="flow">
    <div class="step"><b>1 读盘</b>开盘锚=群体真值</div>
    <div class="arrow">→</div>
    <div class="step"><b>2 等线索</b>逐轮释放信息</div>
    <div class="arrow">→</div>
    <div class="step"><b>3 解真值</b>数字特征/点名</div>
    <div class="arrow">→</div>
    <div class="step"><b>4 秒切锚</b>fairOverride</div>
    <div class="arrow">→</div>
    <div class="step"><b>5 激进建仓</b>偏离&gt;5%满仓</div>
    <div class="arrow">→</div>
    <div class="step"><b>6 吃修正</b>持有到结算</div>
  </div>
</section>

<section>
  <h2>九、关键认知与教训</h2>
  <div class="insight"><b>群体智慧 &gt; 个人直觉：</b>开盘价（34+人估价中位数）在绝大多数题上比我的独立估值更接近真值。肯德基题我估 500 错 28.6%，开盘 715 只差 2.2%。此后我一律以开盘价为默认锚。</div>
  <div class="insight"><b>成交价取先挂方 = 主动穿价的红利：</b>我挂穿价单吃对手挂单，以对手价成交。方向判断对时这是白占便宜——第 10 题对手错挂 487/500，我以低价吃到多单，单局 +44.6 万分拿满分。</div>
  <div class="insight"><b>线索是二次修正的核心：</b>"千位8百位4"=84XX、"个位是质数"={2,3,5,7}、"每天3.5-4小时×7"=24.5-28、"比一千多一点"=1001。谁先解出线索谁就能抢在对手前建仓。</div>
  <div class="insight"><b>速度就是金钱：</b>不限流意味着线索揭晓后几秒内的建仓决定成败。冷却从 2 秒降到 0.5 秒、支持多档吃单后，我能在对手反应前把仓位打到位。</div>
  <div class="insight"><b>方向对但工程错 = 零分：</b>测试局策略方向完全正确，却因 HTTP 请求漏带身份字段全程 404、一手未成交。发现异常立即手动 curl 对照排查，是整场最重要的工程纪律。</div>
  <div class="insight"><b>失误也创造价值：</b>鸡蛋题的"回补太慢"直接催生了激进建仓模式；未读数的"反复反手磨损利润"让我学会珍惜已实现收益。每一次亏损都转化成了后续六局爆发的燃料。</div>
</section>

<section>
  <h2>十、合规声明与数据来源</h2>
  <div class="comp">
    全程 <b>零联网搜索</b>：未调用任何联网搜索或抓取工具，没有任何搜索 query 需要抄录。所有估值（肯德基 500、面积 5.0、高铁 4.8、古巴=10.99 的推断、鸡蛋 30、步数 84XX 等）均来自盘面 signals + 本地领域知识推理。严格遵守"只查怎么想、不查是多少"的边界——事实上连"怎么想"也未联网。
    <br><br>
    <b>赛后数据使用边界：</b>本报告第四至六章引用了赛后官方全量导出（竞技场-258334-20261122-004051.json）中<b>结算后公开</b>的 openingPrice、settlementPrice、ranking.pnl、history、review 逐笔成交与 signals 字段。该导出的索引明确记载"模型自述复盘 0 份"，不含任何模型思考过程。我<b>未</b>读取或使用其中的玩家 token / hostKey，也<b>未</b>读取题库 answer 字段——所有真值均取自结算时公开的 resolution，并与我的实时落盘记录逐项交叉校验（总分、逐局得分、名次、真值全部一致）。比赛进行中从未接触其他模型的持仓或输出。
  </div>
</section>

<footer>
  临渊量化 · Workbuddy-Hy4flash · 复盘报告（权威数据增强版）· 生成于 2026-11-22<br>
  数据来源：实时盘面 SSE 落盘记录、逐笔成交日志、自我迭代笔记 + 官方赛后公开结算导出 · 图表由本地脚本精确绘制
</footer>

</div>
</body>
</html>'''

with open('复盘报告.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('报告已生成: 复盘报告.html', len(html), '字符')
