import json, os, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

# ---- fonts: Chinese Kaiti SC, Latin/numbers Times New Roman ----
plt.rcParams["font.family"] = ["Kaiti SC", "Times New Roman", "PingFang SC"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 11

os.makedirs("charts", exist_ok=True)
d = json.load(open("extracted.json"))

# ---- curated game metadata ----
# truth/close/open in game units; estimate = opening guess submitted (None if not recorded)
META = [
    dict(g="G1", label="上海肯德基门店", unit="家", truth=700.0, est=680.0,
         close=800.01, open=715.61, cat="常识锚定", test=True,
         note="测试局不计分；被麦当劳600家可比锚带高，末轮超调约14%"),
    dict(g="G2", label="第104大面积国", unit="万km²", truth=10.99, est=4.00,
         close=10.64, open=11.32, cat="地理推断", test=False,
         note="无信号先验严重偏低；R5点名古巴，后验11.09偏高0.10"),
    dict(g="G3", label="高铁营业里程", unit="万km", truth=4.80, est=4.80,
         close=4.76, open=4.80, cat="宏观存量", test=False,
         note="16.2万铁路×约三成；估价命中，盘面围绕真值"),
    dict(g="G4", label="上海港集装箱", unit="万TEU", truth=5150.0, est=5150.0,
         close=5155.50, open=5150.60, cat="宏观存量", test=False,
         note="全球第一、洋山四成、同比+5%；估价命中，偏离<0.2%"),
    dict(g="G5", label="民用运输机场", unit="个", truth=263.0, est=270.0,
         close=262.40, open=263.00, cat="存量增量", test=False,
         note="千万级约40个、2024新投产3个；估价偏高7，后验262贴近"),
    dict(g="G6", label="冰箱鸡蛋", unit="枚", truth=30.0, est=None,
         close=29.70, open=22.55, cat="算术闭合", test=False,
         note="10+30−2×5=30；答案闭合后取盘慢，预备单没挂上"),
    dict(g="G7", label="当日步数", unit="步", truth=8476.0, est=None,
         close=8599.00, open=8000.00, cat="数位收窄", test=False,
         note="84xx；趋势猎手推超区间上沿1.2%，本应做空，错过窗口"),
    dict(g="G8", label="相册新增照片", unit="张", truth=7.0, est=None,
         close=6.83, open=15.00, cat="质数收窄", test=False,
         note="个位数质数{2,3,5,7}；错杀5.07后修复6.83，低位买点错过"),
    dict(g="G9", label="微信未读消息", unit="条", truth=0.0, est=None,
         close=15.85, open=36.63, cat="零状态归零", test=False,
         note="从不留未读=0；全场最大做空错位，误当模糊定性，空仓错过"),
    dict(g="G10", label="七天屏幕时长", unit="小时", truth=25.6, est=40.0,
         close=26.38, open=40.00, cat="区间推导", test=False,
         note="日均3.5–4h→周总24.5–28.0；错位在出手前快速填平"),
    dict(g="G11", label="微信好友总数", unit="人", truth=1001.0, est=None,
         close=1049.36, open=1036.66, cat="区间措辞", test=False,
         note="比一千多一点点=1001；盘面高估约48，区间中部犹豫未做空"),
    dict(g="G12", label="当日解锁次数", unit="次", truth=87.0, est=100.0,
         close=85.68, open=100.00, cat="区间收窄", test=False,
         note="80–90偏上半段；R3秒级收敛，旧快照误导，区间中部不做空"),
]

# ---- bucket price series by resolution timestamp ----
res_ts = [r["ts"] for r in d["resolutions"]]
pt = d["phase_timeline"]
series = [[] for _ in META]
for p in pt:
    if p["last"] is None:
        continue
    # find bucket
    idx = 0
    for i, t in enumerate(res_ts):
        if p["ts"] <= t:
            idx = i
            break
    else:
        idx = len(res_ts) - 1
    series[idx].append((p["ts"], p["last"] / 100.0, p["phase"], p["round"]))

for m, s in zip(META, series):
    # keep only live-trading ticks, drop estimate/closed idle and stale None
    s = [v for v in s if v[2] == "trading"]
    m["series"] = s
    m["n_ticks"] = len(s)

# ---- standings progression (clean snapshots after G2) ----
prog = []
for s in d["standings_timeline"]:
    rows = {r["name"]: r["points"] for r in s["rows"]}
    me = rows.get("豆包-远方的mac-豆包2.1l")
    if me is None:
        continue
    mx = max(rows.values())
    if prog and prog[-1][1] == me and prog[-1][2] == mx:
        continue
    prog.append((s["ts"], me, mx))
# drop repeated zero head
prog = [x for x in prog if x[1] > 0 or x[2] > 0]

# ============ Chart 1: cumulative score progression ============
fig, ax = plt.subplots(figsize=(10, 5.2))
labels = [m["g"] for m in META[1:]]
me_pts = [x[1] for x in prog]
lead = [x[2] for x in prog]
x = list(range(len(me_pts)))
ax.plot(x, lead, "-o", color="#b8423a", lw=2, label="全场领先者", markersize=6)
ax.plot(x, me_pts, "-o", color="#2f5d8a", lw=2.4, label="本人（豆包2.1l）", markersize=7)
for xi, v in zip(x, me_pts):
    ax.annotate(str(v), (xi, v), textcoords="offset points", xytext=(0, -16),
                ha="center", fontsize=9, color="#2f5d8a")
for xi, v in zip(x, lead):
    ax.annotate(str(v), (xi, v), textcoords="offset points", xytext=(0, 8),
                ha="center", fontsize=9, color="#b8423a")
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylabel("累计积分")
ax.set_title("图1  累计积分走势：本人 vs 全场领先者（G1 测试局不计分）")
ax.legend(loc="upper left")
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig("charts/01_score_progression.png", dpi=150)
plt.close(fig)

# ============ Chart 2: truth vs closing price (normalized) ============
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.4))
games = [m["g"] for m in META]
truth_idx = [100.0] * len(META)
close_idx = []
err = []
for m in META:
    if m["truth"] == 0:
        close_idx.append(None)
        err.append(None)
    else:
        ci = m["close"] / m["truth"] * 100
        close_idx.append(ci)
        err.append((m["close"] - m["truth"]) / m["truth"] * 100)

import numpy as np
x = np.arange(len(META))
ax1.bar(x - 0.2, truth_idx, 0.4, label="真值=100", color="#7f9bb5")
cv = [v if v is not None else 0 for v in close_idx]
ax1.bar(x + 0.2, cv, 0.4, label="收盘市价（归一化）", color="#e0a458")
ax1.axhline(100, color="#333", ls="--", lw=1)
ax1.set_xticks(x); ax1.set_xticklabels(games)
ax1.set_ylabel("指数（真值=100）")
ax1.set_title("图2a  各局真值与收盘市价对比")
ax1.legend()
ax1.grid(alpha=0.25, axis="y")

ev = [v if v is not None else 0 for v in err]
colors = ["#b8423a" if v > 0 else "#2f5d8a" for v in ev]
ax2.bar(x, ev, color=colors)
ax2.axhline(0, color="#333", lw=1)
ax2.set_xticks(x); ax2.set_xticklabels(games)
ax2.set_ylabel("收盘市价相对真值偏差 (%)")
ax2.set_title("图2b  收盘定价偏差（红=高估，蓝=低估；G9真值为0单列）")
for xi, v, m in zip(x, ev, META):
    if m["truth"] == 0:
        ax2.annotate("真值0\n市价15.85", (xi, 0), textcoords="offset points",
                     xytext=(0, 12), ha="center", fontsize=8, color="#b8423a")
    else:
        ax2.annotate(f"{v:+.1f}%", (xi, v), textcoords="offset points",
                     xytext=(0, 6 if v >= 0 else -14), ha="center", fontsize=8)
ax2.grid(alpha=0.25, axis="y")
fig.tight_layout()
fig.savefig("charts/02_truth_vs_close.png", dpi=150)
plt.close(fig)

# ============ Chart 3: representative trajectories ============
pick = ["G7", "G9", "G11", "G12"]
fig, axes = plt.subplots(2, 2, figsize=(13, 8))
for ax, g in zip(axes.flat, pick):
    m = next(x for x in META if x["g"] == g)
    s = m["series"]
    if s:
        t0 = s[0][0]
        xs = [(v[0] - t0) / 1000.0 for v in s]
        ys = [v[1] for v in s]
        ax.plot(xs, ys, color="#2f5d8a", lw=1.6, label="成交价")
    ax.axhline(m["truth"], color="#b8423a", ls="--", lw=1.6, label=f"真值 {m['truth']:g}")
    ax.set_title(f"{g}  {m['label']}（{m['unit']}）")
    ax.set_xlabel("本局经过时间（秒）")
    ax.set_ylabel("价格")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
fig.suptitle("图3  代表性对局的价格轨迹与真值参照线", fontsize=13)
fig.tight_layout()
fig.savefig("charts/03_trajectories.png", dpi=150)
plt.close(fig)

# ============ Chart 4: final standings ============
final = d["standings_timeline"][-1]["rows"]
final_sorted = sorted(final, key=lambda r: r["points"])
names = [r["name"] for r in final_sorted]
pts = [r["points"] for r in final_sorted]
me_name = "豆包-远方的mac-豆包2.1l"
cols = ["#2f5d8a" if n == me_name else "#9db7cc" for n in names]
fig, ax = plt.subplots(figsize=(10, 6.5))
ax.barh(names, pts, color=cols)
for i, v in enumerate(pts):
    ax.text(v + 1, i, str(v), va="center", fontsize=9)
ax.set_title("图4  全场最终积分排名（15 个模型位）")
ax.set_xlabel("累计积分")
ax.grid(alpha=0.25, axis="x")
fig.tight_layout()
fig.savefig("charts/04_final_standings.png", dpi=150)
plt.close(fig)

# ============ Chart 5: estimate accuracy ============
fig, ax = plt.subplots(figsize=(10, 5))
known = [m for m in META if m["est"] is not None and m["truth"] > 0]
gx = [m["g"] for m in known]
ee = [(m["est"] - m["truth"]) / m["truth"] * 100 for m in known]
cols = ["#2f5d8a" if abs(v) <= 2 else "#e0a458" if abs(v) <= 10 else "#b8423a" for v in ee]
ax.bar(gx, ee, color=cols)
ax.axhline(0, color="#333", lw=1)
for xi, v, m in zip(range(len(gx)), ee, known):
    ax.annotate(f"估{m['est']:g}\n真{m['truth']:g}\n{v:+.1f}%", (xi, v),
                textcoords="offset points", xytext=(0, 6 if v >= 0 else -30),
                ha="center", fontsize=8)
ax.set_ylabel("开局估价相对真值误差 (%)")
ax.set_title("图5  开局估价准确度（蓝=±2%内，橙=2–10%，红=>10%）")
ax.grid(alpha=0.25, axis="y")
fig.tight_layout()
fig.savefig("charts/05_estimate_accuracy.png", dpi=150)
plt.close(fig)

# ---- save summary ----
summary = []
for m in META:
    summary.append({k: v for k, v in m.items() if k != "series"})
json.dump({"games": summary,
           "progression": [{"me": a, "max": b} for _, a, b in prog]},
          open("games_summary.json", "w"), ensure_ascii=False, indent=1)
print("charts done:", os.listdir("charts"))
print("progression:", [(a, b) for _, a, b in prog])
