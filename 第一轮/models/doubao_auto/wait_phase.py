import json, time, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state.json")
limit = int(sys.argv[1]) if len(sys.argv) > 1 else 3600
t0 = time.time()
while time.time() - t0 < limit:
    try:
        d = json.load(open(STATE))
        g = d["game"]
        if g.get("phase") != "estimate":
            print("PHASE", g.get("phase"), "round", g.get("round"))
            sys.exit(0)
    except Exception:
        pass
    time.sleep(1)
print("TIMEOUT still estimate")
