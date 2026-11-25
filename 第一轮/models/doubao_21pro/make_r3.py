#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""古巴局 r3：fair 两次切换 + 仓位从 -8 翻到 +8 的 60 秒"""
import os, re, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

plt.rcParams["font.sans-serif"]=["Kaiti SC","Times New Roman"]
plt.rcParams["font.family"]="sans-serif"
plt.rcParams["axes.unicode_minus"]=False
plt.rcParams["font.size"]=11
plt.rcParams["figure.dpi"]=160
INK="#26221f";RED="#9c3b32";GREEN="#3f6b63";GOLD="#c2a05a";PAPER="#f8f4ec";GRID="#ddd3c0"
BASE="/Users/yuanf/DoubaoWork/chats/2026-11-21/new-chat-5"

# 事件路径
pat=re.compile(r'^\[(\d\d):(\d\d):([\d.]+)\] phase=trading r=3 .*?last=([\d.]+) bid=([\d.]+) ask=([\d.]+) pos=(-?\d+)')
t0=None; path=[]
for ln in open(os.path.join(BASE,"logs/events.log"),encoding="utf-8"):
    m=pat.match(ln)
    if not m: continue
    hh,mm,ss,last,bid,ask,pos=m.groups()
    t=int(hh)*3600+int(mm)*60+float(ss)
    if t0 is None: t0=t
    path.append((t-t0, float(last), int(pos)))
path.sort()
# 只保留到 r3 结束（60 秒）
path=[p for p in path if p[0]<=61]

A=json.load(open(os.path.join(BASE,"logs/my_archive.json"),encoding="utf-8"))
g=[x for x in A["games"] if x["number"]==2][0]
tr=[t for t in g["trades"] if t["round"]==3]
base_ms=tr[0]["at"]-path[0][0]*1000 if False else None
# 用成交的绝对时间对齐：首笔 at 对应钟表时刻
import datetime
first_dt=datetime.datetime.fromtimestamp(tr[0]["at"]/1000)
first_t=first_dt.hour*3600+first_dt.minute*60+first_dt.second+first_dt.microsecond/1e6
off=first_t-t0  # path 的 0 点对应钟表
seg=[]
for t in tr:
    dt=datetime.datetime.fromtimestamp(t["at"]/1000)
    tt=dt.hour*3600+dt.minute*60+dt.second+dt.microsecond/1e6
    seg.append((tt-t0, t["price_unit"], t["side"], t["qty"], t["positionAfter"]))

fig,ax=plt.subplots(figsize=(11,6.2))
ax.set_facecolor(PAPER);fig.patch.set_facecolor(PAPER)
x=[p[0] for p in path];y=[p[1] for p in path]
ax.plot(x,y,color=INK,lw=1.4,alpha=.55,label="最新价",zorder=2)

# fair 阶梯：27:24 前 10.99，之后 11.25；r3 末回 10.99（按 actions 实际 11.25 持续）
# 用钟表 27:24.305 相对 t0 计算
switch=23*3600+27*60+24.305 - t0
ax.plot([0,switch],[10.99,10.99],color=GOLD,lw=2.6,ls="-",label="我的心理价 fair",zorder=3)
ax.plot([switch,61],[11.25,11.25],color=GOLD,lw=2.6,ls="-",zorder=3)
ax.plot([switch,switch],[10.99,11.25],color=GOLD,lw=1.4,ls=":",zorder=3)
ax.axhline(10.99,color="#b5732f",lw=1.2,ls="--",alpha=.85,label="真值 10.99",zorder=1)

# 成交点
for tt,pr,side,qty,pos in seg:
    if side=="buy":
        ax.scatter(tt,pr,marker="^",s=110,color=RED,edgecolor="white",lw=1.2,zorder=5)
        ax.annotate(f"买{qty}@{pr:.2f}",(tt,pr),xytext=(0,-14),textcoords="offset points",
                    ha="center",fontsize=8.2,color=RED)
    else:
        ax.scatter(tt,pr,marker="v",s=110,color=GREEN,edgecolor="white",lw=1.2,zorder=5)
        ax.annotate(f"卖{qty}@{pr:.2f}",(tt,pr),xytext=(0,14),textcoords="offset points",
                    ha="center",fontsize=8.2,color=GREEN)

ax.axvspan(0,switch,color=GREEN,alpha=.05)
ax.axvspan(switch,61,color=RED,alpha=.05)
ax.annotate("27:24  心理价 10.99 → 11.25\n（下沿 10.50 → 11.00，我开始翻多）",
            xy=(switch,11.52),xytext=(switch+2.4,11.66),fontsize=9.2,color="#7a5a1e",
            arrowprops=dict(arrowstyle="->",color="#7a5a1e",lw=1))

ax.set_xlim(-1,62);ax.set_ylim(10.35,11.85)
ax.set_xlabel("r3 内秒数（0 = 轮首 27:13）",color=INK)
ax.set_ylabel("价格（万平方公里）",color=INK)
ax.set_title("古巴局 r3：我如何用 8 秒把「满仓做空」改成「满仓做多」",color=INK,fontsize=14,pad=12)
for s in ax.spines.values(): s.set_color(GRID)
ax.tick_params(colors=INK)
ax.grid(True,color=GRID,ls=":",lw=.8,alpha=.7)
leg=ax.legend(loc="upper left",frameon=True,facecolor=PAPER,edgecolor=GRID,fontsize=9.5)
leg.get_frame().set_alpha(.95)

# 副轴：仓位
ax2=ax.twinx()
px=[p[0] for p in path];py=[p[2] for p in path]
ax2.plot(px,py,color="#4a5d8f",lw=1.8,alpha=.75,label="持仓（手）")
ax2.axhline(0,color="#4a5d8f",lw=.7,ls="--",alpha=.5)
ax2.set_ylim(-9.5,9.5);ax2.set_ylabel("持仓（手）",color="#4a5d8f")
ax2.tick_params(colors="#4a5d8f")
for s in ax2.spines.values(): s.set_color(GRID)

fig.tight_layout()
out=os.path.join(BASE,"charts2","r3_cuba_flip.png")
fig.savefig(out,facecolor=PAPER)
print("saved",out)
print("r3 成交:",len(seg),"笔, 仓位:",py[0],"->",py[-1])
