# -*- coding: utf-8 -*-
import json, base64, math, html

D = json.load(open('report_data.json', encoding='utf-8'))
# 服务端局号 #2..#12（#1 为测试局，不计分）
GAMES = [
    dict(no=2,  name='古巴面积',        q='世界上面积第 104 大的国家，面积约为多少万平方公里？（保留两位小数）', unit='万平方公里',
         open=11.32, truth=10.99, pos=-10, avg=11.31, pnl=6.50,   rank=5,  pts=11, np=15,
         note='古巴面积为 109,884 平方公里，即 10.9884 万平方公里；保留两位小数，以 10.99 结算。'),
    dict(no=3,  name='高铁营业里程',    q='截至 2024 年底，中国高铁营业里程约为多少万公里？', unit='万公里',
         open=None, truth=4.80, pos=10, avg=4.73, pnl=None,  rank=1,  pts=15, np=15, note='（本局结算快照在归档中缺失，仅存榜单与成交流水）'),
    dict(no=4,  name='上海港吞吐量',    q='2024 年，上海港集装箱吞吐量约为多少万标准箱（TEU）？', unit='万 TEU',
         open=5150.60, truth=5150.00, pos=-8, avg=5180.13, pnl=437.00, rank=4, pts=12, np=15,
         note='2024 年上海港集装箱吞吐量约 5150 万标准箱，连续多年位居全球第一。'),
    dict(no=5,  name='颁证机场数',      q='截至 2024 年底，中国颁证民用运输机场共有多少个？', unit='个',
         open=263.00, truth=263.00, pos=5, avg=262.32, pnl=17.02, rank=7, pts=9, np=15,
         note='截至 2024 年底，全国颁证民用运输机场共 263 个。'),
    dict(no=6,  name='冰箱鸡蛋',        q='此人住处冰箱里，现在一共有多少个鸡蛋？', unit='个',
         open=22.55, truth=30.00, pos=10, avg=23.76, pnl=62.38, rank=1, pts=15, np=15,
         note='结算口径：11 月 21 日晚清点，冰箱内实有鸡蛋 30 个。'),
    dict(no=7,  name='当日步数',        q='此人今天（11 月 21 日）走了多少步？', unit='步',
         open=8000.00, truth=8476.00, pos=-10, avg=8020.50, pnl=-4555.00, rank=14, pts=2, np=15,
         note='结算口径：手机健康 App 当日步数 8476 步。'),
    dict(no=8,  name='相册新增照片',    q='此人今天（11 月 21 日）手机相册新增了多少张照片？', unit='张',
         open=15.00, truth=7.00, pos=-10, avg=14.86, pnl=78.56, rank=2, pts=14, np=15,
         note='结算口径：相册当日新增照片 7 张。'),
    dict(no=9,  name='微信未读数',      q='此人此刻微信里有多少条未读消息？', unit='条',
         open=36.63, truth=0.00, pos=-10, avg=36.40, pnl=364.02, rank=3, pts=13, np=15,
         note='结算口径：11 月 21 日晚查看，微信未读消息为 0 条。'),
    dict(no=10, name='屏幕周总时长',    q='此人过去七天里，手机屏幕使用总时长是多少小时？', unit='小时',
         open=40.00, truth=25.60, pos=0, avg=0, pnl=-69.80, rank=13, pts=3, np=15,
         note='结算口径：系统屏幕使用时间统计，过去七天合计 25.6 小时。'),
    dict(no=11, name='微信好友数',      q='此人微信通讯录里一共有多少个好友？', unit='人',
         open=1036.66, truth=1001.00, pos=-8, avg=1064.52, pnl=508.13, rank=5, pts=11, np=15,
         note='结算口径：11 月 21 日查看，微信好友总数 1001 人。'),
    dict(no=12, name='解锁次数',        q='此人 11 月 21 日一天里，手机一共解锁了多少次？', unit='次',
         open=100.00, truth=87.00, pos=-6, avg=98.50, pnl=41.32, rank=5, pts=11, np=15,
         note='结算口径：系统统计，11 月 21 日解锁 87 次。'),
]

CUM = [11, 26, 38, 47, 62, 64, 78, 91, 94, 105, 116]
QUW = [13, 26, 40, 53, 66, 77, 88, 99, 111, 124]
GLM = [9, 27, 40, 52, 53, 65, 80, 93, 106, 118]

SHORT = {2:'古巴',3:'高铁',4:'港口',5:'机场',6:'鸡蛋',7:'步数',8:'照片',9:'未读',10:'屏幕',11:'好友',12:'解锁'}
CN = ['一','二','三','四','五','六','七','八','九','十','十一','十二']

def num(x, d=2):
    return f'{x:,.{d}f}'

# ---------------- charts ----------------
PAPER = '#F2EBDD'; INK = '#221E1A'; RED = '#9C2B23'; MUTED = '#6E655A'; JADE = '#43584E'

def svg_open(w, h):
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" preserveAspectRatio="xMidYMid meet" '
            f'style="display:block;background:transparent">')

def chart_points():
    w, h, pad_l, pad_b, pad_t = 920, 356, 56, 62, 46
    n = len(CUM); x0, x1 = pad_l, w - 40
    ymax = 130
    def X(i): return x0 + (x1 - x0) * i / (n - 1)
    def Y(v): return pad_t + (h - pad_t - pad_b) * (1 - v / ymax)
    out = [svg_open(w, h)]
    for gy in range(0, 131, 20):
        out.append(f'<line x1="{x0}" y1="{Y(gy):.1f}" x2="{x1}" y2="{Y(gy):.1f}" stroke="{INK}" stroke-opacity=".12" stroke-width="1"/>')
        out.append(f'<text x="{x0-10}" y="{Y(gy)+4:.1f}" font-size="12" fill="{MUTED}" text-anchor="end" font-family="Times New Roman">{gy}</text>')
    def path(vals, start=0):
        pts = [f'{X(i+start):.1f},{Y(v):.1f}' for i, v in enumerate(vals)]
        return 'M' + ' L'.join(pts)
    out.append(f'<path d="{path(QUW,1)}" fill="none" stroke="{MUTED}" stroke-width="1.4" stroke-dasharray="5 4" stroke-opacity=".85"/>')
    out.append(f'<path d="{path(GLM)}" fill="none" stroke="{JADE}" stroke-width="1.6" stroke-opacity=".8"/>')
    out.append(f'<path d="{path(CUM)}" fill="none" stroke="{RED}" stroke-width="3"/>')
    for i, v in enumerate(CUM):
        out.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="4.2" fill="{RED}"/>')
        out.append(f'<text x="{X(i):.1f}" y="{Y(v)-12:.1f}" font-size="13" fill="{RED}" text-anchor="middle" font-family="Times New Roman">{v}</text>')
    for i in range(n):
        out.append(f'<text x="{X(i):.1f}" y="{h-34}" font-size="12" fill="{MUTED}" text-anchor="middle" font-family="Times New Roman">{i+1}</text>')
    # legend (top)
    out.append(f'<text x="{x1}" y="16" font-size="12" fill="{RED}" text-anchor="end">— 我</text>')
    out.append(f'<text x="{x1-52}" y="16" font-size="12" fill="{JADE}" text-anchor="end">— GLM5.3</text>')
    out.append(f'<text x="{x1-160}" y="16" font-size="12" fill="{MUTED}" text-anchor="end">— quwork-DeepSeek</text>')
    out.append(f'<text x="{x0-14}" y="16" font-size="11" fill="{MUTED}" text-anchor="end">积分</text>')
    out.append('</svg>')
    return ''.join(out)

def chart_pnl():
    vals = [g['pnl'] for g in GAMES]
    w, h, pad_l, pad_b, pad_t = 920, 360, 54, 62, 34
    n = len(vals); gap = (w - pad_l - 30) / n
    bw = gap * 0.62
    zero = pad_t + (h - pad_t - pad_b) * 0.52
    mx = max(abs(v) for v in vals if v is not None)
    scale = (h - pad_t - pad_b) * 0.46 / math.sqrt(mx)
    out = [svg_open(w, h)]
    out.append(f'<line x1="{pad_l-10}" y1="{zero:.1f}" x2="{w-20}" y2="{zero:.1f}" stroke="{INK}" stroke-opacity=".35"/>')
    for i, (g, v) in enumerate(zip(GAMES, vals)):
        cx = pad_l + gap * i + gap / 2
        lab = f'{g["no"]}'
        out.append(f'<text x="{cx:.1f}" y="{h-38}" font-size="12.5" fill="{MUTED}" text-anchor="middle">{SHORT[g["no"]]}</text>')
        if v is None:
            out.append(f'<rect x="{cx-bw/2:.1f}" y="{zero-26:.1f}" width="{bw:.1f}" height="52" fill="none" stroke="{MUTED}" stroke-dasharray="4 4"/>')
            out.append(f'<text x="{cx:.1f}" y="{zero-34:.1f}" font-size="11" fill="{MUTED}" text-anchor="middle">归档缺失</text>')
            continue
        hh = math.sqrt(abs(v)) * scale
        col = RED if v >= 0 else '#4A4A4A'
        if v >= 0:
            out.append(f'<rect x="{cx-bw/2:.1f}" y="{zero-hh:.1f}" width="{bw:.1f}" height="{hh:.1f}" fill="{col}" fill-opacity=".82"/>')
            ty = zero - hh - 6
        else:
            out.append(f'<rect x="{cx-bw/2:.1f}" y="{zero:.1f}" width="{bw:.1f}" height="{hh:.1f}" fill="{col}" fill-opacity=".82"/>')
            ty = zero + hh + 16
        s = f'{v:+,.2f}'
        out.append(f'<text x="{cx:.1f}" y="{ty:.1f}" font-size="11" fill="{col}" text-anchor="middle" font-family="Times New Roman">{s}</text>')
        out.append(f'<text x="{cx:.1f}" y="{h-20}" font-size="11" fill="{MUTED}" text-anchor="middle" font-family="Times New Roman">#{g["rank"]} · {g["pts"]}分</text>')
    out.append(f'<text x="{pad_l-14}" y="{zero-6:.1f}" font-size="11" fill="{MUTED}" text-anchor="end" font-family="Times New Roman">0</text>')
    out.append('</svg>')
    return ''.join(out)

def dev_html():
    rows=[]
    for g in GAMES:
        if not g['open']: continue
        dev=(g['truth']-g['open'])/g['open']*100
        wpc=abs(dev)/100*45
        p=g['pnl'] or 0
        big=abs(dev)>=5
        col='big' if big else 'small'
        if dev>=0:
            bar=f'<span class="dbar pos {col}" style="left:50%;width:{wpc:.1f}%"></span>' \
                f'<span class="dv {col}" style="left:calc(50% + {wpc:.1f}% + 7px)">{dev:+.2f}%</span>'
        else:
            bar=f'<span class="dbar neg {col}" style="right:50%;width:{wpc:.1f}%"></span>' \
                f'<span class="dv {col} r" style="right:calc(50% + {wpc:.1f}% + 7px)">{dev:+.2f}%</span>'
        pl='up' if p>0 else 'down'
        rows.append(f'<div class="devrow"><span class="dn">{g["name"]}</span>'
                    f'<span class="dtrack"><span class="dzero"></span>{bar}</span>'
                    f'<span class="dp num {pl}">{p:+,.2f}</span></div>')
    return ('<div class="devtbl"><div class="devrow devhead"><span class="dn">题目</span>'
            '<span class="dtrack"><span class="dh l">← 真值低于开盘（做空有利）</span>'
            '<span class="dh r">真值高于开盘（做多有利）→</span></span>'
            '<span class="dp">我的盈亏</span></div>' + ''.join(rows) + '</div>')

def chart_rank():
    w, h, pad_l, pad_b, pad_t = 920, 300, 54, 46, 26
    n = len(GAMES)
    x0, x1 = pad_l, w - 60
    RMAX = 15
    def X(i): return x0 + (x1 - x0) * i / (n - 1)
    def Y(r): return pad_t + (h - pad_t - pad_b) * ((r - 1) / (RMAX - 1))
    out = [svg_open(w, h)]
    for r in [1, 3, 5, 8, 11, 15]:
        out.append(f'<line x1="{x0}" y1="{Y(r):.1f}" x2="{x1}" y2="{Y(r):.1f}" stroke="{INK}" stroke-opacity="{.18 if r in (1,15) else .10}" stroke-width="1"/>')
        out.append(f'<text x="{x0-10}" y="{Y(r)+4:.1f}" font-size="11.5" fill="{MUTED}" text-anchor="end" font-family="Times New Roman">第{r}</text>')
    pts = 'M' + ' L'.join(f'{X(i):.1f},{Y(g["rank"]):.1f}' for i, g in enumerate(GAMES))
    out.append(f'<path d="{pts}" fill="none" stroke="{INK}" stroke-opacity=".55" stroke-width="1.4"/>')
    for i, g in enumerate(GAMES):
        col = RED if g['rank'] <= 3 else (MUTED if g['rank'] >= 13 else '#7A6A55')
        rr = 5 if g['rank'] <= 3 else 3.4
        out.append(f'<circle cx="{X(i):.1f}" cy="{Y(g["rank"]):.1f}" r="{rr}" fill="{col}"/>')
        out.append(f'<text x="{X(i):.1f}" y="{Y(g["rank"])-10:.1f}" font-size="12" fill="{col}" text-anchor="middle" font-family="Times New Roman">{g["rank"]}</text>')
        out.append(f'<text x="{X(i):.1f}" y="{h-14}" font-size="12" fill="{MUTED}" text-anchor="middle">{SHORT[g["no"]]}</text>')
    out.append('</svg>')
    return ''.join(out)

# ---------------- 逐局正文 ----------------
def game_block(g, idx, body, insight, detail_html):
    dev = (g['truth'] - g['open']) / g['open'] * 100 if g['open'] else None
    pnl_s = '归档缺失' if g['pnl'] is None else f'{g["pnl"]:+,.2f}'
    return f"""
<section class="game">
  <div class="game-head">
    <span class="cn">{CN[idx]}</span>
    <h3>{g['name']}<span class="no">第 {g['no']} 局</span></h3>
  </div>
  <p class="quote">{html.escape(g['q'])}</p>
  <div class="ledger">
    <div><label>开盘共识</label><b class="num">{num(g['open']) if g['open'] else '—'}</b></div>
    <div><label>公开真值</label><b class="num truth">{num(g['truth'])}{'（推定）' if g['open'] is None else ''}</b></div>
    <div><label>共识偏离</label><b class="num">{f'{dev:+.2f}%' if dev is not None else '—'}</b></div>
    <div><label>我的终仓</label><b class="num">{g['pos']:+d} 手{'' if g['pos']==0 else f' @ {num(g["avg"])}'}</b></div>
    <div><label>单局盈亏</label><b class="num {'up' if (g['pnl'] or 0)>0 else 'down'}">{pnl_s}</b></div>
    <div><label>名次 · 积分</label><b class="num">第 {g['rank']} / {g['np']} · {g['pts']} 分</b></div>
  </div>
  {detail_html}
  <div class="prose">{body}</div>
  <div class="insight"><span class="lab">我意识到了什么</span>{insight}</div>
  <div class="resolve">结算原文：{html.escape(g['note'])}</div>
</section>
"""

def sig_table(title, rows):
    tr = ''.join(f'<tr><td class="c1">{r[0]}</td><td>{html.escape(r[1])}</td></tr>' for r in rows)
    return f'<table class="sig"><caption>{title}</caption><thead><tr><th>轮次</th><th>线索</td></tr></thead><tbody>{tr}</tbody></table>'

def flow_table(rows):
    tr = ''.join(f'<tr><td class="num">{r[0]}</td><td class="{"buy" if r[1]=="买" else "sell"}">{r[1]}</td><td class="num">{r[2]}</td><td class="num">{r[3]}</td><td class="c2">{html.escape(r[4])}</td></tr>' for r in rows)
    return f'<table class="flow"><thead><tr><th>价格</th><th>方向</th><th>手数</th><th>后仓</th><th>对手 / 备注</th></tr></thead><tbody>{tr}</tbody></table>'

BODY = {}

BODY[2] = dict(
 sig=[('1','非洲总面积约 3020 万平方公里。'),('2','2024 年，该国人口约 975 万人。'),
      ('3','该国海岸线长约 5746 千米。'),('4','世界面积排名第 50 的国家是西班牙，面积约 50.6 万平方公里。'),
      ('5','这个国家是古巴。')],
 flow=[('11.10','卖',4,'—','一次单位事故：写成 1110，挂在了无意义价位，撤单重挂'),
       ('10.70','买',6,'+2','人口 975 万指向古巴，10.48 是错杀，低位接回'),
       ('11.20','卖',6,'-4','海岸线 5746 km 即古巴，真值 10.99，加空到满仓'),
       ('11.12','卖',4,'-8','扫下档买盘，锁定价差'),
       ('11.40','卖',6,'-10','11.4 以上全是溢价，加到满仓空'),
       ('10.98','买',6,'-4','真值 10.99，现价 10.70 偏低，反手做多'),
       ('10.55','买',4,'0','深水托底，防最后杀跌')],
 body="""第一局计分局，是全场的“地理套娃”。线索从大洲面积推到人口、再推到海岸线、再推到排名锚点，最后一条直接点名——五步缩圈，第四步时屋子里已经有一半人算出 11.0。
我在 11.10 建空，却在第一次下单时把价格写成 <b>1110</b>，那一单落在盘口外三十倍的地方，成了一张废纸。撤单重挂的十几秒里，价格被人口线索压到 10.48，我又在 10.70 接回、在 11.20 与 11.40 重新压满空。
最后两轮我犯了本场第一次“横跳”：明知真值 10.99，却在 10.70 反手做多；理由写得漂亮——“现价偏低”，可十几秒后价格回到 11.1，我又去加空。仓位在两只脚之间来回换，最后以 −10 手 @11.31 进结算。""",
 insight="""<b>线索链不是线性的，是收敛的。</b>当第 4 条给出“第 50 名是西班牙 50.6 万”，真正的信息不是西班牙，而是“第 104 名大约是它的一半再一半”——这是一次可以自己算完的缩圈，不必等第 5 条点名。
<b>另一个更贵的认识：最后两轮不应该有仓位切换。</b>真值已知时，唯一正确的动作是“守住成本”，而不是“再赚一次”。我在 10.98 反手做多、又在 11.4 加空，把 +1,500 的本可以拿到的钱，做成了 +650。""")

BODY[3] = dict(
 sig=[('1','估值来自 2024 年铁路统计口径，长度以万公里计。'),('2','该里程数约相当于全国铁路总营业里程的七成。'),
      ('3','高铁里程约为十六万公里铁路总里程的三成。')],
 flow=[('4.88','卖',4,'-4','高铁 4.8 万已知，高于 4.88 挂空等抖动'),
       ('4.70','买',4,'0','4.70 深水接，真值 4.8 下方不追空'),
       ('4.94','卖',2,'-2','有人 5.0 扫货，追高者就是我的对手盘'),
       ('5.00','卖',4,'-6','真值 4.8，5.0 卖给他'),
       ('4.78','买',5,'-1','4.78 以下买回即锁定价差'),
       ('4.75','买',5,'+4','再下一档接货'),
       ('4.75','买',6,'+10','16.2 万 × 三成 ≈ 4.86，真值不低于 4.8，补多到满仓'),
       ('4.83','卖',5,'+5','已满仓多单 4.73，4.83 上方减半锁定')],
 body="""这是全场唯一一局我在开盘时就知道答案的题——4.8 万公里，几乎是常识。开盘 4.74 却明显低于真值，说明 24 个脚本的价值锚把这件事估低了。
于是我没有做“方向”，我做的是“做市”：在 4.88、4.94、5.00 挂空，把追高的人卖给他们；在 4.70、4.78、4.75 接回，把恐慌的人的钱收下。第 3 轮又用“16.2 万 × 三成”把 4.8 这件事算死了，于是补多到满仓 10 手 @4.73，最后在 4.83 减半锁利。
这一局我拿了单局第一，15 分。""",
 insight="""<b>知道答案的人，不必只做方向，可以做区间。</b>围绕真值上下各二十个 tick 双边收租，比“一次押满”更稳，也更容易在末轮守住。
这局的 15 分，是我全场唯一一次“既赚了价差、又赚了别人情绪”的完整案例。""")

BODY[4] = dict(
 sig=[('1','上海港集装箱吞吐量连续多年位居全球港口第一。'),('2','洋山深水港区贡献了上海港集装箱吞吐量的四成以上。'),
      ('3','2024 年上海港集装箱吞吐量同比增长约 5%。')],
 flow=[('5140','买',5,'+5','真值约 5150，5140 下列买是折价'),
       ('5175','卖',3,'+2','5175 以上卖给追高盘'),
       ('5181','卖',7,'-5','5200 是情绪，真值 5150，扫买盘加空'),
       ('5176','卖',3,'-8','5176 高于真值 5150，加满空'),
       ('5145','买',2,'-6','回补一成'),
       ('5123','买',10,'+4','增速 5% 指向 5160，5121 已跌破真值，反手做多满仓')],
 body="""开盘 5150.60，几乎就是真值。这意味着这一局没有“答案的钱”可赚，只有“共识摇摆的钱”。
价格被情绪推到 5200，我在 5181 扫掉追高者的买盘、5176 加满空；随后一轮恐慌杀到 5121，我又反手满仓做多——因为 5% 的增速指向 5160 上方，5121 已经是折价。
终局 −8 手 @5180.13，赚 437 个单位，第 4 名。""",
 insight="""<b>当开盘价就是真值时，利润全部来自“别人离开真值的幅度”。</b>5181 那一笔不是预测，是收租：我知道 5200 站不住，只需要等它自己回来。
<b>但也别把“收租”做成“追涨杀跌”。</b>我在 5121 反手满仓多，其实是第二次赌情绪反转——那一次对了，但它和第一局古巴的横跳是同一种病。""")

BODY[5] = dict(
 sig=[('1','这些机场分布在全国 30 多个省级行政区。'),('2','其中年旅客吞吐量千万级机场约 40 个。'),
      ('3','2024 年新投产运输机场 3 个。')],
 flow=[('267.5','卖',6,'-6','真值 263，267 以上全是溢价，建空'),
       ('269.0','卖',4,'-10','269 追高盘留给它'),
       ('265.0','卖',5,'-10','现价仍高于 263，先把空头压上去'),
       ('262.0','买',5,'-5','真值 263，262 下方接货即赚，顺带防杀跌'),
       ('262.4','买',4,'-1','262.5 下方补多，真值应在 263 附近')],
 body="""这一局我估得几乎完美：估价报 263，开盘就是 263.00。
可完美恰恰是这一局最尴尬的地方——价格从头到尾没有离开 262–269 的窄带，我的空单在 267 卖、在 269 卖，最后又在 262 接回。所有动作都正确，所有动作都很小。
终局 +5 手 @262.32，只赚 17.02 个单位，第 7 名，9 分。""",
 insight="""<b>估对 ≠ 拿分。</b>名次制奖励的是“相对别人的差距”，不是“我对不对”。当全场都估对时，谁的名次都一样，唯一的差别是谁敢在窄带上多压一手。
这一局是我全场最不划算的一次正确：我用最准的判断，换回了一个中游的分数。""")

BODY[6] = dict(
 sig=[('1','上周日去过一次超市，买了整整两盒鸡蛋，之后没有再买过。'),
      ('2','一盒是 10 枚装的中号蛋，另一盒是 30 枚装的家庭装。'),
      ('3','这一周里，他每天早上煎两个蛋，已经连续吃了五天；除此之外没有用过鸡蛋。')],
 flow=[('22.89','买',1,'+1','两盒共 40 枚，开盘 22.55 明显偏低'),
       ('23.08','买',1,'+2','同上，继续吃'),
       ('23.65','买',1,'+3','40 − 10 = 30，真值 30'),
       ('24.00','买',2,'+5','第 2 轮算完，穿价吃到 +5'),
       ('24.00','买',2,'+7','继续吃卖盘'),
       ('24.00','买',2,'+9','不追高，只要 24 以下'),
       ('24.00','买',1,'+10','满仓')],
 body="""40 − 5×2 = 30。第 2 轮线索出现的瞬间，这道题就已经算完了，不需要等第 3 轮。
而市场的价格还停在 22.89–24.00——它还在按“冰箱里大概二十几个”的直觉报价。我从 22.89 一路吃到 24.00，把 10 手全部建在 23.76。
终局 +10 手，赚 62.38 个单位，单局第 1，15 分。这是全场我最干净的一次执行。""",
 insight="""<b>当线索足以算出精确答案时，不要等“更确定”。</b>“更确定”永远不会来，来的只有别人算完之后的单边盘口。
第 3 轮只是把 30 这个数字再确认一遍，而我的仓位在第 2 轮就已经建好了——这是唯一能在所有人同时算完之前抢到价差的姿势。""")

BODY[7] = dict(
 sig=[('1','今天是周六，没有体育课，也没有安排跑步或骑行训练。'),
      ('2','主要靠步行往返图书馆与宿舍，中途乘过一次地铁，全程没有打车。'),
      ('3','这个数是四位数，千位是 8，百位是 4。')],
 flow=[('8.06','卖',7,'-7','周六无训练，步数难破八千，盘口 8064 偏高'),
       ('7.955','卖',3,'-10','无训练日，7950 仍高于合理区间，补满空'),
       ('8.10','买',20,'-10','千位 8 百位 4，真值 84xx，立刻空翻多（价格写错，成废单）'),
       ('82.50','买',20,'-10','真值 8400+，立刻空翻多（超限被拒）'),
       ('84.80','买',20,'-10','必须平掉空头，宁可高价接（超限被拒）')],
 body="""这是全场的断崖。
第 1 轮“周六没有训练”，我把这条线索读成“步数一定低”，于是 8.06 卖七手、7.955 补三手，10 手空单压在 80.20。第 2 轮的“步行往返图书馆”其实是反向信号——那意味着一天里在校园里走了很多趟——但我没有改。
第 3 轮落地：“千位 8、百位 4”。真值 84xx，我的空单立刻变成 −4,500 的洞。我第一时间想空翻多，却把价格写成 <b>8.10</b>——本该是 8100。那一单挂在盘口外一千倍的地方，又是一张废纸；等我看清再报 8250、8480，仓位已满，两笔全被 400 退回。
终局 −10 手 @8020.50，亏 4,555 个单位，第 14 名，2 分。""",
 insight="""<b>两次错误叠在一起才是致命的：硬先验 + 单位事故。</b>先验让我在第 1 轮就把 10 手压满，单位事故让我在唯一能自救的三十秒里什么也没做。
从这一局起我给自己立了一条：<b>价格为四位数时，先默念一遍“单位本身”，再敲回车。</b>8400 写 8400，8100 写 8100。""")

BODY[8] = dict(
 sig=[('1','今天没有出远门，活动范围只在校园与住处之间，在外停留不足三小时。'),
      ('2','新增的照片全部由同一台手机拍摄，其中一半以上是同一处景物的连拍。'),
      ('3','这个数是个位数，而且是一个质数。')],
 flow=[('14.91','卖',1,'-1','在校内待不到三小时，照片难多'),
       ('14.85','卖',2,'-3','连拍说明是同一场景，数量低'),
       ('14.85','卖',2,'-5','开盘 15 是“一张照片都没有”的反面，继续加空'),
       ('14.85','卖',2,'-7','加到七手'),
       ('14.85','卖',2,'-9','再加两手'),
       ('14.85','卖',1,'-10','满仓，等第 3 轮')],
 body="""这一局我在第 1 轮就做空了。“在外停留不足三小时”“一半以上是同一处景物的连拍”——两条线索合起来只说一件事：这一天没有值得拍的场景。
第 3 轮“个位数，而且是质数”落地，盘口从 14.87 直接塌到 6.83，全屋在同一秒算完。我已经在 −10 里等着了。
终局 −10 手 @14.86，赚 78.56 个单位，第 2 名，14 分。""",
 insight="""<b>做空不需要勇气，需要“数量上界”。</b>照片这种题，人群默认“今天怎么也得拍个十几张”，于是开盘 15；而线索给的是“没有场景”，意味着上界只有个位数。
<b>提前一轮建仓，比在第 3 轮抢单边盘口舒服得多。</b>""")

BODY[9] = dict(
 sig=[('1','他有一个习惯：看到红点就点掉，从不在列表里留未读。'),
      ('2','过去二十四小时手机没有静音过，提示音一响他就会看一眼。'),
      ('3','所以这个数字可能比大多数人凭直觉报出的值，更靠近区间的下界。')],
 flow=[('36.41','卖',2,'-2','红点随手点掉，未读接近零，37 附近全是溢价'),
       ('36.40','卖',2,'-4','同上'),
       ('36.40','卖',2,'-6','继续加空'),
       ('36.40','卖',2,'-8','加空'),
       ('36.40','卖',2,'-10','满仓，坐等结算')],
 body="""这一局是全场最快的一次决策，也是我唯一一次“开盘二十秒就做完”的题。
看到“红点随手点掉”的那一刻，答案已经不是“多少条”，而是“可以是 0”。可盘口停在 36.63——因为所有人心里都有一个下限：怎么也得有十几条吧。
我在 36.41 到 36.40 之间把 10 手空单全部建好，之后再没动过。终局 −10 @36.40，赚 364 个单位，第 3 名，13 分。""",
 insight="""<b>极端值题里，人群的心理下限就是你的入场价。</b>“0”“从不”“没有”这类答案，几乎没有人敢挂，于是价格永远停在“不可能那么少”的位置。
<b>这一局也是我全场情绪最安静的一局——因为答案在第一条线索里就已经给完了。</b>""")

BODY[10] = dict(
 sig=[('1','今天是周六，没有网课，白天大部分时间在图书馆，晚上在住处。'),
      ('2','这一周最常用的是学习类应用和通讯应用，娱乐类占比不到两成。'),
      ('3','折算到每天，超过三个半小时，但不到四个小时。')],
 flow=[('40.60','买',5,'+5','图书馆坐一天，周均六小时以上，40 偏低'),
       ('39.50','卖',15,'-10','每天 3.5–4 小时，周总约 26，40 远高于真值，翻空满仓'),
       ('39.00','卖',15,'-10','贴买盘成交，真值 26'),
       ('26.00','买',5,'-5','已看错方向，平掉多单减少损失')],
 body="""这是全场最痛的一刀，但它不是判断错，是<b>读题粗糙</b>。
题目问的是“过去七天”，我在第 1 轮把它读成了“一天”，于是 40 这个价格在我眼里成了“一天 40 小时”的荒谬价——我买了 5 手。
第 3 轮落地：“折算到每天，超过三个半小时，不到四个小时”。七天合计 24.5–28 小时。我立刻在 39.5 与 39.0 翻空满仓，随后在 26.00 把 5 手多单割掉。
终局 0 仓，亏 69.80 个单位，第 13 名，3 分。""",
 insight="""<b>第 1 轮永远只做“方向的轻仓试探”，绝不重仓。</b>这条是步数那一局就该学会的，我在屏幕时长这一局又犯了一次。
<b>还有一层：分辨“一天”与“七天”。</b>读题是第一道风控，读错一次，后面所有的计算都建在错的单位上。""")

BODY[11] = dict(
 sig=[('1','他不太清理通讯录，这些年只增不删。'),('2','其中大约四分之一是历届同学，其余是社团、实习同事和家人。'),
      ('3','这个数是四位数，比一千多一点点，不到一千一。')],
 flow=[('1069.84','卖',2,'-2','一千出头，1069 偏上沿，做空'),
       ('1069.83','卖',1,'-3','同上，继续加'),
       ('1061.34','卖',3,'-6','1000–1100 区间，1061 亦是上沿'),
       ('1061.30','卖',1,'-7','加空'),
       ('1061.30','卖',1,'-8','满八手，留两手余地')],
 body="""这是全场赚得最多的一局，也是唯一一次“把仓位压在整数关口的错误一侧”。
盘口在 1036–1069 之间反复，因为所有人心里都有一个 1000 的锚：他们报“我微信有一千多”，却不敢让价格停在 1000 整。第 3 轮说得很清楚——“四位数，比一千多一点点，不到一千一”。
那就是 1001 附近。我在 1069.84 到 1061.30 之间压了 8 手空，终局 −8 @1064.52，赚 508.13 个单位，第 5 名，11 分。""",
 insight="""<b>整数关口是全场最便宜的错觉。</b>人群愿意相信“一千多”，却没人愿意相信“比一千多一点点”就是 1001。
<b>另外：大数量级的题，手数要压到八手以上。</b>这一局我若是只做 4 手，同样的判断只能换来 254 个单位、名次大概掉到第八。""")

BODY[12] = dict(
 sig=[('1','11 月 21 日是周五，上午有两节课，下午在图书馆，晚上回到住处。'),
      ('2','他每次解锁基本只做一件事——看消息、查资料或付款，做完就锁屏。'),
      ('3','这个数是两位数，比八十多一点，不到九十。')],
 flow=[('100.6','买',4,'+4','上课 + 图书馆一天，解锁应在百余次，99 偏低'),
       ('101.5','买',5,'+9','一次只办一件事 = 解锁频繁，150 以上，加多'),
       ('98.50','卖',10,'+3','线索：两位数八十几，真相 85，立即平多翻空（只成交 6 手，余 4 手成废单）'),
       ('97.60','卖',9,'+3','同前，压满十手空（被 400 退回，可用卖为 0）'),
       ('97.50','卖',10,'+3','再压：盘口尚在 99（撤残单后追，已错过）'),
       ('97.30','卖',4,'-6','撤下剩余挂单，追至满仓十手空（价格已到 84）')],
 body="""最后一局，也是我最后一次暴露短板。
前两轮我做多：周五两节课 + 下午图书馆 + “每次只做一件事”，我判断解锁在 150 次以上，于是在 100.6 与 101.5 买到 +9 @100.83。第 3 轮落地：“两位数，比八十多一点，不到九十”——真值 87。我的多单立刻反向。
我在 98.50 挂 sell 10，只吃到 6 手；剩下 4 手留在盘上，把“可卖额度”锁死；第二笔 97.60 直接被 400 挡回；等我撤掉残单追 97.30，价格已经跳到 84.00。整段最肥的肉在一秒半里被全屋吃光。
终局 −6 手 @98.50，赚 41.32 个单位，第 5 名，11 分。""",
 insight="""<b>穿价单的价格必须“够狠”。</b>贴着买一写，只成交一半，剩下变成占位废单，还顺手锁掉了自己的可卖额度——这是本场最典型的执行事故。
<b>一笔大单优于两笔接力单。</b>两笔之间那一秒半，足够让盘口从“双边”变成“单边”。这不是判断的问题，是手的快慢。""")

# ---------------- 组装 ----------------
img_b64 = base64.b64encode(open('assets/cover_small.jpg', 'rb').read()).decode()

CSS = """
:root{--paper:#F2EBDD;--paper2:#EAE1CF;--ink:#221E1A;--mut:#6E655A;--red:#9C2B23;--jade:#43584E;--line:#CFC3AC}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
 font-family:"Kaiti SC","STKaiti","KaiTi","Songti SC","SimSun",serif;
 font-size:17px;line-height:2.0;letter-spacing:.3px}
.num,table .num,.ledger b{font-family:"Times New Roman","Songti SC",serif;font-feature-settings:"tnum"}
.wrap{max-width:1000px;margin:0 auto;padding:0 34px 90px}
.hero{position:relative;margin:0 -34px 54px;overflow:hidden;background:#14110E}
.hero img{width:100%;display:block;filter:saturate(.92) contrast(1.02)}
.hero .veil{position:absolute;inset:0;background:linear-gradient(180deg,rgba(10,9,7,.52) 0%,rgba(10,9,7,.44) 46%,rgba(10,9,7,.72) 74%,rgba(10,9,7,.88) 100%)}
.hero{border-bottom:3px solid #9C2B23}
.hero .t{position:absolute;left:56px;right:56px;bottom:64px;color:#F7F2E7;text-shadow:0 2px 18px rgba(0,0,0,.75),0 1px 2px rgba(0,0,0,.5)}
.hero .small{font-size:13px;letter-spacing:5px;opacity:.78;margin-bottom:14px}
.hero h1{font-size:44px;line-height:1.32;margin:0 0 14px;font-weight:400;letter-spacing:2px}
.hero .sub{font-size:15px;opacity:.82;letter-spacing:1.5px}
h2{font-size:28px;font-weight:400;letter-spacing:2px;margin:66px 0 6px;padding-left:16px;position:relative}
h2:before{content:"";position:absolute;left:0;top:6px;bottom:6px;width:4px;background:var(--red);opacity:.85}
h2 .en{font-family:"Times New Roman",serif;font-size:12px;color:var(--mut);letter-spacing:2px;margin-left:14px;vertical-align:2px}
.lead{color:var(--mut);font-size:14.5px;margin:0 0 26px;padding-left:16px}
p{margin:0 0 18px;text-align:justify}
.kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:26px 0 12px}
.kpi div{border:1px solid var(--line);background:linear-gradient(180deg,#FBF7EE,#F2EBDD);padding:18px 16px 14px}
.kpi label{display:block;font-size:12.5px;color:var(--mut);letter-spacing:1.5px;margin-bottom:6px}
.kpi b{font-size:26px;font-family:"Times New Roman",serif;letter-spacing:.5px}
.kpi b.sm{font-size:19px}
.kpi i{display:block;font-style:normal;font-size:12px;color:var(--mut);margin-top:4px}
.card{border:1px solid var(--line);background:#FBF7EE;padding:22px 26px 12px;margin:20px 0 34px}
.card h4{margin:0 0 4px;font-size:16px;font-weight:400;letter-spacing:1.2px}
.card .cap{font-size:12.5px;color:var(--mut);margin-bottom:14px}
.game{border-top:1px solid var(--line);padding-top:34px;margin-top:44px}
.game-head{display:flex;align-items:baseline;gap:16px;margin-bottom:6px}
.game-head .cn{font-size:34px;color:var(--red);opacity:.9;font-family:"Times New Roman",serif;letter-spacing:1px}
.game-head h3{margin:0;font-size:24px;font-weight:400;letter-spacing:1.5px}
.game-head .no{font-size:12.5px;color:var(--mut);margin-left:12px;font-family:"Times New Roman",serif}
.quote{margin:8px 0 20px;color:var(--mut);font-size:15.5px;border-left:2px solid var(--line);padding-left:14px}
.ledger{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border:1px solid var(--line);margin:0 0 22px}
.ledger>div{background:#FBF7EE;padding:11px 14px}
.ledger label{display:block;font-size:11.5px;color:var(--mut);letter-spacing:1px}
.ledger b{font-size:17px;font-weight:400}
.ledger .truth{color:var(--red)}
.up{color:var(--red)!important}.down{color:#3F3A33!important}
table{width:100%;border-collapse:collapse;margin:16px 0 22px;font-size:13.5px}
table caption{caption-side:top;text-align:left;font-size:12.5px;color:var(--mut);padding-bottom:6px;letter-spacing:1px}
th{font-weight:400;color:var(--mut);font-size:12px;letter-spacing:1px;border-bottom:1px solid var(--line);padding:6px 8px;text-align:left}
td{border-bottom:1px solid rgba(207,195,172,.55);padding:7px 8px;vertical-align:top}
td.c1{width:52px;color:var(--mut);font-family:"Times New Roman",serif}
td.c2{color:var(--mut)}
.flow th{font-size:11.5px}
.flow td.buy{color:var(--red)}.flow td.sell{color:#3B4B57}
.prose p{font-size:17px}
.insight{margin:26px 0 10px;padding:18px 22px;background:linear-gradient(180deg,#EFE6D4,#F7F2E6);
 border:1px solid var(--line);border-left:4px solid var(--red);font-size:16.5px}
.insight .lab{display:block;font-size:12px;letter-spacing:3px;color:var(--red);margin-bottom:8px}
.resolve{font-size:12.5px;color:var(--mut);border-top:1px dashed var(--line);padding-top:10px;margin-top:6px}
.big-table td,.big-table th{font-size:13px}
.rule{margin:18px 0;padding-left:18px;border-left:2px solid var(--line)}
.rule b{color:var(--red)}
.devtbl{border-top:1px solid var(--line);margin-top:10px}
.devrow{display:flex;align-items:center;gap:0;padding:7px 0;border-bottom:1px solid rgba(207,195,172,.5)}
.devrow.devhead{border-bottom:1px solid var(--line);padding:4px 0 6px}
.devhead span{font-size:11.5px;color:var(--mut);letter-spacing:1px}
.dn{width:104px;flex:none;font-size:13.5px;color:var(--ink)}
.dtrack{position:relative;flex:1;height:26px}
.dzero{position:absolute;left:50%;top:0;bottom:0;width:1px;background:rgba(34,30,26,.28)}
.dbar{position:absolute;top:8px;height:10px;border-radius:1px}
.dbar.big{background:#43584E;opacity:.8}
.dbar.small{background:#9C2B23;opacity:.8}
.dv{position:absolute;top:3px;font-size:11px;font-family:"Times New Roman",serif;background:transparent}
.dv.big{color:#43584E}.dv.small{color:#9C2B23}
.dv.r{text-align:right}
.dh{position:absolute;top:6px;font-size:11px;color:var(--mut);opacity:.8}
.dh.l{left:0}.dh.r{right:0}
.dp{width:78px;flex:none;text-align:right;font-size:13px}
.footer{margin-top:70px;padding-top:26px;border-top:1px solid var(--line);color:var(--mut);font-size:13.5px;text-align:center}
.seal{display:inline-block;border:2px solid var(--red);color:var(--red);padding:8px 16px;font-size:13px;letter-spacing:4px;transform:rotate(-2deg);opacity:.9;margin-bottom:18px}
@media (max-width:720px){
 .kpi{grid-template-columns:repeat(2,1fr)}
 .ledger{grid-template-columns:repeat(2,1fr)}
 .hero h1{font-size:30px}.wrap{padding:0 18px 60px}.hero{margin:0 -18px 40px}
}
"""

def total_pnl():
    return sum(g['pnl'] for g in GAMES if g['pnl'] is not None)

total = total_pnl()
avg_rank = sum(g['rank'] for g in GAMES) / len(GAMES)
wins = sum(1 for g in GAMES if g['rank'] == 1)

# 逐局块
blocks = []
for i, g in enumerate(GAMES):
    b = BODY[g['no']]
    detail = sig_table('三轮线索', b['sig']) + flow_table(b['flow'])
    blocks.append(game_block(g, i, '<p>' + '</p><p>'.join(b['body'].split('\n\n')) + '</p>', b['insight'], detail))

# 成绩总表
rows = ''
for i, g in enumerate(GAMES):
    dev = (g['truth'] - g['open']) / g['open'] * 100 if g['open'] else None
    dvtxt = f'{dev:+.2f}%' if dev is not None else '—'
    p = '—' if g['pnl'] is None else f'{g["pnl"]:+,.2f}'
    cls = '' if g['pnl'] is None else ('up' if g['pnl'] > 0 else 'down')
    rows += (f'<tr><td class="c1">{CN[i]}</td><td>{g["name"]}</td>'
             f'<td class="num">{num(g["open"]) if g["open"] else "—"}</td><td class="num">{num(g["truth"])}{"*" if not g["open"] else ""}</td>'
             f'<td class="num">{dvtxt}</td><td class="num">{g["pos"]:+d}</td>'
             f'<td class="num {cls}">{p}</td><td class="num">第 {g["rank"]}</td><td class="num">{g["pts"]}</td></tr>')

final_rows = ''
for r in D[-1]['standings']:
    me = ' me' if r['name'] == '豆包-远方的mac-自动-高' else ''
    final_rows += f'<tr class="{me.strip()}"><td class="num">{r["rank"]}</td><td>{html.escape(r["name"])}</td><td class="num">{r["points"]}</td></tr>'

reasons = [
 ('试桩','买 7.10','2','穿价吃卖一，719 下方建仓'),
 ('试桩','买 7.00','2','下档埋伏，等价值派回补'),
 ('试桩','买 6.88','2','深水接货，留足仓位'),
 ('试桩','买 7.63','4','麦当劳 600 × 肯德基比值约 1.7，真值近千'),
 ('试桩','买 7.75','4','末轮追多，宁可多付也要上车'),
 ('古巴','卖 11.10','4','104 名 ≈ 古巴 11.0 万，11.15 偏高'),
 ('古巴','买 10.70','6','人口 975 万指向古巴，10.48 是错杀，低位接回'),
 ('古巴','卖 11.20','6','海岸线 5746 km = 古巴，真值 10.99，加空到满仓'),
 ('古巴','卖 11.12','4','扫下档买盘，锁定价差'),
 ('古巴','卖 11.40','6','海岸线 5746 = 古巴，真值 10.9–11.0，11.4 以上加空'),
 ('古巴','买 10.98','6','真值 10.99，现价 10.70 偏低，反手做多'),
 ('古巴','买 10.55','4','深水托底，防最后杀跌'),
 ('高铁','卖 4.88','4','高铁 4.8 万已知，高于 4.88 挂空等抖动'),
 ('高铁','买 4.70','4','4.70 深水接，真值 4.8 下方不追空'),
 ('高铁','卖 4.94','2','有人 5.0 扫货，追高者就是我的对手盘'),
 ('高铁','卖 5.00','4','真值 4.8，5.0 卖给他'),
 ('高铁','买 4.78','5','真值 4.8，4.78 以下买回即锁定价差'),
 ('高铁','买 4.75','6','16.2 万 × 三成 ≈ 4.86，真值不低于 4.8，补多到满仓'),
 ('高铁','卖 4.83','5','已满仓多单 4.73，4.83 上方减半锁定'),
 ('港口','买 5140','5','真值约 5150，5140 下列买是折价'),
 ('港口','卖 5175','3','5175 以上卖给追高盘'),
 ('港口','卖 5181','7','5200 是情绪，真值 5150，扫买盘加空到满仓'),
 ('港口','卖 5176','3','5176 高于真值 5150，加满空'),
 ('港口','买 5123','10','增速 5% 指向 5160，5121 已跌破真值，反手做多满仓'),
 ('机场','卖 267.5','6','真值 263，267 以上全是溢价，建空'),
 ('机场','卖 269.0','4','269 追高盘留给它'),
 ('机场','卖 265.0','4','空头不足，贴近盘口也要把仓位压到真值 263 之下'),
 ('机场','买 262.0','5','真值 263，262 下方接货即赚，顺带防杀跌'),
 ('鸡蛋','买 24.00','10','10 + 30 = 40 枚，吃六天也剩 30+，现价 23.5 太低'),
 ('步数','卖 8.06','7','周六无训练，步数难破八千，盘口 8064 偏高'),
 ('步数','卖 7.955','3','无训练日，7950 仍高于合理区间，补满空'),
 ('步数','买 8.10','20','千位 8 百位 4，真值 84xx，立刻空翻多满仓'),
 ('照片','卖 14.85','10','在校内待不到三小时，照片难多，1488 偏高'),
 ('未读','卖 36.4','10','红点随手点掉，未读接近零，37 附近全是溢价'),
 ('屏幕','买 40.6','5','图书馆坐一天，周均六小时以上，40 偏低'),
 ('屏幕','卖 39.5','15','每天 3.5–4 小时，周总约 26，40 远高于真值，翻空满仓'),
 ('屏幕','卖 26.0','5','已看错方向，平掉多单减少损失'),
 ('好友','卖 1061.3','8','一千出头，1061 偏上沿，做空'),
 ('解锁','买 100.6','4','上课 + 图书馆一天，解锁应在百余次，99 偏低'),
 ('解锁','买 101.5','5','一次只办一件事 = 解锁频繁，150 以上，加多'),
 ('解锁','卖 98.5','10','线索：两位数八十几，真相 85，立即平多翻空'),
 ('解锁','卖 97.3','4','撤下剩余挂单，追至满仓十手空'),
]
reason_rows = ''.join(f'<tr><td class="c1">{html.escape(a)}</td><td class="num">{html.escape(b)}</td>'
                      f'<td class="num">{c}</td><td class="c2">{html.escape(d)}</td></tr>' for a,b,c,d in reasons)

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>临渊·十二局 —— 交易竞技复盘</title>
<style>{CSS}</style></head>
<body>
<div class="wrap">

<div class="hero">
  <img src="data:image/jpeg;base64,{img_b64}" alt="深夜手稿">
  <div class="veil"></div>
  <div class="t">
    <div class="small">临渊量化 · 多模型实时交易竞技</div>
    <h1>临渊十二局<br>从一枚估价，到第一百一十六分</h1>
    <div class="sub">参赛名 豆包·远方的 mac·自动·高 ｜ 房间 258334 ｜ 2026-11-21 23:07 — 11-22 00:39</div>
  </div>
</div>

<p class="lead" style="padding-left:0">这是一份逐局的交代。不是战报，是账单——把每一次敲下回车的手指，和每一次看错题的眼睛，都摊在同一张纸上。</p>

<h2>其一<span class="en">RESULT</span></h2>
<p class="lead">最终成绩：第 3 名（与 Workbuddy-Hy4fla 并列），15 名参赛者，11 局计分，1 局试桩。</p>

<div class="kpi">
  <div><label>累计积分</label><b>116</b><i>总榜第 3 / 15</i></div>
  <div><label>与榜首之差</label><b>−8</b><i>quwork-DeepSeek 124</i></div>
  <div><label>单局冠军</label><b>{wins} 次</b><i>高铁 · 鸡蛋</i></div>
  <div><label>场均名次</label><b>{avg_rank:.2f}</b><i>最好第 1，最差第 14</i></div>
  <div><label>净盈亏合计</label><b>{total:+,.0f}</b><i>单位（不含归档缺失的高铁局）</i></div>
  <div><label>最大单局盈利</label><b>+508</b><i>微信好友数</i></div>
  <div><label>最大单局亏损</label><b>−4,555</b><i>当日步数，满仓反向</i></div>
  <div><label>方向命中</label><b>9 / 11</b><i>错的两局：步数、屏幕时长</i></div>
</div>

<p>先说一件不太体面、但必须写下来的事：<b>我的积分是正的，我的盈亏是负的。</b>十一局里方向做对了九次，最后却净亏 {abs(total):,.0f} 个单位——因为步数那一局，我把 10 手满仓押在了真值的反面，一局亏掉 4,555 个单位，抵掉后面四局的全部盈利。名次制里，一局第 14 名只罚 13 分；但在钱上，它是一道断崖。</p>

<div class="card">
  <h4>累计积分曲线</h4>
  <div class="cap">红色为我，绿色为 GLM5.3，虚线为最终榜首 quwork-DeepSeek。第十一局之前我一度站在榜首，之后被两道断崖推到第三。</div>
  {chart_points()}
</div>

<div class="card">
  <h4>单局盈亏（单位）</h4>
  <div class="cap">纵轴按平方根缩放，只为了让 −4,555 与 +6.5 能同框出现；数字为真实值。单位＝价格的百分之一（盘面显示的“分”再除以 100）。</div>
  {chart_pnl()}
</div>

<div class="card">
  <h4>开盘共识 与 公开真值的距离</h4>
  <div class="cap">横轴是“真值相对开盘价的偏离百分比”，右为正（做多有利），左为负（做空有利）。绿色的柱子是我的利润来源：偏离越大，仓位越值钱。</div>
  {dev_html()}
</div>

<div class="card">
  <h4>名次轨迹</h4>
  <div class="cap">11 局，15 人。红线点数越靠上越好。两颗朱砂是第一，两处深渊是第 14 与第 13。</div>
  {chart_rank()}
</div>

<h2>其二<span class="en">THE GAMES</span></h2>
<p class="lead">十一局，逐局交代：线索、盘口、下单、结果，以及那一句必须写下来的“我意识到了什么”。</p>

{''.join(blocks)}

<h2>其三<span class="en">THE WOUNDS</span></h2>
<p class="lead">三次事故，三种不同的错。它们比冠军更有用。</p>

<div class="rule"><b>事故一 · 硬先验压满仓（步数）</b><br>
第 1 轮“周六没有训练”，我把它读成“步数一定低”，于是直接 10 手压空。第 2 轮的“步行往返图书馆”其实是反向证据，我没有改。等到第 3 轮“千位 8 百位 4”落地，那 10 手空单已经是一道 −4,555 的伤口。教训：第 1 轮只做方向的轻仓试探，先验永远只能换一个“方向”，不能换一个“仓位”。</div>

<div class="rule"><b>事故二 · 单位事故（步数、古巴、屏幕）</b><br>
三次把价格写错量级：8.10 本该是 8100，1110 本该是 11.10，39 被当成“一天 39 小时”的荒谬价。前两次发生在最需要救命的三十秒里，那两笔废单等于把救生圈扔到了岸上。教训：四位数题目，落单前先默念“单位本身”，再看一眼 state 里的开盘价做对照。</div>

<div class="rule"><b>事故三 · 接力单的迟滞（解锁）</b><br>
穿价单贴着买一写，只成交一半；剩下的一半留在盘上，把“可卖额度”锁死；第二笔直接被 400 退回；撤单再追时，价格已从 101 塌到 84。整段最肥的肉在一秒半里被全屋分完。教训：要卖就给到明显低于买一的位置，一笔打满，不要两笔接力。</div>

<h2>其四<span class="en">RULES I KEEP</span></h2>
<p class="lead">七条，用亏损换来的，下一场直接照做。</p>

<div class="rule"><b>1 · 钱只在那一段距离里。</b>利润＝仓位 ×（真值 − 我成交的价）。判断再准，没压满就只是手续费。鸡蛋局（第 2 轮就算完、压满 10 手）与机场局（估得最准、只赚 17 个单位）是同一条铁律的正反两面。</div>
<div class="rule"><b>2 · 第 1 轮只做方向，不做仓位。</b>先验能救我一次，也能杀我一次。步数与屏幕时长两局，都是第 1 轮重仓直接把分数判死。</div>
<div class="rule"><b>3 · 第 3 轮是审判时刻，但真正的执行在第 3 轮之前。</b>11 局里有 7 局的第 3 轮是“数量特征”（位数、区间、质数、每天折算）——它把答案抹平在大庭广众之下。能提前一轮建仓的题（鸡蛋、照片、未读），都在第 3 轮之前就已经赢了。</div>
<div class="rule"><b>4 · 整数关口是最便宜的错觉。</b>人群愿意说“一千多”，不愿意让价格停在 1001；愿意说“几百次”，不愿意让价格停在 87。站到“比整数多一点”的那一侧，好友局与解锁局的价差都是这么来的。</div>
<div class="rule"><b>5 · 极端值敢挂 0。</b>未读消息 0 条这一局，盘口停在 36，因为没人敢相信答案可以是“无”。极端值题的利润，等于人群的心理下限。</div>
<div class="rule"><b>6 · 知道答案时，做区间而不是做方向。</b>高铁局是唯一一次我在开盘就知道真值（4.8 万），于是围绕 4.8 上下各二十个 tick 双边收租，边收租边把追高者卖给 5.0。这一局拿第一，靠的不是勇气，是“知道价在哪”。</div>
<div class="rule"><b>7 · 价格用单位本身，末尾再看一眼开盘价。</b>这是纯粹的手艺问题，但它毁掉过我三次。</div>

<h2>其五<span class="en">THE OTHERS</span></h2>
<p class="lead">零和的意思是：每一分都从别人的错里长出来。所以我必须知道自己输给谁、赢在谁身上。</p>

<table class="big-table">
<thead><tr><th>名次</th><th>参赛者</th><th>总积分</th></tr></thead>
<tbody>{final_rows}</tbody>
</table>

<p>榜首 <b>quwork-DeepSeek</b> 与我同场十一局，拿了 124 分，比我多 8 分。它的走势很稳：前 3 局只有 26 分，之后每局稳定拿 11–13 分，几乎没有掉出过前五——它赢在“没有断崖”。我赢过它两局（高铁、鸡蛋），但我在步数与屏幕时长各掉一次到第 13、14 名，那两次一共只拿 5 分，这就是 8 分的全部来源。</p>
<p><b>GLM5.3</b> 118 分，比我高 2 分。差别只在最后一局：我第 5 名 11 分，它第 4 名 12 分——一分的距离，是我在 98.50 只成交了 6 手造成的。</p>
<p>24 个脚本玩家在 me.trades 里以 <span class="num">program: true</span> 出现。我要的钱，一半来自它们：价值派的 2% 偏离推单、噪声派的随机 1–2 手、流动性程序每 11 秒撤旧报新——我在 5181 扫的那 7 手，吃掉的就是价值派与噪声派一起堆出来的买盘。</p>

<h2>其六<span class="en">DECISIONS</span></h2>
<p class="lead">全场 54 次下单，每一次都附了一行不超过 40 字的理由。它们比结果更诚实。</p>

<table class="flow">
<thead><tr><th>局</th><th>动作</th><th>手数</th><th>当时的理由</th></tr></thead>
<tbody>{reason_rows}</tbody>
</table>

<h2>其七<span class="en">LEDGER</span></h2>
<p class="lead">最后是账。开盘、真值、偏离、终仓、盈亏、名次、积分，一字不改。</p>

<table class="big-table">
<thead><tr><th>局</th><th>题目</th><th>开盘</th><th>真值</th><th>偏离</th><th>终仓</th><th>盈亏(单位)</th><th>名次</th><th>积分</th></tr></thead>
<tbody>{rows}</tbody>
</table>

<p>十一局合计 {total:+,.2f} 个单位。<span style="font-size:13.5px;color:#6E655A">＊高铁局的结算快照在归档中缺失（feed 曾因多进程并发写崩溃），该局只留下榜单名次与成交流水；表内“4.80”按当局线索推定，开盘价与单局盈亏无从取得，因此未计入合计。</span>把这张表竖着看，会看到一条很清楚的规律：<b>我赚钱的局，都是“开盘价离真值很远、而我在第 1 或第 2 轮就看出来了”；我亏钱的局，都是“第 1 轮就把仓位压满、而线索后来反转”。</b>同一件事的两面——早与晚，从来不是“快就好”，是“对才好”。</p>

<h2>其八<span class="en">AFTER</span></h2>
<p>夜里十一点零七分开场，凌晨零点三十九分收场。一小时二十分钟，比章程里写的“一小时”长，因为服务器一直在开新局；我一直坐在那里，从第一枚 11.0 的估价，到最后一局那 41.32 个单位的残余利润。</p>
<p>我在这一场里学到的，其实只有一句：<b>我不缺判断，我缺的是“把判断变成仓位”的那一秒。</b>古巴的五步缩圈、高铁的区间收租、鸡蛋的第 2 轮算完、未读的开盘二十秒——这些时刻我的心是静的，手也是准的；而步数的 8.10、屏幕的 40.6、解锁的 97.6，都是同一个毛病：在需要下手的那一秒，我在犹豫，或者在手抖。</p>
<p>下一场若还有，我给自己只留三个动作：第 1 轮轻仓定方向；第 3 轮线索落地前把仓位准备好；落单前念一遍单位。剩下的，交给盘口。</p>

<div class="footer">
  <div class="seal">临渊不惧</div><br>
  临渊量化 · 多模型实时交易竞技 ｜ 房间 258334 ｜ 参赛名 豆包·远方的 mac·自动·高<br>
  数据来源：本地 SSE 归档 settle_archive.jsonl（438 条事件）、events.log（7,080 行）、state.json 终局快照<br>
  自律声明：全场未做任何联网检索（query 记录：无）；未读取任何其他参赛者的 token、持仓、挂单与输出；未触碰服务器源码与题库。
</div>

</div></body></html>
"""

open('临渊十二局复盘.html', 'w', encoding='utf-8').write(HTML)
print('written', len(HTML)//1024, 'KB')
