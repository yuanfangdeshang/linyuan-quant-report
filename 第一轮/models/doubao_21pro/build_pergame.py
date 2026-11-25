#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐局逐笔明细 + 分析，自包含 HTML"""
import json, datetime, html
A=json.load(open("logs/my_archive.json",encoding="utf-8"))
NAME={1:"肯德基（测试）",2:"古巴",3:"高铁",4:"上海港",5:"机场",6:"鸡蛋",7:"步数",8:"相册新增",9:"微信未读",10:"屏幕时长",11:"微信好友",12:"解锁次数"}
UNIT={1:"元",2:"万 km²",3:"万 km",4:"万 TEU",5:"个",6:"个",7:"步",8:"张",9:"条",10:"小时/周",11:"个",12:"次"}

ANA={
1:("这是唯一一局「价差和方向同时正确」。做市端 23 手买均价 662.44、29 手卖均价 695.99，价差 33.5 赚了 522；"
   "方向端末仓 −6 手、成本 737.53，真值 700，空头又赚 225。合起来 747。"
   "它给了我一个后来害了我的错觉：以为「做市打底 + 空头压方向」这个配方天然成立。"),
2:("价差 0.49，是真值的 4.5%，全场最宽之一：47 手买均 10.847、44 手卖均 11.337，做市端赚 21.5；"
   "末仓 +3 手成本 10.75 低于真值 10.99，方向也对，再赚 0.73。"
   "50 分钟里唯一一次两头都对。但 r3 我曾把 fair 抬到 11.25、满仓翻多，是 r4 才改回来——这局赢得侥幸。"),
3:("真值 = 开盘 = 4.8，没有方向可赚，只剩价差。7 笔、8 手往返，卖 4.965、买 4.811，价差 0.154，赚 1.23。"
   "这是「纯做市」最干净的样本：无方向、无末仓、账目一笔闭合。缺点是量太小、价差太薄，一分钟只够做 7 笔。"),
4:("全场最像「做市机器」的一局：123 笔、125 手，62 手往返赚 251，1 手裸空卖 5165.90、按真值 5150 买回，赚 15.90。"
   "毛流入 5416.99 里，5150 是还债不是亏损。真正利润 267。此前我误写成「被方向仓吃掉 5150」，是把流水当损益。"),
5:("87 笔、90 手的量是全场第三，但价差只有 0.122（0.046%），赚 5.49。真值 = 开盘 = 263，方向没有任何机会。"
   "这是「高频却薄」的典型：机器一直在转，利润薄得像纸。45 手对 45 手，完美对冲，也完美地只赚了 5 块半。"),
6:("灾难局。开盘 22.55，真值 30（+33%）。我卖 13 手均价 24.03、买 7 手均价 27.40——卖价比买价低 3.37，"
   "这是「越涨越卖、再在更高处买回」。末仓 −6 手空，按 30 还债 180，把 120 的价差全吞掉还倒欠 59。方向反、仓位重。"),
7:("成交量全场最大：137 笔、140 手。但做市价差只有 2.39（0.03%），68 手往返才赚 162。末仓 −4 手空、成本约 8063，"
   "真值 8476 高出 413，4 手亏 1652。**这才是真正的「做市利润被方向仓吃掉」**——不是上港的 267，是这里的 −1488。"),
8:("开盘 15，真值 7。买均 12.79、卖均 9.11，负价差 3.68 × 18 手 = 亏 66。价格单边下跌，我的做市变成「接飞刀」："
   "一路买、一路用更低的价卖。这是「先买后卖」在下跌里必然的结局。"),
9:("全场最漂亮的价差。开盘 36.63，真值 0。卖均 29.28、买均 21.93，价差 7.35 × 33 手 = 赚 242.5。"
   "同一台机器、同样的规则，在下跌里因为「先卖后买」的顺序，把单边行情变成了利润。这是唯一一次趋势站在我这边。"),
10:("开盘 40，真值 25.6。买均 37.97、卖均 32.36，负价差 5.6 × 25 手 = 亏 140。和相册同病：下跌里先买后卖，"
    "买在坑口、卖在坑底。25 笔、50 手，每手平均亏 2.8。"),
11:("开盘 1036.66，真值 1001。买均 972.30、卖均 965.09，负价差 7.2 × 28 手 = 亏 202。价格缓慢下行，"
    "我就在 972 附近接、在 965 附近抛，每一轮都亏一点。慢跌比暴跌更磨人，因为它不给你「抄到底」的错觉。"),
12:("开盘 100，真值 87。买均 96.00、卖均 92.82，负价差 3.18 × 37 手 = 亏 118。68 笔的勤奋，"
    "换来的是每笔 1.6 的亏损。这是全场最后一局，也是「勤奋地亏钱」最典型的样本。"),
}

def tstr(ms):
    dt=datetime.datetime.fromtimestamp(ms/1000)
    return dt.strftime("%H:%M:%S")+"."+f"{dt.microsecond//1000:03d}"

def fmt(v):
    return f"{v:,.2f}" if abs(v)>=100 else f"{v:.2f}"

rows_sum=[]
sections=[]
for g in A["games"]:
    tr=g["trades"];n=len(tr);q=sum(t["qty"] for t in tr)
    b=[t for t in tr if t["side"]=="buy"];s=[t for t in tr if t["side"]=="sell"]
    qb=sum(t["qty"] for t in b) or 1;qs=sum(t["qty"] for t in s) or 1
    pb=sum(t["price_unit"]*t["qty"] for t in b)/qb
    ps=sum(t["price_unit"]*t["qty"] for t in s)/qs
    gross=sum(t["price_unit"]*t["qty"] for t in s)-sum(t["price_unit"]*t["qty"] for t in b)
    final=tr[-1]["positionAfter"]
    debt=-(final*g["settlement"])  # 还债：末仓×真值，正数表示现金流出
    net=g["my_pnl"];settle=g["settlement"]
    cls="pos" if net>=0 else "neg"
    rows_sum.append(f"<tr><td>{g['number']}</td><td class='l'>{NAME[g['number']]}</td><td>{fmt(settle)}</td><td>{fmt(g['opening'])}</td>"
                    f"<td class='{cls}'><b>{fmt(net)}</b></td><td>{g['my_rank']}</td><td>{g['my_points']}</td><td>{n}/{q}</td></tr>")
    # 逐笔表
    tb=[]
    for i,t in enumerate(tr,1):
        side="买" if t["side"]=="buy" else "卖"
        cp=html.escape((t.get("counterparty") or "").strip())
        tag="脚本" if t.get("program") else "模型"
        tb.append(f"<tr><td>{i}</td><td>r{t['round']}</td><td>{tstr(t['at'])}</td><td class='{ 'buy' if t['side']=='buy' else 'sell'}'>{side}</td>"
                  f"<td>{fmt(t['price_unit'])}</td><td>{t['qty']}</td><td>{t['positionAfter']:+d}</td>"
                  f"<td>{t['realizedPnl']/100:+.2f}</td><td class='{ 'mod' if not t.get('program') else ''}'>{cp}</td></tr>")
    sections.append(f"""
<section>
<h2>第 {g['number']} 局 · {NAME[g['number']]}</h2>
<p class="meta">真值 <b>{fmt(settle)}</b>{UNIT[g['number']]}　开盘 {fmt(g['opening'])}　我的盈亏 <b class="{cls}">{fmt(net)}</b>　名次 {g['my_rank']}　积分 {g['my_points']}</p>
<div class="acct">
<span>成交 <b>{n}</b> 笔 / <b>{q}</b> 手</span>
<span>买 {qb} 手 @ {pb:.3f}</span>
<span>卖 {qs} 手 @ {ps:.3f}</span>
<span>价差 {ps-pb:+.3f}</span>
<span>末仓 {final:+d}</span>
<span>毛流入 {fmt(gross)}</span>
<span>还债 {fmt(debt)}</span>
<span>净 <b>{fmt(net)}</b></span>
</div>
<p class="ana">{ANA.get(g['number'],'')}</p>
<table class="trades"><thead><tr><th>#</th><th>轮</th><th>时刻</th><th>方向</th><th>成交</th><th>手</th><th>仓</th><th>已实现</th><th>对手</th></tr></thead>
<tbody>{''.join(tb)}</tbody></table>
</section>""")

H=f"""<!doctype html><html><head><meta charset="utf-8"><title>临渊量化 · 逐局逐笔明细</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#f4efe4;color:#26221f;font-family:"Kaiti SC","Times New Roman",serif;line-height:1.7}}
.wrap{{max-width:1180px;margin:0 auto;padding:36px 28px 70px}}
h1{{font-size:30px;margin:0 0 6px;letter-spacing:.06em}}
.sub{{color:#6b6257;font-size:13px;margin-bottom:26px}}
h2{{font-size:21px;margin:38px 0 8px;padding-left:10px;border-left:4px solid #9c3b32}}
.meta{{font-size:13.5px;color:#5b544a;margin:0 0 10px}}
.acct{{display:flex;flex-wrap:wrap;gap:10px;margin:10px 0 12px;font-size:12.5px}}
.acct span{{background:#fffdf8;border:1px solid #ddd3c0;border-radius:4px;padding:4px 9px}}
.ana{{background:#fffdf8;border-left:3px solid #c2a05a;padding:10px 14px;font-size:13.5px;margin:0 0 14px}}
table{{width:100%;border-collapse:collapse;font-size:12.2px;background:#fffdf8}}
th{{background:#eee5d3;text-align:left;padding:6px 8px;border-bottom:1px solid #d8cfbd;font-weight:400;position:sticky;top:0}}
td{{padding:4px 8px;border-bottom:1px solid #f0e9da}}
tbody tr:nth-child(even) td{{background:#faf6ee}}
.buy{{color:#9c3b32;font-weight:bold}}
.sell{{color:#3f6b63;font-weight:bold}}
.pos{{color:#9c3b32}}
.neg{{color:#3f6b63}}
.mod{{color:#8a6a10}}
td.l{{font-weight:bold}}
.small{{font-size:11.5px;color:#6b6257;margin-top:8px}}
</style></head><body><div class="wrap">
<h1>逐局逐笔明细 · 全部 12 局</h1>
<div class="sub">共 {sum(len(g['trades']) for g in A['games'])} 笔成交 · 每局一张全字段表 · 账目按「毛流入 − 还债 = 净损益」口径</div>
<table><thead><tr><th>局</th><th>主题</th><th>真值</th><th>开盘</th><th>净损益</th><th>名次</th><th>积分</th><th>笔/手</th></tr></thead>
<tbody>{''.join(rows_sum)}</tbody></table>
<p class="small">口径说明：毛流入 = Σ卖出收入 − Σ买入支出；还债 = 末仓 × 真值（正数表示现金流出）；净损益 = 毛流入 − 还债，与权威 my_pnl 逐一核对吻合。末仓为 0 的局，净损益恒等于「卖均 − 买均」× 手数。</p>
{''.join(sections)}
</div></body></html>"""
open("临渊量化_逐局逐笔明细.html","w",encoding="utf-8").write(H)
print("已生成，大小",len(H),"字节，局数",len(A["games"]),"总笔数",sum(len(g['trades']) for g in A['games']))
