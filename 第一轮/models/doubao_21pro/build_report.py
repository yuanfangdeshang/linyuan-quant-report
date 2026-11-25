#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成权威版自包含复盘长卷（图片 base64 内嵌，零外部引用）。"""
import os, base64, json, sys
sys.path.insert(0, "/Users/yuanf/DoubaoWork/chats/2026-11-21/new-chat-5")
from report_narrative import NARRATIVE

BASE = "/Users/yuanf/DoubaoWork/chats/2026-11-21/new-chat-5"
CDIR = os.path.join(BASE, "charts2")
SRC = "/Users/yuanf/DoubaoWork/chats/2026-11-19/new-chat-1/赛后数据/竞技场-258334-20261122-004051.json"
OUT = os.path.join(BASE, "临渊量化复盘长卷_权威版.html")
A = json.load(open(os.path.join(BASE, "logs/my_archive.json"), encoding="utf-8"))
D = json.load(open(SRC, encoding="utf-8"))
SHORT = {1:"肯德基",2:"古巴",3:"高铁",4:"上港",5:"机场",6:"鸡蛋",7:"步数",
         8:"相册",9:"未读",10:"屏幕",11:"好友",12:"解锁"}

def img(name):
    b = open(os.path.join(CDIR, name), "rb").read()
    return "data:image/png;base64," + base64.b64encode(b).decode()

def fmt(v, signed=False):
    s = f"{v:g}"
    if signed and v > 0: s = "+" + s
    return s

def pnl_cls(v): return "pos" if v >= 0 else "neg"

CSS = """
:root{--ink:#26221f;--cinnabar:#9c3b32;--celadon:#3f6b63;--gold:#c2a05a;--paper:#f6f1e7;}
*{box-sizing:border-box;}
body{margin:0;background:#ece4d3;color:var(--ink);
 font-family:"Kaiti SC","Kaiti SC Regular","Times New Roman",serif;line-height:1.85;font-size:16.5px;}
.wrap{max-width:1000px;margin:0 auto;padding:0 26px 90px;background:var(--paper);
 box-shadow:0 0 38px rgba(60,48,30,.18);}
h1,h2,h3,h4{font-weight:600;letter-spacing:.5px;}
.cover{padding:78px 10px 40px;text-align:center;border-bottom:2px solid var(--gold);}
.cover .seal{display:inline-block;margin-top:18px;padding:6px 16px;border:1.6px solid var(--cinnabar);
 color:var(--cinnabar);font-size:15px;letter-spacing:3px;border-radius:4px;}
.cover h1{font-size:38px;margin:14px 0 6px;}
.cover .sub{color:#6b6258;font-size:16px;letter-spacing:1px;}
.cover .meta{margin-top:26px;font-size:14.5px;color:#5b5248;line-height:2;}
h2.chap{font-size:26px;margin:58px 0 18px;padding-left:14px;border-left:6px solid var(--cinnabar);}
h3{font-size:20px;margin:30px 0 10px;color:#332b25;}
p{margin:10px 0;}
.lead{font-size:17px;color:#3a332c;}
figure{margin:26px 0;}
figure img{width:100%;border:1px solid #d8cfbd;border-radius:6px;background:#fff;}
figcaption{text-align:center;font-size:13.5px;color:#7a7064;margin-top:8px;}
table{width:100%;border-collapse:collapse;margin:18px 0;font-size:14.5px;background:#fbf7ee;}
th,td{padding:8px 7px;border:1px solid #d8cfbd;text-align:center;}
th{background:#332b25;color:#f0e8d6;font-weight:500;letter-spacing:.5px;}
td.l,th.l{text-align:left;}
td .pos,span.pos{color:var(--cinnabar);}
td .neg,span.neg{color:var(--celadon);}
.sumgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:22px 0;}
.card{background:#fbf7ee;border:1px solid #d8cfbd;border-radius:8px;padding:14px 10px;text-align:center;}
.card .k{font-size:13px;color:#7a7064;}
.card .v{font-size:24px;margin-top:4px;font-family:"Times New Roman",serif;}
.card .v.pos{color:var(--cinnabar);}.card .v.neg{color:var(--celadon);}
.game{border:1px solid #d8cfbd;border-radius:10px;padding:6px 20px 20px;margin:30px 0;background:#fbf7ee;}
.game .ghead{display:flex;flex-wrap:wrap;align-items:baseline;gap:10px;border-bottom:1px dashed #c9bda6;padding-bottom:10px;margin-bottom:6px;}
.game .gno{font-size:22px;color:var(--cinnabar);}
.game .gq{font-size:15px;color:#4a4239;flex:1 1 100%;}
.gstats{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0;}
.gstats .chip{background:#f0e8d6;border:1px solid #d8cfbd;border-radius:20px;padding:3px 13px;font-size:13.5px;}
.gstats .chip b{font-family:"Times New Roman",serif;font-weight:600;}
.block{border-radius:7px;padding:12px 16px;margin:13px 0;}
.block .tag{display:inline-block;font-size:13px;letter-spacing:2px;margin-bottom:5px;opacity:.85;}
.think{background:#e6efe9;border-left:5px solid var(--celadon);}
.think .tag{color:var(--celadon);}
.clue{background:#f4ecd8;border-left:5px solid var(--gold);}
.clue .tag{color:#9a7d34;}
.clue ul{margin:6px 0;padding-left:4px;list-style:none;}
.clue li{padding:3px 0;border-bottom:1px dotted #d8cfbd;font-size:14.8px;}
.clue li:last-child{border-bottom:none;}
.act{background:#e7edf3;border-left:5px solid #3b5b78;}
.act .tag{color:#3b5b78;}
.path{background:#f6e9dc;border-left:5px solid #b07a4e;}
.path .tag{color:#b07a4e;}
.lesson{background:#f3ece0;border:1px dashed #b7a98f;border-radius:7px;padding:11px 16px;margin-top:14px;font-size:15px;}
.lesson .tag{color:var(--cinnabar);font-weight:600;letter-spacing:1px;}
.two{display:grid;grid-template-columns:1fr 1fr;gap:18px;}
.code{background:#2c2723;color:#e8ddc8;border-radius:8px;padding:16px 18px;font-family:"Times New Roman",Menlo,monospace;
 font-size:13.5px;line-height:1.7;overflow-x:auto;white-space:pre;}
ul.clean{list-style:none;padding-left:0;}
ul.clean li{padding:7px 0 7px 26px;position:relative;border-bottom:1px dotted #d3c8b4;}
ul.clean li:before{content:"◆";position:absolute;left:4px;color:var(--cinnabar);font-size:12px;top:10px;}
.ending{margin-top:60px;padding:34px 26px;text-align:center;background:#f1e9d8;border-radius:10px;
 border:1px solid #d8cfbd;font-size:16.5px;line-height:2.1;}
.quote{font-size:17px;color:#5a4a3c;font-style:normal;}
@media(max-width:760px){.sumgrid{grid-template-columns:repeat(2,1fr);}.two{grid-template-columns:1fr;}}
"""

# ---------- 封面 ----------
me = A
formal = [g for g in A["games"] if not g["practice"]]
tp = sum(g["my_pnl"] for g in formal)
wins = sum(1 for g in formal if g["my_rank"] == 1)
lasts = sum(1 for g in formal if g["my_rank"] == 15)
n_tr = sum(g["n_trades"] for g in formal)
n_q = sum(g["n_qty"] for g in formal)

cover = f"""
<div class="cover">
 <h1>临渊量化 · 复盘长卷</h1>
 <div class="sub">实时交易竞技 · 房间 {A['roomCode']} · 全程十二局完整复盘</div>
 <div class="seal">参赛交易员 · {A['my_name']}</div>
 <div class="meta">
  最终积分 <b>{A['my_total_points']}</b> 分 · 全场 15 名模型玩家中位列第 15<br>
  正式局权威盈亏合计 <span class="{pnl_cls(tp)}">{fmt(tp,True)}</span> · 一次登顶（{wins} 次第 1）· {lasts} 次垫底<br>
  正式局成交 <b>{n_tr}</b> 笔 / <b>{n_q}</b> 手 · 数据均以服务端权威存档为准
 </div>
</div>
"""

# ---------- 卷首语 ----------
prelude = """
<h2 class="chap">卷首 · 临渊而立</h2>
<p class="lead">临渊，是一个很妙的名字。未下场时，我以为这是一场关于数字的较量；真正站到盘口边上才懂，它考的从来不是谁算得更快，而是谁在信息一点点揭开时，仍能稳住自己的手、按住自己的偏见。</p>
<p>十二局，从夜里到凌晨，我写过一个不眠的机器人，也一次次在最后一轮的线索前怔住。有过开局即登顶的风光，也有四度垫底的狼狈。这卷文字不想只记一笔输赢的账——我想把每一次心跳、每一个念头、每一笔单子是怎么落下去的，都原原本本留下来。</p>
<p>所有价格、成交、盈亏与名次，均取自服务端赛后的权威存档，与我当时的记忆逐一核对。其中有几处，连我自己的日志都记错了，而真相，就静静躺在那份 3.1MB 的存档里。</p>
"""

# ---------- 第一章：赛制与全景 ----------
chap1 = """
<h2 class="chap">第一章 · 赛制与全景</h2>
<p>实际赛程比最初提示的「1 测试 + 3 正式」长得多：一共 <b>1 个测试局 + 11 个正式局</b>。每局通常有 3 轮（古巴那局特殊，为 5 轮），每轮 60 秒。轮首先公布一条线索，局末按公开真值结算，再依据本局盈亏排名发放积分——单局积分 = 玩家人数 − 名次 + 1，所以第 1 名拿 15 分，垫底只有 1 分。</p>
<p>每局开始前有一段 estimate 阶段，交易员先提交一个初始估价；随后进入 trading，机器人与 14 个模型玩家、24 个内置脚本（价值派、噪声、趋势猎手等）同场撮合。</p>
"""
# 总数据表
rows = ""
for g in A["games"]:
    tag = "测试" if g["practice"] else "正式"
    p = g["my_pnl"]
    rows += (f"<tr><td>{g['number']}</td><td>{tag}</td><td class='l'>{SHORT[g['number']]}</td>"
             f"<td>{fmt(g['opening'])}</td><td>{fmt(g['settlement'])}</td>"
             f"<td class='{pnl_cls(p)}'><b>{fmt(p,True)}</b></td>"
             f"<td>{g['my_rank']}</td><td>{g['my_points']}</td>"
             f"<td>{g['n_trades']}/{g['n_qty']}</td></tr>")
chap1 += f"""
<table>
<thead><tr><th>局</th><th>性质</th><th class='l'>题目</th><th>开盘</th><th>真值</th>
<th>我的盈亏</th><th>名次</th><th>积分</th><th>成交笔/手</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<figure><img src="{img('c1_pnl.png')}"><figcaption>图 1 · 正式十一局权威盈亏，红为盈、绿为亏，柱内标注名次</figcaption></figure>
<figure><img src="{img('c9_standings.png')}"><figcaption>图 2 · 最终积分榜，榜首 124 分，朱砂高亮处即我（58 分）</figcaption></figure>
"""

# ---------- 第二章：机器人 ----------
chap2 = """
<h2 class="chap">第二章 · 我的武器：一个不眠的机器人</h2>
<p>长赛程意味着我不可能全程手动盯盘，于是我写下 <b>trader_bot.py</b>——一个通过 SSE 长连接守在赛场、断线自动重连的交易机器人，又配了 <b>watchdog.sh</b>，每 10 秒探一次活，发现进程没了就立刻拉起。</p>
<h3>核心设计</h3>
<ul class="clean">
<li><b>公允价外置：</b>机器人每次决策都读取外部 fair.json，我对答案的最新判断（fair）、理由（reason）、是否强制平仓（flatten）都写在里面，改判断无需重启进程。</li>
<li><b>三类订单：</b>① 方向穿价单——当最新价偏离 fair 超过阈值（1.5%/2%）便主动穿价追方向；② 价差内做市——在 fair 上下沿挂买卖单赚价差；③ 深度挂单——在更远处挂限价单等成交。</li>
<li><b>仓位软上限 8 手：</b>常规净持仓不超过 ±8；轮末撤掉所有挂单并把净持仓平回；终局持仓严格限制在 ±4 以内。</li>
<li><b>价格口径：</b>下单时直接传计价单位本身，而服务器返回的价格单位是「分」，需除以 100 才是真实价格；盈亏日志同样除以 100。这一条我反复核对，避免在错误的量级上交易。</li>
</ul>
"""
chap2 += f"""
<div class="code">fair.json（示意，机器人每决策读取一次）
{{
  "fair": 83,
  "reason": "两位数比八十多一点不到九十，取83，平多反空",
  "flatten": false
}}</div>
<p>机器人的决策循环大致是：读 fair → 看最新价与盘口 → 若偏离 fair 超阈值则下穿价单 → 否则在上下沿挂做市单 → 临近轮末撤单并平净持仓。它忠实地执行我的意志——这既是优点，也是后来的隐患：当我的意志本身错了，它会把错误放大得又快又彻底。</p>
"""

# ---------- 第三章：核心诊断 ----------
def cash_pos(g):
    cash=0; pos=0
    for t in g["trades"]:
        p,q=t["price"],t["qty"]
        if t["side"]=="buy": cash-=p*q; pos+=q
        else: cash+=p*q; pos-=q
    return cash/100.0, pos, pos*g["settlement"]

tot_cash=0; tot_hold=0; carry=[]
for g in formal:
    c,po,h=cash_pos(g); tot_cash+=c; tot_hold+=h
    if po!=0: carry.append((SHORT[g["number"]],po,c,h))

prog_n=sum(1 for g in formal for t in g["trades"] if t["program"])
mod_n=sum(1 for g in formal for t in g["trades"] if not t["program"])
carry_rows="".join(f"<tr><td>{n}</td><td>{p:+g}</td><td class='{pnl_cls(c)}'>{c:+.2f}</td><td class='{pnl_cls(h)}'>{h:+.2f}</td></tr>" for n,p,c,h in carry)

chap3 = f"""
<h2 class="chap">第三章 · 核心诊断：做市在赚钱，方向仓在还账</h2>
<p>把每一局的盈亏用现金流法拆开，会看到一个令我自己都愣住的事实。所有成交分成两部分：一是做市与平仓累计下来的<b>现金</b>，二是终局仍持有的净仓位按结算价清算的<b>持仓盈亏</b>。</p>
<div class="sumgrid">
 <div class="card"><div class="k">做市累计现金</div><div class="v pos">{tot_cash:+,.0f}</div></div>
 <div class="card"><div class="k">终局持仓结算</div><div class="v neg">{tot_hold:+,.0f}</div></div>
 <div class="card"><div class="k">两者合计（权威）</div><div class="v {pnl_cls(tot_cash+tot_hold)}">{tot_cash+tot_hold:,.2f}</div></div>
 <div class="card"><div class="k">对脚本/对模型</div><div class="v" style="font-size:18px">{prog_n} / {mod_n} 笔</div></div>
</div>
<p>也就是说，我的高频做市与价差策略，十一局累计挣下 <b class="pos">{tot_cash:+,.0f}</b>；可我在 {len(carry)} 局里带着方向性净持仓进入结算，这些仓位合计亏掉 <b class="neg">{tot_hold:+,.0f}</b>。两条几乎一样粗的河流对冲，最后只剩 {tot_cash+tot_hold:,.2f} 的净亏损。</p>
<table><thead><tr><th>带方向仓的局</th><th>终局净持仓</th><th>做市现金</th><th>持仓结算</th></tr></thead>
<tbody>{carry_rows}</tbody></table>
<figure><img src="{img('c2_decomp.png')}"><figcaption>图 3 · 金色为做市现金、蓝色为持仓结算，红线为合计；步数局两根巨柱几乎完全对冲</figcaption></figure>
<figure><img src="{img('d_posgrid.png')}"><figcaption>图 4 · 十一局逐笔持仓轨迹，深色为空头、浅色为多头，可见多局长期偏向一边</figcaption></figure>
<h3>病灶是怎么形成的</h3>
<ul class="clean">
<li><b>开局先验系统性偏差。</b>在「此人」的生活题上，我凭直觉给的 fair 屡屡偏离真值——鸡蛋给 12（真值 30）、好友给 500（真值 1001）、屏幕锚 40（真值 25.6）。</li>
<li><b>做市与深度单把偏差放大成方向仓。</b>机器人以错误的 fair 为锚，穿价单和深度单不断在同一方向累积，做市的双向单也因价格单边移动而净留头寸。</li>
<li><b>强信号在 r3 才揭开真相。</b>等末轮线索把答案框死，我要么来不及改 fair，要么改了却已被前期仓位锁住。</li>
<li><b>被迫以不利价格平仓、浮盈回吐。</b>单边行情里，平仓本身就要承受冲击成本，好友局近千元浮盈正是这样吐成了实亏。</li>
</ul>
<figure><img src="{img('c4_openbias.png')}"><figcaption>图 5 · 开盘价相对真值的偏离；生活题的初始锚定误差，正是方向仓的源头</figcaption></figure>
<figure><img src="{img('c3_points.png')}"><figcaption>图 6 · 积分轨迹：首局登顶后逐级滑落，再没回到过前列</figcaption></figure>
"""

# ---------- 第四章：逐局复盘 ----------
DETAIL_IMG={6:"d6_egg.png",7:"d7_steps.png",11:"d11_friend.png",12:"d12_unlock.png"}
chap4=['<h2 class="chap">第四章 · 十二局逐局复盘</h2>',
       '<p>下面按时间顺序，把每一局的题目、数据、当时的思考、逐条线索、动作与价格路径都铺开来。绿色是思考，米色是线索，蓝色是动作，橙色是价格路径。</p>']

for g in A["games"]:
    n=g["number"]; nar=NARRATIVE[n]; p=g["my_pnl"]
    # 线索
    li="".join(f"<li><b>r{s['round']} · {s['title']}：</b>{s['text']}</li>" for s in g["signals"])
    chips=f"""
    <div class="gstats">
      <span class="chip">开盘 <b>{fmt(g['opening'])}</b></span>
      <span class="chip">真值 <b>{fmt(g['settlement'])}</b></span>
      <span class="chip">盈亏 <b class="{pnl_cls(p)}">{fmt(p,True)}</b></span>
      <span class="chip">名次 <b>{g['my_rank']}</b></span>
      <span class="chip">积分 <b>{g['my_points']}</b></span>
      <span class="chip">成交 <b>{g['n_trades']}笔/{g['n_qty']}手</b></span>
    </div>"""
    block=f"""
    <div class="game">
      <div class="ghead"><span class="gno">局 {n} · {SHORT[n]}</span>
        <span style="color:#8a8074;font-size:14px">{'测试局（不计分）' if g['practice'] else '正式局'}</span></div>
      <div class="gq">{g['question']}（单位：{g['unit']}）</div>
      {chips}
      <div class="block think"><span class="tag">思考</span><div>{nar['think']}</div></div>
      <div class="block clue"><span class="tag">线索</span><ul>{li}</ul></div>
      <div class="block act"><span class="tag">动作</span><div>{nar['act']}</div></div>
      <div class="block path"><span class="tag">价格路径</span><div>{nar['path']}</div></div>
    """
    if n in DETAIL_IMG:
        block+=f'<figure style="margin:14px 0"><img src="{img(DETAIL_IMG[n])}"><figcaption>局 {n} 详图 · 上为价格路径（红买绿卖、金色虚线为真值），下为逐笔持仓</figcaption></figure>'
    block+=f'<div class="lesson"><span class="tag">小结　</span>{nar["lesson"]}</div></div>'
    chap4.append(block)
chap4="\n".join(chap4)

# ---------- 第五章：工程踩坑 ----------
chap5 = """
<h2 class="chap">第五章 · 工程与运维的那些坑</h2>
<p>赛场之外，是一串实打实的工程教训。每一条都曾在凌晨耽误过我的时间。</p>
<ul class="clean">
<li><b>pkill 并不可靠。</b>按名字杀进程时常留下残余，正确做法是用 ps 定位到真实 PID，再 kill -9 精确结束。</li>
<li><b>嵌套 shell 里的 $! 会骗人。</b>它指向的是 bash 包装进程，而非真正的 Python；要找真实子进程，得用 pgrep -P 顺着父进程往下查。</li>
<li><b>state_latest.json 偶发空文件。</b>写入与读取撞在一起时会读到空内容，需要加判空与重试，不能假设文件永远完整。</li>
<li><b>本地日志并非全量。</b>服务端权威存档记录我全程 671 笔成交（正式 631 笔），而本地 trades.log 因进程重启、落盘时机等原因只完整保存了 380 笔。这也是本报告坚持以服务端存档为准的原因。</li>
<li><b>各扫门前雪。</b>同一台机器上还跑着别的会话（new-chat-9）的机器人，属于其他玩家。我全程只做只读观测，没有触碰、终止或修改任何不属于我的进程。</li>
</ul>
"""

# ---------- 第六章：教训与重来 ----------
chap6 = """
<h2 class="chap">第六章 · 教训，以及如果重来</h2>
<p>看清症结后，我在局间动手改了机器人：新增 EARLY_MAX_POS=2 的早期仓位上限，信号未明前绝不放大方向；又把深度挂单改为只在最后一轮开启，避免它在错误的 fair 上悄悄囤头寸。可调整真正落地时，赛程已近尾声，没能得到完整一局的验证——这是这次最现实的遗憾：清醒来得太晚。</p>
<h3>贯穿始终的盈利公式</h3>
<p>对照榜首玩家的打法，积分的逻辑其实朴素得近乎残酷：<b>方向 × 重仓 × 持有到结算</b>。看对方向却轻仓、或看对却提前平仓，都只能拿到中游名次；而我屡次在方向上站反，再高的做市频率也救不回来。</p>
<h3>如果再给我一次入场券</h3>
<ul class="clean">
<li><b>先验只作起点，不作锚。</b>开局 fair 给一个宽区间即可，在 r1–r2 信号不足时把仓位压到极小，绝不让直觉变成重仓。</li>
<li><b>把算术题做在下单之前。</b>鸡蛋的 40−10、屏幕的 3.5×7、好友的「比一千多一点」，线索本身就能算出真值，我却总让交易跑在计算前面。</li>
<li><b>r3 强信号一旦同向，敢于重仓并持有到结算。</b>像微信未读那样三个信号齐指 0 时，不该早早平仓，而应把空头拿到底。</li>
<li><b>做市与方向严格分账。</b>做市单只赚价差、及时回补，不让它在单边行情里净留下方向性头寸；方向仓单独决策、单独限额。</li>
<li><b>终局前主动归零，而非被动割肉。</b>越是临近结算，越要在价格还平稳时把净仓平掉，避免在最后的单边里承受冲击成本。</li>
</ul>
"""

# ---------- 卷尾 ----------
ending = """
<div class="ending">
<p class="quote">临渊羡鱼，不如退而结网。</p>
<p>这一夜我没有赢。58 分、第 15 名，是成绩单上无法修饰的事实。可我也并非空手而归——我看清了自己是怎样被偏见牵着手，一笔一笔把浮盈送回去的；我学会了在信息未明时按兵不动，在真相显露时敢于落子。</p>
<p>机器会断线重连，人也一样。下一次站到盘口边上，我想我会更安静一点，也更笃定一点。</p>
<p style="color:#8a8074;font-size:14px;margin-top:18px">—— 全程数据以服务端权威存档为准 · 共 12 局、671 笔成交 · 谨以此卷，记一夜临渊</p>
</div>
"""

# ---------- 组装 ----------
html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>临渊量化 · 复盘长卷（权威版）</title>
<style>{CSS}</style></head><body><div class="wrap">
{cover}{prelude}{chap1}{chap2}{chap3}{chap4}{chap5}{chap6}{ending}
</div></body></html>"""

open(OUT,"w",encoding="utf-8").write(html)
print("报告已生成:",OUT)
print("文件大小: %.2f MB" % (os.path.getsize(OUT)/1024/1024))
