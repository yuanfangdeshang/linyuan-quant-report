#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.family"] = ["Kaiti SC", "Times New Roman", "PingFang SC"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 11

BASE = os.path.dirname(os.path.abspath(__file__))
A = json.load(open(os.path.join(BASE, "authoritative.json")))
G = A["games"]
os.makedirs(os.path.join(BASE, "charts2"), exist_ok=True)
CD = os.path.join(BASE, "charts2")

BLUE, RED, ORANGE, GRAY = "#2f5d8a", "#b8423a", "#e0a458", "#9db7cc"
labels = [f"G{g['number']}" for g in G]
short = ["肯德基", "104国", "高铁", "上海港", "机场", "鸡蛋", "步数", "照片", "未读", "屏幕", "好友", "解锁"]

# ---------- 1. cumulative points ----------
pts = [g["my_points"] for g in G]
cum = np.cumsum(pts)
fig, ax = plt.subplots(figsize=(10, 5.2))
ax.plot(range(12), cum, "-o", color=BLUE, lw=2.4, markersize=7, label="本人累计积分")
for i, v in enumerate(cum):
    ax.annotate(str(v), (i, v), textcoords="offset points", xytext=(0, -16),
                ha="center", fontsize=9, color=BLUE)
ax.set_xticks(range(12)); ax.set_xticklabels([f"{l}\n{s}" for l, s in zip(labels, short)])
ax.set_ylabel("累计积分"); ax.set_ylim(0, 90)
ax.set_title("图1  本人累计积分走势（G1 测试局不计分，终值 80）")
ax.legend(loc="upper left"); ax.grid(alpha=.25)
fig.tight_layout(); fig.savefig(f"{CD}/01_points.png", dpi=150); plt.close(fig)

# ---------- 2. per-game pnl: mine vs winner ----------
mine = [g["my_pnl"] / 100.0 for g in G]
win = [g["winner_pnl"] / 100.0 if g["winner_pnl"] is not None else 0 for g in G]
x = np.arange(12); w = 0.38
fig, ax = plt.subplots(figsize=(11, 5.2))
ax.bar(x - w/2, win, w, color=GRAY, label="单局冠军盈亏（元级）")
ax.bar(x + w/2, mine, w, color=BLUE, label="本人盈亏（全程 0）")
ax.axhline(0, color="#333", lw=1)
ax.set_xticks(x); ax.set_xticklabels([f"{l}\n{s}" for l, s in zip(labels, short)])
ax.set_ylabel("盈亏（单位：游戏计价单位）")
ax.set_title("图2  各局盈亏对照：本人全程零成交，冠军盈亏由方向×重仓×持仓到结算取得")
ax.legend(); ax.grid(alpha=.25, axis="y")
fig.tight_layout(); fig.savefig(f"{CD}/02_pnl.png", dpi=150); plt.close(fig)

# ---------- 3. per-game rank ----------
ranks = [g["my_rank"] for g in G]
fig, ax = plt.subplots(figsize=(10, 5.2))
cols = [ORANGE if r == min(ranks) else (RED if r == max(ranks) else BLUE) for r in ranks]
ax.bar(range(12), ranks, color=cols)
for i, r in enumerate(ranks):
    ax.annotate(f"第{r}", (i, r), textcoords="offset points", xytext=(0, 6),
                ha="center", fontsize=9)
ax.set_xticks(range(12)); ax.set_xticklabels([f"{l}\n{s}" for l, s in zip(labels, short)])
ax.set_ylim(0, 16); ax.set_ylabel("单局名次（共 15 个模型位）")
ax.set_title("图3  本人单局名次走势：最佳第 5（G6 鸡蛋），最差第 12（G5 机场 / G9 未读）")
ax.grid(alpha=.25, axis="y")
fig.tight_layout(); fig.savefig(f"{CD}/03_rank.png", dpi=150); plt.close(fig)

# ---------- 4. final standings ----------
st = sorted(A["standings"], key=lambda s: s["points"])
names = [s["name"] for s in st]; pvals = [s["points"] for s in st]
me_name = A["me_name"]
cols = [BLUE if n == me_name else GRAY for n in names]
fig, ax = plt.subplots(figsize=(10, 6.5))
ax.barh(names, pvals, color=cols)
for i, v in enumerate(pvals):
    ax.text(v + 1, i, str(v), va="center", fontsize=9)
ax.set_title("图4  全场最终积分排名（15 个模型位，深色为本人）")
ax.set_xlabel("累计积分"); ax.grid(alpha=.25, axis="x")
fig.tight_layout(); fig.savefig(f"{CD}/04_standings.png", dpi=150); plt.close(fig)

# ---------- 5. open vs settle (log) ----------
opens = [g["open"] for g in G]; settles = [g["settle"] for g in G]
fig, ax = plt.subplots(figsize=(11, 5.4))
ax.plot(range(12), opens, "-o", color=GRAY, lw=1.8, label="开盘价（全场估价中位数）")
ax.plot(range(12), settles, "-s", color=RED, lw=1.8, label="结算价（公开真值）")
ax.set_yscale("symlog", linthresh=10)
ax.set_xticks(range(12)); ax.set_xticklabels([f"{l}\n{s}" for l, s in zip(labels, short)])
ax.set_ylabel("数值（对称对数轴）")
ax.set_title("图5  开盘价 vs 结算真值：个人数据题（G6–G12）开盘价普遍失真")
ax.legend(); ax.grid(alpha=.25, which="both")
fig.tight_layout(); fig.savefig(f"{CD}/05_open_vs_settle.png", dpi=150); plt.close(fig)

# ---------- 6. price path 12 panels ----------
fig, axes = plt.subplots(3, 4, figsize=(15, 9))
for ax, g in zip(axes.flat, G):
    path = [h["price"] for h in g["history"]] + [g["settle"]]
    ax.plot(range(len(path)), path, "-o", color=BLUE, lw=1.5, markersize=4)
    ax.axhline(g["settle"], color=RED, ls="--", lw=1.3, label=f"真值 {g['settle']:g}")
    ax.set_title(f"G{g['number']} {short[g['number']-1]}", fontsize=11)
    ax.tick_params(labelsize=8); ax.grid(alpha=.2)
axes.flat[0].legend(fontsize=8)
fig.suptitle("图6  12 局价格路径全景（各轮收盘价 → 结算真值）", fontsize=13)
fig.tight_layout(); fig.savefig(f"{CD}/06_price_path.png", dpi=150); plt.close(fig)

# ---------- 7. estimate error ----------
err = []
for g in G:
    if g["settle"] == 0 or g["my_estimate"] is None:
        err.append(None)
    else:
        err.append((g["my_estimate"] - g["settle"]) / g["settle"] * 100)
fig, ax = plt.subplots(figsize=(11, 5.2))
ev = [v if v is not None else 0 for v in err]
cols = [BLUE if (v is not None and abs(v) <= 2) else (ORANGE if (v is not None and abs(v) <= 10) else RED) if v is not None else GRAY for v in err]
ax.bar(range(12), ev, color=cols)
ax.axhline(0, color="#333", lw=1)
for i, (v, g) in enumerate(zip(err, G)):
    if v is None:
        ax.annotate("真值0\n不可比", (i, 0), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=8, color=RED)
    else:
        ax.annotate(f"估{g['my_estimate']:g}\n真{g['settle']:g}\n{v:+.0f}%", (i, v),
                    textcoords="offset points", xytext=(0, 6 if v >= 0 else -34),
                    ha="center", fontsize=7.5)
ax.set_xticks(range(12)); ax.set_xticklabels([f"{l}\n{s}" for l, s in zip(labels, short)])
ax.set_ylabel("开局估价相对真值误差 (%)")
ax.set_title("图7  本人开局估价准确度：宏观题命中，个人场景题先验普遍跑偏")
ax.grid(alpha=.25, axis="y")
fig.tight_layout(); fig.savefig(f"{CD}/07_estimate_error.png", dpi=150); plt.close(fig)

print("charts:", sorted(os.listdir(CD)))
