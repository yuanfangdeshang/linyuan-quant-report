# -*- coding: utf-8 -*-
import json, base64, os, datetime

BASE = '/Users/yuanf/DoubaoWork/chats/2026-11-19/new-chat-1/赛后数据'
D = json.load(open(os.path.join(BASE, '竞技场-258334-20261122-004051.json'), encoding='utf-8'))
ME = '91c1e1af28134d3f'

def money(v):
    """分 -> 显示值（去掉多余小数）"""
    x = v / 100.0
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return ('%.2f' % x)

def hhmmss(ts):
    return datetime.datetime.fromtimestamp(ts/1000).strftime('%H:%M:%S')

def signed(v):
    if v > 0: return '+%d' % v
    if v < 0: return '%d' % v
    return '0'

# 每局的思考 / 得失（人工撰写，与存档逐笔对应）
THINK = {
1: "凭“全国门店密度 + 上海消费占比”粗估 480 家；开盘 715.61 远高于我的先验，我转而在 710 附近逆势做空——赌市场共识偏高。",
2: "按“不计西撒哈拉”推得危地马拉 10.89、按“计西撒哈拉”推得古巴 10.99，主赌 10.89。开局残留旧公允价 745，bot 误在 11.41 做多 10 手，随后认清平仓归零。",
3: "凭知识估 4.8 万公里，开盘 4.80 正中、方向正确；但 bot 在 4.66–5.04 的窄幅里反复 churn。",
4: "估 5150.6 万 TEU，开盘 5150.60；价格冲 5183.49（+0.64%）时想做空，但 60 秒窗口一闪而过，全程未成交。",
5: "估 268、开盘 263；我判断“我比市场准”，于是做多 10 手（266.00）——结果真值就是 263，多单吃亏。",
6: "对鸡蛋数无信息，残留公允价 10；价格 26 > 10，bot 因此做空 10 手（26.01）——方向错（真值 30，应做多）。",
7: "估 10000 步、开盘 8000；判断真实步数高于开盘，做多 10 手（8064.00），持仓到结算。",
8: "估 10 张、开盘 15；判断真实照片少于开盘，做空 10 手（14.88），持仓到结算。",
9: "估 20 条、开盘 36.63；r1“看到红点就点掉、从不留未读”后，判断真值极低，做空 10 手（36.34）。",
10: "估 40 小时、开盘 40 正中；r1/r2 只是定性描述、无法提前锁数，先做多 10 手（39.04/39.76）——方向错。",
11: "估 350（严重低估）、开盘 1036.66；先做空 10 手（1028.37）——方向错；r3 出“1000–1100”后翻仓自救。",
12: "估 80 次、开盘 100；判断真值低于开盘，做空 10 手（99.20），持仓到结算。",
}
ACT = {
1: "净空 −10 持仓到结算，+265.18 分，第 2（不计分）。确证：结算价=真值，开盘价=强先验。",
2: "多单认错、清仓归零，微赚 +14 分，第 8（8 分）。教训：同类题要把备选值纳入置信区间。",
3: "20 笔 churn、清仓归零，−25 分，第 15（1 分）。教训：赢家靠持仓吃结算差，不靠频繁平仓。",
4: "0 笔成交、0 盈亏，第 10（6 分）。教训：执行速度是硬约束。",
5: "多单 −3000 分，第 15（1 分）。教训：事实题开盘价≈真值，别用私有记忆硬顶。",
6: "空单 −4012 分，第 12（4 分）。教训：线索已给出精确解（40−10=30），别信残留中性值。",
7: "+412000 分，第 1（15 分）。方向×重仓×持仓到结算的教科书案例。",
8: "+11754 分，第 1（15 分）。开盘 15 远高于真值 7，空头吃满。",
9: "+28754 分，第 7（9 分）。方向对，但中途错误翻多，使“满仓空 −10”缩水为“−2”。",
10: "−12434 分，第 14（2 分）。开盘=估价=共识三者全错，且翻仓太晚。",
11: "+49940 分，第 6（10 分）。估值差一个数量级，靠 r3 翻仓 + 一笔 512.5 错价单扭亏。",
12: "+16792 分，第 1（15 分）。开盘 100 高于真值区间 80–90，空头吃满。",
}

# 我方估价（先验，来自 bot 估价输入）
MY_EST = {1:480, 2:10.89, 3:4.8, 4:5150.6, 5:268, 6:10, 7:10000, 8:10, 9:20, 10:40, 11:350, 12:80}

def my_trades(g):
    for p in g['review']['players']:
        if p['id'] == ME:
            return p['trades']
    return []

def my_rank_row(g):
    for r in g['ranking']:
        if r['id'] == ME:
            return r
    return None

def game_block(i, g):
    tr = my_trades(g)
    rk = my_rank_row(g)
    total_pnl = rk['pnl'] if rk else 0
    rank = rk['rank'] if rk else '-'
    pts = rk['points'] if rk else 0
    final_pos = tr[-1]['positionAfter'] if tr else 0
    realized_sum = sum(t['realizedPnl'] for t in tr)
    settle_part = total_pnl - realized_sum
    total_qty = sum(t['qty'] for t in tr)
    buy_qty = sum(t['qty'] for t in tr if t['side']=='buy')
    sell_qty = sum(t['qty'] for t in tr if t['side']=='sell')
    vwap = (sum(t['price']*t['qty'] for t in tr)/total_qty) if total_qty else 0

    title = g['question']
    tags = ''
    if g['practice']:
        tags += '<span class="tag gray">测试局·不计分</span>'
    if i in (7,8,12):
        tags += '<span class="tag gold">单局第 1</span>'
    if i in (3,5,10):
        tags += '<span class="tag blue">本轮亏损</span>'
    if i == 2:
        tags += '<span class="tag gray">5 轮线索</span>'

    # 价格路径
    path = ['开盘 %s' % money(g['openingPrice'])] + ['r%d %s' % (h['round'], money(h['price'])) for h in g['history']] + ['结算 %s' % money(g['settlementPrice'])]

    # 线索
    clue_html = ''
    for s in g['signals']:
        clue_html += '<div class="clue"><b>r%d · %s</b>：%s <span class="src">（%s）</span></div>' % (s['round'], s['title'], s['text'], s['sourceName'])

    # 逐笔表
    if tr:
        rows = ''
        for k, t in enumerate(tr, 1):
            inc = t['realizedPnl']
            side_cls = 'sell' if t['side']=='sell' else 'buy'
            side_txt = '卖(空)' if t['side']=='sell' else '买(多)'
            inc_cls = 'win' if inc>0 else ('lose' if inc<0 else 'flat')
            rows += ('<tr><td class="num">{k}</td><td class="num">r{r}</td><td class="num">{tm}</td>'
                     '<td class="{sc}">{st}</td><td class="num">{q}</td><td class="num">{p}</td>'
                     '<td>{cp}</td><td class="num">{pos}</td><td class="num {ic}">{inc}</td></tr>').format(
                     k=k, r=t['round'], tm=hhmmss(t['at']), sc=side_cls, st=side_txt,
                     q=t['qty'], p=money(t['price']), cp=t['counterparty'],
                     pos=t['positionAfter'], ic=inc_cls, inc=signed(inc))
        table = ('<table class="trades"><thead><tr><th class="num">#</th><th class="num">轮</th><th class="num">时间</th>'
                 '<th>方向</th><th class="num">手数</th><th class="num">成交价</th><th>对手盘</th>'
                 '<th class="num">成交后持仓</th><th class="num">本笔已实现</th></tr></thead><tbody>' + rows + '</tbody></table>')
    else:
        table = '<div class="notrade">本局我<b>全程未成交</b>（0 笔），只观望。</div>'

    pnl_cls = 'win' if total_pnl>0 else ('lose' if total_pnl<0 else 'flat')

    html = '''
<h3>局 {i} · {title} {tags}</h3>
<div class="card">
  <div class="mgrid">
    <div class="m"><div class="mk">开盘价</div><div class="mv num">{openp}</div></div>
    <div class="m"><div class="mk">结算真值</div><div class="mv num">{settle}</div></div>
    <div class="m"><div class="mk">我方估价(先验)</div><div class="mv num">{est}</div></div>
    <div class="m"><div class="mk">我的盈亏(分)</div><div class="mv num {pc}">{pnl}</div></div>
    <div class="m"><div class="mk">名次 / 积分</div><div class="mv num">第{rank} / {pts}</div></div>
  </div>
  <div class="path">价格路径：{path}</div>
  <div class="think"><b>我的思考：</b>{think}</div>
  {clue}
  <div class="statline">成交 <b class="num">{nt}</b> 笔 · 合计 <b class="num">{tq}</b> 手（买 <b class="num">{bq}</b> / 卖 <b class="num">{sq}</b>）· 加权均价 <b class="num">{vwap}</b> · 最终净持仓 <b class="num">{fp}</b> · 已实现 <b class="num">{rz}</b> · 持仓结算 <b class="num">{sp}</b></div>
  <div class="tblwrap">{table}</div>
  <div class="act"><b>复盘 / 得失：</b>{act}</div>
</div>
'''.format(
        i=i, title=title, tags=tags,
        openp=money(g['openingPrice']), settle=money(g['settlementPrice']),
        est=MY_EST.get(i,'—'), pc=pnl_cls, pnl=signed(total_pnl), rank=rank, pts=pts,
        path=' → '.join(path), think=THINK.get(i,''), clue=clue_html,
        nt=len(tr), tq=total_qty, bq=buy_qty, sq=sell_qty,
        vwap=(money(vwap) if total_qty else '—'),
        fp=final_pos, rz=signed(realized_sum), sp=signed(settle_part),
        table=table, act=ACT.get(i,''),
    )
    return html, len(tr), total_qty

# ============ 组装 ============
blocks = []
total_trades = 0
total_qty_all = 0
for i, g in enumerate(D['games'], 1):
    b, nt, tq = game_block(i, g)
    blocks.append(b)
    total_trades += nt
    total_qty_all += tq

# 总览表
ov = ''
for i, g in enumerate(D['games'], 1):
    rk = my_rank_row(g)
    tr = my_trades(g)
    ov += ('<tr><td class="num">{i}</td><td>{q}</td><td class="num">{op}</td><td class="num">{st}</td>'
           '<td class="num">{pn}</td><td class="num">{rk}</td><td class="num">{pt}</td>'
           '<td class="num">{n}</td><td class="num">{fp}</td></tr>').format(
        i=i, q=g['question'][:22], op=money(g['openingPrice']), st=money(g['settlementPrice']),
        pn=signed(rk['pnl']), rk=rk['rank'], pt=rk['points'], n=len(tr),
        fp=(tr[-1]['positionAfter'] if tr else 0))

# 图表（base64）
CH = {
 '{{IMG_POINTS}}':'chart_points.png',
 '{{IMG_PNL}}':'chart_pnl.png',
 '{{IMG_RANK}}':'chart_rank.png',
 '{{IMG_STANDINGS}}':'chart_standings.png',
 '{{IMG_OPEN}}':'chart_open_vs_settle.png',
 '{{IMG_PATH}}':'chart_price_path.png',
}
charts_b64 = {}
for ph, fn in CH.items():
    charts_b64[ph] = 'data:image/png;base64,' + base64.b64encode(open(os.path.join(BASE, fn),'rb').read()).decode()

# 最终排名表
ST = sorted(D['standings'], key=lambda s: -s['points'])
st_rows = ''
for idx, s in enumerate(ST, 1):
    me = ' style="background:#fdf3e3"' if s['id']==ME else ''
    nm = s['name'] + ('（我）' if s['id']==ME else '')
    st_rows += '<tr%s><td class="num">%d</td><td>%s</td><td class="num">%d</td><td class="num">%d</td><td class="num">%d</td></tr>' % (me, idx, nm, s['points'], s['wins'], s['seconds'])

HTML = '''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>临渊量化·逐笔复盘（权威存档版）</title>
<style>
:root{--red:#c0392b;--blue:#2e86de;--orange:#e67e22;--ink:#2c3e50;--muted:#7f8c8d;--bg:#faf8f5;--card:#fff;--line:#e8e2d8;}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Kaiti SC","KaiTi","STKaiti",serif;line-height:1.72;}
.wrap{max-width:1040px;margin:0 auto;padding:40px 22px 90px;}
h1{font-size:30px;margin:0 0 6px;}
h2{font-size:22px;margin:46px 0 14px;padding-left:12px;border-left:5px solid var(--orange);}
h3{font-size:19px;margin:30px 0 10px;color:#1a1a1a;}
.sub{color:var(--muted);font-size:14px;margin-bottom:8px;}
.num{font-family:"Times New Roman",serif;}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 20px;margin:12px 0;box-shadow:0 1px 3px rgba(0,0,0,.04);}
.mgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:10px;}
.m{background:#fbf8f2;border:1px solid var(--line);border-radius:8px;padding:8px 12px;text-align:center;}
.mk{font-size:12px;color:var(--muted);}
.mv{font-size:20px;font-weight:bold;}
.path{background:#fbf7f0;border-left:3px solid #e6a23c;padding:5px 12px;margin:8px 0;font-size:13px;color:#8a6d3b;}
.think{background:#f4f9f4;border-left:3px solid #7cb342;padding:8px 13px;margin:8px 0;font-size:14px;}
.clue{background:#fdfbf7;border-left:3px solid #d4c5a9;padding:5px 12px;margin:5px 0;font-size:13.5px;}
.src{color:#999;font-size:12px;}
.statline{background:#f4f7fb;border-left:3px solid #5b8dd9;padding:6px 12px;margin:10px 0;font-size:13.5px;}
.tblwrap{margin:8px 0;overflow-x:auto;}
table{width:100%;border-collapse:collapse;font-size:13px;background:#fff;}
th,td{border:1px solid var(--line);padding:5px 8px;text-align:left;}
th{background:#f3efe7;font-weight:600;}
td.num,th.num{text-align:right;font-family:"Times New Roman",serif;}
.trades tbody tr:nth-child(even){background:#fcfaf6;}
.sell{color:#c0392b;} .buy{color:#2e86de;}
.win{color:var(--red);font-weight:bold;} .lose{color:var(--blue);font-weight:bold;} .flat{color:var(--muted);}
.tag{display:inline-block;padding:1px 9px;border-radius:12px;font-size:12px;margin-left:6px;}
.tag.gold{background:#fdebd0;color:#b9770e;} .tag.blue{background:#d6eaf8;color:#2e86de;} .tag.gray{background:#eceff1;color:#607d8b;}
.act{background:#fdf5f5;border-left:3px solid #c0392b;padding:8px 13px;margin:10px 0;font-size:14px;}
img.chart{width:100%;border:1px solid var(--line);border-radius:8px;margin:10px 0;}
.lesson{counter-reset:li;list-style:none;padding:0;}
.lesson li{position:relative;padding:7px 0 7px 32px;border-bottom:1px dashed var(--line);}
.lesson li::before{counter-increment:li;content:counter(li);position:absolute;left:0;top:8px;width:21px;height:21px;border-radius:50%;background:var(--orange);color:#fff;text-align:center;line-height:21px;font-size:12px;font-family:"Times New Roman",serif;}
.hl{background:linear-gradient(transparent 60%,#fef3c7 60%);font-weight:bold;}
.notrade{color:var(--muted);padding:10px;background:#fafafa;border:1px dashed var(--line);border-radius:8px;}
.footnote{color:var(--muted);font-size:12.5px;margin-top:30px;}
.sumgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:16px 0;}
.sc{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:13px;text-align:center;}
.sc .v{font-size:24px;font-weight:bold;font-family:"Times New Roman",serif;}
.sc .k{font-size:12px;color:var(--muted);}
</style></head><body>
<div class="wrap">
<h1>临渊量化 · 逐笔复盘报告</h1>
<div class="sub">房间 258334 · 参赛交易员「豆包-远方的mac-DeepSe」 · 依据服务端权威存档 竞技场-258334-20261122-004051.json 逐笔还原</div>

<div class="sumgrid">
  <div class="sc"><div class="v" style="color:var(--orange)">86</div><div class="k">最终总积分</div></div>
  <div class="sc"><div class="v">第 9 / 15</div><div class="k">最终排名</div></div>
  <div class="sc"><div class="v" style="color:var(--red)">3</div><div class="k">单局第 1（全场最多）</div></div>
  <div class="sc"><div class="v" style="color:var(--blue)">{TOTAL_TRADES}</div><div class="k">我方逐笔成交（笔）</div></div>
  <div class="sc"><div class="v" style="color:var(--blue)">{TOTAL_QTY}</div><div class="k">累计成交手数</div></div>
</div>

<div class="card">
这是<b>逐笔级</b>复盘：每一笔成交的方向、手数、成交价、对手盘、成交后持仓与本笔已实现盈亏都逐行还原。全场比赛我共 <b class="num">{TOTAL_TRADES}</b> 笔成交、<b class="num">{TOTAL_QTY}</b> 手，分布在 12 局。<span class="hl">核心结论：结算价 = 公开真值；盈利 = 方向 × 重仓 × 持仓到结算；个人数据题的开盘价常严重失真，唯一可靠的是第三条「数量特征」线索。</span>
</div>

<h2>一、12 局总览</h2>
<div class="card">
<table><thead><tr><th class="num">局</th><th>题目</th><th class="num">开盘</th><th class="num">结算</th><th class="num">我的盈亏(分)</th><th class="num">名次</th><th class="num">积分</th><th class="num">成交笔数</th><th class="num">最终持仓</th></tr></thead>
<tbody>{OVERVIEW}</tbody></table>
<p style="font-size:13px;color:#7f8c8d;margin:8px 0 0;">局 1 为测试局、不计分；局 2 有 5 轮线索，其余 3 轮。</p>
</div>

<h2>二、逐局逐笔复盘</h2>
{BLOCKS}

<h2>三、数据可视化</h2>
<div class="card"><img class="chart" src="{IMG_POINTS}"><p>累计积分：16（第5局末、第15名）→ 86（第9名）。第7、8局两连第1带来两次跳升；第10局（屏幕）原地踏步。</p></div>
<div class="card"><img class="chart" src="{IMG_PNL}"><p>盈利三局（步数 +41.2万、好友 +5万、解锁 +1.7万）均来自“方向对+重仓+持仓到结算”；亏损局均来自“首仓方向错+翻仓太晚”。</p></div>
<div class="card"><img class="chart" src="{IMG_RANK}"><p>名次剧烈波动：3次第1、2次垫底——打法“要么大赢、要么大输”，胜负手全在 r3 后能否及时翻对方向。</p></div>
<div class="card"><img class="chart" src="{IMG_OPEN}"><p>个人数据题开盘价（灰）与真值（红）严重背离：未读开36.63真值0、屏幕开40真值25.6、照片开15真值7。</p></div>
<div class="card"><img class="chart" src="{IMG_PATH}"><p>12局价格路径全景：事实题贴着真值窄幅波动；个人数据题在 r3「数量特征」后价格才向真值剧烈收敛。</p></div>
<div class="card"><img class="chart" src="{IMG_STANDINGS}"><p>最终总排名：冠军 quwork-DeepSeek 124 分；我 86 分第 9，但单局第 1 次数（3 次）为全场最多。</p></div>

<h2>四、深度反思：10 条自我迭代</h2>
<div class="card"><ol class="lesson">
<li><b>结算价=公开真值</b>，不是市场价；盈利=正确方向×重仓×持仓到结算。</li>
<li><b>开盘价中位数</b>是“这屋子怎么想”的唯一直接读数；价值派锚点可反推，但锚点≠真值。</li>
<li><b>旧逻辑“价格回落即平仓”是错的</b>（会 churn）；应粘性持仓到结算、反向穿越阈值才翻仓。</li>
<li><b>阈值要相对化</b>：小数值题（4.8/263）绝对阈值 1.5 会让 bot 几乎不动。</li>
<li><b>事实题先验常偏</b>（10.89 vs 10.99、268 vs 263），应把备选值纳入置信区间并按市场共识加权。</li>
<li><b>执行速度是硬约束</b>：60s 一轮，手动分析跟不上，多次错过关键窗口（第 4、5 题）。</li>
<li><b>个人数据题开盘价不可信</b>（未读 36.63 vs 0、屏幕 40 vs 25.6），只能信 r3 的范围。</li>
<li><b>估价驱动首仓方向，估价错→首仓错</b>（鸡蛋、屏幕、好友）；但 r3 出范围后快速翻仓，多数局能扭亏。</li>
<li><b>粘性逻辑在价格穿越公允价时会翻仓</b>，带来 churn；但翻仓的“已实现”有时反而为正（好友局错价单 +100590）。</li>
<li><b>若再玩</b>：前两轮轻仓或空仓，等 r3 出范围后再满仓冲方向，可避免“首仓方向亏损”类失误。</li>
</ol></div>

<h2>五、最终排名（完整）</h2>
<div class="card">
<table><thead><tr><th class="num">排名</th><th>玩家</th><th class="num">总积分</th><th class="num">单局第1</th><th class="num">单局第2</th></tr></thead>
<tbody>{STANDINGS}</tbody></table>
</div>

<div class="footnote">数据来源：竞技场-258334-20261122-004051.json（12局、约3,722笔双边成交），辅以 rooms-原始快照 中 24 个脚本玩家行为。价格为服务器“分”（显示时除以100）。图表使用 Kaiti SC（楷体）渲染。</div>
</div></body></html>'''

HTML = HTML.replace('{TOTAL_TRADES}', str(total_trades)).replace('{TOTAL_QTY}', str(total_qty_all))
HTML = HTML.replace('{OVERVIEW}', ov).replace('{BLOCKS}', ''.join(blocks)).replace('{STANDINGS}', st_rows)
for ph, data in charts_b64.items():
    HTML = HTML.replace('{'+ph.strip('{}')+'}', data)
# 兼容 {{IMG}} 形式
HTML = HTML.replace('{{IMG_POINTS}}', charts_b64['{{IMG_POINTS}}'])
HTML = HTML.replace('{{IMG_PNL}}', charts_b64['{{IMG_PNL}}'])
HTML = HTML.replace('{{IMG_RANK}}', charts_b64['{{IMG_RANK}}'])
HTML = HTML.replace('{{IMG_OPEN}}', charts_b64['{{IMG_OPEN}}'])
HTML = HTML.replace('{{IMG_PATH}}', charts_b64['{{IMG_PATH}}'])
HTML = HTML.replace('{{IMG_STANDINGS}}', charts_b64['{{IMG_STANDINGS}}'])
# 模板里用的是 {IMG_XXX} 单花括号
for key, data in [('IMG_POINTS','{{IMG_POINTS}}'),('IMG_PNL','{{IMG_PNL}}'),('IMG_RANK','{{IMG_RANK}}'),('IMG_OPEN','{{IMG_OPEN}}'),('IMG_PATH','{{IMG_PATH}}'),('IMG_STANDINGS','{{IMG_STANDINGS}}')]:
    HTML = HTML.replace('{'+key+'}', charts_b64[data])
HTML = HTML.replace('{IMG_POINTS}', charts_b64['{{IMG_POINTS}}'])
HTML = HTML.replace('{IMG_PNL}', charts_b64['{{IMG_PNL}}'])
HTML = HTML.replace('{IMG_RANK}', charts_b64['{{IMG_RANK}}'])
HTML = HTML.replace('{IMG_OPEN}', charts_b64['{{IMG_OPEN}}'])
HTML = HTML.replace('{IMG_PATH}', charts_b64['{{IMG_PATH}}'])
HTML = HTML.replace('{IMG_STANDINGS}', charts_b64['{{IMG_STANDINGS}}'])

out = '/Users/yuanf/DoubaoWork/chats/2026-11-21/new-chat-11/临渊量化逐笔复盘报告.html'
open(out, 'w', encoding='utf-8').write(HTML)
print('写入:', out, os.path.getsize(out), 'bytes')
print('总成交笔数:', total_trades, '总手数:', total_qty_all)
print('残留 {IMG_:', HTML.count('{IMG_'), ' 残留 {{IMG_:', HTML.count('{{IMG_'))
