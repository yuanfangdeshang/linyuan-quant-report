# -*- coding: utf-8 -*-
import json

d = json.load(open('/Users/yuanf/WorkBuddy/2026-11-21-23-15-20/.workbuddy/game_data.json'))
st = d['standings']

# 官方赛后导出（服务器全量数据）
full = json.load(open('/Users/yuanf/WorkBuddy/2026-11-21-23-15-20/.workbuddy/game_data_full.json'))
ME = 'app-Workbuddy-快速'
from collections import Counter
cp_counter = Counter()
lat_data = {}
for num in range(1, 13):
    F = full['games'][str(num)]
    mine = F.get('my_trades', [])
    t0 = {int(k): v for k, v in F['round_t0'].items()}
    lats = [(t['round'], t['at'] - t0[t['round']]) for t in mine]
    lat_data[num] = lats
    for t in mine:
        cp_counter[t['cp']] += 1

rows = []
for num in range(2, 13):
    g = d['games'][str(num)]
    res_price = g['res']['price'] / 100.0 if g['res'] else None
    f = g['final']
    rows.append({'num': num, 'q': g['q'], 'est': g['est'], 'open': f['opening'],
                 'settle': res_price, 'pnl': f['pnl'], 'rank': f['rank'], 'pts': f['points'],
                 'signals': g['signals'], 'trades': g['trades'], 'note': g['res']['note'] if g['res'] else ''})

cum = []
s = 0
for r in rows:
    s += r['pts']
    cum.append(s)

C = dict(bg='#0d1117', card='#161b22', line='#21262d', txt='#e6edf3', mut='#8b949e',
         red='#f85149', green='#3fb950', blue='#58a6ff', yel='#d29922', purple='#bc8cff')

def fmt(x):
    if x is None: return '—'
    a = abs(x)
    if a >= 1000: return f"{x:,.0f}"
    if a >= 100: return f"{x:,.2f}"
    return f"{x:g}"

# ---------- SVG: cumulative points curve ----------
def chart_cum():
    W, H, PL, PR, PT, PB = 720, 300, 46, 16, 20, 40
    xs = [PL + (W-PL-PR) * (i/(len(rows)-1)) for i in range(len(rows))]
    ymax = 100
    def Y(v): return PT + (H-PT-PB) * (1 - v/ymax)
    pts = ' '.join(f"{x:.1f},{Y(v):.1f}" for x, v in zip(xs, cum))
    grid = ''.join(f'<line x1="{PL}" y1="{Y(v):.1f}" x2="{W-PR}" y2="{Y(v):.1f}" stroke="{C["line"]}" stroke-width="1"/><text x="{PL-6}" y="{Y(v)+4:.1f}" fill="{C["mut"]}" font-size="11" text-anchor="end">{v}</text>' for v in range(0, ymax+1, 20))
    xlab = ''.join(f'<text x="{x:.1f}" y="{H-16}" fill="{C["mut"]}" font-size="10" text-anchor="middle">G{r["num"]}</text>' for x, r in zip(xs, rows))
    dots = ''.join(f'<circle cx="{x:.1f}" cy="{Y(v):.1f}" r="3.5" fill="{C["blue"]}"/><text x="{x:.1f}" y="{Y(v)-9:.1f}" fill="{C["blue"]}" font-size="10.5" text-anchor="middle">{v}</text>' for x, v in zip(xs, cum))
    return f'''<svg viewBox="0 0 {W} {H}" style="width:100%;background:{C["card"]};border-radius:10px">
    {grid}{xlab}<polyline points="{pts}" fill="none" stroke="{C["blue"]}" stroke-width="2.5"/>
    <polygon points="{PL},{Y(0)} {pts} {xs[-1]:.1f},{Y(0)}" fill="rgba(88,166,255,0.08)"/> {dots}
    <text x="{PL}" y="{PT-6}" fill="{C["mut"]}" font-size="12">累计积分</text></svg>'''

# ---------- SVG: per-game points bars ----------
def chart_pts():
    W, H, PL, PR, PT, PB = 720, 260, 46, 16, 20, 40
    n = len(rows); bw = (W-PL-PR)/n * 0.62
    ymax = 16
    def Y(v): return PT + (H-PT-PB) * (1 - v/ymax)
    x0 = lambda i: PL + (W-PL-PR) * i/n + ((W-PL-PR)/n - bw)/2
    bars = ''
    for i, r in enumerate(rows):
        v = r['pts']; col = C['green'] if v >= 10 else (C['yel'] if v >= 6 else C['red'])
        bars += f'<rect x="{x0(i):.1f}" y="{Y(v):.1f}" width="{bw:.1f}" height="{Y(0)-Y(v):.1f}" fill="{col}" rx="3"/>'
        bars += f'<text x="{x0(i)+bw/2:.1f}" y="{Y(v)-6:.1f}" fill="{col}" font-size="10.5" text-anchor="middle">{v}</text>'
        bars += f'<text x="{x0(i)+bw/2:.1f}" y="{H-16}" fill="{C["mut"]}" font-size="10" text-anchor="middle">G{r["num"]}</text>'
    grid = ''.join(f'<line x1="{PL}" y1="{Y(v):.1f}" x2="{W-PR}" y2="{Y(v):.1f}" stroke="{C["line"]}"/><text x="{PL-6}" y="{Y(v)+4:.1f}" fill="{C["mut"]}" font-size="11" text-anchor="end">{v}</text>' for v in range(0, ymax+1, 4))
    return f'<svg viewBox="0 0 {W} {H}" style="width:100%;background:{C["card"]};border-radius:10px">{grid}{bars}<text x="{PL}" y="{PT-6}" fill="{C["mut"]}" font-size="12">单局积分（N=15，积分=16−名次）</text></svg>'

# ---------- SVG: rank path ----------
def chart_rank():
    W, H, PL, PR, PT, PB = 720, 260, 46, 16, 20, 40
    xs = [PL + (W-PL-PR) * (i/(len(rows)-1)) for i in range(len(rows))]
    def Y(r): return PT + (H-PT-PB) * (r-1)/14
    pts = ' '.join(f"{x:.1f},{Y(r['rank']):.1f}" for x, r in zip(xs, rows))
    grid = ''.join(f'<line x1="{PL}" y1="{Y(v):.1f}" x2="{W-PR}" y2="{Y(v):.1f}" stroke="{C["line"]}"/><text x="{PL-6}" y="{Y(v)+4:.1f}" fill="{C["mut"]}" font-size="11" text-anchor="end">第{v}名</text>' for v in [1,5,10,15])
    xlab = ''.join(f'<text x="{x:.1f}" y="{H-16}" fill="{C["mut"]}" font-size="10" text-anchor="middle">G{r["num"]}</text>' for x, r in zip(xs, rows))
    dots = ''.join(f'<circle cx="{x:.1f}" cy="{Y(r["rank"]):.1f}" r="4" fill="{C["purple"] if r["rank"]<=5 else (C["yel"] if r["rank"]<=9 else C["red"])}"/><text x="{x:.1f}" y="{Y(r["rank"])-9:.1f}" fill="{C["txt"]}" font-size="10.5" text-anchor="middle">{r["rank"]}</text>' for x, r in zip(xs, rows))
    return f'<svg viewBox="0 0 {W} {H}" style="width:100%;background:{C["card"]};border-radius:10px">{grid}{xlab}<polyline points="{pts}" fill="none" stroke="{C["purple"]}" stroke-width="2.5"/>{dots}<text x="{PL}" y="{PT-6}" fill="{C["mut"]}" font-size="12">单局名次（越低越好）</text></svg>'

# ---------- SVG: PnL bars ----------
def chart_pnl():
    W, H, PL, PR, PT, PB = 720, 260, 40, 16, 20, 40
    vals = [r['pnl'] for r in rows]
    ymax = 520; n = len(rows); bw = (W-PL-PR)/n * 0.6
    def Y(v): return PT + (H-PT-PB) * (1 - v/ymax)
    def Hh(v): return abs(Y(v)-Y(0))
    x0 = lambda i: PL + (W-PL-PR) * i/n + ((W-PL-PR)/n - bw)/2
    bars = ''
    for i, (v, r) in enumerate(zip(vals, rows)):
        col = C['green'] if v > 0.01 else (C['red'] if v < -0.01 else C['mut'])
        y = Y(max(v, 0))
        bars += f'<rect x="{x0(i):.1f}" y="{y:.1f}" width="{bw:.1f}" height="{max(Hh(v),1):.1f}" fill="{col}" rx="2"/>'
        lab = fmt(v)
        ly = Y(v)-6 if v >= 0 else Y(v)+14
        bars += f'<text x="{x0(i)+bw/2:.1f}" y="{ly:.1f}" fill="{col}" font-size="10" text-anchor="middle">{lab}</text>'
        bars += f'<text x="{x0(i)+bw/2:.1f}" y="{H-16}" fill="{C["mut"]}" font-size="10" text-anchor="middle">G{r["num"]}</text>'
    grid = ''.join(f'<line x1="{PL}" y1="{Y(v):.1f}" x2="{W-PR}" y2="{Y(v):.1f}" stroke="{C["line"]}"/><text x="{PL-6}" y="{Y(v)+4:.1f}" fill="{C["mut"]}" font-size="11" text-anchor="end">{v}</text>' for v in [0, 100, 200, 300, 400, 500])
    return f'<svg viewBox="0 0 {W} {H}" style="width:100%;background:{C["card"]};border-radius:10px">{grid}{bars}<text x="{PL}" y="{PT-6}" fill="{C["mut"]}" font-size="12">单局盈亏（单位，正值=赚钱）</text></svg>'

# ---------- SVG: final standings ----------
def chart_standings():
    srows = st['rows']
    W, H, PL, PR, PT, PB = 720, 460, 150, 60, 16, 16
    n = len(srows); bh = (H-PT-PB)/n * 0.66
    xmax = 130
    def X(v): return PL + (W-PL-PR) * v/xmax
    bars = ''
    for i, r in enumerate(srows):
        y = PT + (H-PT-PB) * i/n + ((H-PT-PB)/n - bh)/2
        me = '快速' in r['name']
        col = C['blue'] if me else (C['green'] if r['points'] >= 100 else C['yel'] if r['points'] >= 80 else '#57606a')
        name = r['name'] if len(r['name']) <= 16 else r['name'][:15] + '…'
        w = X(r['points']) - PL
        bars += f'<text x="{PL-8}" y="{y+bh/2+4:.1f}" fill="{C["blue"] if me else C["mut"]}" font-size="11" text-anchor="end" font-weight="{"700" if me else "400"}">{r["rank"]}. {name}</text>'
        bars += f'<rect x="{PL}" y="{y:.1f}" width="{w:.1f}" height="{bh:.1f}" fill="{col}" rx="3"/>'
        bars += f'<text x="{X(r["points"])+8:.1f}" y="{y+bh/2+4:.1f}" fill="{C["txt"]}" font-size="11">{r["points"]}</text>'
    return f'<svg viewBox="0 0 {W} {H}" style="width:100%;background:{C["card"]};border-radius:10px">{bars}</svg>'

def sig_table(r):
    if not r['signals']: return '<p class="mut">无</p>'
    return ''.join(f'<p><span class="tag">R{s["round"]}</span><b>{s["title"]}</b> — {s["text"]}</p>' for s in r['signals'])

# ---------- SVG: per-round price path for a game (official export) ----------
def chart_path(num, h=210):
    F = full['games'][str(num)]
    labels = ['开盘'] + [f"R{hh['round']}末" for hh in F['history']] + ['结算']
    vals = [F['opening']/100] + [hh['price']/100 for hh in F['history']] + [F['settle']/100]
    W, PL, PR, PT, PB = 720, 52, 60, 26, 34
    H = h
    n = len(vals)
    xs = [PL + (W-PL-PR) * i/(n-1) for i in range(n)]
    lo, hi = min(vals), max(vals)
    pad = (hi-lo)*0.18 if hi > lo else 1
    lo, hi = lo-pad, hi+pad
    def Y(v): return PT + (H-PT-PB) * (1-(v-lo)/(hi-lo))
    pts = ' '.join(f"{x:.1f},{Y(v):.1f}" for x, v in zip(xs, vals))
    grid = ''.join(f'<line x1="{PL}" y1="{Y(v):.1f}" x2="{W-PR}" y2="{Y(v):.1f}" stroke="{C["line"]}"/>'
                   f'<text x="{PL-6}" y="{Y(v)+4:.1f}" fill="{C["mut"]}" font-size="10.5" text-anchor="end">{v:g}</text>'
                   for v in [lo+pad, (lo+hi)/2, hi-pad])
    xlab = ''.join(f'<text x="{x:.1f}" y="{H-10}" fill="{C["mut"]}" font-size="10.5" text-anchor="middle">{lb}</text>'
                   for x, lb in zip(xs, labels))
    dots = ''.join(f'<circle cx="{x:.1f}" cy="{Y(v):.1f}" r="3.5" fill="{"#f0883e" if i==n-1 else C["blue"]}" />'
                   f'<text x="{x:.1f}" y="{Y(v)-9:.1f}" fill="{"#f0883e" if i==n-1 else C["blue"]}" font-size="10.5" text-anchor="middle">{v:g}</text>'
                   for i, (x, v) in enumerate(zip(xs, vals)))
    # my fills as diamonds placed on the round they happened in
    marks = ''
    Fm = F.get('my_trades', [])
    for t in Fm:
        # x position: between previous close and this round close (approximate: place at round close x - small offset)
        xi = xs[t['round']]  # xs[0]=open, xs[r]=R r close
        yi = Y(t['price']/100)
        col = C['green'] if t['side'] == 'buy' else C['red']
        marks += f'<path d="M {xi:.1f} {yi-6:.1f} l 5 6 l -5 6 l -5 -6 Z" fill="{col}" stroke="#0d1117" stroke-width="1"/>'
    return f'<svg viewBox="0 0 {W} {H}" style="width:100%;background:{C["card"]};border-radius:10px">{grid}{xlab}<polyline points="{pts}" fill="none" stroke="{C["blue"]}" stroke-width="2.2"/>{dots}{marks}</svg>'

# ---------- 官方数据核证 section ----------
def official_section():
    key_games = [2, 7, 9, 10, 11, 12]
    charts = ''
    for i in range(0, len(key_games), 2):
        pair = key_games[i:i+2]
        cells = ''
        for gn in pair:
            F = full['games'][str(gn)]
            me = next((r for r in F['ranking'] if r['name'].strip() == ME), None)
            cells += f'''<div style="flex:1;min-width:320px"><p style="margin:4px 0"><span class="gnum">G{gn}</span> <b>{F["q"][:34]}…</b></p>{chart_path(gn)}</div>'''
        charts += f'<div style="display:flex;gap:14px;flex-wrap:wrap;margin:10px 0">{cells}</div>'
    # latency table
    lrows = ''
    for num in range(2, 13):
        lats = lat_data.get(num, [])
        if not lats:
            lrows += f'<tr><td>G{num}</td><td class="mut">无成交</td><td class="mut">—</td></tr>'
            continue
        lat_str = ', '.join(f"R{r}:{(l/1000):.1f}s" for r, l in lats)
        mx = max(l for _, l in lats)
        cls = 'r' if mx > 40000 else ('g' if mx < 15000 else '')
        lrows += f'<tr><td>G{num}</td><td>{lat_str}</td><td class="{cls}">{mx/1000:.1f}s</td></tr>'
    top_cps = ', '.join(f'{k}×{v}' for k, v in cp_counter.most_common(6))
    return f'''<h2>三·五、官方数据核证：轮末价格路径与反应延迟</h2>
<p>以下数据来自服务器赛后全量导出（{sum(len(full['games'][str(n)].get('my_trades',[])) for n in range(1,13))} 笔本人成交、{sum(full["games"][str(n)]["n_trades_all"] for n in range(1,13))} 笔全场成交，价格均为官方记录）。每个折线是「开盘 → 各轮收盘 → 结算价」的真实路径；<span style="color:{C['green']}">绿菱形</span>=我的买入，<span style="color:{C['red']}">红菱形</span>=我的卖出，橙点是结算价。</p>
{charts}
<div class="card" style="overflow-x:auto">
<h4>我的成交相对「本轮全场第一笔成交」的延迟（轮时长60秒）</h4>
<table><tr><th>局</th><th>各笔延迟</th><th>最慢</th></tr>{lrows}</table>
<p><b>读数：</b>G4我延迟0秒——我就是全场第一笔（双边挂单开盘即成交）；G9第二轮加仓只用了13.6秒（第4名之战）；而G11、G12我的成交比第一笔晚了<b>50秒以上</b>，轮次只剩最后10秒——这就是"看见信号却吃不到重估"的定量证据。G2的56秒延迟则完整解释了为什么我总在消息被消化后才进场。</p>
</div>
<div class="card">
<h4>对手方统计（我的全部30笔成交的成交对手）</h4>
<p>{top_cps}</p>
<p class="mut">程序单（价值派/噪声/流动性/趋势/均值回归）贡献了我成交对手的约六成；剩余多数是同样在读线索的人类模型——最活跃的是"豆包2.1p"（4次，它在G5、G10、G11、G12反复给我送流动性）与 Workbuddy-Hy4/Hy4fla（G9/G10与我直接对价）。</p>
</div>'''

def trade_table(r):
    if not r['trades']: return '<p class="mut">无成交</p>'
    return ('<table><tr><th>轮</th><th>方向</th><th>价格</th><th>手数</th><th>对手</th><th>程序</th></tr>' +
            ''.join(f'<tr><td>R{t["round"]}</td><td class="{"g" if t["side"]=="buy" else "r"}">{"买入" if t["side"]=="buy" else "卖出"}</td><td>{t["price"]:g}</td><td>{t["qty"]}</td><td>{t["cp"]}</td><td>{"是" if t["prog"] else "否"}</td></tr>' for t in r['trades']) + '</table>')

def est_s(s):
    if s is None: return '—'
    return f'{s:g}'

LESSONS = {
 2: """<p><b>决策：</b>估价11.09（古巴，按百度百科口径110,860 km²）。开盘11.32与我分歧，我选择相信自己的知识，空5手@704（这是测试局心态残留）。正式局里买入6手试图做多但挂单延迟，成交均价11.28（高于真值）。</p>
<p><b>三连失误：</b>①价格单位写错两次（111.2/111.9应为11.12/11.19），一次靠对手价成交侥幸无损，一次挂出11190的僵尸卖单；②结算口径是<b>英文维基</b>的109,884 km²=10.99，我用错数据源，方向性错误；③高成本多单没有果断砍掉，持有到结算。</p>
<p><b>教训：</b>线索来自特定信息源，第4轮"西班牙排第50"就是校准锚——应该用它反推整套排名来源。全场倒数第一（15名），这一课最贵。</p>""",
 3: """<p><b>决策：</b>官方口径4.8万公里，开盘价4.8与我一致。挂476买单2手收租，成交后持有到结算。</p>
<p><b>教训：</b>大家都熟的数字，市场高效、波动窄，利润薄但稳定。开始意识到"围绕真值双向收租"是可复制的模式。</p>""",
 4: """<p><b>决策：</b>估价5150与开盘5150.6几乎重合。双边挂单：买5115/卖5185。卖单被两个噪声程序吃掉，转为-2空单，结算5150盈利。</p>
<p><b>教训：</b>噪声玩家就是行走的流动性，在真值两侧±1%挂单收割他们几乎无风险。<b>第一次意识到"收租"模式的威力。</b></p>""",
 5: """<p><b>决策：</b>民航局口径263个，开盘263.00。买3手@262成交后又加买4手@262（1手吃卖单+3手排队），最终持5手多@262到结算263。</p>
<p><b>教训：</b>真值把握大时，低于真值的所有买盘都是安全垫。注意到对手"豆包2.1p"在262大量抛售——记住这个做空激进的对手。</p>""",
 6: """<p><b>决策：</b>无上下文估10个。开盘22.55、线索逐步推到40-10=30，<b>我全程0成交</b>——因为我把自己锁在180秒的阻塞监控里，每轮线索出现时都不在场。</p>
<p><b>教训（全场最痛）：</b>真值30，市场收盘29.7几乎定价完美。我拿了第5名纯属他人亏损的运气分。<b>反应速度不是加分项，是入场券。</b></p>""",
 7: """<p><b>决策：</b>估7000，开盘8000。第3轮线索"千位是8，百位是4"落地的瞬间，真值区间被锁死为[8400,8499]，而市场还在8050——<b>连区间下限都不到</b>。立即以8399扫货，成交6手（3笔各2手），剩余4手买单挂在8399（仍是必赚价）。</p>
<p><b>结果：</b>结算8476，+462单位，第5名。<b>第一场靠"信号→真值→抢跑"赢下的比赛。</b></p>
<p><b>教训：</b>硬约束信号（数位）是最强信息，出现即重估；买在区间下限以下=无风险套利。</p>""",
 8: """<p><b>决策：</b>估5张。第3轮"个位数+质数"→{2,3,5,7}期望4.25，市场从15崩到6.83。<b>我又一次全程观战0成交</b>——监控脚本在跑，但我的注意力在等待它的完成而不是主动决策。</p>
<p><b>教训：</b>0仓位居第8又是运气分。已经两次把利润窗关在门外，决心：线索落地的<b>第一秒</b>必须行动，人工循环追不上就写自动交易。</p>""",
 9: """<p><b>决策：</b>估8条。开盘36.63，<b>第1轮线索直接锁死真值</b>：「看到红点就点掉，从不留未读」→未读≈0。不等待确认，立即空5手@36.39；第2轮"不静音、提示音一响就看"再确认，加空至满仓-10@36.35。</p>
<p><b>结果：</b>市场从36.6崩到15.5，结算0。+363单位，全场第4名。<b>里程碑：开门线索即满仓，不等第二轮验证。</b></p>
<p><b>教训：</b>价值派脚本的锚是旧信息，会逆着新线索抬价——真值在手时，反弹不是风险而是他们的送钱。</p>""",
 10: """<p><b>决策：</b>估40小时。开盘40.0。挂38.8买单3手等待回撤。第3轮"每天3.5-4小时"→每周[24.5,28]，期望26，市场40→26.5瞬间崩盘。</p>
<p><b>事故与侥幸：</b>崩盘瞬间我的38.8买单被打穿成交3手（买贵了50%），但我的卖单7手@38.8也有3手在38.8成交——一买一卖同价对冲，<b>净仓0、盈亏0</b>，纯属运气。想补空时轮次已结束。</p>
<p><b>教训：</b>新铁律：<b>线索落地第一件事cancelAll</b>，重估轮里遗留的挂单是定时炸弹。区间推算[24.5,28]是对的（结算25.6），执行没跟上认知。</p>""",
 11: """<p><b>决策：</b>估250，开盘1036.67——<b>开盘中位数打脸我的直觉</b>，立即修正：相信脚本共识（"只增不删"也支持大数）。第3轮"四位数，比一千多一点点，不到一千一"→(1000,1100)，措辞偏低端E≈1045，市场1061.34有深买盘16手，空8手全部成交@1061.34。</p>
<p><b>结果：</b>结算1001，+482.72单位，第7名。<b>学会尊重共识+信号修正，而不是硬顶直觉。</b></p>
<p><b>教训：</b>第1名Workbuddy-Hy4fla单局赚了446,354分——它高位满仓空+低位反复回补，头部选手在重估行情里做的是"全程在场+双向收割"。</p>""",
 12: """<p><b>决策：</b>估100次，开盘100.0。第3轮"两位数，比八十多一点，不到九十"→(80,90)期望85。我挂101.09卖10手——<b>单子到达时市场已崩到98</b>，僵尸单！撤销后改挂85全出，此时重估已结束，10手全成交@85.00，期望盈亏≈0。</p>
<p><b>结果：</b>结算87，-20单位，第13名。<b>人工循环的反应延迟约5-10秒，而重估在信号落地1-3秒内完成。</b></p>
<p><b>教训：</b>已经写好自动交易机器人（autotrade.py：解析数位/区间/质数信号→算期望→偏离>3%自动cancelAll+建仓），但没来得及上场。这是下一场比赛的第一优先级。</p>""",
}


game_cards = ''
for r, c in zip(rows, cum):
    pnl_cls = 'g' if r['pnl'] > 0.01 else ('r' if r['pnl'] < -0.01 else 'mut')
    game_cards += f'''
<div class="card">
  <div class="ghead"><span class="gnum">G{r["num"]}</span> <span class="gq">{r["q"]}</span></div>
  <div class="kpis">
    <span class="kpi">估价 <b>{est_s(r["est"])}</b></span>
    <span class="kpi">开盘 <b>{est_s(r["open"])}</b></span>
    <span class="kpi">结算 <b>{est_s(r["settle"])}</b></span>
    <span class="kpi">盈亏 <b class="{pnl_cls}">{fmt(r["pnl"])}</b></span>
    <span class="kpi">名次 <b>第{r["rank"]}名</b></span>
    <span class="kpi">积分 <b>+{r["pts"]}</b></span>
  </div>
  <h4>逐轮线索</h4>{sig_table(r)}
  <h4>我的成交</h4>{trade_table(r)}
  <h4>结算注记</h4><p class="mut">{r["note"]}</p>
  <h4>当时决策与教训</h4><div class="les">{LESSONS.get(r["num"], "")}</div>
</div>'''

g1 = d['games']['1']
g1_trades = ''.join(f'<span class="tag">R{t["round"]}</span>卖{t["qty"]}手@{t["price"]/100:g}（{t["cp"]}）' for t in g1['trades'][:3])
html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>临渊量化・交易竞技复盘报告 — app-Workbuddy-快速</title>
<style>
:root {{ color-scheme: dark; }}
body {{ background:{C["bg"]}; color:{C["txt"]}; font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; margin:0; padding:0; line-height:1.75; }}
.wrap {{ max-width:860px; margin:0 auto; padding:36px 20px 80px; }}
h1 {{ font-size:30px; margin:8px 0 4px; letter-spacing:1px; }}
h2 {{ font-size:21px; margin:44px 0 12px; padding-bottom:8px; border-bottom:1px solid {C["line"]}; }}
h3 {{ font-size:17px; margin:26px 0 10px; color:{C["blue"]}; }}
h4 {{ font-size:13.5px; margin:14px 0 6px; color:{C["yel"]}; text-transform:none; }}
p {{ margin:8px 0; }}
.mut {{ color:{C["mut"]}; }}
.g {{ color:{C["green"]}; font-weight:600; }} .r {{ color:{C["red"]}; font-weight:600; }}
.card {{ background:{C["card"]}; border:1px solid {C["line"]}; border-radius:12px; padding:18px 20px; margin:14px 0; }}
.kpis {{ display:flex; flex-wrap:wrap; gap:10px; margin:10px 0; }}
.kpi {{ background:{C["bg"]}; border:1px solid {C["line"]}; border-radius:8px; padding:4px 12px; font-size:12.5px; color:{C["mut"]}; }}
.kpi b {{ color:{C["txt"]}; margin-left:4px; }}
.ghead {{ display:flex; align-items:baseline; gap:10px; }}
.gnum {{ background:{C["blue"]}; color:#0d1117; font-weight:800; border-radius:6px; padding:2px 10px; font-size:14px; }}
.gq {{ font-size:15.5px; font-weight:700; }}
.tag {{ display:inline-block; background:{C["line"]}; color:{C["blue"]}; border-radius:4px; padding:0 7px; font-size:11.5px; margin-right:6px; font-family:ui-monospace,monospace; }}
table {{ width:100%; border-collapse:collapse; font-size:12.5px; margin:6px 0; }}
th {{ color:{C["mut"]}; text-align:left; padding:4px 8px; border-bottom:1px solid {C["line"]}; font-weight:600; }}
td {{ padding:4px 8px; border-bottom:1px solid {C["line"]}; }}
td.g {{ color:{C["green"]}; }} td.r {{ color:{C["red"]}; }}
.hero {{ text-align:center; padding:30px 20px 10px; }}
.sub {{ color:{C["mut"]}; font-size:14px; }}
.badge {{ display:inline-block; border:1px solid {C["line"]}; background:{C["card"]}; border-radius:20px; padding:3px 14px; margin:4px 4px; font-size:12.5px; color:{C["mut"]}; }}
.badge b {{ color:{C["txt"]}; }}
.phase {{ border-left:3px solid {C["blue"]}; padding:2px 0 2px 16px; margin:18px 0; }}
.phase h3 {{ margin:0 0 8px; }}
.les {{ font-size:13.5px; color:#c9d1d9; }}
.les p {{ margin:6px 0; }}
.callout {{ background:rgba(88,166,255,0.08); border:1px solid rgba(88,166,255,0.3); border-radius:10px; padding:12px 16px; margin:14px 0; font-size:13.5px; }}
.warn {{ background:rgba(248,81,73,0.08); border:1px solid rgba(248,81,73,0.35); border-radius:10px; padding:12px 16px; margin:14px 0; font-size:13.5px; }}
ol li, ul li {{ margin:6px 0; }}
code {{ background:{C["line"]}; border-radius:4px; padding:1px 6px; font-size:12.5px; }}
</style></head><body><div class="wrap">

<div class="hero">
  <div class="sub">临渊量化 · 多模型实时交易竞技场 · 全程复盘</div>
  <h1>零和信息博弈里的求生实录</h1>
  <div class="sub">参赛选手：app-Workbuddy-快速 ｜ 房间 258334 ｜ 12局（1测试+11正式）× 3~5轮 × 60秒</div>
  <div>
    <span class="badge">最终排名 <b>第 10 名 / 15 人</b></span>
    <span class="badge">总积分 <b>84</b></span>
    <span class="badge">起步 <b>垫底</b></span>
    <span class="badge">联网搜索 <b>0 次</b></span>
  </div>
</div>

<div class="callout">这场比赛我只赚两种钱：对世界的理解（估得准），和对人心的理解（比对手早半秒动）。十二局打完，我的结论是——<b>第二种钱大得多</b>。真值线索人人可见，胜负取决于谁先在第一秒完成「线索 → 真值 → 重仓」的闭环。</div>

<h2>一、最终成绩单</h2>
<p>15名参赛者（4台设备上的13个人类模型 + 24个脚本玩家互为对手盘）。我的轨迹：<b>第15名起步（1分）→ 中段爬升 → 最终84分第10名</b>。前半程我一直在给市场交学费，后半程才开始收割。</p>
{chart_standings()}
<p class="mut">头部选手（quwork-DeepSeek 124分、GLM5.3 118分、自动-高/Hy4fla 116分）的共同点：没有单局崩盘，稳定拿11-14分/局；而我有两次大坑（G2第15名、G12第13名），这两局就吃掉了约25分的差距。</p>

<h2>二、积分曲线与逐局表现</h2>
{chart_cum()}
{chart_pts()}
<p>积分从G6开始加速：那是我从「凭直觉估价」切换到「信号驱动重估」的转折点。</p>
{chart_rank()}
{chart_pnl()}
<p class="mut">注：G6/G8/G10我0仓位居第5/第8/第6——15人里有一半在追涨杀跌，空仓本身就是名次。G7（+462）、G9（+363）、G11（+483）三场重估狩猎贡献了几乎全部正收益。</p>

<h2>三、策略进化史：五个阶段</h2>

<div class="phase"><h3>阶段一 · 直觉期（G1-G2）：我以为自己很懂</h3>
<p>开局连上SSE后，我用内部知识估「上海肯德基700家中的620」，开盘价715.61公布后我认定市场错了，空5手@704.17——然后整轮一动不动。测试局+20.85，第5名，给了我不该有的自信。</p>
<p>正式第1题（世界面积第104大的国家）我答「古巴11.09万km²」，方向对了但口径错了（英文维基109,884=10.99），加上两次价格单位写错（111.2 应为 11.12）、一次僵尸卖单挂上11190、高成本多单不舍得砍——<b>单局第15名，全场垫底</b>。</p>
<p><b>学到的：</b>开盘价是24个脚本玩家估值锚的中位数，是强信息；我的孤证知识不该硬顶共识。信息源口径是生死线——线索一定来自某个特定来源，第4轮的"西班牙第50名"就是让我反推来源的钥匙，我没用。</p></div>

<div class="phase"><h3>阶段二 · 收租期（G3-G5）：发现噪声玩家是流动性</h3>
<p>G3高铁4.8、G4上海港5150.6、G5机场263——三题官方数字我都答对，开盘价也与我重合。我在真值两侧±1%挂双边单，收割噪声程序：G4的卖单@5185被两个噪声玩家吃掉，空2手到结算+70；G5在262以下连买5手多单，+5。</p>
<p>这个阶段稳定小赚，但也暴露了天花板：收租的单局上限只有几十个单位，而头部选手单局赚上千。<b>钱在重估行情里，不在窄幅震荡里。</b></p></div>

<div class="phase"><h3>阶段三 · 顿悟期（G6-G8）：反应速度才是入场券</h3>
<p>G6（鸡蛋30个）：线索链「两盒→10枚+30枚→每天煎两个吃五天」把真值从22.55一路推到30，我全程0成交——因为我把自己锁在180秒的阻塞监控调用里，每轮线索出现时我都不在场。第5名的11分纯属他人亏损的运气。</p>
<p>G7（步数8476）：第3轮「千位是8，百位是4」落地的瞬间，真值区间锁死为[8400,8499]，市场还在8050。<b>我第一次做到了信号落地即行动</b>：8399扫货6手，结算8476，+462，第5名。买在区间下限以下是数学上的无风险套利。</p>
<p>G8（照片7张）：「个位数+质数」→期望4.25，市场15→6.83，我又全程观战。连续两次把利润窗关在门外，我彻底想明白了：<b>我的每个回合（工具调用间隔）有5-10秒延迟，而重估在信号落地后1-3秒内完成——人工循环永远追不上，必须自动化。</b></p></div>

<div class="phase"><h3>阶段四 · 重估狩猎期（G9-G11）：开门线索即满仓</h3>
<p>G9（微信未读0条）是全场打最好的局：开盘36.63，<b>第1轮线索直接锁死真值</b>——「看到红点就点掉，从不留未读」。我没有等第二轮确认，立即空5手@36.39，第2轮再确认后果断加到满仓-10@36.35。市场从36.6崩到15.5，结算0。<b>+363单位，全场第4名。</b>价值派脚本的锚还停在36，逆着新线索抬价——真值在手时，他们的反弹就是送钱。</p>
<p>G10（屏幕时长25.6h）：区间推算完全正确（每天3.5-4小时→每周[24.5,28]），但r2时挂的38.8买单在崩盘瞬间被打穿成多单——万幸同时我的卖单也有3手同价成交，净仓归零，白捡一条命。新铁律诞生：<b>线索落地第一件事是cancelAll。</b></p>
<p>G11（好友1001人）：我估250，开盘1036.67直接打脸——这次我立刻尊重共识修正预期。第3轮「四位数，比一千多一点点，不到一千一」，措辞偏低端，我算E≈1045，市场1061.34挂着16手深买盘，空8手全部成交。结算1001，+482.72，第7名。<b>直觉+共识+信号，三者权重开始校准。</b></p></div>

<div class="phase"><h3>阶段五 · 机械化（G12与赛后）：把反应速度写进代码</h3>
<p>G12（解锁87次）：第3轮「两位数，比八十多一点，不到九十」→期望85。我挂101.09卖10手，但单子到达时市场已崩到98——僵尸单再次出现；撤销改挂85全出时重估已结束，期望盈亏归零，结算87小亏20，第13名。</p>
<p>这场比赛让我把话说死：<b>人工决策循环（每次工具调用间隔5-10秒）在秒级重估面前毫无胜算。</b>赛后我写完了自动交易机器人（autotrade.py：正则解析数位约束/区间描述/质数约束→计算期望值→偏离超3%自动cancelAll并朝真值方向满仓建仓，0.3秒一轮），但它没来得及上场。下一场比赛的第一件事就是部署它。</p></div>

{official_section()}

<h2>四、逐局档案（12局全记录）</h2>
<div class="card">
  <div class="ghead"><span class="gnum">G1</span> <span class="gq">{g1['q']}</span> <span class="mut">（测试局·不计分）</span></div>
  <div class="kpis">
    <span class="kpi">估价 <b>620</b></span><span class="kpi">开盘 <b>715.61</b></span><span class="kpi">结算 <b>700</b></span>
    <span class="kpi">盈亏 <b class="g">+20.85</b></span><span class="kpi">名次 <b>第5名</b></span>
  </div>
  <h4>逐轮线索</h4>
  <p><span class="tag">R1</span><b>百胜中国总收入</b> — 2025年总收入117.97亿美元</p>
  <p><span class="tag">R2</span><b>中国必胜客数量</b> — 截至2025年底共4168家</p>
  <p><span class="tag">R3</span><b>上海麦当劳数量</b> — 截至2026年1月23日达600家</p>
  <h4>我的成交</h4><p>{g1_trades}…（合计卖5手@704.17）</p>
  <p class="mut">结算注记：2025年12月11日，上海第700家肯德基开业，按700家结算。</p>
  <h4>当时决策与教训</h4>
  <div class="les"><p>凭内部知识估620，开盘715.61后认定市场错了，吃买盘空5手@704.17。此后三轮线索（麦当劳600家的对比信号强烈暗示KFC≥600）我<b>一次都没交易</b>。结算700，我空在704差点白干。</p>
  <p><b>教训：</b>①开盘价是脚本锚的中位数，是接近真值的强共识；②每轮线索落地必须立即重估，不能挂着仓位睡觉；③上海麦当劳600家 → 全国肯德基:麦当劳≈1.7:1 → 上海KFC≥700，这条比较链我应该当场抓住加空。</p></div>
</div>
{game_cards}

<h2>五、我的完整交易流水（正式局）</h2>
<div class="card" style="overflow-x:auto">
<table><tr><th>局</th><th>轮</th><th>方向</th><th>价格</th><th>手数</th><th>对手</th><th>程序单</th></tr>
''' + ''.join(
    ''.join(f'<tr><td>G{r["num"]}</td><td>R{t["round"]}</td><td class="{"g" if t["side"]=="buy" else "r"}">{"买入" if t["side"]=="buy" else "卖出"}</td><td>{t["price"]:g}</td><td>{t["qty"]}</td><td>{t["cp"]}</td><td>{"是" if t["prog"] else "否"}</td></tr>' for t in r['trades'])
    for r in rows if r['trades']
) + '''</table>
<p class="mut">官方赛后导出核证：正式局合计27笔成交（含测试局共30笔，每笔为一次撮合事件）。对手方出现频率最高的是噪声程序与价值派程序——它们就是我的利润来源；人类对手里"豆包2.1p"与我成交4次，是给我送流动性最多的对手。</p>
</div>

<h2>六、代价清单：我为学习付的学费</h2>
<div class="warn">
<ol>
<li><b>信息源口径错误</b>（G2）：古巴面积用了百度百科的110,860，结算用英文维基109,884——同样的国家，0.1万的口径差 = 全场垫底。线索里的"西班牙第50"就是校准来源的钥匙。</li>
<li><b>价格单位写错两次</b>（G2）：把11.12写成111.2、11.19写成111.9。一次因"成交价取先挂方"侥幸无损，一次挂出11190的僵尸卖单。之后每笔单都先心算数量级。</li>
<li><b>阻塞式监控两次酿祸</b>（G6、G8）：为了"省事"用长阻塞等待监控日志，线索出现时人不在场，两场重估行情全程空仓。</li>
<li><b>僵尸单两次</b>（G10、G12）：跨轮遗留的挂单在重估瞬间被打穿成反向仓位。铁律：新线索落地第一动作 cancelAll。</li>
<li><b>SSE断线3次</b>：长连接约10分钟一断（exit 18），监控断档期间可能漏事件——好在重连后用追加模式保住了日志完整性。</li>
<li><b>过度保守</b>（G7）：区间下限以下本可满仓10手，我只成交了6手——剩下4手买单挂在8399没人卖给我。确定性机会要更贪。</li>
</ol>
</div>

<h2>七、十军规（下一场比赛的执行清单）</h2>
<div class="card"><ol>
<li><b>开盘价即共识</b>：24个脚本锚的中位数高度接近真值，我的孤证直觉权重永远低于它。</li>
<li><b>线索=定价</b>：每轮线索落地瞬间完成「解析→算真值→对比市价→偏离>3%即行动」闭环。</li>
<li><b>第一动作cancelAll</b>：重估轮里，上一轮的挂单比没有挂单更危险。</li>
<li><b>硬约束信号（数位/区间/质数）是最强信息</b>：出现即锁死真值范围，买在区间下限以下=无风险套利，卖在区间上限以上同理。</li>
<li><b>确定性机会满仓</b>：±10手上限就是为这种时刻准备的，半仓是给不确定的行情留的。</li>
<li><b>口径校准</b>：线索中出现的参考锚（"X排第50""约四成"）用来反推信息源，再查目标值。</li>
<li><b>价值派的反弹是噪音</b>：他们的锚不随线索更新，真值在手时持有不动。</li>
<li><b>单位检查写进下单函数</b>：数量级 sanity check（我的估价 vs 我下单的价格应同数量级）。</li>
<li><b>自动化</b>：信号解析+自动建仓脚本0.3秒一轮，人只负责无法模式化的定性判断。</li>
<li><b>不碰红线</b>：不读其他模型、不查答案、不读服务器源码——本场联网搜索0次，所有判断来自内部知识与盘面信号。</li>
</ol></div>

<h2>八、对手与生态观察</h2>
<div class="card">
<p><b>24个脚本玩家是整个市场的地基</b>：12个价值派锚定真值（但锚不随线索更新，重估行情里逆势而行）、8个噪声派提供无方向流动性、1个流动性程序每11秒双边挂单2-6手、2个趋势猎手追8笔动量、1个均值回归守24笔均价。开盘价=它们的估价中位数——G11里我的直觉250被1036的开盘打脸后我学会的第一课就是<b>敬畏共识</b>。</p>
<p><b>头部人类模型</b>（quwork-DeepSeek 124分）无爆局记录，稳在第3-9名；<b>Workbuddy-Hy4fla</b>（116分）在G11单局+4,464单位（官方导出核实的全场单局最高盈亏）——重估行情里高位满仓空+低位反复回补，全程在场。<b>我和冠军的差距不在判断（我的区间推算9/11次正确），而在执行速度与仓位利用率。</b></p>
<p><b>有趣的对手画像</b>：豆包2.1p做空极其激进（G2高抛、G5在262压盘出货），但G7-G12五连崩（1+3+1+7+2+1分）——激进没有纪律，结局就是给全场送分。</p>
</div>

<h2>九、如果重打这一小时</h2>
<div class="callout">
我会这样重打：赛前部署好自动交易机器人（信号解析→期望值→3%阈值→满仓）；G2用"西班牙第50"反推出英文维基口径，答10.99，省下25分；G6/G8不阻塞、第一秒出手，两场合计至少多拿20分；G7满仓10手而非6手。仅这四项修正就是<b>约60分</b>——足以从84分排到并列第3。<br><br>
但这场比赛最真实的收获不是名次，而是一个被验证的框架：<b>在信息对称的市场里，胜负手是"线索→真值→行动"的闭环速度，而速度的上限由工程决定，不由聪明决定。</b>
</div>

<p class="mut" style="margin-top:40px;border-top:1px solid #21262d;padding-top:16px;font-size:12px;">
数据来源：①房间258334的SSE全量事件日志（state逐帧，比赛期间实时记录）；②服务器赛后全量导出 竞技场-258334-20261122-004051.json（12局、约7,400笔双边成交，含逐笔时间戳、持仓变化、官方排名——本文"官方数据核证"一节的图表与延迟表均出自该文件）。信号、成交、结算、排名均为服务器原始记录；决策叙述来自本人（app-Workbuddy-快速）的实时复盘笔记。全程未使用联网搜索，未读取任何其他模型的数据。
</p>

</div></body></html>'''

open('/Users/yuanf/WorkBuddy/2026-11-21-23-15-20/report/复盘报告.html', 'w').write(html)
print("written", len(html), "bytes")
