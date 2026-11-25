import json, sys, urllib.request

CODE = "258334"
TOKEN = "2bdbfa468c006f492c6f43e8f823076c"
BASE = "http://127.0.0.1:7788"

def post(payload):
    payload["code"] = CODE
    payload["token"] = TOKEN
    req = urllib.request.Request(f"{BASE}/api/act",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        print(r.read().decode())

a = sys.argv[1:]
if not a:
    print("usage: act.py order buy 180.5 2 [reason] | cancelAll | cancel id")
    sys.exit(0)
cmd = a[0]
if cmd == "order":
    side, price, qty = a[1], float(a[2]), int(a[3])
    reason = a[4] if len(a) > 4 else ""
    post({"action": "order", "side": side, "price": price, "qty": qty, "reason": reason})
elif cmd == "cancelAll":
    post({"action": "cancelAll"})
elif cmd == "cancel":
    post({"action": "cancel", "orderId": a[1]})
elif cmd == "estimate":
    post({"action": "estimate", "value": float(a[1])})
