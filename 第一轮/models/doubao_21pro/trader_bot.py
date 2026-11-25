#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临渊量化实时交易竞技 —— 豆包交易机器人
- SSE 长连接订阅（自动重连）
- 动态估值 fair 由 fair.json 外部控制（MainAgent 读信号后更新）
- 做市收租 + 方向单 + 轮末/终局仓位管理
- 全量日志，供逐笔复盘与自我迭代
"""
import json, time, threading, os, sys, subprocess, datetime
import requests

BASE = "http://127.0.0.1:7788"
CODE = "258334"
TOKEN = "ffc8ea5818b81658693adcd35de0cc65"
ROOT = "/Users/yuanf/DoubaoWork/chats/2026-11-21/new-chat-5"
LOGDIR = os.path.join(ROOT, "logs")
FAIR_FILE = os.path.join(ROOT, "fair.json")
TICK = 0.5                 # 最小挂单偏移
EDGE = 0.02                # 方向穿价阈值 2%
DEEP = 0.025               # 深度挂单偏离 2.5%
MM_QTY = 1                 # 做市每边手数
DEEP_QTY = 2               # 深度单手数
MAX_POS = 8                # 正式局仓位上限（最后一轮放开）
EARLY_MAX_POS = 2          # 非最后一轮净持仓上限（信号未明，严控方向敞口）
END_BUFFER = 8             # 轮末撤单秒数
WATCH_OPEN = 2.5           # 开盘观察秒数
MIN_DECISION_GAP = 0.25

os.makedirs(LOGDIR, exist_ok=True)

def ts():
    return datetime.datetime.now().strftime("%H:%M:%S.") + f"{datetime.datetime.now().microsecond//1000:03d}"

def log(fname, msg):
    line = f"[{ts()}] {msg}\n"
    with open(os.path.join(LOGDIR, fname), "a", encoding="utf-8") as f:
        f.write(line)

def notify(title, msg):
    try:
        subprocess.run(["osascript", "-e",
            f'display notification "{msg}" with title "{title}"'],
            timeout=3, capture_output=True)
    except Exception:
        pass

def y(v):
    """分 -> 单位"""
    return None if v is None else round(v / 100.0, 4)

class Bot:
    def __init__(self):
        self.lock = threading.RLock()
        self.state = None
        self.evt = threading.Event()
        self.fair = 10.99
        self.fair_reason = "排名锚点推理：日本61/朝鲜98，104名约古巴10.99"
        self.flatten = False
        self.seen_signals = set()
        self.seen_reviews = set()
        self.trading_since = None
        self.new_round_since = None
        self.last_phase = None
        self.last_round = None
        self.last_decision = 0.0
        self.last_book_key = None
        self.running = True
        self.trade_count = 0

    # ---------- 工具 ----------
    def g(self):
        with self.lock:
            return json.loads(json.dumps(self.state)) if self.state else None

    def write_fair(self):
        if not os.path.exists(FAIR_FILE):
            with open(FAIR_FILE, "w", encoding="utf-8") as f:
                json.dump({"fair": self.fair, "reason": self.fair_reason}, f, ensure_ascii=False, indent=2)

    def read_fair(self):
        try:
            if os.path.exists(FAIR_FILE):
                d = json.load(open(FAIR_FILE, encoding="utf-8"))
                if d.get("fair"):
                    self.fair, self.fair_reason = float(d["fair"]), d.get("reason", "")
                self.flatten = bool(d.get("flatten", False))
        except Exception as e:
            log("bot.log", f"fair.json 读取失败: {e}")

    def act(self, payload, reason):
        payload.update({"code": CODE, "token": TOKEN})
        try:
            r = requests.post(BASE + "/api/act", json=payload, timeout=4)
            res = r.json()
            log("actions.log", f"{json.dumps(payload, ensure_ascii=False)} => {json.dumps(res, ensure_ascii=False)} 理由：{reason}")
            return res
        except Exception as e:
            log("actions.log", f"{json.dumps(payload, ensure_ascii=False)} => ERROR {e} 理由：{reason}")
            return None

    def cancel_all(self, reason):
        return self.act({"action": "cancelAll"}, reason)

    def consume_flatten(self):
        self.flatten = False
        try:
            d = json.load(open(FAIR_FILE, encoding="utf-8"))
            d["flatten"] = False
            json.dump(d, open(FAIR_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        except Exception as e:
            log("bot.log", f"消费flatten标志失败: {e}")

    # ---------- SSE ----------
    def sse_loop(self):
        url = f"{BASE}/api/stream?code={CODE}&token={TOKEN}"
        while self.running:
            try:
                with requests.get(url, stream=True, timeout=(5, 60)) as r:
                    log("bot.log", f"SSE 连接建立 status={r.status_code}")
                    for raw in r.iter_lines(decode_unicode=True):
                        if not raw or not raw.startswith("data:"):
                            continue
                        try:
                            data = json.loads(raw[5:].strip())
                        except Exception:
                            continue
                        if data.get("t") == "state":
                            self.on_state(data)
            except Exception as e:
                log("bot.log", f"SSE 断开: {e}，1 秒后重连")
                time.sleep(1)

    def on_state(self, data):
        with self.lock:
            self.state = data
        try:
            with open(os.path.join(LOGDIR, "state_latest.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        gm = data.get("game") or {}
        me = gm.get("me") or {}
        bk = gm.get("book") or {}
        phase, rnd, remain = gm.get("phase"), gm.get("round"), gm.get("roundRemain")
        lp, op = y(gm.get("lastPrice")), y(gm.get("openingPrice"))
        ba, bb = y(bk.get("bestAsk")), y(bk.get("bestBid"))
        log("events.log",
            f"phase={phase} r={rnd} remain={remain} open={op} last={lp} bid={bb} ask={ba} "
            f"pos={me.get('position')} avg={y(me.get('avgCost')) if me.get('avgCost') else 0} "
            f"realized={me.get('realized')} pnl={me.get('pnl')} orders={len(me.get('orders') or [])} trades={len(me.get('trades') or [])}")

        # 新信号
        for s in gm.get("signals") or []:
            key = f"{s.get('round')}-{s.get('title')}"
            if key not in self.seen_signals:
                self.seen_signals.add(key)
                log("signals.log", f"=== 第{s.get('round')}轮信号《{s.get('title')}》来源:{s.get('sourceName')}\n{s.get('text')}")
                notify("新线索", f"{s.get('title')}")
        # 复盘
        rv = gm.get("review")
        if rv:
            rkey = json.dumps(rv, ensure_ascii=False)[:80]
            if rkey not in self.seen_reviews:
                self.seen_reviews.add(rkey)
                fn = os.path.join(LOGDIR, f"review_r{rnd}.json")
                with open(fn, "w", encoding="utf-8") as f:
                    json.dump(rv, f, ensure_ascii=False, indent=2)
                log("bot.log", f"复盘已保存 {fn}")
        # 成交记录
        tlen = len(me.get("trades") or [])
        if tlen > self.trade_count:
            for tr in (me.get("trades") or [])[self.trade_count:]:
                log("trades.log",
                    f"轮{tr.get('round')} {tr.get('side')} {y(tr.get('price'))} x{tr.get('qty')} "
                    f"对手={tr.get('counterparty')} program={tr.get('program')} at={tr.get('at')}")
            self.trade_count = tlen

        # 阶段/轮次切换
        if phase != self.last_phase:
            log("bot.log", f"阶段切换 {self.last_phase} -> {phase}")
            if phase == "trading":
                self.trading_since = time.time()
            self.last_phase = phase
        if rnd != self.last_round:
            log("bot.log", f"轮次切换 {self.last_round} -> {rnd} (label={gm.get('label')})")
            if self.last_round is not None and phase == "trading":
                self.new_round_since = time.time()
                if me.get("orders"):
                    self.cancel_all("新轮开始，撤旧单避开信号乱流")
            self.last_round = rnd
        self.evt.set()

    # ---------- 决策 ----------
    def decide_loop(self):
        while self.running:
            self.evt.wait(timeout=1.0)
            self.evt.clear()
            if time.time() - self.last_decision < MIN_DECISION_GAP:
                continue
            self.last_decision = time.time()
            try:
                self.decide()
            except Exception as e:
                log("bot.log", f"决策异常: {e}")

    def decide(self):
        self.write_fair()
        self.read_fair()
        data = self.g()
        if not data:
            return
        gm = data["game"]
        if gm.get("phase") != "trading":
            return
        me = gm["me"]
        bk = gm["book"]

        # 强制平仓指令
        if self.flatten:
            pos0 = me.get("position", 0)
            if pos0 == 0:
                self.consume_flatten()
                return
            if me.get("orders"):
                self.cancel_all("平仓模式：先撤全部挂单")
                return
            ba0, bb0 = y(bk.get("bestAsk")), y(bk.get("bestBid"))
            lp0 = y(gm.get("lastPrice"))
            if pos0 > 0 and bb0 is not None:
                self.act({"action": "order", "side": "sell", "price": bb0 - TICK, "qty": pos0},
                         "强制平仓：卖出归零")
            elif pos0 < 0 and ba0 is not None:
                self.act({"action": "order", "side": "buy", "price": ba0 + TICK, "qty": -pos0},
                         "强制平仓：买入归零")
            elif lp0 is not None:
                side = "sell" if pos0 > 0 else "buy"
                p = lp0 - TICK if pos0 > 0 else lp0 + TICK
                self.act({"action": "order", "side": side, "price": p, "qty": abs(pos0)},
                         "强制平仓：盘口空，挂最新价外侧")
            return
        rnd, remain = gm.get("round"), gm.get("roundRemain") or 0
        max_round = gm.get("maxRound", 3)
        pos = me.get("position", 0)
        my_orders = me.get("orders") or []
        avail_buy = me.get("availableBuy", 0)
        avail_sell = me.get("availableSell", 0)
        best_ask, best_bid = y(bk.get("bestAsk")), y(bk.get("bestBid"))
        asks = [(y(a["price"]), a["qty"]) for a in (bk.get("asks") or [])]
        bids = [(y(b["price"]), b["qty"]) for b in (bk.get("bids") or [])]
        fair = self.fair
        last = y(gm.get("lastPrice"))

        # 信号未明的早期轮次严控敞口；最后一轮才放开做方向
        is_final = (rnd == max_round - 1)
        pos_cap = MAX_POS if is_final else EARLY_MAX_POS

        # 开盘观察期 / 新轮信号观察期
        if self.trading_since and time.time() - self.trading_since < WATCH_OPEN:
            return
        if self.new_round_since and time.time() - self.new_round_since < WATCH_OPEN:
            return

        # 轮末：撤单；非最后一轮平净持仓到中性；最后一轮按 fair 决定终局持仓
        if remain <= END_BUFFER:
            if my_orders:
                self.cancel_all("轮末撤单，不留隔夜风险")
                return
            if rnd == max_round - 1:
                self.terminal_position(gm, me, best_bid, best_ask, fair, pos, avail_buy, avail_sell, remain)
            elif pos > 0 and best_bid is not None:
                self.act({"action": "order", "side": "sell", "price": best_bid - TICK, "qty": pos},
                         "轮末平多，轻仓等下轮信号")
            elif pos < 0 and best_ask is not None:
                self.act({"action": "order", "side": "buy", "price": best_ask + TICK, "qty": -pos},
                         "轮末平空，轻仓等下轮信号")
            return

        my_buy_prices = [round(o["price"] / 100.0, 2) for o in my_orders if o["side"] == "buy"]
        my_sell_prices = [round(o["price"] / 100.0, 2) for o in my_orders if o["side"] == "sell"]

        # 1) 方向性穿价机会（早期轮次受 pos_cap 约束）
        if best_ask is not None and best_ask <= fair * (1 - EDGE) and pos < pos_cap and avail_buy > 0:
            qty = min(2, avail_buy, pos_cap - pos)
            if qty > 0:
                self.act({"action": "order", "side": "buy", "price": best_ask + TICK, "qty": qty},
                         f"折价穿价买，fair={fair} 偏离>{EDGE:.1%} cap={pos_cap}")
                return
        if best_bid is not None and best_bid >= fair * (1 + EDGE) and pos > -pos_cap and avail_sell > 0:
            qty = min(2, avail_sell, pos_cap + pos)
            if qty > 0:
                self.act({"action": "order", "side": "sell", "price": best_bid - TICK, "qty": qty},
                         f"溢价穿价卖，fair={fair} 偏离>{EDGE:.1%} cap={pos_cap}")
                return

        # 2) 清理偏离过大的陈旧挂单
        stale = []
        for o in my_orders:
            p = round(o["price"] / 100.0, 2)
            if abs(p - fair) / fair > DEEP + 0.012:
                stale.append(o["id"])
        if stale:
            self.cancel_all("挂单偏离估值，整体重置")
            return

        # 3) 做市：价差足够宽时插队双边挂单
        if best_bid is not None and best_ask is not None:
            spread = best_ask - best_bid
            if spread >= 2 * TICK:
                mm_buy = best_bid + TICK
                mm_sell = best_ask - TICK
                if mm_buy not in my_buy_prices and avail_buy > 0 and pos < pos_cap:
                    self.act({"action": "order", "side": "buy", "price": mm_buy, "qty": MM_QTY},
                             f"价差内做市买，spread={spread} cap={pos_cap}")
                if mm_sell not in my_sell_prices and avail_sell > 0 and pos > -pos_cap:
                    self.act({"action": "order", "side": "sell", "price": mm_sell, "qty": MM_QTY},
                             f"价差内做市卖，spread={spread} cap={pos_cap}")

        # 4) 深度方向挂单（等鱼上钩）——仅最后一轮开启，早期不做赌注式挂单
        if is_final:
            deep_buy = round((fair * (1 - DEEP)) / TICK) * TICK
            deep_sell = round((fair * (1 + DEEP)) / TICK) * TICK
            if avail_buy > 0 and pos < pos_cap and deep_buy not in my_buy_prices:
                near = any(abs(p - deep_buy) < TICK for p in my_buy_prices)
                if not near:
                    self.act({"action": "order", "side": "buy", "price": deep_buy, "qty": DEEP_QTY},
                             f"估值下沿挂买 {deep_buy}")
            if avail_sell > 0 and pos > -pos_cap and deep_sell not in my_sell_prices:
                near = any(abs(p - deep_sell) < TICK for p in my_sell_prices)
                if not near:
                    self.act({"action": "order", "side": "sell", "price": deep_sell, "qty": DEEP_QTY},
                             f"估值上沿挂卖 {deep_sell}")

    def terminal_position(self, gm, me, best_bid, best_ask, fair, pos, avail_buy, avail_sell, remain):
        """最后一轮末尾：只在折价/溢价超过不确定度时持仓到结算，否则归零"""
        lp = y(gm.get("lastPrice")) or 0
        target = 0
        if best_ask is not None and best_ask < fair * (1 - EDGE):
            target = min(4, MAX_POS)
        elif best_bid is not None and best_bid > fair * (1 + EDGE):
            target = -min(4, MAX_POS)
        if pos < target and avail_buy > 0 and best_ask is not None:
            qty = min(target - pos, avail_buy)
            self.act({"action": "order", "side": "buy", "price": best_ask + TICK, "qty": qty},
                     "终局建多，持仓等真值")
        elif pos > target and avail_sell > 0 and best_bid is not None:
            qty = min(pos - target, avail_sell)
            self.act({"action": "order", "side": "sell", "price": best_bid - TICK, "qty": qty},
                     "终局减仓/建空，归位目标仓位")

if __name__ == "__main__":
    bot = Bot()
    t1 = threading.Thread(target=bot.sse_loop, daemon=True)
    t2 = threading.Thread(target=bot.decide_loop, daemon=True)
    t1.start(); t2.start()
    log("bot.log", "机器人启动")
    notify("临渊量化", "交易机器人已启动")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        bot.running = False
