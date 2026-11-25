import json, os, sys

LOG = "events.log"
out = {"resolutions": [], "standings_timeline": [], "my_trades": [],
       "my_orders": [], "phase_timeline": [], "games": []}

last_state_ts = None
seen_res = set()

with open(LOG, "rb") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line.decode("utf-8", "replace"))
        except Exception:
            continue
        t = d.get("t")
        ts = d.get("serverNow") or d.get("at")
        if t == "clock":
            continue
        g = d.get("game") or {}
        me = g.get("me") or {}
        # resolution
        res = g.get("resolution")
        if res and res.get("price") is not None:
            key = (res.get("round"), res.get("price"), res.get("at"))
            if key not in seen_res:
                seen_res.add(key)
                out["resolutions"].append({
                    "ts": ts, "round": res.get("round"),
                    "price": res.get("price"), "note": res.get("note"),
                    "question": (g.get("question") or {}).get("q"),
                    "unit": (g.get("question") or {}).get("unit"),
                    "opening": g.get("openingPrice"), "last": g.get("lastPrice"),
                    "history": g.get("history"),
                    "signals": [{"round": s.get("round"), "text": s.get("text"),
                                 "title": s.get("title"), "source": s.get("source")}
                                for s in g.get("signals", [])],
                })
        # standings
        st = d.get("standings")
        if st and st.get("rows"):
            rows = [{"rank": r.get("rank"), "name": r.get("name"),
                     "points": r.get("points")} for r in st["rows"]]
            out["standings_timeline"].append({"ts": ts, "rows": rows})
        # my trades
        for tr in me.get("trades", []):
            key = tr.get("id") or (tr.get("round"), tr.get("at"), tr.get("side"), tr.get("price"), tr.get("qty"))
            if key not in [x.get("key") for x in out["my_trades"]]:
                out["my_trades"].append({"key": key, "round": tr.get("round"),
                    "at": tr.get("at"), "side": tr.get("side"),
                    "price": tr.get("price"), "qty": tr.get("qty"),
                    "counterparty": tr.get("counterparty"), "program": tr.get("program")})
        # my orders snapshot (record changes)
        for o in me.get("orders", []):
            key = o.get("id")
            if key not in [x.get("key") for x in out["my_orders"]]:
                out["my_orders"].append({"key": key, "id": key, "side": o.get("side"),
                    "price": o.get("price"), "qty": o.get("qty"),
                    "remaining": o.get("remaining"), "round": o.get("round")})
        # phase / last price timeline (thin sample per state)
        if g:
            out["phase_timeline"].append({"ts": ts, "phase": g.get("phase"),
                "round": g.get("round"), "last": g.get("lastPrice"),
                "opening": g.get("openingPrice"),
                "position": me.get("position"), "pnl": me.get("pnl"),
                "realized": me.get("realized"),
                "question": (g.get("question") or {}).get("q")})

json.dump(out, open("extracted.json", "w"), ensure_ascii=False, indent=1)
print("resolutions:", len(out["resolutions"]))
print("standings snapshots:", len(out["standings_timeline"]))
print("my trades:", len(out["my_trades"]))
print("my orders:", len(out["my_orders"]))
print("state samples:", len(out["phase_timeline"]))
