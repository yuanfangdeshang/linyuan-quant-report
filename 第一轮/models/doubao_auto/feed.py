import json, time, urllib.request, os, sys

CODE = "258334"
TOKEN = "2bdbfa468c006f492c6f43e8f823076c"
BASE = "http://127.0.0.1:7788"
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state.json")
LOG = os.path.join(HERE, "events.log")

def main():
    url = f"{BASE}/api/stream?code={CODE}&token={TOKEN}"
    with open(LOG, "a") as lg:
        lg.write(f"\n=== stream start {time.strftime('%H:%M:%S')} ===\n")
        lg.flush()
        while True:
            try:
                req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
                with urllib.request.urlopen(req, timeout=600) as r:
                    for raw in r:
                        line = raw.decode("utf-8", "ignore").strip()
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        try:
                            ev = json.loads(data)
                        except Exception:
                            continue
                        if ev.get("t") == "state":
                            tmp = STATE + ".tmp"
                            with open(tmp, "w") as f:
                                json.dump(ev, f, ensure_ascii=False)
                            os.replace(tmp, STATE)
                            g = ev.get("game", {})
                            if g.get("phase") in ("settled", "closed") and (g.get("resolution") or g.get("ranking")):
                                with open(os.path.join(HERE, "settle_archive.jsonl"), "a") as af:
                                    af.write(json.dumps(ev, ensure_ascii=False) + "\n")
                            me = g.get("me", {}) or {}
                            lg.write("[state] %s ph=%s r=%s/%s rem=%s open=%s last=%s pos=%s pnl=%s\n" % (
                                time.strftime('%H:%M:%S'), g.get("phase"), g.get("round"), g.get("maxRound"),
                                g.get("roundRemain"), g.get("openingPrice"), g.get("lastPrice"),
                                me.get("position"), me.get("pnl")))
                            lg.flush()
                        elif ev.get("t") == "clock":
                            lg.write("[clock] %s r=%s rem=%s last=%s\n" % (
                                time.strftime('%H:%M:%S'), ev.get("round"), ev.get("remain"), ev.get("lastPrice")))
                            lg.flush()
            except Exception as e:
                with open(LOG, "a") as lg:
                    lg.write(f"[err] {time.strftime('%H:%M:%S')} {e}\n")
                    lg.flush()
                time.sleep(2)
            time.sleep(0.5)

if __name__ == "__main__":
    main()
