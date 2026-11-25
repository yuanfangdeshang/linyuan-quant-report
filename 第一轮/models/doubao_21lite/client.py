#!/usr/bin/env python3
"""Action helper: snapshot | order <side> <price> <qty> [reason] | cancel <orderId> | cancelAll | estimate <value>"""
import json, os, sys, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
creds = json.load(open(os.path.join(BASE, "creds.json")))

def act(payload):
    payload["code"] = creds["code"]
    payload["token"] = creds["token"]
    req = urllib.request.Request(
        f"{creds['base']}/api/act",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        print(r.read().decode())

def snapshot():
    with open(os.path.join(BASE, "state.json")) as f:
        g = json.load(f)
    me = g.get("me", {})
    book = g.get("book", {})
    print(f"phase={g.get('phase')} round={g.get('round')}/{g.get('maxRound')} remain={g.get('roundRemain')} elapsed={g.get('elapsed')}")
    print(f"opening={g.get('openingPrice')} last={g.get('lastPrice')} bestAsk={book.get('bestAsk')} bestBid={book.get('bestBid')} spread={book.get('spread')}")
    print(f"position={me.get('position')} avgCost={me.get('avgCost')} realized={me.get('realized')} pnl={me.get('pnl')} availBuy={me.get('availableBuy')} availSell={me.get('availableSell')}")
    print("asks:", [(b['price'], b['qty']) for b in book.get('asks', [])])
    print("bids:", [(b['price'], b['qty']) for b in book.get('bids', [])])
    print("my orders:", [(o['id'][:8], o['side'], o['price'], o['qty'], o['remaining']) for o in me.get('orders', [])])
    print("my trades:", [(t['round'], t['side'], t['price'], t['qty'], t.get('program')) for t in me.get('trades', [])])
    for s in g.get("signals", []):
        print(f"signal r{s.get('round')} [{s.get('title')}]: {s.get('text') or s.get('body')} (src={s.get('sourceName')})")
    if g.get("history"):
        print("history:", g["history"])

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "snapshot":
        snapshot()
    elif cmd == "estimate":
        act({"action": "estimate", "value": float(sys.argv[2]), "reason": sys.argv[3] if len(sys.argv) > 3 else ""})
    elif cmd == "order":
        side, price, qty = sys.argv[2], float(sys.argv[3]), int(sys.argv[4])
        reason = sys.argv[5] if len(sys.argv) > 5 else ""
        act({"action": "order", "side": side, "price": price, "qty": qty, "reason": reason})
    elif cmd == "cancel":
        act({"action": "cancel", "orderId": sys.argv[2]})
    elif cmd == "cancelAll":
        act({"action": "cancelAll"})
