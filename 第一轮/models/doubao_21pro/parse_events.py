#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析 events.log，按局汇总价格/仓位/盈亏序列，输出 game_stats.json 与逐笔采样。"""
import re, json, datetime

LOG = "/Users/yuanf/DoubaoWork/chats/2026-11-21/new-chat-5/logs/events.log"
OUT = "/Users/yuanf/DoubaoWork/chats/2026-11-21/new-chat-5/logs/game_stats.json"

# 每局 label 的起始时间（来自 bot.log 阶段切换到 estimate 的时刻 HH:MM:SS）
# (label, 进入该局 estimate 的时间)
GAME_BOUNDS = [
    ("测试局·肯德基", "23:12:04"),
    ("正式第1题·古巴", "23:21:20"),
    ("正式第2题·高铁", "23:30:19"),
    ("正式第3题·上海港", "23:37:42"),
    ("正式第4题·机场", "23:43:51"),
    ("正式第5题·鸡蛋", "23:51:29"),
    ("正式第6题·步数", "23:57:44"),
    ("正式第7题·相册照片", "00:03:30"),
    ("正式第8题·微信未读", "00:09:36"),
    ("正式第9题·屏幕时长", "00:16:22"),
    ("正式第10题·好友", "00:22:20"),
    ("正式第11题·解锁", "00:28:42"),
]

pat = re.compile(
    r"\[(?P<ts>[\d:.]+)\] phase=(?P<phase>\w+) r=(?P<r>-?\d+) remain=(?P<remain>-?\d+) "
    r"open=(?P<open>[\d.]+|None) last=(?P<last>[\d.]+|None) bid=(?P<bid>[\d.]+|None) ask=(?P<ask>[\d.]+|None) "
    r"pos=(?P<pos>-?\d+) avg=(?P<avg>[\d.]+) realized=(?P<realized>-?\d+) pnl=(?P<pnl>-?\d+) orders=(?P<orders>\d+) trades=(?P<trades>\d+)"
)

# 每局名次积分（测试局不计分）；与最终总分 58 对齐
POINTS = {
    "测试局·肯德基": 0, "正式第1题·古巴": 15, "正式第2题·高铁": 10,
    "正式第3题·上海港": 10, "正式第4题·机场": 7, "正式第5题·鸡蛋": 1,
    "正式第6题·步数": 3, "正式第7题·相册照片": 1, "正式第8题·微信未读": 7,
    "正式第9题·屏幕时长": 1, "正式第10题·好友": 2, "正式第11题·解锁": 1,
}

def num(x):
    return None if x == "None" else float(x)

def to_sec(hhmmss):
    hhmmss = hhmmss.split(".")[0]
    h, m, s = map(int, hhmmss.split(":"))
    return h * 3600 + m * 60 + s

rows = []
with open(LOG, encoding="utf-8") as f:
    for line in f:
        m = pat.match(line)
        if not m:
            continue
        d = m.groupdict()
        rows.append({
            "ts": d["ts"], "sec": to_sec(d["ts"]),
            "phase": d["phase"], "r": int(d["r"]), "remain": int(d["remain"]),
            "open": num(d["open"]), "last": num(d["last"]),
            "bid": num(d["bid"]), "ask": num(d["ask"]),
            "pos": int(d["pos"]), "avg": float(d["avg"]),
            "realized": float(d["realized"]), "pnl": float(d["pnl"]),
            "orders": int(d["orders"]), "trades": int(d["trades"]),
        })

# 时间跨午夜：00:xx 的秒数加 24h
for r in rows:
    if r["ts"].startswith("00:"):
        r["sec"] += 24 * 3600

bounds = [(lb, to_sec(t) + (24 * 3600 if t.startswith("00:") else 0)) for lb, t in GAME_BOUNDS]

games = []
for i, (lb, start) in enumerate(bounds):
    end = bounds[i + 1][1] if i + 1 < len(bounds) else 10 ** 9
    grp = [r for r in rows if start <= r["sec"] < end]
    if not grp:
        continue
    trad = [r for r in grp if r["phase"] == "trading"]
    lasts = [r["last"] for r in trad if r["last"] is not None]
    poss = [r["pos"] for r in trad]
    # 局末真实值：取最后一条记录（closed/settled 阶段保留权威 me 数据）
    final_realized = grp[-1]["realized"]
    final_pnl = grp[-1]["pnl"]
    rounds = sorted({r["r"] for r in trad})
    # 每轮开盘/收盘
    per_round = []
    for rn in rounds:
        rg = [r for r in trad if r["r"] == rn]
        rl = [r["last"] for r in rg if r["last"] is not None]
        per_round.append({
            "round": rn,
            "first": rl[0] if rl else None,
            "last": rl[-1] if rl else None,
            "hi": max(rl) if rl else None,
            "lo": min(rl) if rl else None,
        })
    games.append({
        "label": lb,
        "start_ts": grp[0]["ts"], "end_ts": grp[-1]["ts"],
        "opening": trad[0]["open"] if trad else None,
        "close": lasts[-1] if lasts else None,
        "hi": max(lasts) if lasts else None,
        "lo": min(lasts) if lasts else None,
        "max_abs_pos": max((abs(p) for p in poss), default=0),
        "final_realized": round(final_realized / 100.0, 2),
        "final_pnl": round(final_pnl / 100.0, 2),
        "points": POINTS.get(lb, 0),
        "n_events": len(grp),
        "rounds": per_round,
        "max_round_index": max(rounds) if rounds else None,
    })

json.dump(games, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

print(f"共解析 {len(rows)} 行，{len(games)} 局")
tot_pnl = sum(g["final_realized"] for g in games if g["label"] != "测试局·肯德基")
tot_pts = sum(g["points"] for g in games)
for g in games:
    print(f"{g['label']:<16} 开={g['opening']} 收={g['close']} 最大仓位={g['max_abs_pos']} "
          f"盈亏={g['final_realized']:>9} 积分={g['points']:>2}")
print(f"\n正式局累计盈亏(单位)={round(tot_pnl,2)}  累计积分={tot_pts}")
