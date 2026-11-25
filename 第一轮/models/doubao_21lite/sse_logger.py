#!/usr/bin/env python3
"""Persistent SSE logger: writes latest state to state.json, appends events to events.log."""
import json, time, urllib.request, os, sys, threading

BASE = os.path.dirname(os.path.abspath(__file__))
creds = json.load(open(os.path.join(BASE, "creds.json")))
URL = f"{creds['base']}/api/stream?code={creds['code']}&token={creds['token']}"

state_path = os.path.join(BASE, "state.json")
log_path = os.path.join(BASE, "events.log")
lock = threading.Lock()

def write_state(state):
    with lock:
        tmp = state_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state, f, ensure_ascii=False)
        os.replace(tmp, state_path)

def log_event(ev):
    with open(log_path, "a") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")

def connect():
    req = urllib.request.Request(URL, headers={"Accept": "text/event-stream"})
    resp = urllib.request.urlopen(req, timeout=30)
    buf = b""
    while True:
        chunk = resp.read(4096)
        if not chunk:
            break
        buf += chunk
        while b"\n" in buf:
            raw, buf = buf.split(b"\n", 1)
            line = raw.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload:
                continue
            try:
                ev = json.loads(payload)
            except Exception:
                continue
            ev["_recv"] = time.time()
            if ev.get("t") == "state":
                write_state(ev.get("game", {}))
                log_event(ev)
            elif ev.get("t") == "clock":
                # keep latest clock in a sidecar for quick polling
                with open(os.path.join(BASE, "clock.json"), "w") as f:
                    json.dump(ev, f)
                log_event(ev)

if __name__ == "__main__":
    while True:
        try:
            connect()
        except Exception as e:
            with open(log_path, "a") as f:
                f.write(json.dumps({"t": "error", "err": str(e), "_recv": time.time()}, ensure_ascii=False) + "\n")
        time.sleep(1)
