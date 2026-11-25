#!/usr/bin/env python3
"""临渊量化 - Workbuddy-Hy4flash 交易终端
维持 SSE 长连接、落盘盘面、记录线索、按 config.json 规则自动交易。
config.json 可热更新，无需重启。
"""
import json, time, urllib.request, os, traceback

BASE = "http://192.168.1.7:7788"
CODE = "258334"
TOKEN = "121f3da3b3ebda192f505f41fd103b18"
DIR = "/Users/yuanf/WorkBuddy/2026-11-21-23-15-00"
STATE_FILE = os.path.join(DIR, "state.json")
EVENTLOG = os.path.join(DIR, "events.log")
CONFIG_FILE = os.path.join(DIR, "config.json")

last_action_ts = 0.0
last_phase = None
last_round = None
last_sig_count = -1
last_book_log_ts = 0.0


def log(line):
    ts = time.strftime("%H:%M:%S")
    try:
        with open(EVENTLOG, "a") as f:
            f.write(f"[{ts}] {line}\n")
    except Exception:
        pass


def load_cfg():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {"mode": "passive"}


def act(payload, reason=""):
    global last_action_ts
    full = {"code": CODE, "token": TOKEN}
    full.update(payload)
    req = urllib.request.Request(
        BASE + "/api/act",
        data=json.dumps(full).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as r:
            res = r.read().decode("utf-8", "ignore")
        last_action_ts = time.time()
        log(f"ACT {json.dumps(full, ensure_ascii=False)} || {reason} || RESP {res}")
        return res
    except Exception as e:
        log(f"ACT-ERR {json.dumps(full, ensure_ascii=False)} {e}")
        return None


def snapshot(game, standings):
    obj = {"ts": time.time(), "game": game, "standings": standings}
    try:
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(obj, f, ensure_ascii=False)
        os.replace(tmp, STATE_FILE)
    except Exception:
        pass


def decide(game, cfg):
    global last_action_ts
    mode = cfg.get("mode", "passive")
    if mode == "passive":
        return
    if game.get("phase") != "trading":
        return
    me = game.get("me", {}) or {}
    book = game.get("book", {}) or {}
    asks = book.get("asks") or []
    bids = book.get("bids") or []
    if not asks or not bids:
        return
    now = time.time()
    cd = float(cfg.get("cooldown", 3))
    if now - last_action_ts < cd:
        return

    fair_override = cfg.get("fairOverride")
    if fair_override:
        fair = float(fair_override)
    else:
        op = game.get("openingPrice")
        fair = float(op) / 100.0 if op else float(cfg.get("fair", 500))
    th = float(cfg.get("threshold", 0.03))
    max_order = int(cfg.get("maxOrder", 2))

    # 清理上轮残留挂单
    if cfg.get("cancelStale", True):
        for o in (me.get("orders") or []):
            if int(o.get("round", 0)) < int(game.get("round", 0) or 0):
                act({"action": "cancel", "orderId": o["id"]}, f"清理上轮残留单#{o['id']}")
                return

    bestAsk = asks[0]["price"] / 100.0
    bestBid = bids[0]["price"] / 100.0
    ab = int(me.get("availableBuy", 0))
    asell = int(me.get("availableSell", 0))
    pos = int(me.get("position", 0))

    if mode in ("value", "auto"):
        limit = int(cfg.get("maxPos", 10))
        aggr_th = float(cfg.get("aggressiveTh", 0.05))  # 偏离超此值 -> 激进建满
        # 偏离度：以中价相对公允
        mid = (bestAsk + bestBid) / 2.0
        dev = (fair - mid) / mid  # >0 低估(该买), <0 高估(该卖)

        # 累计吃穿盘口：从对手最优价开始，吃到覆盖 want 手或价格越过公允
        def eat_asks(want, ceiling):
            left, cost = want, 0.0
            for a in asks:
                p = a["price"] / 100.0
                if p > ceiling:
                    break
                take = min(left, int(a.get("qty", 0)))
                cost += take * p
                left -= take
                if left <= 0:
                    break
            return want - left, cost

        def eat_bids(want, floor):
            left, cost = want, 0.0
            for x in bids:
                p = x["price"] / 100.0
                if p < floor:
                    break
                take = min(left, int(x.get("qty", 0)))
                cost += take * p
                left -= take
                if left <= 0:
                    break
            return want - left, cost

        # 低估：目标加多；偏离越大目标仓位越满
        if not cfg.get("noCover", False) and bestAsk <= fair * (1 - th) and ab > 0:
            if abs(dev) >= aggr_th:
                target = limit  # 激进：直接干到满仓多
            else:
                target = min(limit, pos + max_order)
            want = min(target - pos, ab)
            if want > 0:
                fill, cost = eat_asks(want, fair * 1.005)
                qty = max(1, min(want, fill))
                px = round(fair * 1.005, 2)  # 穿价吃单
                act({"action": "order", "side": "buy", "price": px, "qty": qty},
                    f"低估买入 中{mid:.2f} 公允{fair} 折{dev*100:.1f}% 目标{target}")
        elif bestBid >= fair * (1 + th) and asell > 0:
            if abs(dev) >= aggr_th:
                target = -limit  # 激进：直接干到满仓空
            else:
                target = max(-limit, pos - max_order)
            want = min(-(target - pos), asell) if target < pos else 0
            if want > 0:
                fill, cost = eat_bids(want, fair * 0.995)
                qty = max(1, min(want, fill))
                px = round(fair * 0.995, 2)
                act({"action": "order", "side": "sell", "price": px, "qty": qty},
                    f"高估卖出 中{mid:.2f} 公允{fair} 溢{-dev*100:.1f}% 目标{target}")
        elif cfg.get("takeProfit", False) and pos > 0 and bestBid >= fair * 0.995:
            qty = min(max_order, pos, int(bids[0].get("qty", 1)))
            if qty > 0:
                act({"action": "order", "side": "sell", "price": round(bestBid - 0.01, 2), "qty": qty},
                    "回归公允 平多锁定")
        elif cfg.get("takeProfit", False) and pos < 0 and bestAsk <= fair * 1.005:
            qty = min(max_order, -pos, int(asks[0].get("qty", 1)))
            if qty > 0:
                act({"action": "order", "side": "buy", "price": round(bestAsk + 0.01, 2), "qty": qty},
                    "回归公允 平空锁定")


def handle_state(evt):
    global last_phase, last_round, last_sig_count, last_book_log_ts
    game = evt.get("game", {}) or {}
    standings = evt.get("standings", {}) or {}
    snapshot(game, standings)
    cfg0 = load_cfg()
    now0 = time.time()
    if now0 - last_book_log_ts >= float(cfg0.get("bookLogEvery", 15)):
        b = game.get("book", {}) or {}
        me0 = game.get("me", {}) or {}
        log(f"BOOK r{game.get('round')} remain={game.get('roundRemain')} last={game.get('lastPrice')} "
            f"ask={[(a['price'],a['qty']) for a in (b.get('asks') or [])]} "
            f"bid={[(x['price'],x['qty']) for x in (b.get('bids') or [])]} "
            f"pos={me0.get('position')} buy={me0.get('availableBuy')} sell={me0.get('availableSell')} "
            f"ord={[(o['side'],o['price'],o['remaining']) for o in (me0.get('orders') or [])]}")
        last_book_log_ts = now0
    phase = game.get("phase")
    rnd = game.get("round")
    sigs = game.get("signals", []) or []
    if phase != last_phase:
        log(f"PHASE {last_phase} -> {phase} | round={rnd} | open={game.get('openingPrice')} last={game.get('lastPrice')}")
        last_phase = phase
    if rnd != last_round:
        log(f"ROUND -> {rnd} | open={game.get('openingPrice')} last={game.get('lastPrice')}")
        last_round = rnd
    if len(sigs) != last_sig_count:
        log(f"SIGNALS n={len(sigs)}")
        for s in sigs:
            log(f"  SIG r{s.get('round')} [{s.get('title')}] {str(s.get('body') or s.get('text') or '')[:240]} src={s.get('source')}")
        last_sig_count = len(sigs)
    try:
        decide(game, load_cfg())
    except Exception as e:
        log(f"DECIDE-ERR {e}\n{traceback.format_exc()}")


def stream():
    url = f"{BASE}/api/stream?code={CODE}&token={TOKEN}"
    while True:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=300) as r:
                log("STREAM connected")
                for raw in r:
                    line = raw.decode("utf-8", "ignore").rstrip("\r\n")
                    if line.startswith("data:"):
                        payload = line[5:].strip()
                        if not payload:
                            continue
                        try:
                            evt = json.loads(payload)
                        except Exception:
                            continue
                        t = evt.get("t")
                        if t == "state":
                            handle_state(evt)
        except Exception as e:
            log(f"STREAM-RECONNECT {e}")
            time.sleep(2)


if __name__ == "__main__":
    log("=== BOOT ===")
    stream()
