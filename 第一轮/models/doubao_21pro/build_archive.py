#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从服务端权威全量存档提取「我」的逐局数据，输出 my_archive.json。"""
import json

SRC = "/Users/yuanf/DoubaoWork/chats/2026-11-19/new-chat-1/赛后数据/竞技场-258334-20261122-004051.json"
OUT = "/Users/yuanf/DoubaoWork/chats/2026-11-21/new-chat-5/logs/my_archive.json"
MY = "bc1554e1705eff9a"

d = json.load(open(SRC, encoding="utf-8"))

# 我的总战绩
my_std = next(s for s in d["standings"] if s["id"] == MY)

games_out = []
for g in d["games"]:
    # 我在本局的排名/盈亏
    my_rank = next((r for r in g["ranking"] if r["id"] == MY), None)
    # 我在本局的逐笔成交
    my_review = next((p for p in g["review"]["players"] if p["id"] == MY), None)
    trades = my_review["trades"] if my_review else []
    # 归一化成交（价格分->单位）
    trades_n = []
    for t in trades:
        tt = dict(t)
        if "price" in tt: tt["price_unit"] = round(t["price"] / 100.0, 3)
        trades_n.append(tt)
    games_out.append({
        "number": g["number"],
        "question": g["question"],
        "unit": g["unit"],
        "practice": g["practice"],
        "opening": g["openingPrice"] / 100.0,
        "settlement": g["settlementPrice"] / 100.0,
        "my_pnl": (my_rank["pnl"] / 100.0) if my_rank else 0,
        "my_rank": my_rank["rank"] if my_rank else None,
        "my_points": my_rank["points"] if my_rank else 0,
        "signals": g["signals"],
        "history": g["history"],
        "resolution_note": g["resolution"].get("note", ""),
        "trades": trades_n,
        "n_trades": len(trades_n),
        "n_qty": sum(t.get("qty", 0) for t in trades_n),
    })

archive = {
    "roomCode": d["roomCode"],
    "my_id": MY,
    "my_name": my_std["name"],
    "my_total_points": my_std["points"],
    "my_wins": my_std["wins"],
    "my_seconds": my_std["seconds"],
    "my_results": my_std["results"],
    "games": games_out,
}
json.dump(archive, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

print("选手:", my_std["name"], "总分:", my_std["points"])
tot_pnl = 0
for g in games_out:
    tot_pnl += g["my_pnl"]
    print(f"局{g['number']:>2} {'测试' if g['practice'] else '正式'} 开{g['opening']:>8} 结{g['settlement']:>8} "
          f"盈亏{g['my_pnl']:>9} rank{g['my_rank']:>2} 成交{g['n_trades']:>3}笔/{g['n_qty']:>3}手")
print("12局盈亏合计(含测试):", round(tot_pnl, 2))
