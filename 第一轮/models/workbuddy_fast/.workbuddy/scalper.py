#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 临渊量化刮头皮机器人：围绕真值锚点双向收割噪声波动
import json, time, os, urllib.request, sys

BASE = "http://192.168.1.7:7788"
CODE = "258334"
TOKEN = "263a4a4e67a146cf8c32237c46ba4252"
SSE_LOG = "/Users/yuanf/WorkBuddy/2026-11-21-23-15-20/.workbuddy/sse.log"

ANCHOR = float(sys.argv[1]) if len(sys.argv) > 1 else None   # 真值锚点(单位本身)
LOW_BAND = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5  # 买: 锚点下方百分比%
HIGH_BAND = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5 # 卖: 锚点上方百分比%
CLIP = int(sys.argv[4]) if len(sys.argv) > 4 else 4          # 每次手数
MAXPOS = int(sys.argv[5]) if len(sys.argv) > 5 else 10       # 仓位上限
DEBUG = True

def log(*a):
    if DEBUG: print(time.strftime('%H:%M:%S'), *a, flush=True)

def act(payload):
    payload.update({"code": CODE, "token": TOKEN})
    req = urllib.request.Request(BASE + "/api/act", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=2)
        return json.loads(r.read().decode())
    except Exception as e:
        log("ACT ERR", e, payload)
        return None

def latest_state(offset):
    try:
        with open(SSE_LOG) as f:
            f.seek(offset); new = f.read(); offset = f.tell()
    except Exception:
        return None, offset
    st = None
    for e in new.split('\n\n'):
        if not e.startswith('data: '): continue
        try: j = json.loads(e[6:])
        except: continue
        if j.get('t') == 'state': st = j
    return st, offset

def main():
    offset = os.path.getsize(SSE_LOG)
    pos = 0; orders = []
    last_action = 0
    while True:
        st, offset = latest_state(offset)
        if st:
            g = st['game']; me = g['me']
            ph = g['phase']
            if ph in ('closed', 'settled'):
                log("phase:", ph, "pos", me['position'], "pnl", me['pnl'])
                if ph == 'settled':
                    log("RESOLUTION:", g.get('resolution'))
                    return
                # closed: cancel all and end
                act({"action": "cancelAll"}); log("cancelAll at close")
                time.sleep(0.3); continue
            if ph != 'trading':
                time.sleep(0.5); continue
            pos = me['position']
            book = g['book']
            bb = book['bids'][0]['price'] / 100.0 if book['bids'] else None
            ba = book['asks'][0]['price'] / 100.0 if book['asks'] else None
            buy_room = me['availableBuy']; sell_room = me['availableSell']
            now = time.time()
            # 锚点校验
            if ANCHOR is None: time.sleep(1); continue
            buy_trig = ANCHOR * (1 - LOW_BAND / 100.0)
            sell_trig = ANCHOR * (1 + HIGH_BAND / 100.0)
            # 便宜就买（吃卖盘）
            if ba is not None and ba <= buy_trig and buy_room >= 1 and now - last_action > 0.25:
                q = min(CLIP, buy_room)
                r = act({"action": "order", "side": "buy", "price": round(buy_trig, 4), "qty": q,
                         "reason": "低于真值锚，市价接多"})
                log(f"BUY {q} @ask {ba:.2f} pos->{pos+q}")
                last_action = now
            # 贵就卖（吃买盘）
            elif bb is not None and bb >= sell_trig and sell_room >= 1 and now - last_action > 0.25:
                q = min(CLIP, sell_room)
                r = act({"action": "order", "side": "sell", "price": round(sell_trig, 4), "qty": q,
                         "reason": "高于真值锚，市价做空"})
                log(f"SELL {q} @bid {bb:.2f} pos->{pos-q}")
                last_action = now
        time.sleep(0.25)

main()
