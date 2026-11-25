#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""关键局价格路径+持仓详图，及分轮持仓小多图。"""
import os, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"]=["Kaiti SC","Times New Roman"]
plt.rcParams["font.family"]="sans-serif"
plt.rcParams["axes.unicode_minus"]=False
plt.rcParams["font.size"]=11
plt.rcParams["figure.dpi"]=150
INK="#26221f";CINNABAR="#9c3b32";CELADON="#3f6b63";GOLD="#c2a05a";PAPER="#f6f1e7";GRID="#d8cfbd"
BASE="/Users/yuanf/DoubaoWork/chats/2026-11-21/new-chat-5"
CDIR=os.path.join(BASE,"charts2")
A=json.load(open(os.path.join(BASE,"logs/my_archive.json"),encoding="utf-8"))
SHORT={2:"古巴",3:"高铁",4:"上港",5:"机场",6:"鸡蛋",7:"步数",8:"相册",9:"未读",10:"屏幕",11:"好友",12:"解锁"}
GM={g["number"]:g for g in A["games"]}

def detail(num, fname, note):
    g=GM[num]; tr=g["trades"]; n=len(tr)
    x=np.arange(n)
    price=np.array([t["price_unit"] for t in tr])
    pos=np.array([t["positionAfter"] for t in tr])
    rounds=np.array([t["round"] for t in tr])
    fig,(axp,axq)=plt.subplots(2,1,figsize=(10.5,6.8),sharex=True,
                               gridspec_kw={"height_ratios":[2.4,1]})
    # 轮次背景
    rbounds=[0]+[i for i in range(1,n) if rounds[i]!=rounds[i-1]]+[n]
    rcols=["#efe7d6","#e7dcc4"]
    for k in range(len(rbounds)-1):
        for ax in (axp,axq):
            ax.axvspan(rbounds[k],rbounds[k+1]-1,color=rcols[k%2],zorder=0)
        axp.text((rbounds[k]+rbounds[k+1]-1)/2, axp.get_ylim()[1]*0.96 if False else 0,
                 "",)
    # 价格
    axp.plot(x,price,color=INK,lw=1,alpha=.55,zorder=2)
    buy=rounds*0+[t["side"]=="buy" for t in tr]
    for t,xi,pi in zip(tr,x,price):
        c=CINNABAR if t["side"]=="buy" else CELADON
        axp.scatter(xi,pi,color=c,s=16,zorder=3,edgecolor="none")
    axp.axhline(g["settlement"],color=GOLD,lw=1.8,ls="--",zorder=4)
    axp.text(n-1,g["settlement"],f" 真值 {g['settlement']:g}",va="center",ha="left",
             fontsize=10,color="#8a6d2f")
    axp.scatter([0],[g["opening"]],color=INK,s=55,marker="D",zorder=5)
    axp.text(0,g["opening"],f" 开盘 {g['opening']:g}",va="bottom",ha="left",
            fontsize=9.5,color=INK)
    axp.set_facecolor(PAPER); axp.set_ylabel("价格"); axp.grid(color=GRID,lw=.6)
    for s in axp.spines.values(): s.set_color(GRID)
    axp.set_title(f"局{num} · {SHORT[num]}：{g['question'][:30]}",color=INK,fontsize=13,pad=8)
    # 轮次标签
    for k in range(len(rbounds)-1):
        axq.text((rbounds[k]+rbounds[k+1]-1)/2, axq.get_ylim()[1] if False else 0,
                 f"r{rounds[rbounds[k]]}",ha="center",va="bottom",fontsize=9,color="#8a8074")
    # 持仓
    qc=[CINNABAR if p>=0 else CELADON for p in pos]
    axq.bar(x,pos,color=qc,width=1.0,edgecolor="none")
    axq.axhline(0,color=INK,lw=.8)
    axq.set_facecolor(PAPER); axq.set_ylabel("持仓"); axq.set_xlabel("成交序号")
    axq.grid(color=GRID,lw=.6)
    for s in axq.spines.values(): s.set_color(GRID)
    axq.text(.005,.06,note,transform=axq.transAxes,fontsize=9.5,color="#5b5248",
             bbox=dict(boxstyle="round,pad=.4",fc="#fbf6ec",ec=GRID))
    plt.tight_layout(); plt.savefig(f"{CDIR}/{fname}"); plt.close()

detail(7,"d7_steps.png","末仓 −4 手空头，真值却在 8476 高位；做市浮盈被空头结算吞没。")
detail(6,"d6_egg.png","fair 初值 12 严重低估，r3 才修正为 30；6 手空头留在高位结算。")
detail(11,"d11_friend.png","fair 初值 500，在 1000 上方持续做空；r3 平仓时浮盈大幅回吐。")
detail(12,"d12_unlock.png","r3 一度追多至 +9 手，80 多的真值低于开盘 100，方向反复挨打。")

# ---------- 分轮持仓小多图（11 正式局） ----------
formal=[g for g in A["games"] if not g["practice"]]
fig,axes=plt.subplots(3,4,figsize=(13,7.6),sharey=False)
axes=axes.ravel()
for ax,g in zip(axes,formal):
    tr=g["trades"]; x=np.arange(len(tr))
    pos=np.array([t["positionAfter"] for t in tr])
    rounds=np.array([t["round"] for t in tr])
    rb=[0]+[i for i in range(1,len(tr)) if rounds[i]!=rounds[i-1]]+[len(tr)]
    for k in range(len(rb)-1):
        ax.axvspan(rb[k],rb[k+1]-1,color=["#efe7d6","#e7dcc4"][k%2],zorder=0)
    ax.plot(x,pos,color=INK,lw=.9)
    ax.axhline(0,color="#9c3b32",lw=.8,ls=":")
    ax.set_facecolor(PAPER)
    for s in ax.spines.values(): s.set_color(GRID)
    endp=pos[-1] if len(pos) else 0
    ax.set_title(f"{SHORT[g['number']]}（末仓{endp:+g}）",fontsize=10.5,color=INK)
    ax.tick_params(labelsize=8)
for ax in axes[len(formal):]: ax.axis("off")
fig.suptitle("正式十一局 · 逐笔持仓轨迹（背景深浅区分轮次，虚线为零仓）",fontsize=14,color=INK)
plt.tight_layout(rect=[0,0,1,.97]); plt.savefig(f"{CDIR}/d_posgrid.png"); plt.close()
print("详图完成:",sorted(f for f in os.listdir(CDIR) if f.startswith("d")))
