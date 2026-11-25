#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the self-contained HTML post-match review report."""
import json, base64, os, html

BASE = os.path.dirname(os.path.abspath(__file__))
summ = json.load(open(os.path.join(BASE, "games_summary.json")))
ext = json.load(open(os.path.join(BASE, "extracted.json")))
GAMES = summ["games"]
RES = ext["resolutions"]
assert len(GAMES) == len(RES) == 12

# attach signals
for g, r in zip(GAMES, RES):
    g["signals"] = [{"round": s["round"], "text": s.get("text", "")} for s in r["signals"]]
    g["note_truth"] = r.get("note", "")

# G1 early events were logged before the UTF-8 decode fix; restore clean text from journal
GAMES[0]["signals"] = [
    {"round": 1, "text": "2025 年百胜中国（Yum China）总收入约 117.97 亿美元。"},
    {"round": 2, "text": "必胜客 2025 年在中国大陆共有 4168 家门店（干扰品牌）。"},
    {"round": 3, "text": "截至 2026 年 1 月 23 日，上海麦当劳门店约 600 家（可比锚）。"},
]

# per-game points (formal G2..G12); G1 test excluded
PTS = {"G1": None, "G2": 7, "G3": 5, "G4": 6, "G5": 4, "G6": 11,
       "G7": 9, "G8": 8, "G9": 4, "G10": 10, "G11": 6, "G12": 10}

# ---- rich per-game narrative ----
NARR = {
"G1": dict(
  title="上海肯德基门店数（测试局 · 不计分）",
  prior="先验把上海一线市场的门店密度作为锚：常住约 2480 万人，连锁快餐按一人/店量级反推，区间 550–750，点估 680。此时尚未看到任何线索，先验只靠城市人口与品牌全国量级的常识外推，并已预留目录口径（在营/甜品站/停车场店）带来的 10–20% 浮动。",
  think="R1 给出百胜中国总收入 117.97 亿美元，只是背景盘子；R2 必胜客大陆 4168 家是干扰品牌，不能并入 KFC 估值；R3 上海麦当劳 600 家才是同品类可比锚。一线市场两品牌门店差距远小于全国，KFC:McD 大致 1.17:1。",
  action="全程空仓，未挂任何限价单。估价 680 提交后，盘面开盘中位 715.6，末轮被麦当劳锚与追涨盘推到 800.01 收盘。",
  review="真值 700，收盘高估约 14.3%。这是全场第一处清晰的反向收租机会：可比锚出现后趋势猎手追涨把价格推出后验区间，按规则偏离 10%+ 应反向做空。测试局让我看清了脚本盘口的驱动方式，但没有留下可复用的仓位动作。",
  lesson="① 开盘价是房间共识的读数，不是真值；利润来自共识与真值的偏差。② 先分清线索是背景 / 干扰 / 可比，干扰品牌不入估值。③ 末轮 R3 信息最充分，仓位应在 R2 末–R3 建立，而不是 R1 赌方向。"),
"G2": dict(
  title="世界第 104 大面积国家（万平方公里）",
  prior="无信号先验严重不足：按中位国家面积拍了 4.00 万 km²，完全是量级猜测，没有区域、人口或邻邦锚。",
  think="线索逐轮收敛：R1 非洲总面积 3020 万是背景干扰；R2 人口 975 万；R3 海岸线 5746 km；R4 第 50 大国西班牙 50.6 万作为排名参照锚；R5 直接点名古巴。候选国在 R2–R3 已可圈定，R5 是决定性信号，窗口只有十几秒。",
  action="全程空仓。盘面开盘 11.32，R2/R3 冲高 11.39，R4 回落 11.09，末轮 10.64–10.94。后验修正到 11.09，偏高 0.10（约 0.9%）。",
  review="真值古巴 109,884 km² = 10.99 万（数据集取此口径，非常见 110,860）。估价 4.00 偏离 -63.6%，是开局估价最差的一局；后验修正后已贴近真值，但盘面本身围绕真值窄幅波动，没有可交易的错位。",
  lesson="① 正式局轮次不固定（本局 maxRound=5，其余多为 3），以 state.maxRound 为准。② 点名类决定性信号窗口极短，R1–R3 锁定候选后应提前挂好双向预备单，点名后秒级反应。③ 真值口径以题目数据集为准，参照锚与真值同源。④ 薄盘极端价位有陈旧挂单，噪声尖峰不可追。"),
"G3": dict(
  title="2024 年底中国高铁营业里程（万公里）",
  prior="先验记 2023 年底约 4.5 万 km，2024 新增约两千公里，点估 4.8 万 km。",
  think="R1 全国铁路 16.2 万 km；R2 高铁约占三成；R3 2024 投产新线超 3000 km、高铁过半。16.2×三成≈4.86 只是近似推导，占比线索给的是区间锚，不能直接相乘当答案；存量口径以官方 4.8 为准。",
  action="空仓中性。盘面 4.66–4.88 围绕真值波动，末段贴近 4.76，偏离不足 1%。",
  review="真值 4.8 万 km，估价 4.80 命中（误差 0.0%）。共识定价有效，薄盘窄偏离不值得交差价。",
  lesson="占比/增速类线索只能框定区间，答案落在官方存量口径上；基数记忆偏差是主要误差源。"),
"G4": dict(
  title="2024 上海港集装箱吞吐量（万 TEU）",
  prior="先验记 2023 年 4916 万 TEU，2024 同比约 +5%，点估 5150 万。",
  think="R1 全球第一；R2 洋山港区贡献四成以上；R3 同比 +5%。增速要乘上一年存量基数，基数本身靠先验记忆。",
  action="空仓中性。盘面 5119–5197 围绕真值，末段 5159，偏离 <0.2%。",
  review="真值 5150 万 TEU，估价 5150 命中（误差 0.0%）。又是一局共识高度有效的宏观存量题，没有错位可赚。",
  lesson="宏观存量题若先验基数准，估价即可命中；交易机会主要出现在个人场景题与情绪追涨杀跌局。"),
"G5": dict(
  title="2024 年底颁证民用运输机场数量（个）",
  prior="先验记 2023 年底 259 个，2024 新增约 10，点估 270。",
  think="R1 覆盖 30 多个省级行政区；R2 千万级机场约 40 个；R3 2024 新投产 3 个。存量增量线索要乘上一年基数，基数记忆偏差直接传导到估价。",
  action="空仓中性。盘面 261.5–268.8 围绕 263，R3 后后验修正到 262，贴近真值。",
  review="真值 263 个，估价 270 偏高 7（+2.7%）。盘面定价有效，未出手。",
  lesson="新增 N 个的线索要回加一年基数；对存量类题目，先验基数的准确度比线索推导更决定估价误差。"),
"G6": dict(
  title="冰箱里现有鸡蛋数量（枚）",
  prior="算术题，先验只等线索闭合，不提前押方向。",
  think="R1 上周日买两盒、之后未再买；R2 一盒 10 枚 + 一盒 30 枚；R3 每天煎 2 枚、连续 5 天，无其他使用。闭合式：10+30−2×5=30。",
  action="答案闭合后，我的分析叠加取盘周期约 10–15 秒，等二次取盘时末轮窗口已接近关闭，预备单没能挂上。盘面 R3 末段 29.65–30.12 贴合真值。",
  review="真值 30 枚，后验精确命中。这是流程失误而非判断失误：算术题答案一旦闭合，应在 R3 后立刻挂双向预备单，不等二次取盘。",
  lesson="R3 闭合即下单：提前在心里算好买卖两侧挂单价，线索落地后第一笔请求直接发出；把取盘动作压到只读本地快照，不再重连 SSE。"),
"G7": dict(
  title="当日步数（步）",
  prior="数位收窄题，先验区间待 R3 锁定。",
  think="R1 周六无体育课、无跑步骑行训练；R2 步行往返图书馆宿舍、乘一次地铁、未打车；R3 四位数，千位 8、百位 4，即 84xx。后验区间 8400–8499。",
  action="盘面 R3 被追涨盘推到 8599，高出区间上限约 1.2%，本应做空 2–3 手；仍因取盘慢错过窗口，空仓。",
  review="真值 8476 步，收盘 8599 高估约 1.45%。确认了关键模式：数位/锚点线索落地后，趋势猎手把价格推出已披露区间上沿，反向收租是 +EV。",
  lesson="快照直读本地 state.json（日志器实时刷新），不再每次重连 SSE 占用 5–8 秒；R3 闭合后立即下单，预备单先行。"),
"G8": dict(
  title="相册新增照片张数（张）",
  prior="范围类线索，先验不赌单点。",
  think="R1 未出远门、在外不足三小时；R2 同一手机、过半为同一景物连拍；R3 个位数质数 {2,3,5,7}。线索无法进一步收窄到具体质数。",
  action="R3 后盘面先错杀到 5.07，再修复到 6.83。在 5.07 时无法区分 2/3/5/7，按期望为负，空仓；事后真值 7，低位买点被错过。",
  review="真值 7 张，收盘 6.83 略低于真值 2.4%。重定价初期的极端价多为噪声，不追；但范围无法收窄时，低位赔率其实偏向区间上沿，这一点当时没有量化。",
  lesson="质数/数位类范围题，若不能进一步收窄到单点，不赌方向；但应记录区间分布，在价格打到区间下沿、且区间上沿赔率占优时，允许小仓位试多。"),
"G9": dict(
  title="此刻微信未读消息条数（条）",
  prior="零状态题，先验等待习惯类线索定性。",
  think="R1 见红点就点掉、列表从不留未读；R2 24h 未静音、提示音一响就看；R3 数字更靠近区间下界。R1 的习惯陈述是字面事实——“从不留未读”即未读=0，R3 的下界就是 0。",
  action="误把绝对表述当成模糊定性，空仓。盘面 R1/R2 后从 36.8 错杀到 15.5，收盘 15.85，相对真值 0 仍是严重高估。",
  review="真值 0 条，这是全场最大的做空错位：真值锚定 0，市价越高赚越多，本应在 R2 后重仓做空。判断链条其实已经走到 0，却在最后一步没有转化为仓位。",
  lesson="场景题第三类：零状态字面归零。一旦 R1 出现“从不 / 全部 / 没有”类绝对表述，后验直接锚 0，市价偏高一律做空，不等 R3 确认。"),
"G10": dict(
  title="过去七天屏幕使用总时长（小时）",
  prior="先验偏粗：日均 5–6h×7，估价 40 小时。",
  think="R1 周六无网课、白天图书馆晚上住处；R2 学习+通讯为主、娱乐<两成；R3 日均 3.5–4 小时。推导周总 ∈ (24.5, 28.0)。",
  action="盘面 R3 后由 38.7 快速收敛到 26.38，错位在我出手前已填平，空仓中性。",
  review="真值 25.6 小时，区间命中偏下沿；估价 40 偏高 56.2%，是先验基数（日均时长）记错导致的开局偏差。收盘 26.38 高估 3.05%，窗口很短。",
  lesson="区间推导题先把上下界算出来；市价落入区间内即不赌方向。日均×天数的乘法题，先验日均是误差主源。"),
"G11": dict(
  title="微信通讯录好友总数（人）",
  prior="区间措辞题，先验等待 R3 收窄。",
  think="R1 只增不删；R2 约四分之一历届同学，其余社团/实习同事/家人；R3 四位数、比一千多一点点、不到一千一。措辞“多一点点”应把后验钉在 X+1～X+5，而不是区间中位。",
  action="盘面 1041–1075 区间中部，closed 时 1049.36；我在区间中部犹豫，未做空。",
  review="真值 1001 人，“多一点点”就是 1001，贴近下界；盘面高估约 48（+4.83%）。后验偏下界的判断是对的，但没有落到仓位上。",
  lesson="措辞“多一点点 / 接近下界”直接锚 X+1～X+5；市价在区间中位偏上即可做空，不必等到打到上沿。"),
"G12": dict(
  title="当日手机解锁次数（次）",
  prior="日均解锁常见 80–150 次，点估 100，估价提交 100。",
  think="R1 周五，上午两节课、下午图书馆、晚上回住处；R2 每次解锁只做一件事（看消息/查资料/付款），做完即锁屏；R3 两位数，八十多一点、不到九十，即 80–90。",
  action="R3 盘面从 101.9 秒级收敛到 83.5，买盘 16 手托在 83.50；落入区间后错位基本填平，剩余 18 秒边际不足，空仓等结算。",
  review="真值 87 次，落在区间上半段；收盘 85.68 略低于真值 1.52%。“多一点”不必过度偏下界——87 并非贴近 80。区间中部不做空是正确的。",
  lesson="R3 收敛极快（十几秒内填平错位），旧快照会误导；区间中部、赔率对称时不赌方向。"),
}

# ---------- helpers ----------
def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def pct(close, truth):
    if truth == 0:
        return None
    return (close - truth) / truth * 100

def est_err(est, truth):
    if est is None or truth == 0:
        return None
    return (est - truth) / truth * 100

charts = {name: b64(os.path.join(BASE, "charts", f)) for name, f in [
    ("score", "01_score_progression.png"), ("cmp", "02_truth_vs_close.png"),
    ("traj", "03_trajectories.png"), ("stand", "04_final_standings.png"),
    ("est", "05_estimate_accuracy.png")]}

# ---------- standings ----------
final = sorted(ext["standings_timeline"][-1]["rows"], key=lambda r: r["rank"])
me_id = "c64f9cfced6ef32b"
stand_rows = ""
for r in final:
    me = r["name"] == "豆包-远方的mac-豆包2.1l"
    cls = ' class="me-row"' if me else ""
    stand_rows += f"<tr{cls}><td>{r['rank']}</td><td>{html.escape(r['name'])}</td><td>{r['points']}</td></tr>\n"

# ---------- summary table ----------
tbl = ""
for g in GAMES:
    e = pct(g["close"], g["truth"])
    ee = est_err(g["est"], g["truth"])
    e_s = "—" if e is None else f"{e:+.1f}%"
    ee_s = "—" if ee is None else f"{ee:+.1f}%"
    est_s = "—" if g["est"] is None else f"{g['est']:g}"
    pts = PTS[g["g"]]
    pts_s = "不计分" if pts is None else str(pts)
    tag = "测试" if g["test"] else "正式"
    tbl += (f"<tr><td><b>{g['g']}</b><span class='tag'>{tag}</span></td>"
            f"<td>{html.escape(g['label'])}</td><td>{g['unit']}</td>"
            f"<td class='num'>{g['truth']:g}</td><td class='num'>{g['open']:g}</td>"
            f"<td class='num'>{g['close']:g}</td><td class='num'>{e_s}</td>"
            f"<td class='num'>{est_s}</td><td class='num'>{ee_s}</td>"
            f"<td>0 笔 / 0 手</td><td class='num'>{pts_s}</td></tr>\n")

# ---------- per-game cards ----------
cards = ""
for g in GAMES:
    n = NARR[g["g"]]
    sig = ""
    for s in g["signals"]:
        sig += f"<li><b>R{s['round']}</b> · {html.escape(s['text'])}</li>"
    e = pct(g["close"], g["truth"])
    e_s = "真值为 0，市价不可比" if e is None else f"收盘偏差 {e:+.1f}%"
    cards += f"""
<section class="game">
  <h3>{g['g']} · {html.escape(n['title'])}</h3>
  <div class="meta">真值 <b>{g['truth']:g} {g['unit']}</b> ｜ 开盘 {g['open']:g} ｜ 收盘 {g['close']:g} ｜ {e_s} ｜ 本局积分 {PTS[g['g']] if PTS[g['g']] is not None else '不计分'}</div>
  <div class="block"><div class="bh">先验与开局思考</div><p>{html.escape(n['prior'])}</p></div>
  <div class="block"><div class="bh">线索链（逐轮公布）</div><ul class="sigs">{sig}</ul></div>
  <div class="block"><div class="bh">盘面解读与决策过程</div><p>{html.escape(n['think'])}</p><p>{html.escape(n['action'])}</p></div>
  <div class="block"><div class="bh">结算与事后评判</div><p>{html.escape(n['review'])}</p></div>
  <div class="block lesson"><div class="bh">本局迭代认知</div><p>{html.escape(n['lesson'])}</p></div>
</section>"""

# missed dislocation table
miss = [
 ("G1", "700", "800.01", "+14.3%", "可比锚（麦当劳600）出现后追涨超调", "做空 2 手", "测试局，仅观战"),
 ("G7", "8476", "8599.00", "+1.45%", "数位线索后趋势猎手推超区间上沿", "做空 2–3 手", "取盘慢，错过窗口"),
 ("G8", "7", "6.83", "−2.4%", "错杀 5.07 后修复，区间下沿赔率偏上沿", "低位试多 1–2 手", "范围无法收窄，按期望为空"),
 ("G9", "0", "15.85", "不可比", "零状态锚定 0，全场最大做空错位", "R2 后重仓做空", "误当模糊定性，空仓错过"),
 ("G10", "25.6", "26.38", "+3.05%", "区间内小幅高估，收敛极快", "轻仓做空", "出手前错位已填平"),
 ("G11", "1001", "1049.36", "+4.83%", "措辞偏下界，盘面停在区间中位偏上", "做空 2 手", "区间中部犹豫未出手"),
 ("G12", "87", "85.68", "−1.52%", "区间中部、赔率对称", "不交易（正确）", "空仓中性"),
]
miss_rows = ""
for m in miss:
    miss_rows += "<tr>" + "".join(f"<td>{x}</td>" for x in m) + "</tr>\n"

HTML = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>临渊量化 · 多模型实时交易竞技复盘报告（房间 258334）</title>
<style>
:root{{--ink:#1d2733;--blue:#2f5d8a;--red:#b8423a;--gold:#e0a458;--bg:#f7f4ee;--card:#fff;--line:#e3ddd0;}}
*{{box-sizing:border-box;}}
body{{margin:0;background:var(--bg);color:var(--ink);
 font-family:"Times New Roman","Kaiti SC","STKaiti","Songti SC",serif;line-height:1.85;}}
.wrap{{max-width:980px;margin:0 auto;padding:40px 28px 80px;}}
h1{{font-size:30px;letter-spacing:1px;margin:0 0 8px;}}
h2{{font-size:22px;margin:46px 0 16px;padding-left:12px;border-left:5px solid var(--blue);}}
h3{{font-size:18px;margin:0 0 10px;color:var(--blue);}}
.sub{{color:#5a6672;font-size:15px;}}
.cover{{background:linear-gradient(135deg,#2f5d8a,#4a7ba6);color:#fff;border-radius:18px;padding:38px 34px;margin-bottom:30px;}}
.cover h1{{color:#fff;}} .cover .sub{{color:#e8eef4;}}
.kpis{{display:flex;gap:18px;flex-wrap:wrap;margin-top:24px;}}
.kpi{{background:rgba(255,255,255,.14);border-radius:12px;padding:16px 20px;min-width:150px;}}
.kpi b{{font-size:28px;display:block;}} .kpi span{{font-size:13px;opacity:.85;}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:24px 26px;margin:18px 0;}}
table{{border-collapse:collapse;width:100%;font-size:14px;}}
th,td{{border-bottom:1px solid var(--line);padding:8px 10px;text-align:left;}}
th{{color:#5a6672;font-weight:600;}}
.num{{text-align:right;font-variant-numeric:tabular-nums;}}
.tag{{display:inline-block;margin-left:6px;font-size:11px;color:#fff;background:var(--gold);border-radius:6px;padding:0 6px;}}
.me-row{{background:#eaf1f7;}}
.game{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:24px 26px;margin:22px 0;}}
.meta{{font-size:13px;color:#5a6672;margin-bottom:14px;}}
.block{{margin:12px 0;padding:12px 16px;background:#fbf9f5;border-radius:10px;}}
.block.lesson{{background:#f3f7f3;border-left:3px solid #5b8c6a;}}
.bh{{font-weight:700;color:var(--blue);margin-bottom:4px;}}
.lesson .bh{{color:#3f7a52;}}
ul.sigs{{margin:6px 0;padding-left:20px;}} ul.sigs li{{margin:4px 0;}}
figure{{margin:22px 0;}} figure img{{width:100%;border-radius:12px;border:1px solid var(--line);}}
figcaption{{font-size:13px;color:#5a6672;text-align:center;margin-top:8px;}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:18px;}}
.note{{font-size:13px;color:#5a6672;}}
ul.tight li{{margin:6px 0;}}
.badge{{display:inline-block;background:#eef2f6;border-radius:8px;padding:2px 10px;margin:2px 4px;font-size:13px;}}
</style></head>
<body><div class="wrap">

<div class="cover">
  <h1>临渊量化 · 多模型实时交易竞技复盘报告</h1>
  <div class="sub">房间 258334 ｜ 参赛者：豆包-远方的mac-豆包2.1lite-高（服务器名截断为 豆包-远方的mac-豆包2.1l）｜ 赛制：1 测试局 + 11 正式局，每局 3–5 轮、每轮 60 秒，净持仓 ±10 手</div>
  <div class="kpis">
    <div class="kpi"><b>80</b><span>最终累计积分</span></div>
    <div class="kpi"><b>11 / 15</b><span>模型位并列名次</span></div>
    <div class="kpi"><b>0</b><span>成交笔数 / 挂单笔数</span></div>
    <div class="kpi"><b>12</b><span>观察局数（含测试）</span></div>
    <div class="kpi"><b>44</b><span>与第一名积分差（124）</span></div>
  </div>
</div>

<h2>一、结论摘要（一页看懂）</h2>
<div class="card">
<p>本场是同一道题、同一个盘、同一批对手的零和信息博弈：15 个模型位加上 24 个脚本玩家（价值派 12、噪声派 8、流动性程序 1、趋势猎手 2、均值回归 1）。我从入场、估价、订阅盘面到逐轮决策全程在场，技术链路稳定，<b>但交易执行几乎为零</b>——12 局下来挂单 0 笔、成交 0 笔，净持仓始终为 0，已实现与浮动盈亏均为 0。</p>
<p>估值能力呈两极：宏观存量题（高铁里程、上海港吞吐量）估价精准命中，算术题（鸡蛋）后验闭合，区间题（屏幕时长、好友数、解锁次数）能把真值框进区间；但<b>判断没有转化为仓位</b>。全场最清晰的几处错位——G9 未读消息锚定 0 而市价 15.85、G11 好友 1001 而市价 1049、G7 步数被推超区间上沿——全部以空仓旁观结束。积分主要来自中性排位，而非主动定价误差。</p>
<p>最终 80 分，与另外两名选手并列第 11；第一名 quwork-DeepSeek 124 分。差距不在“算不准”，而在<b>出手慢、怕出错、错过窗口</b>：R3 线索闭合后分析叠加取盘耗时 10–15 秒，而盘面在十几秒内就把错位填平。</p>
</div>

<h2>二、赛制、规则与价格口径</h2>
<div class="card">
<div class="grid2">
<div>
<ul class="tight">
<li><b>入场</b>：POST /api/join，凭房间号换 token；断线同 token 重连恢复身份，不重复占座。</li>
<li><b>订阅</b>：GET /api/stream 的 SSE 长连接，state 在盘面变化时推送，clock 每秒推送剩余时间与最新价；掉线退化为轮询 /api/room。</li>
<li><b>动作</b>：estimate（开局估价，中位数成开盘价）、order（限价单，穿价部分立即成交、剩余留在盘上）、cancel / cancelAll。无市价单：要立刻买就挂卖一之上，立刻卖就挂买一之下。</li>
<li><b>撮合</b>：连续撮合、价格优先时间优先，成交价取先挂方；禁止自成交；净持仓 ±10 手；服务器按到达时间打戳，不补偿网络延迟；不限流。</li>
</ul>
</div>
<div>
<ul class="tight">
<li><b>结算</b>：单局盈亏 = 已实现 + 净持仓 ×（结算价 − 均价成本）；单局积分 = N − 名次 + 1；留到结算的持仓计全额盈亏，提前平仓只算已实现。</li>
<li><b>价格不对称口径（易错点）</b>：服务器返回价是“分”，读盘 ÷100；下单 price 与 estimate 传游戏计价单位本身，不乘 100。例：真值 700 家返回 70000，估价 4.00 存为 400。</li>
<li><b>线索节奏</b>：一条线索在轮首公布，当轮不再有新信息；没有固定决策点，任意毫秒都可行动。</li>
</ul>
</div>
</div>
</div>

<h2>三、技术架构与交易流程</h2>
<div class="card">
<p>为支撑一小时赛制，在项目目录下搭了两个常驻脚本，决策直读本地快照，避免每次重连长连接占用时间：</p>
<ul class="tight">
<li><span class="badge">sse_logger.py</span> 常驻 SSE 日志器：连接 /api/stream，state 事件原子写入 state.json（先写 .tmp 再 os.replace，避免读写竞态读到空文件），全量事件追加 events.log，clock 写入 clock.json；断线 1 秒后自动重连。</li>
<li><span class="badge">client.py</span> 动作/快照 CLI：snapshot 读本地快照，estimate / order / cancel / cancelAll 直连 /api/act；order 可附 ≤40 字理由，计入决策质量评分。</li>
</ul>
<p>联调中修过两个 bug：① 初版按单字节 decode 导致中文变 FFFD 乱码，改为字节缓冲、按行整体 UTF-8 解码；② state.json 读写竞态（读到空文件 JSON 报错），改为原子替换。旧日志进程 kill 未死时用 kill -9 清理。</p>
<p><b>标准决策回路</b>：join 取 token → estimate 占位 → 日志器喂本地 state.json → 收到 state 变化时读一次盘（无变化不空转）→ R1/R2 建后验区间 → R3 闭合后对照市价与后验偏差 → 偏差超阈值且有把握才挂单 → 收盘前把仓位收敛到把握最高的方向。</p>
</div>

<h2>四、全局数据复盘</h2>

<figure><img src="data:image/png;base64,{charts['score']}" alt="积分走势">
<figcaption>图1 累计积分走势：本人（蓝）与全场领先者（红）。G1 测试局不计分；G2–G12 每局结算后取快照。</figcaption></figure>

<div class="card">
<h3>最终全场排名（15 个模型位）</h3>
<table><thead><tr><th>名次</th><th>参赛者</th><th>累计积分</th></tr></thead><tbody>
{stand_rows}</tbody></table>
<p class="note">脚本玩家不计入模型位排名；本人行为零持仓，靠中性排位拿到并列第 11。</p>
</div>

<figure><img src="data:image/png;base64,{charts['stand']}" alt="最终排名条形图">
<figcaption>图4 全场最终积分横向条形图，深色为本人。</figcaption></figure>

<figure><img src="data:image/png;base64,{charts['cmp']}" alt="真值与收盘对比">
<figcaption>图2 各局真值（归一化 100）与收盘市价对比（左）；收盘相对真值偏差（右，红=高估、蓝=低估）。G9 真值为 0，单列标注。</figcaption></figure>

<figure><img src="data:image/png;base64,{charts['est']}" alt="估价准确度">
<figcaption>图5 开局估价准确度：蓝=±2% 内，橙=2–10%，红=&gt;10%。宏观题命中，先验基数记错的个人场景题偏差最大。</figcaption></figure>

<div class="card">
<h3>12 局总览表</h3>
<table><thead><tr><th>局</th><th>题目</th><th>单位</th><th>真值</th><th>开盘</th><th>收盘</th><th>收盘偏差</th><th>开局估价</th><th>估价偏差</th><th>本人成交</th><th>本局积分</th></tr></thead>
<tbody>{tbl}</tbody></table>
</div>

<figure><img src="data:image/png;base64,{charts['traj']}" alt="代表性价格轨迹">
<figcaption>图3 四局代表性价格轨迹与真值参照线：G7 步数被推超上沿；G9 长期悬在真值 0 之上；G11 停在 1001 上方；G12 末段快速收敛到 87 附近。</figcaption></figure>

<h2>五、逐局详录：思考过程、盘面观察与决策</h2>
{cards}

<h2>六、对手盘行为画像</h2>
<div class="card">
<table><thead><tr><th>脚本类型</th><th>人数</th><th>可观察行为</th><th>盘口含义</th></tr></thead><tbody>
<tr><td>价值派</td><td>12</td><td>各有估值锚，价格偏离锚超 2% 就朝锚推 2 手</td><td>锚附近有反复托底/压顶力量，偏离锚 2% 内不易单边走远</td></tr>
<tr><td>噪声派</td><td>8</td><td>随机方向 1–2 手，约一半时间不动</td><td>制造薄盘噪声尖峰，极端价位多为陈旧挂单，不可追</td></tr>
<tr><td>流动性程序</td><td>1</td><td>每 11 秒撤旧报价，围绕最新价上下两档双边挂 2–6 手</td><td>维持盘口宽度，买卖一之间常有可吃的流动性</td></tr>
<tr><td>趋势猎手</td><td>2</td><td>看最近 8 笔，涨过约 0.4% 追多 2 手，跌过追空</td><td>锚点线索后会把价格短期推出已披露区间上/下沿，是反向收租的对手盘</td></tr>
<tr><td>均值回归</td><td>1</td><td>偏离 24 笔均价 1.2% 以上时反向 2 手</td><td>极端偏离后提供一层回归力量，但反应慢于趋势猎手</td></tr>
</tbody></table>
<p class="note">模型对手彼此不可见；脚本成交在 me.trades.program 标记为 true。无法分辨单笔来自谁，只能从成交价、手数、时间三个维度推断。整场观察：价值派锚定 + 趋势猎手追涨，是宏观题盘面围绕真值收敛的主要力量；个人场景题里，噪声与趋势盘容易在 R3 制造短暂超调。</p>
</div>

<h2>七、场景题分类学与后验规则</h2>
<div class="card">
<p>12 局可归为四类，每类对应不同的后验方式与交易触发条件：</p>
<table><thead><tr><th>类别</th><th>本局案例</th><th>后验方法</th><th>交易触发</th></tr></thead><tbody>
<tr><td>① 宏观存量/常识锚定</td><td>G3 高铁、G4 港口、G5 机场、G1 门店</td><td>先验基数 × 占比/增速线索，落在官方存量口径</td><td>共识通常有效；仅当盘面偏离后验 &gt;3% 才动手</td></tr>
<tr><td>② 算术闭合</td><td>G6 鸡蛋（10+30−2×5=30）</td><td>线索给出全部输入，直接算出单点</td><td>R3 闭合即挂双向预备单，不等二次取盘</td></tr>
<tr><td>③ 数位/质数/区间收窄</td><td>G7 步数、G8 照片、G10 时长、G11 好友、G12 解锁</td><td>先定区间，再按措辞（“多一点点/接近下界”）调整区间内位置</td><td>价格打到区间外沿且后验把握足时反向；区间中部赔率对称不赌</td></tr>
<tr><td>④ 零状态字面归零</td><td>G9 未读消息（=0）</td><td>R1“从不/全部/没有”类绝对表述直接锚 0</td><td>市价偏高一律做空，R2 后即可建仓，不等 R3</td></tr>
</tbody></table>
</div>

<h2>八、失误清单：错过的错位（事后量化）</h2>
<div class="card">
<table><thead><tr><th>局</th><th>真值</th><th>收盘</th><th>偏差</th><th>错位性质</th><th>本应动作</th><th>实际处置</th></tr></thead>
<tbody>{miss_rows}</tbody></table>
<p class="note">注：偏差与手数为事后复盘口径；实际盈亏还受成交价、对手盘深度与窗口流动性影响。G12 是唯一一局“不交易被事后证明正确”的例子。</p>
</div>

<h2>九、自我迭代时间线（我意识到了什么）</h2>
<div class="card">
<ul class="tight">
<li><b>G1 后</b>：开盘价是房间共识而非真值；利润来自共识与真值的偏差；线索先分背景/干扰/可比；仓位应在末轮前建立。</li>
<li><b>G2 后</b>：轮次不固定以 state.maxRound 为准；点名类信号窗口极短，要提前挂预备单；真值口径以数据集为准；噪声尖峰不可追。</li>
<li><b>G3–G5 后</b>：占比/增速线索只给区间锚；存量题先验基数是误差主源；窄偏离不值得交差价。</li>
<li><b>G6 后</b>：闭合题必须 R3 落地即下单；取盘只读本地快照，去掉重连 SSE 的 5–8 秒。</li>
<li><b>G7 后</b>：数位锚点后趋势猎手推超区间上沿，反向收租是 +EV；流程上预备单先行。</li>
<li><b>G8 后</b>：范围题不能收窄到单点时不赌方向；但下沿赔率占优时允许小仓试多。</li>
<li><b>G9 后（最大教训）</b>：零状态题的习惯陈述是字面事实，绝对表述直接锚 0；判断走到 0 必须落成仓位。</li>
<li><b>G10 后</b>：区间推导先算上下界；市价落入区间内不赌方向；日均基数是乘法题误差主源。</li>
<li><b>G11 后</b>：“多一点点/接近下界”锚 X+1～X+5，而非区间中位；中位偏上即可做空。</li>
<li><b>G12 后</b>：R3 收敛极快，旧快照误导；区间中部、赔率对称时不交易；“多一点”不必过度偏下界。</li>
</ul>
</div>

<h2>十、下一场可执行的改进清单（SOP）</h2>
<div class="card">
<ol class="tight">
<li><b>预备单前置</b>：R2 末后就在心里算好买卖两侧挂单价；R3 线索一落地，第一笔请求直接发出，不再先取盘复核。</li>
<li><b>偏差阈值</b>：|市价 − 后验| &gt;3% 且后验有单点/窄区间把握时出手；区间内、赔率对称时保持中性。</li>
<li><b>仓位节奏</b>：试探 2 手起步，把握最高的零状态/算术题可加到 3–4 手；临近收盘把持仓收敛到后验把握最高的方向，不留模糊头寸。</li>
<li><b>状态题专项</b>：R1 出现“从不/全部/没有”即标记零状态，R2 后直接准备做空腿。</li>
<li><b>执行提速</b>：决策只依赖本地 state.json；日志器掉线 3 秒内重启；下单理由随请求一并提交，便于复盘计分。</li>
<li><b>风控边界</b>：穿价成交后立刻检查残留挂单，撤掉不想要的腿；不追噪声尖峰；净持仓贴近 ±10 前停止同向加仓。</li>
<li><b>复盘闭环</b>：每局结束立刻记录真值、盘面收盘、后验与偏差；把新场景补进分类学，下一场开赛前过一遍规则表。</li>
</ol>
</div>

<h2>附录：数据口径、文件与合规边界</h2>
<div class="card">
<h3>本地产物（linyuan 目录）</h3>
<ul class="tight">
<li><span class="badge">creds.json</span> code / token / playerId / base 地址</li>
<li><span class="badge">sse_logger.py</span> 常驻 SSE 日志器；<span class="badge">client.py</span> 动作与快照 CLI</li>
<li><span class="badge">state.json / clock.json</span> 实时快照；<span class="badge">events.log</span> 全量事件流水</li>
<li><span class="badge">journal.md</span> 逐局手写复盘；<span class="badge">games_summary.json</span> 结构化汇总；<span class="badge">charts/</span> 本报告五张图表</li>
</ul>
<h3>口径说明</h3>
<ul class="tight">
<li>真值全部取自服务器 resolution 事件（price 为分单位，÷100）；开盘/收盘取 openingPrice 与末轮 lastPrice。</li>
<li>本局积分由累计积分差分得到；G1 为测试局不计分。</li>
<li>估价偏差 =（估价 − 真值）/ 真值；收盘偏差 =（收盘 − 真值）/ 真值。</li>
</ul>
<h3>合规边界（全程遵守）</h3>
<ul class="tight">
<li>未读取其他模型的 token、持仓、挂单与输出；未伪造 token 或冒充他人；未修改题面。</li>
<li>未联网检索本题答案，未读取服务器源码或题库结算值；联网仅限方法论层面。</li>
<li>本报告所有数据来自本人可见的 me、book、history、signals 与服务器公开结算事件。</li>
</ul>
</div>

<p class="note" style="margin-top:30px;text-align:center;">—— 报告由参赛客户端自动生成 ｜ 房间 258334 ｜ 临渊量化实时交易竞技场 ——</p>
</div></body></html>"""

out = os.path.join(BASE, "复盘报告_临渊量化_258334.html")
open(out, "w", encoding="utf-8").write(HTML)
print("written:", out, f"{len(HTML)/1024:.1f} KB")
