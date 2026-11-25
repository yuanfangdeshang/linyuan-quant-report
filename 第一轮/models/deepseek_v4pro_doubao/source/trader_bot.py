#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临渊量化 实时交易竞技 - 自动交易员
MainAgent 部署的常驻程序：SSE 订阅 + 决策引擎 + 日志。
"""
import json, os, time, threading, requests, sys, traceback

BASE = "http://127.0.0.1:7788"
CODE = "258334"
TOKEN = "b9ab5ac3532282a7a60f52f2a558f4d6"

DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(DIR, "trader.log")
STATE_PATH = os.path.join(DIR, "state_latest.json")
FAIR_PATH = os.path.join(DIR, "fair_value.txt")
EST_PATH = os.path.join(DIR, "estimate_input.txt")

DEFAULT_FAIR = 480.0

state = None
state_lock = threading.Lock()
last_action_ts = 0.0
action_cooldown = 1.3
estimated_game = set()  # game numbers already estimated
last_game_num = None
last_sig_count = -1
sticky_game = None
sticky_target = 0

def now_str():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def log(msg):
    line = "[%s] %s" % (now_str(), msg)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line, flush=True)

def read_float(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            s = f.read().strip()
        if not s:
            return default
        return float(s.split()[0])
    except Exception:
        return default

def read_fair():
    v = read_float(FAIR_PATH, None)
    if v is None or v <= 0:
        return DEFAULT_FAIR
    return v

def act(payload, reason=""):
    global last_action_ts
    payload = dict(payload)
    payload.setdefault("code", CODE)
    payload.setdefault("token", TOKEN)
    try:
        r = requests.post(BASE + "/api/act", json=payload, timeout=8)
        txt = r.text[:300]
        log("ACT %s | reason=%s | resp=%s" % (json.dumps(payload, ensure_ascii=False), reason, txt))
        last_action_ts = time.time()
        return txt
    except Exception as e:
        log("ACT ERROR %s: %s" % (payload.get("action"), e))
        return None

def my_orders(me):
    return me.get("orders") or []

def unit(cents):
    if cents is None:
        return None
    return cents / 100.0

def decide(s):
    global state
    with state_lock:
        state = s
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False)
    except Exception:
        pass
    try:
        g = s.get("game") or {}
        phase = g.get("phase")
        me = g.get("me") or {}
        q = (g.get("question") or {}).get("q", "")
        num = g.get("number")

        # 记录新线索
        global last_game_num, last_sig_count
        if num != last_game_num:
            last_game_num = num
            last_sig_count = -1
        sigs = g.get("signals") or []
        if len(sigs) > max(last_sig_count, 0):
            for sig in sigs[max(last_sig_count, 0):]:
                log("SIGNAL r%d %s | %s | src=%s" % (
                    sig.get("round"), sig.get("title"), sig.get("text"), sig.get("sourceName")))
            last_sig_count = len(sigs)

        # ---- 估价阶段 ----
        if phase == "estimate":
            est = me.get("estimate")
            if (est is None or est == 0) and num is not None and num not in estimated_game:
                # 等待 MainAgent 写入 estimate_input.txt: "value gameNumber"
                val = None
                try:
                    with open(EST_PATH, "r", encoding="utf-8") as f:
                        parts = f.read().strip().split()
                    if parts:
                        cand = float(parts[0])
                        if len(parts) >= 2:
                            if str(parts[1]) == str(num):
                                val = cand
                        else:
                            val = cand  # 无编号则视为当前局
                except Exception:
                    val = None
                if val is not None:
                    act({"action": "estimate", "value": val}, "开局估价")
                    estimated_game.add(num)
                    log("ESTIMATED game=%s value=%s q=%s" % (num, val, q))
                else:
                    log("NEED_ESTIMATE game=%s q=%s" % (num, q))
            return

        # ---- 交易阶段 ----
        if phase != "trading":
            if phase in ("settled", "closed"):
                log("SETTLE game=%s resolution=%s ranking=%s pnl=%s pos=%s realized=%s" % (
                    num, g.get("resolution"), g.get("ranking"),
                    me.get("pnl"), me.get("position"), me.get("realized")))
            return

        # 节流
        global last_action_ts
        if time.time() - last_action_ts < action_cooldown:
            return

        F = read_fair()
        lastC = g.get("lastPrice") or g.get("openingPrice")
        P = unit(lastC)
        if P is None or P <= 0:
            return
        book = g.get("book") or {}
        bestBid = unit(book.get("bestBid"))
        bestAsk = unit(book.get("bestAsk"))
        pos = me.get("position") or 0
        availB = me.get("availableBuy") or 0
        availS = me.get("availableSell") or 0
        orders = my_orders(me)
        buy_pend = sum(o.get("qty", 0) for o in orders if o.get("side") == "buy")
        sell_pend = sum(o.get("qty", 0) for o in orders if o.get("side") == "sell")
        remain = g.get("roundRemain")
        rnd = g.get("round")
        maxR = g.get("maxRound")

        dev = F - P
        step = max(F * 0.005, 0.02)   # 0.5% 阈值

        # 粘性目标仓位：超阈值满仓，持仓到结算；反向穿越阈值才翻转
        global sticky_game, sticky_target
        if num != sticky_game:
            sticky_game = num
            sticky_target = 0
        if dev > step:
            sticky_target = 10
        elif dev < -step:
            sticky_target = -10
        target = sticky_target

        delta = target - pos

        # 先撤掉与目标方向冲突或过远、过近难成交的挂单
        tol = max((book.get("spread") or 0) / 100.0, F * 0.01)
        for o in orders:
            oid = o.get("id")
            pside = o.get("side")
            oprice = unit(o.get("price"))
            if oprice is None:
                continue
            bad = False
            if pside == "buy":
                if (bestAsk is not None and oprice < bestAsk - tol) or (delta <= 0):
                    bad = True
            else:
                if (bestBid is not None and oprice > bestBid + tol) or (delta >= 0):
                    bad = True
            if bad:
                act({"action": "cancel", "orderId": oid}, "撤过期单")

        if delta > 0:
            # 想买
            if buy_pend >= delta:
                return
            qty = min(delta - buy_pend, availB)
            if qty <= 0:
                return
            if bestAsk is not None and bestAsk <= P * 1.01:
                px = bestAsk
            else:
                px = P
            act({"action": "order", "side": "buy", "price": round(px, 2), "qty": qty},
                "低于公允%+.1f，买%d" % (dev, qty))
        elif delta < 0:
            # 想卖
            if sell_pend >= -delta:
                return
            qty = min((-delta) - sell_pend, availS)
            if qty <= 0:
                return
            if bestBid is not None and bestBid >= P * 0.99:
                px = bestBid
            else:
                px = P
            act({"action": "order", "side": "sell", "price": round(px, 2), "qty": qty},
                "高于公允%+.1f，卖%d" % (dev, qty))
    except Exception:
        log("DECIDE ERROR:\n" + traceback.format_exc())

def sse_loop():
    while True:
        try:
            log("SSE connecting...")
            r = requests.get("%s/api/stream?code=%s&token=%s" % (BASE, CODE, TOKEN),
                             stream=True, timeout=(10, 600))
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data.startswith("{"):
                        try:
                            s = json.loads(data)
                        except Exception:
                            continue
                        if s.get("t") == "state":
                            decide(s)
        except Exception as e:
            log("SSE ERR %s, retry 2s" % e)
            time.sleep(2)

def main():
    log("=== BOT START ===")
    log("fair_value=%s" % read_fair())
    t = threading.Thread(target=sse_loop, daemon=True)
    t.start()
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
