#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild the post-match review report from authoritative server-side export."""
import json, base64, os, html

BASE = os.path.dirname(os.path.abspath(__file__))
A = json.load(open(os.path.join(BASE, "authoritative.json")))
G = {g["number"]: g for g in A["games"]}
ME = A["me_name"]

def b64(name):
    p = os.path.join(BASE, "charts2", name)
    return base64.b64encode(open(p, "rb").read()).decode()

CH = {k: b64(v) for k, v in {
    "points": "01_points.png", "pnl": "02_pnl.png", "rank": "03_rank.png",
    "stand": "04_standings.png", "open": "05_open_vs_settle.png",
    "path": "06_price_path.png", "est": "07_estimate_error.png",
}.items()}

# ---- per-game authentic narrative (from match journal, facts cross-checked vs archive) ----
N = {
1: dict(
 think="先验：百胜中国 KFC 全国门店约 1.1 万家上下，上海 2480 万人口按一线密度反推区间 550–750，点估 680。开局即意识到：<b>开盘价是房间共识的读数，不是真值</b>；交易利润来自共识与真值的偏差，而不是猜开盘方向。",
 clue="R1 百胜中国 2025 总收入 117.97 亿美元（背景）；R2 必胜客中国大陆 4168 家（干扰项）；R3 上海麦当劳约 600 家（可比锚）→ 一线市场 KFC∶McD ≈ 1.17，反推 ≈ 700。",
 act="全程<b>零挂单、零成交、净持仓恒为 0</b>。盘面被麦当劳锚带高至 800.01，真值 700，共识在 R3 后明显超调约 14%，这波反向收租的窗口我没有出手。估价 680，偏 −2.9%。",
 lesson="确认两条底层认知：① 结算价是固定的公开真值；② 开盘价是强先验但非真值。可比锚出现后趋势猎手会追涨，价格高出后验 10%+ 时应反向做空收租；干扰品牌不能纳入估值。"),
2: dict(
 think="无信号先验下，按“中位国家面积”粗估 4.00 万 km²；排名类题目必须等线索锁定候选国，单点先验几乎没有信息含量。",
 clue="R1 非洲总面积 3020 万 km²（背景/干扰）；R2 该国人口约 975 万；R3 海岸线 5746 km；R4 世界第 50 大国西班牙 50.6 万 km²（参照锚）；R5 直接点名古巴。",
 act="全程空仓。开盘 11.32，R2/R3 冲高 11.39，R4 回落 11.09，末轮 10.64；真值 10.99。估价 4.00 严重偏低（−63.6%），后验在 R5 点名后才贴近 11.09。",
 lesson="正式局轮次不固定（本局 5 轮，其余 3 轮），以 state.maxRound 为准；R5 点名是决定性信号，窗口只有十几秒，候选锁定后应提前挂好双向预备单。盘口薄、极端价位有陈旧挂单，噪声尖峰不可追。"),
3: dict(
 think="先验：2023 年底高铁约 4.5 万 km，2024 新增约 2 千 km，估 4.8 万 km。开盘 4.80 正中，方向正确。",
 clue="R1 全国铁路总里程 16.2 万 km；R2 高铁约占三成；R3 2024 投产新线超 3000 km、高铁过半。",
 act="空仓中性。盘面 4.74 → 4.84 → 4.76 围绕真值 4.80，偏离不足 1%，没有可吃的差价。估价 4.80 命中（误差 0.0%）。",
 lesson="占比类线索只给区间锚：16.2×三成 ≈ 4.86 是近似推导，真值以官方存量口径 4.8 为准。估对方向不等于有交易价值；窄幅震荡里反复 churn 只会磨损，空仓在这类题上是合理克制。"),
4: dict(
 think="先验：2023 年 4916 万 TEU，2024 同比约 +5%，估 5150 万 TEU。开盘 5150.60。",
 clue="R1 连续多年全球第一；R2 洋山港区贡献四成以上；R3 同比增长约 5%。",
 act="空仓。盘面 5183.49 → 5141.50 → 5155.50，偏离 <0.7%；价格一度冲到 5183.49（+0.64%）想做空，但时机错过。估价 5150 命中（误差 0.0%）。",
 lesson="增速线索要乘上一年存量基数，基数本身靠先验；薄盘 + 窄偏离不值得交差价。执行速度是硬约束：60 秒一轮，分析与取盘慢一步，窗口就关上了。"),
5: dict(
 think="先验：2023 年底 259 个，2024 新增约 10，估 270；市场开盘 263，比我低 7。我一度判断“我比市场更准”。",
 clue="R1 覆盖 30 多个省级行政区；R2 千万级机场约 40 个；R3 2024 新投产运输机场 3 个 → 2023 基线 + 3 ≈ 262。",
 act="空仓。盘面 264.02 → 262.21 → 262.40 围绕 263；R3 后修正后验 262，贴近真值。估价 270 偏高 +2.7%。",
 lesson="最典型的一课：事实题里开盘价 263 本身就在真值方向，私有记忆（270）反而跑偏；存量增量线索要乘上一年基数，基数记忆偏差是主要误差源。"),
6: dict(
 think="对“冰箱鸡蛋数”没有任何先验信息，估价阶段按中性值 10 枚提交。",
 clue="R1 上周日买了两盒、之后没有再买；R2 一盒 10 枚装、一盒 30 枚家庭装；R3 每天早上煎 2 枚、连续吃了五天，除此之外没有用过鸡蛋。算术：10 + 30 − 2×5 = 30。",
 act="空仓。盘面 23.27 → 26.40 → 29.70 单边上行至真值 30；算术闭合后，我的分析 + 取盘周期约 10–15 秒，赶在末轮窗口关闭前没挂上单。估价 10（偏低 −66.7%），但后验精确命中 30。",
 lesson="算术题答案一旦闭合，应在 R3 后立刻挂预备单（双向各一笔贴近后验），不等二次取盘。本局是我正式局最佳名次：<b>第 5 名，11 分</b>。"),
7: dict(
 think="中性先验估 7000 步；开盘 8000。",
 clue="R1 周六无体育课、也没有跑步骑行；R2 步行往返图书馆与宿舍、乘过一次地铁、没打车；R3 四位数、千位是 8、百位是 4 → 8400–8499。",
 act="空仓。盘面 8040.16 → 7952 → 8599；R3 被追涨推到 8599，高出区间上限约 1.2%，本应反向做空 2–3 手，仍因取盘慢错过窗口。后验区间判断正确；估价 7000 偏低 −17.4%。",
 lesson="确认关键模式：数位/锚点线索落地后，趋势猎手会把价格推出已披露区间上沿，反向收租是正期望。流程改进：快照直读本地 state.json，不再每次重连 SSE 占用 5–8 秒。"),
8: dict(
 think="中性先验估 30 张；开盘 15。",
 clue="R1 没出远门、在外不足 3 小时；R2 同一台手机拍、一半以上是同一景物连拍；R3 个位数且是质数 → {2, 3, 5, 7}。",
 act="空仓。盘面 14.70 → 14.87 → 6.83；R3 后先错杀到 5.07，末段修复到 6.83。我在 5.07 无法区分 2/3/5/7，按期望为负不赌方向。估价 30（高估 +328.6%）；真值 7。",
 lesson="范围类线索（质数/数位）若无法进一步收窄到单点，不赌方向；重定价初期的极端价往往是噪声，不追。低位买点就这样被错过。"),
9: dict(
 think="中性先验估 30 条；开盘 36.63。",
 clue="R1 看到红点就点掉、从不在列表留未读；R2 过去 24 小时没静音、提示音一响就看一眼；R3 数字更靠近区间下界。",
 act="空仓。盘面 35.93 → 15.54 → 15.85，收盘相对真值 0 严重高估；这是全场最大的错位，我却把“从不留未读”当成模糊定性，没有在 R2 后锚 0 做空。估价 30；真值 0，误差不可比。",
 lesson="重大教训：R1 的习惯陈述是字面事实——“从不留未读”即未读 = 0；R3“靠近下界”的下界就是 0。零状态题一旦出现“从不 / 全部 / 没有”类绝对表述，后验直接锚 0，市价越高越应做空。"),
10: dict(
 think="先验日均 5–6 小时 ×7，估 40 小时；开盘 40 正中。",
 clue="R1 周六无网课、白天在图书馆、晚上在住处；R2 学习 + 通讯为主、娱乐不足两成；R3 折算每天 3.5–4 小时 → 周总时长 24.5–28.0 小时。",
 act="空仓。盘面 39.27 → 40.08 → 26.38；R3 后由 38.7 快速收敛到 26.4，错位在我出手前已经填平。估价 40 高估 +56.2%；真值 25.6，区间命中偏下沿。",
 lesson="区间推导题（日均 × 天数）要先把上下界算出来；市价落入区间内即不赌方向。开盘价 = 我的估价 = 市场共识，三者全错，是个人数据题的典型坑。"),
11: dict(
 think="先验估 400 人，严重低估了一个数量级；开盘 1036.66。",
 clue="R1 只增不删；R2 约 1/4 是历届同学，其余是社团/实习同事/家人；R3 四位数、比一千多一点点、不到一千一 → 1000–1100。",
 act="空仓。盘面 1061.63 → 1061.34 → 1049.36；“多一点点”= 1001，贴近下界；市价在区间中部偏上（高估约 48），我在区间中部犹豫未做空。估价 400 偏低 −60.0%。",
 lesson="措辞“多一点点 / 接近下界”应直接把后验钉在 X+1～X+5，而不是区间中位；市价在区间中位偏上即可做空。"),
12: dict(
 think="中性先验估 100 次；开盘 100。",
 clue="R1 周五上午两节课、下午图书馆、晚上住处；R2 每次解锁只做一件事、做完就锁屏；R3 两位数、比八十多一点、不到九十 → 80–90。",
 act="空仓。盘面 100.20 → 101.91 → 85.68；R3 十几秒内从 101.9 收敛到 83.5，错位填平极快，旧快照会误导；87 落在区间上半段，区间中部不做空。估价 100 偏高 +14.9%。",
 lesson="R3 收敛以秒计，决策窗口极短；“多一点”不必过度偏下界。收官局第 6 名、10 分。"),
}

SHORT = {1:"肯德基",2:"104国",3:"高铁",4:"上海港",5:"机场",6:"鸡蛋",7:"步数",8:"照片",9:"未读",10:"屏幕",11:"好友",12:"解锁"}

def fmt(x):
    if x is None: return "—"
    if abs(x - round(x)) < 1e-9: return str(int(round(x)))
    return f"{x:g}"

def est_err(g):
    if g["settle"] == 0 or g["my_estimate"] is None: return None
    return (g["my_estimate"] - g["settle"]) / g["settle"] * 100

# ---------- build per-game cards ----------
cards = []
for n in range(1, 13):
    g = G[n]; v = N[n]
    path = " → ".join(fmt(h["price"]) for h in g["history"]) + f" → {fmt(g['settle'])}"
    rounds = " · ".join(f"R{s['round']} {html.escape(s['title'])}：{html.escape(s['text'])}"
                        for s in g["signals"])
    tag = '<span class="tag gray">测试局 · 不计分</span>' if g["practice"] else (
        f'<span class="tag gold">正式 {n-1}</span>')
    err = est_err(g)
    err_txt = "真值为 0，误差不可比" if err is None else (
        f"估价误差 {err:+.1f}%")
    win = g["winner_name"]; win_pnl = g["winner_pnl"]
    win_txt = ""
    if win_pnl is not None:
        win_txt = f"本局冠军 {html.escape(win)}，服务器口径盈亏 {win_pnl} 分（≈{win_pnl/100:.2f} 计价单位）。"
    cards.append(f"""
  <h3>局 {n}（{'测试' if g['practice'] else '正式'+str(n-1)}）· {html.escape(g['question'])} {tag}</h3>
  <div class="card">
    <p><b>开盘 {fmt(g['open'])} · 结算真值 {fmt(g['settle'])}{('（'+g['resolution_note']+'）') if g['resolution_note'] else ''}</b>
       · 价格路径：<span class="num">{path}</span></p>
    <div class="think"><b>我的思考：</b>{v['think']}</div>
    <div class="clue"><b>线索链：</b>{rounds}</div>
    <div class="act"><b>交易动作：</b>{v['act']} {win_txt}</div>
    <p><b>本局排位：</b>第 <span class="num">{g['my_rank']}</span> / 15，积分 <span class="num">{g['my_points']}</span>，
       本人盈亏 <span class="num">{g['my_pnl']}</span>，成交 <span class="num">{g['my_trades']}</span> 笔；{err_txt}。</p>
    <p><b>得失与迭代：</b>{v['lesson']}</p>
  </div>""")

# ---------- standings table ----------
rows = []
for s in sorted(A["standings"], key=lambda x: (-x["points"], x["rank"])):
    me = s["name"] == ME
    rows.append(
        f'<tr{" style=\"background:#fdf3e3\"" if me else ""}>'
        f'<td class="num">{"<b>"+str(s["rank"])+"</b>" if me else s["rank"]}</td>'
        f'<td>{"<b>"+html.escape(s["name"])+"（我）</b>" if me else html.escape(s["name"])}</td>'
        f'<td class="num">{"<b>"+str(s["points"])+"</b>" if me else s["points"]}</td>'
        f'<td class="num">{s["wins"]}</td><td class="num">{s["seconds"]}</td></tr>')

tot_vol = sum(h["volume"] for g in A["games"] for h in g["history"])
tot_ord = sum(h["orders"] for g in A["games"] for h in g["history"])

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>临渊量化·实时交易竞技场 赛后详细复盘（权威重建版）</title>
<style>
  :root {{ --red:#c0392b; --blue:#2e86de; --orange:#e67e22; --ink:#2c3e50; --muted:#7f8c8d; --bg:#faf8f5; --card:#ffffff; --line:#e8e2d8; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font-family:"Kaiti SC","KaiTi","STKaiti",serif; line-height:1.78; }}
  .wrap {{ max-width:1000px; margin:0 auto; padding:42px 24px 90px; }}
  h1 {{ font-size:30px; margin:0 0 6px; letter-spacing:1px; }}
  h2 {{ font-size:22px; margin:46px 0 14px; padding-left:12px; border-left:5px solid var(--orange); }}
  h3 {{ font-size:17px; margin:28px 0 10px; color:#1a1a1a; }}
  .sub {{ color:var(--muted); font-size:14px; margin-bottom:8px; }}
  .num {{ font-family:"Times New Roman",serif; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:18px 22px; margin:14px 0; box-shadow:0 1px 3px rgba(0,0,0,.04); }}
  table {{ border-collapse:collapse; width:100%; font-size:13.5px; margin:12px 0; background:#fff; }}
  th,td {{ border:1px solid var(--line); padding:7px 9px; text-align:left; vertical-align:top; }}
  th {{ background:#f3efe7; font-weight:600; }}
  td.num, th.num {{ text-align:right; font-family:"Times New Roman",serif; }}
  .win {{ color:var(--red); font-weight:bold; }}
  .flat {{ color:var(--muted); }}
  .tag {{ display:inline-block; padding:1px 9px; border-radius:12px; font-size:12px; margin-right:6px; }}
  .tag.gold {{ background:#fdebd0; color:#b9770e; }}
  .tag.blue {{ background:#d6eaf8; color:var(--blue); }}
  .tag.gray {{ background:#eceff1; color:#607d8b; }}
  .clue {{ background:#fdfbf7; border-left:3px solid #d4c5a9; padding:6px 12px; margin:6px 0; font-size:14px; }}
  .think {{ background:#f4f9f4; border-left:3px solid #7cb342; padding:8px 14px; margin:8px 0; font-size:14.5px; }}
  .act {{ background:#f4f7fb; border-left:3px solid #5b8dd9; padding:6px 12px; margin:6px 0; font-size:13.5px; }}
  img.chart {{ width:100%; border:1px solid var(--line); border-radius:8px; margin:10px 0; }}
  .summary-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(155px,1fr)); gap:12px; margin:18px 0; }}
  .metric {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; text-align:center; }}
  .metric .v {{ font-size:25px; font-weight:bold; font-family:"Times New Roman",serif; }}
  .metric .k {{ font-size:13px; color:var(--muted); margin-top:2px; }}
  .lesson {{ counter-reset:li; list-style:none; padding:0; }}
  .lesson li {{ position:relative; padding:8px 0 8px 34px; border-bottom:1px dashed var(--line); }}
  .lesson li::before {{ counter-increment:li; content:counter(li); position:absolute; left:0; top:9px; width:22px; height:22px; border-radius:50%; background:var(--orange); color:#fff; text-align:center; line-height:22px; font-size:13px; font-family:"Times New Roman",serif; }}
  .footnote {{ color:var(--muted); font-size:12.5px; margin-top:32px; }}
  .hl {{ background:linear-gradient(transparent 60%, #fef3c7 60%); font-weight:bold; }}
</style></head>
<body><div class="wrap">

  <h1>临渊量化 · 实时交易竞技场</h1>
  <div class="sub">赛后详细复盘报告（服务端权威存档重建版）· 房间 258334 · 参赛交易员「{html.escape(ME)}」</div>

  <div class="summary-grid">
    <div class="metric"><div class="v" style="color:var(--orange)">80</div><div class="k">最终总积分</div></div>
    <div class="metric"><div class="v">第 11 / 15</div><div class="k">最终排名（三人并列 80）</div></div>
    <div class="metric"><div class="v" style="color:var(--blue)">0</div><div class="k">成交笔数 / 挂单笔数</div></div>
    <div class="metric"><div class="v">12</div><div class="k">总局数（1 测试 + 11 正式）</div></div>
    <div class="metric"><div class="v">第 5 → 第 12</div><div class="k">单局最佳 / 最差名次</div></div>
  </div>

  <div class="card">
    本报告基于服务端权威存档 <span class="num">竞技场-258334-20261122-004051.json</span>（12 局、全场累计 <span class="num">{tot_vol}</span> 手成交、<span class="num">{tot_ord}</span> 笔挂单）逐局重建，包含<b>全部线索原文、每轮价格路径、本人逐局排位与盈亏、完整最终排名</b>。核心结论先行：<span class="hl">本人全程零挂单、零成交、净持仓恒为 0，盈亏恒为 0，仅靠中性排位累计 80 分；结算价 = 公开真值；盈利公式 =「方向 × 重仓 × 持仓到结算」；个人数据题的开盘价往往严重失真，唯一可靠的是第三条「数量特征」线索。</span>
  </div>

  <h2>一、赛制与规则</h2>
  <div class="card">
    <p>「临渊量化」实时交易竞技场，房间号 <span class="num">258334</span>，同场 <b>15 个真人/模型玩家</b> + <b>24 个脚本玩家</b>（价值派、噪声、流动性、趋势猎手、均值回归）。题目为事实/估算类，每局在事实题与「此人」个人场景题之间切换。</p>
    <table>
      <tr><th>阶段</th><th class="num">时长</th><th>说明</th></tr>
      <tr><td>估价阶段</td><td class="num">60s</td><td>全体提交估价；<b>开盘价 = 全场估价中位数</b>。</td></tr>
      <tr><td>交易轮</td><td class="num">每轮 60s</td><td>每轮开始公布 1 条线索（局 2 有 5 轮，其余 3 轮）；连续撮合、禁止自成交、净持仓上限 ±10 手。</td></tr>
      <tr><td>结算</td><td class="num">局末</td><td><b>按公开真值结算</b>：单局盈亏 = 已实现盈亏 + 净持仓 ×（结算价 − 均价成本）。</td></tr>
    </table>
    <p>积分规则：单局积分 = 总人数 − 名次 + 1。价格单位：<b>成交价、答案、盈亏均为整数「分」，显示时除以 100</b>；比赛积分直接读取 points，不除以 100。</p>
  </div>

  <h2>二、策略演进：全局思考过程</h2>
  <div class="card">
    <p>12 局里，我的认知经历了 <b>8 次关键迭代</b>，每一次都对应盘面观察或一次错过的窗口：</p>
    <ol class="lesson">
      <li><b>开盘价是房间共识读数（测试局）</b>：开盘价 = 全场估价中位数，是“这屋子怎么想”的唯一直接读数，不是真值；交易利润来自共识与真值的偏差，而不是猜开盘方向。</li>
      <li><b>结算价是固定公开真值（测试局）</b>：局末持仓按真值全额结算，提前平仓只算已实现；临近收盘应把仓位收敛到后验把握最高的方向，而不是赌最后一轮信号。</li>
      <li><b>脚本行为画像（测试局）</b>：价值派按各自锚偏离 2% 推 2 手；趋势猎手追 0.4% 短期动量；均值回归反向 1.2%；流动性程序双边挂单。盘口宽度与方向可据此解读。</li>
      <li><b>线索三分法（G1 后）</b>：先分清线索是「背景 / 干扰 / 可比锚」（必胜客是干扰，麦当劳是可比锚）；占比、增量类线索只给区间锚，不能直接相乘当答案。</li>
      <li><b>个人数据题不可信开盘（G6 起）</b>：未读消息开 36.63 而真值 0、屏幕时长开 40 而真值 25.6、照片开 15 而真值 7；开盘价系统性失真，只能信 R3 的数量范围。</li>
      <li><b>场景题三类结局（G9 后补全）</b>：① 算术闭合（鸡蛋、步数）；② 数位/质数收窄（照片）；③ 零状态字面归零（未读）。第三类一旦出现“从不 / 全部 / 没有”类绝对表述，后验直接锚 0。</li>
      <li><b>执行速度是硬约束（G6/G7）</b>：60 秒一轮，R3 落地后我的分析 + 取盘约 10–15 秒，多个窗口在挂单前已填平；应直读本地快照、提前挂双向预备单。</li>
      <li><b>估值口径校准（G3/G5/G11）</b>：真值以题目数据集为准；存量增量线索要乘上一年基数；私有记忆先验在事实题上多次跑偏，应贴市场共识，只在信号给足时偏离。</li>
    </ol>
  </div>

  <h2>三、逐局详细复盘</h2>
  {''.join(cards)}

  <h2>四、数据可视化</h2>
  <div class="card">
    <h3 style="margin-top:0">① 本人累计积分走势</h3>
    <img class="chart" src="data:image/png;base64,{CH['points']}" alt="累计积分">
    <p>积分从 G1 测试局 0 分缓步爬到终值 80：G6（鸡蛋）与 G10/G12（屏幕、解锁）三次拿到 10 分上下的高分，是累计分的主要来源；G5、G9 两局仅 4 分，是拖低排名的深坑。全程没有单局爆发——空仓策略的排位分天然是“中游水位”。</p>
  </div>
  <div class="card">
    <h3 style="margin-top:0">② 各局盈亏：本人 vs 单局冠军</h3>
    <img class="chart" src="data:image/png;base64,{CH['pnl']}" alt="各局盈亏">
    <p>蓝柱是本人盈亏：12 局全部为 0——零成交意味着既没有方向错误带来的亏损，也没有任何结算差收益。灰柱是单局冠军盈亏，全部来自“方向判对 × 满仓 ±10 × 持仓到结算”：步数局 +4120.00、好友局 +4463.54、上海港 +811.94，量级差距一目了然。</p>
  </div>
  <div class="card">
    <h3 style="margin-top:0">③ 本人单局名次走势</h3>
    <img class="chart" src="data:image/png;base64,{CH['rank']}" alt="名次走势">
    <p>名次在第 5 到第 12 之间波动：最佳是 G6 鸡蛋（第 5，11 分），G10/G12 第 6，G7 第 7；最差是 G5 机场与 G9 未读（第 12，各 4 分）。空仓者的名次完全取决于“有多少玩家方向做错被结算淘汰”，自身没有调控手段。</p>
  </div>
  <div class="card">
    <h3 style="margin-top:0">④ 全场最终积分排名</h3>
    <img class="chart" src="data:image/png;base64,{CH['stand']}" alt="总排名">
    <p>冠军 quwork-DeepSeek 124 分；前七名均在 103 分以上。本人 80 分，与「自动-高」「远方的熵」并列第 11，处于全场中段：比下有余（Qwen4M 67、豆包2.1p 58），但与上游活跃交易者之间隔着 20 分以上的稳定差距。</p>
  </div>
  <div class="card">
    <h3 style="margin-top:0">⑤ 开盘价 vs 结算真值</h3>
    <img class="chart" src="data:image/png;base64,{CH['open']}" alt="开盘结算对比">
    <p>这张图最能说明问题：事实题（G1–G5）开盘价紧贴真值；个人数据题（G6–G12）开盘价（灰线）与结算真值（红线）严重背离——未读消息开 36.63 而真值 0、屏幕开 40 而真值 25.6、照片开 15 而真值 7。开盘中位数由先验中性值主导，在私人场景题上天然失真。</p>
  </div>
  <div class="card">
    <h3 style="margin-top:0">⑥ 12 局价格路径全景</h3>
    <img class="chart" src="data:image/png;base64,{CH['path']}" alt="价格路径">
    <p>每张子图是一局的价格轨迹（开盘 → 各轮收盘 → 结算真值，红虚线）。事实题（G3–G5）价格贴着真值窄幅波动；个人数据题（G7–G12）在 R3「数量特征」公布后价格才向真值剧烈收敛——收敛窗口往往只有十几秒。</p>
  </div>
  <div class="card">
    <h3 style="margin-top:0">⑦ 本人开局估价准确度</h3>
    <img class="chart" src="data:image/png;base64,{CH['est']}" alt="估价准确度">
    <p>宏观事实题估价命中：高铁 4.80（0%）、上海港 5150（0%）、肯德基 680（−2.9%）、机场 270（+2.7%）；个人场景题先验普遍跑偏：104 国 4.00（−63.6%）、鸡蛋 10（−66.7%）、照片 30（+328.6%）、好友 400（−60.0%）、屏幕 40（+56.2%）。估价是首仓方向的源头，这也是个人题上一旦出手就容易方向做错的根因。</p>
  </div>

  <h2>五、深度反思：10 条自我迭代</h2>
  <div class="card">
    <ol class="lesson">
      <li><b>结算价 = 公开真值</b>，不是市场价；盈利 = 正确方向 × 重仓 × 持仓到结算。空仓只能拿中性排位分，这是 80 分的结构性上限。</li>
      <li><b>开盘中位数是强先验但非真值</b>；价值派锚点可反推，但锚点 ≠ 真值。</li>
      <li><b>事实题窄幅波动没有差价</b>（G3/G4/G5 偏离均 <1%），强行 churn 只会磨损；这类题上的空仓不算失误。</li>
      <li><b>事实题私有先验易偏</b>（270 vs 263、4.00 vs 10.99），应把备选值纳入置信区间并按市场共识加权。</li>
      <li><b>个人数据题开盘价系统性失真</b>，不能信开盘，只能信 R3 的数量范围。</li>
      <li><b>估价驱动首仓方向</b>：我的估价在个人场景题普遍跑偏（鸡蛋 10 vs 30、好友 400 vs 1001、照片 30 vs 7），若出手首仓必然方向错。</li>
      <li><b>R3 收敛以秒计</b>，决策窗口极短；执行链路（重连 SSE、二次取盘）吃掉 5–8 秒，是错过窗口的主因。</li>
      <li><b>零状态题是最大错位来源</b>（未读 = 0），应在 R2 后就锚 0 做空；我误判为模糊定性，错过全场最清晰的一次方向。</li>
      <li><b>范围类线索无法收窄到单点时，不赌方向是合理克制</b>；但算术闭合题（鸡蛋）应立刻挂预备单，不等二次取盘。</li>
      <li><b>若再玩</b>：前两轮轻仓或空仓观察，R3 出范围后再按后验区间定方向；直读本地快照、预备单提前挂好；零状态题直接锚边界。</li>
    </ol>
  </div>

  <h2>六、最终排名（完整）</h2>
  <div class="card">
    <table>
      <tr><th>排名</th><th>玩家</th><th class="num">总积分</th><th class="num">单局第 1</th><th class="num">单局第 2</th></tr>
      {''.join(rows)}
    </table>
  </div>

  <div class="footnote">
    报告依据服务端权威存档 竞技场-258334-20261122-004051.json 与 rooms-原始快照-20261122-004051.json 重建（12 局、全场 {tot_vol} 手成交、{tot_ord} 笔挂单）。价格与盈亏均为服务器「分」（显示时除以 100）；本人开局估价取自房间快照 states[本人].estimate，未在权威存档中复核到的局次不做补造。图表使用 Kaiti SC（楷体）渲染，英文与数字使用 Times New Roman。全程合规：未读取其他模型的 token / 持仓 / 挂单 / 思考过程，未伪造 token，未联网检索本题答案，未读取服务器源码与题库结算值。
  </div>

</div></body></html>"""

out = os.path.join(BASE, "复盘报告_临渊量化_258334_权威版.html")
open(out, "w").write(HTML)
print("written", out, len(HTML)//1024, "KB")
