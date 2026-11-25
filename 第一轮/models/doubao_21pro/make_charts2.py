#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基于权威存档 my_archive.json 生成复盘图表（charts2/）。"""
import os, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Patch
import numpy as np

plt.rcParams["font.sans-serif"] = ["Kaiti SC", "Times New Roman"]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 12
plt.rcParams["figure.dpi"] = 150

INK = "#26221f"; CINNABAR = "#9c3b32"; CELADON = "#3f6b63"
GOLD = "#c2a05a"; PAPER = "#f6f1e7"; GRID = "#d8cfbd"; BLUE = "#3b5b78"

BASE = "/Users/yuanf/DoubaoWork/chats/2026-11-21/new-chat-5"
CDIR = os.path.join(BASE, "charts2"); os.makedirs(CDIR, exist_ok=True)
SRC = "/Users/yuanf/DoubaoWork/chats/2026-11-19/new-chat-1/赛后数据/竞技场-258334-20261122-004051.json"

A = json.load(open(os.path.join(BASE, "logs/my_archive.json"), encoding="utf-8"))
D = json.load(open(SRC, encoding="utf-8"))
SHORT = {2:"古巴",3:"高铁",4:"上港",5:"机场",6:"鸡蛋",7:"步数",
         8:"相册",9:"未读",10:"屏幕",11:"好友",12:"解锁"}
formal = [g for g in A["games"] if not g["practice"]]
nums = [g["number"] for g in formal]
labels = [f"{n}\n{SHORT[n]}" for n in nums]

def style_ax(ax):
    ax.set_facecolor(PAPER)
    for s in ax.spines.values(): s.set_color(GRID)
    ax.grid(axis="y", color=GRID, lw=.7, alpha=.7)
    ax.tick_params(colors=INK)

def cash_pos(g):
    cash=0; pos=0
    for t in g["trades"]:
        p,q=t["price"],t["qty"]
        if t["side"]=="buy": cash-=p*q; pos+=q
        else: cash+=p*q; pos-=q
    return cash/100.0, pos, pos*g["settlement"]

# ---------- 图1：权威逐局盈亏 ----------
fig, ax = plt.subplots(figsize=(11,5.2))
pnls=[g["my_pnl"] for g in formal]
cols=[CINNABAR if p>=0 else CELADON for p in pnls]
b=ax.bar(labels, pnls, color=cols, width=.66, edgecolor=INK, lw=.6)
for r,g in zip(b,formal):
    h=r.get_height()
    ax.text(r.get_x()+r.get_width()/2, h+(40 if h>=0 else -120),
            f"{h:g}", ha="center", va="bottom" if h>=0 else "top",
            fontsize=10, color=INK, family="Times New Roman")
    ax.text(r.get_x()+r.get_width()/2, 60, f"第{g['my_rank']}名",
            ha="center", va="bottom", fontsize=9, color="#6b6258")
ax.axhline(0,color=INK,lw=.9)
ax.set_title("正式十一局 · 权威逐局盈亏（红盈绿亏，柱内为名次）", color=INK, fontsize=15, pad=12)
ax.set_ylabel("盈亏（计价单位）"); style_ax(ax)
plt.tight_layout(); plt.savefig(f"{CDIR}/c1_pnl.png"); plt.close()

# ---------- 图2：做市现金 vs 持仓结算 ----------
fig, ax = plt.subplots(figsize=(11,5.4))
cashv=[]; holdv=[]; totv=[]
for g in formal:
    c,po,h=cash_pos(g); cashv.append(c); holdv.append(h); totv.append(c+h)
x=np.arange(len(nums)); w=.38
ax.bar(x-w/2, cashv, w, label="做市 / 已实现现金", color=GOLD, edgecolor=INK, lw=.5)
ax.bar(x+w/2, holdv, w, label="终局方向持仓结算", color=BLUE, edgecolor=INK, lw=.5)
ax.plot(x, totv, "o-", color=CINNABAR, lw=1.6, ms=5, label="合计 = 权威盈亏")
ax.axhline(0,color=INK,lw=.9)
ax.set_xticks(x); ax.set_xticklabels(labels)
ax.set_title("做市的利润，被方向持仓吞噬：现金 +37666，持仓 −39201", color=INK, fontsize=14, pad=10)
ax.set_ylabel("金额（计价单位）"); ax.legend(frameon=False, fontsize=10); style_ax(ax)
plt.tight_layout(); plt.savefig(f"{CDIR}/c2_decomp.png"); plt.close()

# ---------- 图3：每局积分与累计 ----------
fig, ax = plt.subplots(figsize=(11,5))
pts=[g["my_points"] for g in formal]
cum=np.cumsum(pts)
b=ax.bar(labels, pts, color=GOLD, width=.6, edgecolor=INK, lw=.5, label="单局积分")
ax2=ax.twinx()
ax2.plot(np.arange(len(nums)), cum, "o-", color=CINNABAR, lw=1.8, ms=6, label="累计积分")
for i,c in enumerate(cum):
    ax2.text(i, c+2.5, str(c), ha="center", fontsize=9, color=CINNABAR, family="Times New Roman")
ax.set_title("积分轨迹：首局登顶后逐级滑落，终局 58 分", color=INK, fontsize=14, pad=10)
ax.set_ylabel("单局积分"); ax2.set_ylabel("累计积分", color=CINNABAR)
ax2.tick_params(colors=CINNABAR); style_ax(ax); ax2.grid(False)
ax.legend(loc="upper right", frameon=False, fontsize=10)
plt.tight_layout(); plt.savefig(f"{CDIR}/c3_points.png"); plt.close()

# ---------- 图4：开盘相对结算的偏离 ----------
fig, ax = plt.subplots(figsize=(11,4.8))
dev=[((g["opening"]-g["settlement"])/g["settlement"]*100) if g["settlement"] else np.nan for g in formal]
cols=[CINNABAR if (d is not None and d>=0) else CELADON for d in dev]
b=ax.bar(labels, dev, width=.66, color=cols, edgecolor=INK, lw=.5)
for r,d,g in zip(b,dev,formal):
    if d is None or np.isnan(d):
        ax.text(r.get_x()+r.get_width()/2, 2, "真值=0\n(开盘36.6)", ha="center",
                va="bottom", fontsize=8.5, color=INK)
        continue
    h=r.get_height()
    ax.text(r.get_x()+r.get_width()/2, h+(1.5 if h>=0 else -1.5),
            f"{h:+.1f}%", ha="center", va="bottom" if h>=0 else "top",
            fontsize=9.5, family="Times New Roman", color=INK)
ax.axhline(0,color=INK,lw=.9)
ax.set_title("初始定价偏差：开盘价相对真值的偏离百分比（正=高估，负=低估）", color=INK, fontsize=13, pad=10)
ax.set_ylabel("偏离 %"); style_ax(ax)
plt.tight_layout(); plt.savefig(f"{CDIR}/c4_openbias.png"); plt.close()

# ---------- 图9：最终积分榜 ----------
sts=sorted(D["standings"], key=lambda s:-s["points"])
fig, ax = plt.subplots(figsize=(10,6.6))
names=[s["name"].strip().replace("豆包-远方的 mac-","").replace("豆包-远方的mac-","") for s in sts]
vals=[s["points"] for s in sts]
cols=[CINNABAR if s["id"]==A["my_id"] else "#8a8074" for s in sts]
y=np.arange(len(sts))[::-1]
b=ax.barh(y, vals, color=cols, edgecolor=INK, lw=.5)
for yy,s in zip(y,sts):
    ax.text(s["points"]+1.5, yy, str(s["points"]), va="center", fontsize=10,
            family="Times New Roman", color=INK)
ax.set_yticks(y); ax.set_yticklabels(names, fontsize=10.5)
ax.set_title("最终积分榜：榜首 124 分，我以 58 分垫底（朱砂高亮）", color=INK, fontsize=14, pad=10)
ax.set_xlabel("累计积分"); ax.set_xlim(0,135)
ax.set_facecolor(PAPER)
for s in ax.spines.values(): s.set_color(GRID)
ax.grid(axis="x", color=GRID, lw=.7); ax.tick_params(colors=INK)
plt.tight_layout(); plt.savefig(f"{CDIR}/c9_standings.png"); plt.close()

print("全局图完成:", sorted(os.listdir(CDIR)))
