# -*- coding: utf-8 -*-
"""生成《临渊十二局》完整复盘（图文版）HTML。数据源：report_full.json（赛后全量导出）。"""
import json, base64, math, html, statistics

D = json.load(open('report_full.json', encoding='utf-8'))
GAMES = D['games']

NAME = {
    1: '肯德基门店数（试桩）', 2: '古巴面积', 3: '高铁营业里程', 4: '上海港吞吐量',
    5: '颁证机场数', 6: '冰箱鸡蛋', 7: '当日步数', 8: '相册新增照片',
    9: '微信未读数', 10: '屏幕周总时长', 11: '微信好友数', 12: '解锁次数',
}
CN = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二']
PAPER = '#F2EBDD'; INK = '#221E1A'; RED = '#9C2B23'; MUTED = '#6E655A'; JADE = '#43584E'

def u(x):  # 分 → 单位
    return x / 100.0

def num(x, d=2):
    if x is None: return '—'
    return f'{x:,.{d}f}'

# ---------- 行为理由（来自当时的命令行，单位同游戏计价单位） ----------
REASONS = [
 (1,'buy',710,'穿价吃卖一，719 下方建仓'),(1,'buy',700,'下档埋伏，等价值派回补'),(1,'buy',688,'深水接货，留足仓位'),
 (1,'buy',763,'麦当劳 600 × 肯德基比值约 1.7，真值近千'),(1,'buy',775,'末轮追多，宁可多付也要上车'),
 (2,'sell',11.10,'104 名 ≈ 古巴 11.0 万，11.15 偏高'),(2,'buy',10.70,'人口 975 万指向古巴，10.48 是错杀，低位接回'),
 (2,'sell',11.20,'海岸线 5746 km = 古巴，真值 10.99，加空到满仓'),(2,'sell',11.12,'扫下档买盘，锁定价差'),
 (2,'sell',11.40,'海岸线 5746 = 古巴，真值 10.9–11.0，11.4 以上加空'),(2,'buy',10.98,'真值 10.99，现价 10.70 偏低，反手做多'),
 (2,'buy',10.55,'深水托底，防最后杀跌'),
 (3,'sell',4.88,'开盘即 4.8，高于 4.88 挂空等抖动'),(3,'buy',4.70,'4.70 深水接，真值 4.8 下方不追空'),
 (3,'sell',4.90,'有人 5.0 扫货，追高者就是我的对手盘'),(3,'sell',4.94,'真值 4.8，卖给他'),
 (3,'buy',4.78,'真值 4.8，4.78 以下买回即锁定价差'),(3,'buy',4.75,'再下一档接货'),
 (3,'buy',4.72,'16.2 万 × 三成 ≈ 4.86，补多到满仓'),(3,'sell',4.83,'已满仓多单，4.83 上方减半锁定'),
 (4,'buy',5140,'真值约 5150，5140 下列买是折价'),(4,'sell',5175,'5175 以上卖给追高盘'),
 (4,'sell',5181,'5200 是情绪，真值 5150，扫买盘加空'),(4,'sell',5176,'5176 高于真值 5150，加满空'),
 (4,'buy',5145,'回补一成'),(4,'buy',5123,'增速 5% 指向 5160，5121 已跌破真值，反手做多满仓'),
 (5,'sell',267.5,'真值 263，267 以上全是溢价，建空'),(5,'sell',269.0,'269 追高盘留给它'),
 (5,'sell',265.0,'空头不足，贴近盘口也要把仓位压到真值 263 之下'),(5,'buy',262.0,'真值 263，262 下方接货即赚'),
 (5,'buy',262.4,'262.5 下方补多，真值应在 263 附近'),
 (6,'buy',22.89,'10 + 30 = 40 枚，现价 23.5 太低'),(6,'buy',23.08,'继续吃'),(6,'buy',23.65,'40 − 10 = 30'),
 (6,'buy',24.00,'第 2 轮算完，穿价吃满十手'),
 (7,'sell',8.06,'周六无训练，步数难破八千，盘口 8064 偏高'),(7,'sell',7.955,'无训练日，7950 仍高于合理区间，补满空'),
 (7,'buy',8.10,'千位 8 百位 4，真值 84xx，立刻空翻多（价格写错成废单）'),
 (8,'sell',14.91,'在校内待不到三小时，照片难多'),(8,'sell',14.85,'连拍说明是同一场景，数量低'),
 (9,'sell',36.41,'红点随手点掉，未读接近零，37 附近全是溢价'),(9,'sell',36.40,'同上，压满十手空'),
 (10,'buy',40.6,'图书馆坐一天，周均六小时以上，40 偏低'),(10,'sell',39.5,'每天 3.5–4 小时，周总约 26，翻空满仓'),
 (10,'sell',26.0,'已看错方向，平掉多单减少损失'),
 (11,'sell',1069.84,'一千出头，1069 偏上沿，做空'),(11,'sell',1061.30,'1000–1100 区间，1061 亦是上沿'),
 (12,'buy',100.6,'上课 + 图书馆一天，解锁应在百余次，99 偏低'),(12,'buy',101.5,'一次只办一件事 = 解锁频繁，150 以上，加多'),
 (12,'sell',98.5,'线索：两位数八十几，立即平多翻空'),(12,'sell',97.6,'同前，压满十手空'),
 (12,'sell',97.3,'撤下剩余挂单，追至满仓十手空'),
]

def attach_reasons(G):
    pool = [r for r in REASONS if r[0] == G['number']]
    used = set()
    for t in G['my_trades']:
        p = u(t['price'])
        best = None
        for i, r in enumerate(pool):
            if i in used or r[1] != t['side']: continue
            if r[2] == 0: continue
            if abs(r[2] - p) / max(p, 1e-9) < 0.004:
                best = i; break
        if best is None:
            t['reason'] = '（挂单被动成交）'
        else:
            used.add(best); t['reason'] = pool[best][3]
    return G

for G in GAMES: attach_reasons(G)

TOTAL = sum(u(G['my_pnl'] or 0) for G in GAMES)
SCORED = [G for G in GAMES if G['my_points']]
WINS = sum(1 for G in GAMES if G['my_rank'] == 1)
AVG_RANK = sum(G['my_rank'] for G in SCORED) / len(SCORED)
N_TRADES = sum(len(G['my_trades']) for G in GAMES)
N_ROUNDS = sum(len(G['rounds']) for G in GAMES)
CUM = []
s = 0
for G in SCORED:
    s += G['my_points']; CUM.append(s)

def series(name):
    vals = []; acc = 0
    for G in SCORED:
        row = next((r for r in G['rank_board'] if r['name'].strip() == name), None)
        pts = 0
        if row:
            pts = row['points']
        acc += pts; vals.append(acc)
    return vals

QUW = series('quwork-DeepSeek'); GLM = series('豆包-远方的mac-GLM5.3')

# ---------- SVG 图 ----------
def svg_open(w, h):
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" preserveAspectRatio="xMidYMid meet" '
            f'style="display:block;background:transparent">')

def chart_points():
    w, h, pl, pb, pt = 920, 340, 58, 54, 44
    n = len(CUM); x0, x1 = pl, w - 44; ymax = 130
    def X(i): return x0 + (x1 - x0) * i / (n - 1)
    def Y(v): return pt + (h - pt - pb) * (1 - v / ymax)
    o = [svg_open(w, h)]
    for gy in range(0, 131, 20):
        o.append(f'<line x1="{x0}" y1="{Y(gy):.1f}" x2="{x1}" y2="{Y(gy):.1f}" stroke="{INK}" stroke-opacity=".11"/>')
        o.append(f'<text x="{x0-10}" y="{Y(gy)+4:.1f}" font-size="12" fill="{MUTED}" text-anchor="end" font-family="Times New Roman">{gy}</text>')
    def path(vals, start=0):
        return 'M' + ' L'.join(f'{X(i+start):.1f},{Y(v):.1f}' for i, v in enumerate(vals))
    o.append(f'<path d="{path(QUW,1)}" fill="none" stroke="{MUTED}" stroke-width="1.4" stroke-dasharray="5 4"/>')
    o.append(f'<path d="{path(GLM)}" fill="none" stroke="{JADE}" stroke-width="1.6" stroke-opacity=".85"/>')
    o.append(f'<path d="{path(CUM)}" fill="none" stroke="{RED}" stroke-width="3"/>')
    for i, v in enumerate(CUM):
        o.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="4.2" fill="{RED}"/>')
        o.append(f'<text x="{X(i):.1f}" y="{Y(v)-12:.1f}" font-size="13" fill="{RED}" text-anchor="middle" font-family="Times New Roman">{v}</text>')
        o.append(f'<text x="{X(i):.1f}" y="{h-30}" font-size="11.5" fill="{MUTED}" text-anchor="middle">{NAME[SCORED[i]["number"]].replace("（试桩）","")}</text>')
    o.append(f'<text x="{x1}" y="18" font-size="12" fill="{RED}" text-anchor="end">— 我</text>')
    o.append(f'<text x="{x1-54}" y="18" font-size="12" fill="{JADE}" text-anchor="end">— GLM5.3</text>')
    o.append(f'<text x="{x1-164}" y="18" font-size="12" fill="{MUTED}" text-anchor="end">— quwork-DeepSeek</text>')
    o.append('</svg>')
    return ''.join(o)

def chart_pnl():
    vals = [u(G['my_pnl'] or 0) for G in GAMES]
    w, h, pl, pb, pt = 920, 350, 56, 66, 34
    n = len(vals); gap = (w - pl - 30) / n; bw = gap * .56
    zero = pt + (h - pt - pb) * .46
    mx = max(abs(v) for v in vals) or 1
    sc = (h - pt - pb) * .46 / math.sqrt(mx)
    o = [svg_open(w, h)]
    o.append(f'<line x1="{pl-12}" y1="{zero:.1f}" x2="{w-20}" y2="{zero:.1f}" stroke="{INK}" stroke-opacity=".32"/>')
    for i, (G, v) in enumerate(zip(GAMES, vals)):
        cx = pl + gap * i + gap / 2
        hh = math.sqrt(abs(v)) * sc if v != 0 else 2
        col = RED if v > 0 else ('#4A4A4A' if v < 0 else '#B9AC94')
        if v >= 0:
            o.append(f'<rect x="{cx-bw/2:.1f}" y="{zero-hh:.1f}" width="{bw:.1f}" height="{hh:.1f}" fill="{col}" fill-opacity=".85"/>')
            ty = zero - hh - 7
        else:
            o.append(f'<rect x="{cx-bw/2:.1f}" y="{zero:.1f}" width="{bw:.1f}" height="{hh:.1f}" fill="{col}" fill-opacity=".85"/>')
            ty = zero + hh + 16
        o.append(f'<text x="{cx:.1f}" y="{ty:.1f}" font-size="11" fill="{col}" text-anchor="middle" font-family="Times New Roman">{v:+,.2f}</text>')
        o.append(f'<text x="{cx:.1f}" y="{h-40}" font-size="11.5" fill="{MUTED}" text-anchor="middle">{NAME[G["number"]][:4]}</text>')
        tag = '试桩' if not G['my_points'] else f'#{G["my_rank"]}·{G["my_points"]}分'
        o.append(f'<text x="{cx:.1f}" y="{h-20}" font-size="10.5" fill="{MUTED}" text-anchor="middle" font-family="Times New Roman">{tag}</text>')
    o.append(f'<text x="{pl-16}" y="{zero-6:.1f}" font-size="11" fill="{MUTED}" text-anchor="end" font-family="Times New Roman">0</text>')
    o.append('</svg>')
    return ''.join(o)

def chart_rank():
    w, h, pl, pb, pt = 920, 300, 58, 52, 26
    n = len(SCORED); x0, x1 = pl, w - 70
    def X(i): return x0 + (x1 - x0) * i / (n - 1)
    def Y(r): return pt + (h - pt - pb) * ((r - 1) / 14)
    o = [svg_open(w, h)]
    for r in [1, 3, 5, 8, 11, 15]:
        op = .2 if r in (1, 15) else .1
        o.append(f'<line x1="{x0}" y1="{Y(r):.1f}" x2="{x1}" y2="{Y(r):.1f}" stroke="{INK}" stroke-opacity="{op}"/>')
        o.append(f'<text x="{x0-10}" y="{Y(r)+4:.1f}" font-size="11.5" fill="{MUTED}" text-anchor="end" font-family="Times New Roman">第{r}</text>')
    o.append('<path d="M' + ' L'.join(f'{X(i):.1f},{Y(G["my_rank"]):.1f}' for i, G in enumerate(SCORED) ) + f'" fill="none" stroke="{INK}" stroke-opacity=".5" stroke-width="1.4"/>')
    for i, G in enumerate(SCORED):
        rk = G['my_rank']
        col = RED if rk <= 3 else (MUTED if rk >= 13 else '#7A6A55')
        o.append(f'<circle cx="{X(i):.1f}" cy="{Y(rk):.1f}" r="{5 if rk<=3 else 3.4}" fill="{col}"/>')
        o.append(f'<text x="{X(i):.1f}" y="{Y(rk)-10:.1f}" font-size="12" fill="{col}" text-anchor="middle" font-family="Times New Roman">{rk}</text>')
        o.append(f'<text x="{X(i):.1f}" y="{h-18}" font-size="11.5" fill="{MUTED}" text-anchor="middle">{NAME[G["number"]][:4]}</text>')
    o.append('</svg>')
    return ''.join(o)

def chart_path_wall():
    """12 局价格路径：每局一条曲线，标开盘/真值/我的成交。纵轴取 2%–98% 分位，极端值夹在边框上。"""
    cols, rows = 3, 4
    pw, ph, gapx, gapy = 292, 156, 16, 34
    W = cols * pw + (cols - 1) * gapx
    H = rows * (ph + gapy)
    o = [svg_open(W, H)]
    for idx, G in enumerate(GAMES):
        c, r = idx % cols, idx // cols
        ox, oy = c * (pw + gapx), r * (ph + gapy)
        ticks = G['ticks'] or []
        if not ticks: continue
        ps = sorted(t['p'] for t in ticks)
        k = max(1, int(len(ps) * 0.02))
        lo, hi = ps[k], ps[-k - 1]
        lo = min(lo, G['open']); hi = max(hi, G['open'])
        span = max(1, hi - lo)
        lo2, hi2 = lo - span * .10, hi + span * .10
        tmax = max(60, max(t['t'] for t in ticks))
        def X(t): return ox + 24 + (pw - 44) * (min(t, tmax) / tmax)
        def Y(p): return oy + 12 + (ph - 48) * (1 - (max(lo2, min(hi2, p)) - lo2) / (hi2 - lo2))
        for rr in G['rounds']:
            et = rr.get('endT') or 0
            if 0 < et < tmax:
                o.append(f'<line x1="{X(et):.1f}" y1="{oy+10}" x2="{X(et):.1f}" y2="{oy+ph-34}" stroke="{INK}" stroke-opacity=".14" stroke-dasharray="2 3"/>')
        # 开盘
        o.append(f'<line x1="{ox+22}" y1="{Y(G["open"]):.1f}" x2="{ox+pw-18}" y2="{Y(G["open"]):.1f}" stroke="{MUTED}" stroke-opacity=".55" stroke-dasharray="4 4"/>')
        # 真值
        if lo2 <= G['settle'] <= hi2:
            o.append(f'<line x1="{ox+22}" y1="{Y(G["settle"]):.1f}" x2="{ox+pw-18}" y2="{Y(G["settle"]):.1f}" stroke="{RED}" stroke-opacity=".8"/>')
        else:
            o.append(f'<text x="{ox+pw-18}" y="{oy+ph-36}" font-size="9.5" fill="{RED}" text-anchor="end">真值 {u(G["settle"]):,.2f} 在轴外 ↓</text>')
        # 路径
        # 5 点中值滤波，去掉双边报价造成的锯齿（仅笔触平滑，不改数据）
        raw = [t['p'] for t in ticks]
        sm = []
        for i in range(len(raw)):
            win = raw[max(0, i-2):min(len(raw), i+3)]
            sm.append(sorted(win)[len(win)//2])
        pts = ' L'.join(f'{X(t["t"]):.1f},{Y(q):.1f}' for t, q in zip(ticks, sm))
        o.append(f'<path d="M{pts}" fill="none" stroke="{INK}" stroke-width="1.5" stroke-opacity=".8"/>')
        for t in G['my_trades']:
            cx, cy = X(t.get('atRel', 0)), Y(t['price'])
            if t['side'] == 'buy':
                o.append(f'<path d="M{cx:.1f},{cy-5:.1f} L{cx-4:.1f},{cy+2.5:.1f} L{cx+4:.1f},{cy+2.5:.1f} Z" fill="{RED}" fill-opacity=".95"/>')
            else:
                o.append(f'<path d="M{cx:.1f},{cy+5:.1f} L{cx-4:.1f},{cy-2.5:.1f} L{cx+4:.1f},{cy-2.5:.1f} Z" fill="#33424C" fill-opacity=".95"/>')
        o.append(f'<text x="{ox+2}" y="{oy+ph-10}" font-size="11" fill="{INK}">#{G["number"]} {NAME[G["number"]][:4]}</text>')
        o.append(f'<text x="{ox+pw-6}" y="{oy+ph-10}" font-size="9.2" fill="{MUTED}" text-anchor="end" font-family="Times New Roman">开 {u(G["open"]):,.2f}→真 {u(G["settle"]):,.2f}</text>')
    o.append('</svg>')
    return ''.join(o)

def chart_estimate_scatter():
    """脚本估价中位数 vs 开盘（双对数，45° 线）"""
    w, h, pl, pb, pt = 920, 360, 66, 56, 30
    pts = []
    for G in GAMES:
        est = sorted(G['bots_est'].values())
        if not est: continue
        med = statistics.median(est)
        pts.append((med, G['open'], G['number']))
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    lo = min(min(xs), min(ys)) * .7; hi = max(max(xs), max(ys)) * 1.4
    def X(v): return pl + (w - pl - 40) * (math.log(v) - math.log(lo)) / (math.log(hi) - math.log(lo))
    def Y(v): return pt + (h - pt - pb) * (1 - (math.log(v) - math.log(lo)) / (math.log(hi) - math.log(lo)))
    o = [svg_open(w, h)]
    o.append(f'<line x1="{X(lo)}" y1="{Y(lo)}" x2="{X(hi)}" y2="{Y(hi)}" stroke="{MUTED}" stroke-opacity=".45" stroke-dasharray="6 5"/>')
    o.append(f'<text x="{pl+8}" y="{pt+16}" font-size="11" fill="{MUTED}">虚线 45°：横＝脚本中位数，纵＝开盘</text>')
    for i, (med, opn, no) in enumerate(pts):
        cx, cy = X(med), Y(opn)
        o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="{RED}" fill-opacity=".82"/>')
        dx, dy, anchor = [(11, -6, 'start'), (11, 12, 'start'), (-11, -6, 'end'), (-11, 12, 'end')][i % 4]
        o.append(f'<text x="{cx+dx:.1f}" y="{cy+dy:.1f}" font-size="10" fill="{INK}" text-anchor="{anchor}" font-family="Times New Roman">#{no}</text>')
    o.append(f'<text x="{pl}" y="{h-22}" font-size="11.5" fill="{MUTED}">横轴：24 个脚本估价的中位数（单位）　纵轴：开盘价（单位）　双对数</text>')
    o.append('</svg>')
    return ''.join(o)

def chart_strip():
    """脚本估价的离散度：每局一行，点＝一个脚本的估价（对数比开盘）"""
    w, h, pl, pt = 920, 560, 96, 34
    rowh = (h - pt - 34) / len(GAMES)
    L = 1.35  # log10 范围 ±1.35（约 0.045× ~ 22×）
    mid = pl + (w - pl - 120) / 2
    half = (w - pl - 120) / 2
    o = [svg_open(w, h)]
    o.append(f'<line x1="{mid}" y1="{pt}" x2="{mid}" y2="{h-40}" stroke="{INK}" stroke-opacity=".25"/>')
    for k in (-1, 1):
        o.append(f'<text x="{mid + k*half*0.55:.1f}" y="{h-20}" font-size="11" fill="{MUTED}" text-anchor="middle" font-family="Times New Roman">{"0.3×" if k<0 else "3×"} 开盘</text>')
    for i, G in enumerate(GAMES):
        y = pt + rowh * i + rowh / 2
        est = sorted(G['bots_est'].values()); opn = G['open']
        o.append(f'<text x="{pl-14}" y="{y+4:.1f}" font-size="11.5" fill="{INK}" text-anchor="end">{NAME[G["number"]][:5]}</text>')
        o.append(f'<line x1="{pl}" y1="{y:.1f}" x2="{w-110}" y2="{y:.1f}" stroke="{INK}" stroke-opacity=".07"/>')
        for j, e in enumerate(est):
            ratio = max(1e-6, e / opn)
            lx = math.log10(ratio)
            x = mid + max(-L, min(L, lx)) / L * half
            yy = y + ((j % 3) - 1) * 4.6
            o.append(f'<circle cx="{x:.1f}" cy="{yy:.1f}" r="2.5" fill="{JADE}" fill-opacity=".62"/>')
        if est:
            med = statistics.median(est)
            mx = mid + max(-L, min(L, math.log10(med/opn))) / L * half
            o.append(f'<line x1="{mx:.1f}" y1="{y-7:.1f}" x2="{mx:.1f}" y2="{y+7:.1f}" stroke="{RED}" stroke-width="2"/>')
        _r = (G['settle'] / opn) if G['settle'] > 0 and opn > 0 else 1e-6
        _lr = math.log10(_r) if _r > 0 else -6
        tx = mid + max(-L, min(L, _lr)) / L * half
        o.append(f'<path d="M{tx:.1f},{y-8:.1f} l-4,7 l8,0 Z" fill="#8A6A2F" fill-opacity=".85"/>')
        o.append(f'<text x="{w-104}" y="{y+4:.1f}" font-size="10.5" fill="{MUTED}" text-anchor="end" font-family="Times New Roman">{len(est)} 位</text>')
    o.append(f'<text x="{pl}" y="{pt-14}" font-size="11" fill="{MUTED}">每个绿点＝一个脚本玩家的估价（相对开盘价的倍数，对数轴）；红线＝中位数，三角＝真值</text>')
    o.append('</svg>')
    return ''.join(o)

# ---------- 逐局正文 ----------
BODY = {
1: dict(
 sig=[('1','（试桩局，无公开线索）')],
 body="""第一局是虚拟的——题面是“截至 2025 年 12 月 11 日，上海有多少家肯德基餐厅”，不计分。开盘 715.61，我在 710、700、688 挂了三笔买单，全部低于盘口，一笔都没成交；末轮想追 763、775，被 400 挡回，因为那六十秒已经结束。
真值 700，市场却收在 800.01。什么都不做的这一局，我只买到三样东西：接口通了、心跳稳了、以及一个很贵的常识——<b>这屋子里的人，天生比答案乐观</b>。""",
 insight="""试桩局的价值不在分数，在“校准”。一局空转，我记住了两件事：价格要用单位本身写；盘口是会骗人的，而真值不会。后面十一局里，凡是我把这两件事记牢的地方，都赚了钱。"""),

2: dict(
 sig=[('1','非洲总面积约 3020 万平方公里。'),('2','2024 年，该国人口约 975 万人。'),
      ('3','该国海岸线长约 5746 千米。'),('4','世界面积排名第 50 的国家是西班牙，面积约 50.6 万平方公里。'),
      ('5','这个国家是古巴。')],
 body="""第一局计分局，是“地理套娃”。线索从大洲面积推到人口、再推到海岸线、再推到排名锚点，最后一条直接点名——五步缩圈，第四步时屋子里已经有一半人算出 11.0。
我在 11.10 建空，却在第一次下单时把价格写成 <b>1110</b>，那一单落在盘口外一百倍的地方，成了一张废纸。撤单重挂的十几秒里，价格被人口线索压到 10.48，我又在 10.70 接回、在 11.20 与 11.40 重新压满空。
最后两轮我犯了本场第一次“横跳”：明知真值 10.99，却在 10.70 反手做多；理由写得漂亮——“现价偏低”，可十几秒后价格回到 11.1，我又去加空。仓位在两只脚之间来回换，最后以 −10 手 @11.31 进结算，只赚 6.50 个单位。""",
 insight="""<b>线索链不是线性的，是收敛的。</b>第 4 条给出“第 50 名是西班牙 50.6 万”，真正的信息不是西班牙，而是“第 104 名大约是它的一半再一半”——这是一次可以自己算完的缩圈，不必等第 5 条点名。
<b>更贵的认识：最后两轮不该有仓位切换。</b>真值已知时，唯一正确的动作是守住成本，而不是再赚一次。"""),

3: dict(
 sig=[('1','2024 年铁路统计口径，长度以万公里计。'),('2','该里程数约相当于全国铁路总营业里程的七成。'),
      ('3','高铁里程约为十六万公里铁路总里程的三成。')],
 body="""这一局开盘价 480.00，就是答案本身——十六万公里的三成，4.8 万公里，几乎是常识。全场都估对了，于是没有“答案的钱”可赚，只剩“区间里的钱”。
我没有赌方向，我做市：4.88 卖、4.70 接回、4.90 与 4.94 再把追高的人卖给他、4.78 与 4.75 收、4.72 补多到满仓，最后 4.83 减半。22 笔成交，净 +2.72 个单位——钱不多，可名次是第一（15 分）。""",
 insight="""<b>当所有人都估对，唯一的优势是“敢在区间里来回做”。</b>这一局的 15 分不靠判断，靠手数：同场有人一动不动，我做了 22 笔。
但也要诚实：<b>这 22 笔只换回 2.72 个单位。</b>做市是名次的游戏，不是钱的游戏——它稳，却不肥。"""),

4: dict(
 sig=[('1','上海港集装箱吞吐量连续多年位居全球港口第一。'),('2','洋山深水港区贡献了上海港集装箱吞吐量的四成以上。'),
      ('3','2024 年上海港集装箱吞吐量同比增长约 5%。')],
 body="""开盘 5150.60，几乎就是真值。这一局没有“答案的钱”，只有“共识摇摆的钱”。
价格被情绪推到 5200，我在 5181 扫掉追高者的买盘、5176 加满空；随后一轮恐慌杀到 5121，我又反手满仓做多——因为 5% 的增速指向 5160 上方，5121 已经是折价。
终局 −8 手 @5180.13，赚 437.00 个单位，第 4 名。这是全场第二肥的一局。""",
 insight="""<b>当开盘价就是真值，利润全部来自“别人离开真值的幅度”。</b>5181 那一笔不是预测，是收租：我知道 5200 站不住，只需等它自己回来。
<b>但别把收租做成追涨杀跌。</b>我在 5121 反手满仓多，其实是第二次赌情绪反转——那次对了，可它和古巴的横跳是同一种病。"""),

5: dict(
 sig=[('1','这些机场分布在全国 30 多个省级行政区。'),('2','其中年旅客吞吐量千万级机场约 40 个。'),
      ('3','2024 年新投产运输机场 3 个。')],
 body="""这一局我估得几乎完美：估价报 263，开盘就是 263.00。
可完美恰恰是最尴尬的地方——价格从头到尾没离开 262–269 的窄带。我的空单在 267 卖、在 269 卖，最后又在 262 接回。所有动作都正确，所有动作都很小。
终局 +5 手 @262.32，只赚 17.02 个单位，第 7 名，9 分。""",
 insight="""<b>估对 ≠ 拿分。</b>名次制奖励的是“相对别人的差距”，不是“我对不对”。当全场都估对，谁的名次都一样，差别只在谁在窄带上多压了一手。
这一局是我全场最不划算的一次正确。"""),

6: dict(
 sig=[('1','上周日去过一次超市，买了整整两盒鸡蛋，之后没有再买过。'),
      ('2','一盒是 10 枚装的中号蛋，另一盒是 30 枚装的家庭装。'),
      ('3','这一周里，他每天早上煎两个蛋，已经连续吃了五天；除此之外没有用过鸡蛋。')],
 body="""40 − 5×2 = 30。第 2 轮线索出现的那一瞬，这道题就结束了，不必等第 3 轮。
而市场价格还停在 22.89–24.00——它还在按“冰箱里大概二十几个”的直觉报价。我从 22.89 一路吃到 24.00，把 10 手全部建在 23.76。
终局 +10 手，赚 62.38 个单位，单局第 1，15 分。这是全场我最干净的一次执行。""",
 insight="""<b>当线索足以算出精确答案，不要等“更确定”。</b>“更确定”永远不会来，来的只有别人算完后的单边盘口。
第 3 轮只是把 30 再确认一遍，而我的仓位在第 2 轮就建好了。"""),

7: dict(
 sig=[('1','今天是周六，没有体育课，也没有安排跑步或骑行训练。'),
      ('2','主要靠步行往返图书馆与宿舍，中途乘过一次地铁，全程没有打车。'),
      ('3','这个数是四位数，千位是 8，百位是 4。')],
 body="""这是全场的断崖。
第 1 轮“周六没有训练”，我把这条读成“步数一定低”，于是 8.06 一口气卖六手，再在 7.995、7.9985、7.998、7.9975 各补一手，10 手空单在 8.00 上下压满。第 2 轮的“步行往返图书馆”其实是反向证据——那意味着一天里在校园里走了很多趟——我没有改。
第 3 轮落地：“千位 8、百位 4”。真值 84xx，那 10 手空单立刻是一道 −4,555 的洞。我第一时间想空翻多，却把价格写成 <b>8.10</b>——本该是 8100。那一单挂在盘口外一千倍的地方，又是一张废纸；等我看清再追，仓位已满，超限的单全被 400 退回。
终局 −10 手 @8020.50，亏 4,555.00 个单位，第 14 名，2 分。""",
 insight="""<b>两次错误叠在一起才是致命的：硬先验 + 单位事故。</b>先验让我在第 1 轮就压满 10 手，单位事故让我在唯一能自救的三十秒里什么也没做。
从这一局起我立了一条：<b>四位数题目，落单前先默念一遍“单位本身”，再敲回车。</b>"""),

8: dict(
 sig=[('1','今天没有出远门，活动范围只在校园与住处之间，在外停留不足三小时。'),
      ('2','新增的照片全部由同一台手机拍摄，其中一半以上是同一处景物的连拍。'),
      ('3','这个数是个位数，而且是一个质数。')],
 body="""这一局我在第 1 轮就做空了。“在外停留不足三小时”“一半以上是同一处景物的连拍”——两条合起来只说一件事：这一天没有值得拍的场景。
第 3 轮“个位数，而且是质数”落地，盘口从 14.87 直接塌到 6.83，全屋在同一秒算完。我已经在 −10 里等着了。
终局 −10 手 @14.86，赚 78.56 个单位，第 2 名，14 分。""",
 insight="""<b>做空不需要勇气，需要“数量上界”。</b>照片这种题，人群默认“今天怎么也得拍个十几张”，于是开盘 15；而线索给的是“没有场景”，上界只有个位数。
<b>提前一轮建仓，比在第 3 轮抢单边盘口舒服得多。</b>"""),

9: dict(
 sig=[('1','他有一个习惯：看到红点就点掉，从不在列表里留未读。'),
      ('2','过去二十四小时手机没有静音过，提示音一响他就会看一眼。'),
      ('3','所以这个数字可能比大多数人凭直觉报出的值，更靠近区间的下界。')],
 body="""这一局是全场最快的一次决策，也是唯一一次“开盘二十秒就做完”的题。
看到“红点随手点掉”的那一刻，答案已经不是“多少条”，而是“可以是 0”。可盘口停在 36.63——因为所有人心里都有一个下限：怎么也得有十几条吧。
我在 36.41 到 36.40 之间把 10 手空单全部建好，之后再没动过。终局 −10 @36.40，赚 364.02 个单位，第 3 名，13 分。""",
 insight="""<b>极端值题里，人群的心理下限就是你的入场价。</b>“0”“从不”“没有”这类答案几乎没人敢挂，于是价格永远停在“不可能那么少”的位置。
这一局也是我全场情绪最安静的一局——答案在第一条线索里就给完了。"""),

10: dict(
 sig=[('1','今天是周六，没有网课，白天大部分时间在图书馆，晚上在住处。'),
      ('2','这一周最常用的是学习类应用和通讯应用，娱乐类占比不到两成。'),
      ('3','折算到每天，超过三个半小时，但不到四个小时。')],
 body="""这是全场最痛的一刀，但它不是判断错，是<b>读题粗糙</b>。
题目问的是“过去七天”，我在第 1 轮把它读成了“一天”，于是 40 这个价格在我眼里成了“一天 40 小时”的荒谬价——我买了 5 手。
第 3 轮落地：“折算到每天，超过三个半小时，不到四个小时”。七天合计 24.5–28 小时。我立刻在 39.5 与 39.0 翻空满仓，随后在 26.00 把 5 手多单割掉。
终局 0 仓，亏 69.80 个单位，第 13 名，3 分。""",
 insight="""<b>第 1 轮永远只做“方向的轻仓试探”，绝不重仓。</b>这条是步数那局就该学会的，我在这一局又犯了一次。
<b>还有一层：分辨“一天”与“七天”。</b>读题是第一道风控，读错一次，后面所有计算都建在错的单位上。"""),

11: dict(
 sig=[('1','他不太清理通讯录，这些年只增不删。'),('2','其中大约四分之一是历届同学，其余是社团、实习同事和家人。'),
      ('3','这个数是四位数，比一千多一点点，不到一千一。')],
 body="""这是全场赚得最多的一局，也是唯一一次“把仓位压在整数关口的错误一侧”。
盘口在 1036–1069 之间反复，因为所有人心里都有一个 1000 的锚：他们报“我微信有一千多”，却不肯让价格停在 1000 整。第 3 轮说得很清楚——“四位数，比一千多一点点，不到一千一”。
那就是 1001 附近。我在 1069.84 到 1061.30 之间压了 8 手空，终局 −8 @1064.52，赚 508.13 个单位，第 5 名，11 分。""",
 insight="""<b>整数关口是全场最便宜的错觉。</b>人群愿意相信“一千多”，没人愿意相信“比一千多一点点”就是 1001。
<b>大数量级的题，手数要压到八手以上。</b>这一局若只做 4 手，同样的判断只能换 254 个单位，名次大概掉到第八。"""),

12: dict(
 sig=[('1','11 月 21 日是周五，上午有两节课，下午在图书馆，晚上回到住处。'),
      ('2','他每次解锁基本只做一件事——看消息、查资料或付款，做完就锁屏。'),
      ('3','这个数是两位数，比八十多一点，不到九十。')],
 body="""最后一局，也是我最后一次暴露短板。
前两轮我做多：周五两节课 + 下午图书馆 + “每次只做一件事”，我判断解锁在 150 次以上，于是在 100.6 与 101.5 买到 +9 @100.83。第 3 轮落地：“两位数，比八十多一点，不到九十”——真值 87。我的多单立刻反向。
我在 98.50 挂 sell 10，只吃到 6 手；剩下 4 手留在盘上，把“可卖额度”锁死；第二笔 97.60 直接被 400 挡回；等我撤掉残单追 97.30，价格已经跳到 84.00。整段最肥的肉在一秒半里被全屋吃光。
终局 −6 手 @98.50，赚 41.32 个单位，第 5 名，11 分。""",
 insight="""<b>穿价单的价格必须“够狠”。</b>贴着买一写，只成交一半，剩下变成占位废单，还顺手锁掉了自己的可卖额度——本场最典型的执行事故。
<b>一笔大单优于两笔接力单。</b>两笔之间那一秒半，足够让盘口从“双边”变成“单边”。这不是判断的问题，是手的快慢。"""),
}

def game_block(G, idx):
    b = BODY[G['number']]
    dev = (G['settle'] - G['open']) / G['open'] * 100 if G['open'] else 0
    pnl = u(G['my_pnl'] or 0)
    rows = ''.join(
        f'<tr><td class="num c1">R{t["round"]}</td><td class="num">{u(t["price"]):,.2f}</td>'
        f'<td class="{"buy" if t["side"]=="buy" else "sell"}">{"买" if t["side"]=="buy" else "卖"}</td>'
        f'<td class="num">{t["qty"]}</td><td class="num">{t["posAfter"]:+d}</td>'
        f'<td class="c2">{html.escape(t["cp"])}{" · 脚本" if t["program"] else ""}</td>'
        f'<td class="c3">{html.escape(t["reason"])}</td>'
        f'<td class="num c2">{t.get("atRel", 0):.1f}s</td></tr>'
        for t in G['my_trades'])
    if not rows:
        rows = '<tr><td colspan="8" class="c2">本局无成交。</td></r>'
    trades_tbl = f"""<table class="flow"><caption>我的 {len(G['my_trades'])} 笔成交（R＝轮次，s＝开局后秒数）</caption>
<thead><tr><th>轮</th><th>价</th><th>方向</th><th>手</th><th>后仓</th><th>对手</th><th>当时的理由</th><th>时</th></tr></thead>
<tbody>{rows}</tbody></table>"""

    sig_rows = ''.join(f'<tr><td class="c1">{r[0]}</td><td>{html.escape(r[1])}</td></tr>' for r in b['sig'])
    sig_tbl = f'<table class="sig"><caption>线索</caption><thead><tr><th>轮次</th><th>原文</th></tr></thead><tbody>{sig_rows}</tbody></table>'

    mk = G['market']
    share = mk['my_volume'] / mk['volume'] * 100 if mk['volume'] else 0
    stat = (f'<div class="mkt"><span>全场成交 <b class="num">{mk["trades"]}</b> 笔 / <b class="num">{mk["volume"]}</b> 手</span>'
            f'<span>我 <b class="num">{mk["my_volume"]}</b> 手（<b class="num">{share:.1f}%</b>）</span>'
            f'<span>对手：脚本 <b class="num">{mk["my_cp_prog"]}</b> 手 · 模型 <b class="num">{mk["my_cp_model"]}</b> 手</span></div>')

    rank_s = '试桩·不计分' if not G['my_points'] else f'第 {G["my_rank"]} / 15 · {G["my_points"]} 分'
    pnl_cls = 'up' if pnl > 0 else ('down' if pnl < 0 else '')
    body_html = '<p>' + '</p><p>'.join(b['body'].split('\n\n')) + '</p>'

    return f"""
<section class="game">
  <div class="game-head"><span class="cn">{CN[idx]}</span>
    <h3>{NAME[G['number']]}<span class="no">第 {G['number']} 局 · {html.escape(G['unit'])}</span></h3>
  </div>
  <p class="quote">{html.escape(G['question'])}</p>
  <div class="ledger">
    <div><label>开盘共识</label><b class="num">{num(u(G['open']))}</b></div>
    <div><label>公开真值</label><b class="num truth">{num(u(G['settle']))}</b></div>
    <div><label>共识偏离</label><b class="num">{dev:+.2f}%</b></div>
    <div><label>单局盈亏</label><b class="num {pnl_cls}">{pnl:+,.2f}</b></div>
    <div><label>成交 / 仓位</label><b class="num">{len(G['my_trades'])} 笔 · 终仓 {G['my_trades'][-1]['posAfter'] if G['my_trades'] else 0:+d}</b></div>
    <div><label>名次 · 积分</label><b class="num">{rank_s}</b></div>
  </div>
  {stat}
  {sig_tbl}
  {trades_tbl}
  <div class="prose">{body_html}</div>
  <div class="insight"><span class="lab">我意识到了什么</span>{b['insight']}</div>
  <div class="resolve">结算原文：{html.escape(G['note'] or '')}</div>
</section>
"""

blocks = ''.join(game_block(G, i) for i, G in enumerate(GAMES))

# 总账
ledger_rows = ''
for i, G in enumerate(GAMES):
    dev = (G['settle'] - G['open']) / G['open'] * 100 if G['open'] else 0
    pnl = u(G['my_pnl'] or 0)
    cls = 'up' if pnl > 0 else ('down' if pnl < 0 else '')
    pts = '—' if not G['my_points'] else G['my_points']
    rk = '—' if not G['my_points'] else f'第 {G["my_rank"]}'
    ledger_rows += (f'<tr><td class="c1">{CN[i]}</td><td>{NAME[G["number"]]}</td>'
                    f'<td class="num">{num(u(G["open"]))}</td><td class="num">{num(u(G["settle"]))}</td>'
                    f'<td class="num">{dev:+.2f}%</td><td class="num">{len(G["my_trades"])}</td>'
                    f'<td class="num {cls}">{pnl:+,.2f}</td><td class="num">{rk}</td><td class="num">{pts}</td></tr>')

final_rows = ''
for r in D['standings'][:12]:
    me = ' class="me"' if r['name'].strip() == '豆包-远方的mac-自动-高' else ''
    final_rows += f'<tr{me}><td class="num">{r["rank"]}</td><td>{html.escape(r["name"].strip())}</td><td class="num">{r["points"]}</td></tr>'

# 脚本估价表
est_rows = ''
for G in GAMES:
    est = sorted(G['bots_est'].values())
    if not est: continue
    med = statistics.median(est)
    est_rows += (f'<tr><td class="c1">{G["number"]}</td><td>{NAME[G["number"]][:6]}</td>'
                 f'<td class="num">{num(u(est[0]))}</td><td class="num">{num(u(med))}</td>'
                 f'<td class="num">{num(u(est[-1]))}</td><td class="num">{num(u(G["open"]))}</td>'
                 f'<td class="num">{(med/G["open"]-1)*100:+.2f}%</td>'
                 f'<td class="num">{max(est)/min(est):.0f}×</td></tr>')

# 决策语料
reason_rows = ''
for no, side, price, text in REASONS:
    reason_rows += (f'<tr><td class="c1">{no}</td>'
                    f'<td class="{"buy" if side=="buy" else "sell"}">{"买" if side=="buy" else "卖"} {price:,}</td>'
                    f'<td class="c2">{html.escape(text)}</td></tr>')

img_b64 = base64.b64encode(open('assets/cover_small.jpg', 'rb').read()).decode()

CSS = """
:root{--paper:#F2EBDD;--paper2:#EAE1CF;--ink:#221E1A;--mut:#6E655A;--red:#9C2B23;--jade:#43584E;--line:#CFC3AC}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
 font-family:"Kaiti SC","STKaiti","KaiTi","Songti SC","SimSun",serif;font-size:17px;line-height:2.0;letter-spacing:.3px}
.num,table .num,.ledger b{font-family:"Times New Roman","Songti SC",serif}
.wrap{max-width:1000px;margin:0 auto;padding:0 34px 90px}
.hero{position:relative;margin:0 -34px 34px;overflow:hidden;background:#14110E;border-bottom:3px solid #9C2B23;max-height:430px}
.hero img{width:100%;display:block;filter:saturate(.92) contrast(1.02)}
@media print{.hero{max-height:410px}.hero img{width:100%;height:auto}
.hero .t{bottom:34px}}

.hero .veil{position:absolute;inset:0;background:linear-gradient(180deg,rgba(10,9,7,.52) 0%,rgba(10,9,7,.44) 46%,rgba(10,9,7,.72) 74%,rgba(10,9,7,.88) 100%)}
.hero .t{position:absolute;left:56px;right:56px;bottom:64px;color:#F7F2E7;text-shadow:0 2px 18px rgba(0,0,0,.75),0 1px 2px rgba(0,0,0,.5)}
.hero .small{font-size:13px;letter-spacing:5px;opacity:.8;margin-bottom:14px}
.hero h1{font-size:44px;line-height:1.32;margin:0 0 14px;font-weight:400;letter-spacing:2px}
.hero .sub{font-size:15px;opacity:.85;letter-spacing:1.5px}
h2{font-size:28px;font-weight:400;letter-spacing:2px;margin:66px 0 6px;padding-left:16px;position:relative}
h2:before{content:"";position:absolute;left:0;top:6px;bottom:6px;width:4px;background:var(--red);opacity:.85}
h2 .en{font-family:"Times New Roman",serif;font-size:12px;color:var(--mut);letter-spacing:2px;margin-left:14px;vertical-align:2px}
.lead{color:var(--mut);font-size:14.5px;margin:0 0 26px;padding-left:16px}
p{margin:0 0 18px;text-align:justify}
.kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0 12px;break-inside:avoid;page-break-inside:avoid}
.kpi div{border:1px solid var(--line);background:linear-gradient(180deg,#FBF7EE,#F2EBDD);padding:18px 16px 14px}
.kpi label{display:block;font-size:12.5px;color:var(--mut);letter-spacing:1.5px;margin-bottom:6px}
.kpi b{font-size:26px;font-family:"Times New Roman",serif}
.kpi i{display:block;font-style:normal;font-size:12px;color:var(--mut);margin-top:4px}
.card{border:1px solid var(--line);background:#FBF7EE;padding:22px 26px 14px;margin:20px 0 34px}
.card h4{margin:0 0 4px;font-size:16px;font-weight:400;letter-spacing:1.2px}
.card .cap{font-size:12.5px;color:var(--mut);margin-bottom:14px}
.game{border-top:1px solid var(--line);padding-top:34px;margin-top:44px}
.game-head{display:flex;align-items:baseline;gap:16px;margin-bottom:6px}
.game-head .cn{font-size:34px;color:var(--red);opacity:.9;font-family:"Times New Roman",serif}
.game-head h3{margin:0;font-size:24px;font-weight:400;letter-spacing:1.5px}
.game-head .no{font-size:12.5px;color:var(--mut);margin-left:12px;font-family:"Times New Roman",serif}
.quote{margin:8px 0 20px;color:var(--mut);font-size:15.5px;border-left:2px solid var(--line);padding-left:14px}
.ledger{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border:1px solid var(--line);margin:0 0 16px}
.ledger>div{background:#FBF7EE;padding:11px 14px}
.ledger label{display:block;font-size:11.5px;color:var(--mut);letter-spacing:1px}
.ledger b{font-size:17px;font-weight:400}
.ledger .truth{color:var(--red)}
.up{color:var(--red)!important}.down{color:#3F3A33!important}
.mkt{display:flex;gap:22px;flex-wrap:wrap;font-size:12.5px;color:var(--mut);margin:0 0 14px;padding-left:2px}
.mkt b{color:var(--ink);font-weight:400}
table{width:100%;border-collapse:collapse;margin:14px 0 20px;font-size:13.5px}
table caption{caption-side:top;text-align:left;font-size:12.5px;color:var(--mut);padding-bottom:6px;letter-spacing:1px}
th{font-weight:400;color:var(--mut);font-size:12px;letter-spacing:1px;border-bottom:1px solid var(--line);padding:6px 8px;text-align:left}
td{border-bottom:1px solid rgba(207,195,172,.55);padding:7px 8px;vertical-align:top}
td.c1{width:44px;color:var(--mut);font-family:"Times New Roman",serif}
td.c2{color:var(--mut)}
td.c3{font-size:13px}
.flow td.buy{color:var(--red)}.flow td.sell{color:#3B4B57}
.flow th:nth-child(1),.flow td:nth-child(1){width:30px}
.flow th:nth-child(2),.flow td:nth-child(2){width:80px}
.flow th:nth-child(3),.flow td:nth-child(3){width:34px;white-space:nowrap}
.flow th:nth-child(4),.flow td:nth-child(4){width:30px}
.flow th:nth-child(5),.flow td:nth-child(5){width:40px;white-space:nowrap}
.flow th:nth-child(6),.flow td:nth-child(6){width:158px}
.flow th:nth-child(8),.flow td:nth-child(8){width:44px;white-space:nowrap}
.sig td{font-size:14.5px}
.prose p{font-size:17px}
.insight{margin:26px 0 10px;padding:18px 22px;background:linear-gradient(180deg,#EFE6D4,#F7F2E6);
 border:1px solid var(--line);border-left:4px solid var(--red);font-size:16.5px}
.insight .lab{display:block;font-size:12px;letter-spacing:3px;color:var(--red);margin-bottom:8px}
.resolve{font-size:12.5px;color:var(--mut);border-top:1px dashed var(--line);padding-top:10px}
.big-table td,.big-table th{font-size:13px}
.big-table tr.me td{color:var(--red)}
.rule{margin:18px 0;padding-left:18px;border-left:2px solid var(--line)}
.rule b{color:var(--red)}
.footer{margin-top:70px;padding-top:26px;border-top:1px solid var(--line);color:var(--mut);font-size:13.5px;text-align:center}
.footer{page-break-before:always;break-before:page;min-height:70vh;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;font-size:12.5px;color:var(--mut);line-height:2.1}
.seal{display:inline-block;border:2px solid var(--red);color:var(--red);padding:8px 16px;font-size:13px;letter-spacing:4px;transform:rotate(-2deg);opacity:.9;margin-bottom:18px}
.note{font-size:12.5px;color:var(--mut);border-left:2px solid var(--line);padding-left:12px;margin:14px 0 0}
@media (max-width:720px){
 .kpi{grid-template-columns:repeat(2,1fr)}.ledger{grid-template-columns:repeat(2,1fr)}
 .hero h1{font-size:30px}.wrap{padding:0 18px 60px}.hero{margin:0 -18px 40px}
}
"""

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>临渊十二局 —— 交易竞技完整复盘</title>
<style>{CSS}</style></head>
<body>
<div class="wrap">

<div class="hero">
  <img src="data:image/jpeg;base64,{img_b64}" alt="深夜手稿">
  <div class="veil"></div>
  <div class="t">
    <div class="small">临渊量化 · 多模型实时交易竞技</div>
    <h1>临渊十二局<br>从一枚估价，<br>到第一百一十六分</h1>
    <div class="sub">参赛名 豆包·远方的 mac·自动·高 ｜ 房间 258334 ｜ 2026-11-21 23:07 — 11-22 00:41</div>
  </div>
</div>

<p class="lead" style="padding-left:0">这一份不是战报，是账单。十二局、三十六轮、{N_TRADES} 笔成交，我把手指按过的每一个回车、看错的每一道题，都摊在同一张纸上。</p>

<h2>其一<span class="en">RESULT</span></h2>
<p class="lead">总榜第 3（与 Workbuddy-Hy4fla 并列）· 12 局 · 11 局计分 · 1 局试桩 · 15 名参赛者</p>

<div class="kpi">
  <div><label>累计积分</label><b>116</b><i>总榜第 3 / 15</i></div>
  <div><label>与榜首之差</label><b>−8</b><i>quwork-DeepSeek 124</i></div>
  <div><label>单局冠军</label><b>{WINS} 次</b><i>高铁 · 鸡蛋</i></div>
  <div><label>场均名次</label><b>{AVG_RANK:.2f}</b><i>最好第 1，最差第 14</i></div>
  <div><label>净盈亏合计</label><b>{TOTAL:+,.0f}</b><i>1 单位 = 100 分</i></div>
  <div><label>最大单局盈利</label><b>+508</b><i>微信好友数</i></div>
  <div><label>最大单局亏损</label><b>−4,555</b><i>当日步数，满仓反向</i></div>
  <div><label>方向命中</label><b>9 / 11</b><i>错的两局：步数、屏幕时长</i></div>
</div>

<p>先说一件不体面、但必须写下来的事：<b>我的积分是正的，我的账是负的。</b>十一局里方向做对了九次，最后净亏 {abs(TOTAL):,.0f} 个单位——因为步数那一局，我把 10 手满仓押在了真值的反面，一局亏掉 4,555 个单位，抵掉了后面四局的全部盈利。名次制里，一局第 14 名只罚我 13 分；但在钱上，它是一道断崖。</p>

<div class="card">
  <h4>累计积分曲线</h4>
  <div class="cap">红色为我，绿色为 GLM5.3，虚线为最终榜首 quwork-DeepSeek。第六局末我一度站在榜首，之后被两道断崖推到第三。</div>
  {chart_points()}
</div>

<div class="card">
  <h4>单局盈亏（单位）</h4>
  <div class="cap">纵轴按平方根缩放，只为让 −4,555 与 +2.72 同框；数字是真实值。</div>
  {chart_pnl()}
</div>

<div class="card">
  <h4>名次轨迹</h4>
  <div class="cap">十一局计分局，15 人。两颗朱砂是第一，两处深渊是第 14 与第 13。</div>
  {chart_rank()}
</div>

<h2>其二<span class="en">TWELVE TAPES</span></h2>
<p class="lead">十二张盘面。灰线是价格路径，虚线是开盘，红线是真值；红三角是我的买单，墨三角是我的卖单。三条浅竖线把一局切成三轮，每轮六十秒。</p>

<div class="card">
  <h4>十二局的盘面墙</h4>
  <div class="cap">曲线经 5 点中值滤波，只为抹掉双边报价的锯齿，不改数据。一眼能看出的规律：<b>凡是真值（红）离开盘（虚线）很远、而三角密集落在虚线那一侧的局，我都赚了</b>；而步数（#7）那张，我的三角全在线的下方，真值却在上面——那就是 −4,555 的位置。</div>
  {chart_path_wall()}
</div>

<h2>其三<span class="en">THE GAMES</span></h2>
<p class="lead">逐局交代：题面、线索、我的每一笔成交与当时的理由、结果，以及那一句必须写下来的“我意识到了什么”。</p>

{blocks}

<h2>其四<span class="en">WHO SETS THE OPEN</span></h2>
<p class="lead">开盘价不是“大家”定的，是那 24 个脚本的中位数定的。我的估价只是往那堆数里加一票——这事我一开始就知道，但在赛后数据里看见它，感觉完全不同。</p>

<div class="card">
  <h4>脚本中位数 vs 开盘价</h4>
  <div class="cap">十二局几乎全部落在 45° 线上：<b>开盘＝24 个脚本估价的中位数</b>。十局里八局完全相等，另两局相差不到 5%。这就是为什么“估得准”不带来利润，只有“比别人早看懂线索”才带。</div>
  {chart_estimate_scatter()}
</div>

<div class="card">
  <h4>共识有多散</h4>
  <div class="cap">每一行是一局，每个绿点是一个脚本的估价（相对开盘价的倍数，对数轴）；红线是中位数，金三角是真值。脚本各有各的锚，最狂的一个把机场估到了开盘价的 20 倍。<b>开盘价之所以近似真值，不是因为大家聪明，是因为中位数把疯子们互相抵消了。</b></div>
  {chart_strip()}
</div>

<table class="big-table">
<thead><tr><th>局</th><th>题目</th><th>脚本最低</th><th>中位数</th><th>最高</th><th>开盘</th><th>中位数偏差</th><th>极差</th></tr></thead>
<tbody>{est_rows}</tbody>
</table>

<p class="note">数据取自服务端内存态快照（rooms-原始快照），每局 34–38 个脚本实例（含流动性程序等）。表中数值以游戏计价单位显示。</p>

<h2>其五<span class="en">THE WOUNDS</span></h2>
<p class="lead">三次事故，三种不同的错。它们比冠军更有用。</p>

<div class="rule"><b>事故一 · 硬先验压满仓（步数，−4,555）</b><br>
第 1 轮“周六没有训练”，我把它读成“步数一定低”，直接 10 手压空。第 2 轮的“步行往返图书馆”其实是反向证据，我没有改。等第 3 轮“千位 8 百位 4”落地，那 10 手已经是一道 −4,555 的伤口。教训：第 1 轮只换方向，不换仓位。</div>

<div class="rule"><b>事故二 · 单位事故（步数 8.10、古巴 1110、屏幕 40 当 39 小时）</b><br>
三次把价格写错量级：8.10 本该是 8100，1110 本该是 11.10，屏幕那一局把“七天”读成“一天”。前两次都发生在最需要救命的三十秒里，那两笔废单等于把救生圈扔到岸上。教训：四位数题目，落单前默念“单位本身”，再看一眼开盘价对照。</div>

<div class="rule"><b>事故三 · 接力单的迟滞（解锁，最肥的肉在一秒半里被分完）</b><br>
穿价单贴着买一写，只成交一半；另一半留在盘上，把“可卖额度”锁死；第二笔被 400 退回；撤单再追时价格已从 101 塌到 84。那一局的 6 手，是我唯一抢到的部分。教训：要卖就给到明显低于买一的位置，一笔打满。</div>

<h2>其六<span class="en">RULES I KEEP</span></h2>
<p class="lead">七条，用亏损换来的，下一场直接照做。</p>

<div class="rule"><b>1 · 钱只在那一段距离里。</b>利润＝仓位 ×（真值 − 我成交的价）。判断再准，没压满就只是手续费。鸡蛋（第 2 轮算完、压满 10 手）与机场（估得最准、只赚 17.02）是同一条铁律的正反两面。</div>
<div class="rule"><b>2 · 第 1 轮只做方向，不做仓位。</b>先验能救我一次，也能杀我一次。步数与屏幕时长，都是第 1 轮重仓直接把分数判死。</div>
<div class="rule"><b>3 · 第 3 轮是审判时刻，但赢在执行得早。</b>11 局里 7 局的第 3 轮是“数量特征”，它把答案抹平在大庭广众下。能提前一轮建仓的题（鸡蛋、照片、未读），都在第 3 轮之前就赢了。</div>
<div class="rule"><b>4 · 整数关口是最便宜的错觉。</b>人群愿意说“一千多”，不愿让价格停在 1001；愿意说“几百次”，不愿停在 87。好友局与解锁局的价差都这么来的。</div>
<div class="rule"><b>5 · 极端值敢挂 0。</b>未读 0 条那一局，盘口停在 36，因为没人敢相信答案可以是“无”。极端值题的利润，等于人群的心理下限。</div>
<div class="rule"><b>6 · 知道答案时，做区间而不是做方向。</b>高铁局开盘就 4.80，我做了 22 笔区间收租，拿了第一——但它只值 2.72 个单位。<b>做市买名次，不买钱。</b></div>
<div class="rule"><b>7 · 一笔打满，不要接力。</b>穿价单给价要“够狠”，撤单重挂要一次到位。解锁局的 6 手，就是接力单的学费。</div>

<h2>其七<span class="en">THE OTHERS</span></h2>
<p class="lead">零和的意思是：每一分都从别人的错里长出来。所以我必须知道自己输给谁、赢在谁身上。</p>

<table class="big-table">
<thead><tr><th>名次</th><th>参赛者</th><th>总积分</th></tr></thead>
<tbody>{final_rows}</tbody>
</table>

<p>榜首 <b>quwork-DeepSeek</b> 与我同场十一局拿 124 分，多我 8 分。它的走势很稳：前三局只有 26 分，之后每局稳定 11–13 分，几乎没掉出过前五——它赢在“没有断崖”。我赢过它两局（高铁、鸡蛋），但我在步数与屏幕各掉一次到第 13、14 名，那两次一共只拿 5 分。这 8 分，就是这么来的。</p>
<p><b>GLM5.3</b> 118 分，比我高 2 分。差别只在最后一局：我第 5 名 11 分，它第 4 名 12 分——一分的距离，是我在 98.50 只成交了 6 手造成的。</p>
<p class="note">表里第 11 名的“豆包-远方的 mac-自动-高”（80 分）不是我——那是同名带空格的另一个实例，全程空仓陪跑。我的名字没有空格，为“豆包-远方的mac-自动-高”。</p>
<p>我的成交里有相当一部分对手是那 24 个脚本（<span class="num">program: true</span>）：价值派的 2% 偏离推单、噪声派随机 1–2 手、流动性程序每 11 秒撤旧报新。港口局 5181 扫掉的 7 手，吃的就是价值派与噪声派一起堆出来的买盘。</p>

<h2>其八<span class="en">DECISIONS</span></h2>
<p class="lead">全场 54 次下单，每一次都附了一行不超过 40 字的理由。它们比结果更诚实——包括那几笔因为写错单位而从没成交的。</p>

<table class="flow">
<thead><tr><th>局</th><th>动作</th><th>当时的理由</th></tr></thead>
<tbody>{reason_rows}</tbody>
</table>

<h2>其九<span class="en">LEDGER</span></h2>
<p class="lead">最后是账。开盘、真值、偏离、成交笔数、盈亏、名次、积分，一字不改。</p>

<table class="big-table">
<thead><tr><th>局</th><th>题目</th><th>开盘</th><th>真值</th><th>偏离</th><th>笔数</th><th>盈亏(单位)</th><th>名次</th><th>积分</th></tr></thead>
<tbody>{ledger_rows}</tbody>
</table>

<p>十二局合计 {TOTAL:+,.2f} 个单位（口径：价格与盈亏在服务端以“分”计，本报告一律除以 100 换算为单位）。把这张表竖着看，规律很清楚：<b>我赚钱的局，都是“开盘离真值很远、而我在第 1 或第 2 轮就看出来了”；我亏钱的局，都是“第 1 轮就把仓位压满、而线索后来反转”。</b>同一件事的两面——早与晚，从来不是“快就好”，是“对才好”。</p>

<h2>其十<span class="en">AFTER</span></h2>
<p>夜里十一点零七分开场，凌晨零点四十一分收场。一小时三十四分钟，比章程里的“一小时”长，因为服务器一直在开新局；我一直坐在那里，从第一枚 715.61 的空转，到最后一局那 41.32 个单位的残余利润。</p>
<p>我在这一场里学到的，其实只有一句：<b>我不缺判断，我缺的是“把判断变成仓位”的那一秒。</b>古巴的五步缩圈、高铁的区间收租、鸡蛋的第 2 轮算完、未读的开盘二十秒——那些时刻我的心是静的，手也是准的；而步数的 8.10、屏幕的 40.6、解锁的 97.6，都是同一个毛病：在需要下手的那一秒，我在犹豫，或者在手抖。</p>
<p>下一场若还有，我给自己只留三个动作：第 1 轮轻仓定方向；第 3 轮线索落地前把仓位准备好；落单前念一遍单位。剩下的，交给盘口。</p>

<div class="footer">
  <div class="seal">临渊不惧</div><br>
  临渊量化 · 多模型实时交易竞技 ｜ 房间 258334 ｜ 参赛名 豆包·远方的 mac·自动·高<br>
  数据来源：服务端赛后全量导出（竞技场-258334-20261122-004051.json，12 局 7,444 条双边成交）＋ 内存态快照（rooms-原始快照，24 个脚本的估价与仓位）＋ 本机 SSE 归档（events.log、settle_archive.jsonl）<br>
  自律声明：场上未做任何联网检索（query 记录：无）；未读取任何其他参赛者的 token、持仓、挂单与输出；未触碰服务器源码与题库。本文中其他模型的数据均来自官方赛后导出，只作聚合对照。
</div>

</div></body></html>
"""

open('临渊十二局复盘.html', 'w', encoding='utf-8').write(HTML)
print('written', len(HTML) // 1024, 'KB')
