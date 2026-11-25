#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild authoritative per-game record from server-side export JSON."""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = "/Users/yuanf/DoubaoWork/chats/2026-11-19/new-chat-1/赛后数据"
MAIN = os.path.join(DATA, "竞技场-258334-20261122-004051.json")
ROOMS = os.path.join(DATA, "rooms-原始快照-20261122-004051.json")
ME = "c64f9cfced6ef32b"

main = json.load(open(MAIN))
rooms = json.load(open(ROOMS))
room = [x for x in rooms["rooms"] if x["code"] == main["roomCode"]][0]

# my estimates from room snapshot states
est_by_game = {}
for g in room["games"]:
    st = g["states"].get(ME, {})
    e = st.get("estimate")
    est_by_game[g["number"]] = None if e is None else e / 100.0

games = []
for g in main["games"]:
    rank_me = next((r for r in g["ranking"] if r["id"] == ME), {})
    rev_me = next((p for p in g["review"]["players"] if p["id"] == ME), {"trades": []})
    winner = g["ranking"][0] if g["ranking"] else {}
    history = [{"round": h["round"], "price": h["price"] / 100.0,
                 "volume": h["volume"], "orders": h["orders"]} for h in g["history"]]
    games.append({
        "number": g["number"],
        "question": g["question"],
        "unit": g["unit"],
        "practice": g["practice"],
        "open": g["openingPrice"] / 100.0,
        "settle": g["resolution"]["price"] / 100.0,
        "resolution_note": g["resolution"].get("note", ""),
        "history": history,
        "signals": [{"round": s["round"], "title": s.get("title", ""),
                     "text": s.get("text", ""), "source": s.get("sourceName", "")}
                    for s in g["signals"]],
        "my_estimate": est_by_game.get(g["number"]),
        "my_pnl": rank_me.get("pnl", 0),
        "my_rank": rank_me.get("rank"),
        "my_points": rank_me.get("points", 0),
        "my_trades": len(rev_me.get("trades", [])),
        "winner_name": winner.get("name"),
        "winner_pnl": winner.get("pnl"),
        "winner_rank": winner.get("rank"),
    })

standings = []
for s in main["standings"]:
    standings.append({
        "id": s["id"], "name": s["name"], "points": s["points"],
        "wins": s.get("wins", 0), "seconds": s.get("seconds", 0),
        "rank": s["rank"],
        "results": s.get("results", []),
    })

out = {
    "room": main["roomCode"],
    "amount_unit": main["amountUnit"],
    "scored_game_count": main["scoredGameCount"],
    "me_id": ME,
    "me_name": next((s["name"] for s in standings if s["id"] == ME), ""),
    "games": games,
    "standings": standings,
}
json.dump(out, open(os.path.join(BASE, "authoritative.json"), "w"),
          ensure_ascii=False, indent=1)

# quick printout
for g in games:
    est = g["my_estimate"]
    print(f"G{g['number']:2} settle={g['settle']:g} open={g['open']:g} est={est} "
          f"rank={g['my_rank']} pts={g['my_points']} pnl={g['my_pnl']} trades={g['my_trades']} "
          f"winner={g['winner_name']}({g['winner_pnl']})")
me = next(s for s in standings if s["id"] == ME)
print("FINAL:", me["points"], "rank", me["rank"], "wins", me["wins"], "seconds", me["seconds"])
