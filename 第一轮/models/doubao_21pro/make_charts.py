#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成复盘图表：总览、仓位风险、各局价格网格、代表局详图。"""
import re, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import matplotlib.dates as mdates
import numpy as np

# ---------- 字体与风格 ----------
plt.rcParams["font.sans-serif"] = ["Kaiti SC", "Times New Roman"]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 12
plt.rcParams["figure.dpi"] = 140

INK = "#26221f"        # 墨
CINNABAR = "#9c3b32"   # 朱砂（涨/盈/多）
CELADON = "#3f6b63"    # 青瓷（跌/亏/空）
GOLD = "#c2a05a"       # 金
PAPER = "#f6f1e7"      # 宣纸
GRID = "#d8cfbd"

LOG = "/Users/yuanf/DoubaoWork/chats/2026-11-21/new-chat-5/logs/events.log"
CDIR = "/Users/yuanf/DoubaoWork/chats/2026-11-21/new-chat-5/charts"

GAME_BOUNDS = [
    ("测试局·肯德基", "23:12:04"), ("正式第1题·古巴", "23:21:20"),
    ("正式第2题·高铁", "23:30:19"), ("正式第3题·上海港", "23:37:42"),
    ("正式第4题·机场", "23:43:51"), ("正式第5题·鸡蛋", "23:51:29"),
    ("正式第6题·步数", "23:57:44"), ("正式第7题·相册照片", "00:03:30"),
    ("正式第8题·微信未读", "00:09:36"), ("正式第9题·屏幕时长", "00:16:22"),
    ("正式第10题·好友", "00:22:20"), ("正式第11题·解锁", "00:28:42"),
]
POINTS = [0, 15, 10, 10, 7, 1, 3, 1, 7, 1, 2, 1]

pat = re.compile(
    r"\[(?P<ts>[\d:.]+)\] phase=(?P<phase>\w+) r=(?P<r>-?\d+) remain=(?P<remain>-?\d+) "
    r"open=(?P<open>[\d.]+|None) last=(?P<last>[\d.]+|None) bid=(?P<bid>[\d.]+|None) ask=(?P<ask>[\d.]+|None) "
    r"pos=(?P<pos>-?\d+) avg=(?P<avg>[\d.]+) realized=(?P<realized>-?\d+) pnl=(?P<pnl>-?\d+) orders=(?P<orders>\d+) trades=(?P<trades>\d+)"
)
def num(x): return None if x == "None" else float(x)
def to_sec(t):
    t = t.split(".")[0]; h, m, s = map(int, t.split(":")); return h * 3600 + m * 60 + s

rows = []
for line in open(LOG, encoding="utf-8"):
    m = pat.match(line)
    if not m: continue
    d = m.groupdict()
    sec = to_sec(d["ts"])
    if d["ts"].startswith("00:"): sec += 24 * 3600
    rows.append({"sec": sec, "phase": d["phase"], "r": int(d["r"]),
                 "remain": int(d["remain"]), "open": num(d["open"]), "last": num(d["last"]),
                 "bid": num(d["bid"]), "ask": num(d["ask"]), "pos": int(d["pos"]),
                 "realized": float(d["realized"]) / 100.0, "pnl": float(d["pnl"]) / 100.0})

bounds = [(lb, to_sec(t) + (24 * 3600 if t.startswith("00:") else 0)) for lb, t in GAME_BOUNDS]
games = []
for i, (lb, st) in enumerate(bounds):
    en = bounds[i + 1][1] if i + 1 < len(bounds) else 10 ** 9
    grp = [r for r in rows if st <= r["sec"] < en]
    games.append({"label": lb, "points": POINTS[i], "grp": grp,
                  "final_pnl": grp[-1]["pnl"], "trading": [r for r in grp if r["phase"] == "trading"]})

official = games[1:]
labels = [g["label"].split("·")[1] for g in official]
pnls = [g["final_pnl"] for g in official]
pts = [g["points"] for g in official]

def style_ax(ax):
    ax.set_face_line = None
    ax.set_facecolor(PAPER)
    for s in ax.spines.values(): s.set_color(GRID)
    ax.tick_params(colors=INK)
    ax.grid(True, color=GRID, lw=0.7, alpha=0.7)

# ============ 图1：总览（盈亏柱 + 积分柱 + 累计积分） ============
fig, axes = plt.subplots(2, 1, figsize=(12, 9), facecolor=PAPER)
x = np.arange(len(labels))
colors = [CINNABAR if v >= 0 else CELADON for v in pnls]
ax = axes[0]; style_ax(ax)
bars = ax.bar(x, pnls, color=colors, width=0.62, edgecolor=INK, lw=0.6)
ax.axhline(0, color=INK, lw=1)
ax.set_ylabel("单局盈亏（计价单位）", color=INK)
ax.set_title("十二局征战录 · 单局盈亏与名次积分", color=INK, fontsize=17, pad=12)
ax.set_xticks(x); ax.set_xticklabels(labels, rotation=30, ha="right")
for b, v in zip(bars, pnls):
    ax.text(b.get_x() + b.get_width() / 2, v + (12 if v >= 0 else -28),
            f"{v:.0f}", ha="center", color=INK, fontsize=10)
ax = axes[1]; style_ax(ax)
b2 = ax.bar(x - 0.2, pts, width=0.4, color=GOLD, edgecolor=INK, lw=0.6, label="单局名次积分")
cum = np.cumsum(pts)
ax.plot(x, cum, "-o", color=CINNABAR, lw=2, label="累计积分")
for xi, c in zip(x, cum): ax.text(xi, c + 2, str(c), ha="center", color=CINNABAR, fontsize=10)
ax.set_ylabel("积分", color=INK); ax.set_ylim(0, 70)
ax.set_xticks(x); ax.set_xticklabels(labels, rotation=30, ha="right")
ax.legend(loc="upper left", facecolor=PAPER, edgecolor=GRID)
plt.tight_layout(); plt.savefig(f"{CDIR}/fig1_overview.png", facecolor=PAPER); plt.close()
print("fig1 ok")

# ============ 图2：最大仓位 vs 盈亏（风险关系） ============
fig, ax = plt.subplots(figsize=(10, 6.5), facecolor=PAPER); style_ax(ax)
maxpos = [max((abs(r["pos"]) for r in g["trading"]), default=0) for g in official]
sc = ax.scatter(maxpos, pnls, s=150, c=colors, edgecolor=INK, zorder=3)
for xi, yi, lb in zip(maxpos, pnls, labels):
    ax.annotate(lb, (xi, yi), xytext=(7, 4), textcoords="offset points", color=INK, fontsize=10)
ax.axhline(0, color=INK, lw=1)
z = np.polyfit(maxpos, pnls, 1); xs = np.linspace(min(maxpos), max(maxpos), 50)
ax.plot(xs, np.polyval(z, xs), "--", color=GOLD, lw=1.8, label=f"趋势：斜率 {z[0]:.1f}")
ax.set_xlabel("当轮最大绝对仓位（手）", color=INK)
ax.set_ylabel("单局盈亏", color=INK)
ax.set_title("仓位即险境 · 敞口越大，盈亏越向深处滑落", color=INK, fontsize=15)
ax.legend(facecolor=PAPER, edgecolor=GRID)
plt.tight_layout(); plt.savefig(f"{CDIR}/fig2_risk.png", facecolor=PAPER); plt.close()
print("fig2 ok")

# ============ 图3：11 局价格网格（归一化） ============
ncol = 4; nrow = 3
fig, axes = plt.subplots(nrow, ncol, figsize=(15, 9), facecolor=PAPER)
axes = axes.ravel()
for k, g in enumerate(official):
    ax = axes[k]; style_ax(ax)
    tr = g["trading"]
    t = np.array([(r["sec"] - tr[0]["sec"]) / 60.0 for r in tr])
    px = np.array([r["last"] for r in tr], dtype=float)
    op = tr[0]["open"]
    ax.plot(t, px / op * 100, color=CINNABAR if g["final_pnl"] >= 0 else CELADON, lw=1.8)
    ax.axhline(100, color=GOLD, ls="--", lw=1)
    ax.set_title(g["label"].split("·")[1], color=INK, fontsize=12)
    ax.tick_params(labelsize=8)
for k in range(len(official), len(axes)):
    axes[k].axis("off")
fig.suptitle("各局价格归一化走势（开盘=100，金虚线为开盘锚）", color=INK, fontsize=16)
plt.tight_layout(rect=[0, 0, 1, 0.96]); plt.savefig(f"{CDIR}/fig3_grid.png", facecolor=PAPER); plt.close()
print("fig3 ok")

# ============ 图4：代表局详图（价格+仓位双轴） ============
def detail(g, fname, note):
    tr = g["trading"]
    t = np.array([(r["sec"] - tr[0]["sec"]) / 60.0 for r in tr])
    px = np.array([r["last"] for r in tr], dtype=float)
    pos = np.array([r["pos"] for r in tr], dtype=float)
    fig, ax1 = plt.subplots(figsize=(11, 6), facecolor=PAPER); style_ax(ax1)
    ax1.plot(t, px, color=INK, lw=2, label="最新价")
    ax1.set_ylabel("价格（计价单位）", color=INK); ax1.set_xlabel("局内时间（分钟）", color=INK)
    ax2 = ax1.twinx()
    ax2.fill_between(t, pos, 0, where=pos >= 0, color=CINNABAR, alpha=0.25, step="post")
    ax2.fill_between(t, pos, 0, where=pos < 0, color=CELADON, alpha=0.25, step="post")
    ax2.plot(t, pos, color=GOLD, lw=1.2, label="净持仓")
    ax2.set_ylabel("净持仓（手）", color=GOLD); ax2.set_ylim(-11, 11)
    ax2.axhline(0, color=GRID, lw=0.8)
    ax1.set_title(f"{g['label']} · {note}（盈亏 {g['final_pnl']:.2f}）", color=INK, fontsize=14)
    plt.tight_layout(); plt.savefig(f"{CDIR}/{fname}", facecolor=PAPER); plt.close()
    print(fname, "ok")

detail(games[3], "fig4_shanghai.png", "做市收租的全胜范本")
detail(games[6], "fig6_steps.png", "信号反向，空头被趋势吞没")
detail(games[10], "fig10_friend.png", "浮盈近千，尾盘平仓尽付东流")
detail(games[11], "fig11_unlock.png", "高位多头，信号暴跌后割肉")
print("all charts done")
