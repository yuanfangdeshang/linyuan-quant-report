#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 信号解析+自动交易：解析数量特征线索 → 计算真值区间 → 偏离超阈值自动建仓
import json, time, os, re, urllib.request, sys

BASE = "http://192.168.1.7:7788"
CODE = "258334"
TOKEN = "263a4a4e67a146cf8c32237c46ba4252"
SSE_LOG = "/Users/yuanf/WorkBuddy/2026-11-21-23-15-20/.workbuddy/sse.log"

THRESH = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0   # 偏离阈值%
MAXPOS = int(sys.argv[2]) if len(sys.argv) > 2 else 10
CLIP = int(sys.argv[3]) if len(sys.argv) > 3 else 3

PRIMES = {2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97,101,103,107,109}

def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)

def act(payload):
    payload.update({"code": CODE, "token": TOKEN})
    req = urllib.request.Request(BASE + "/api/act", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=2)
        return json.loads(r.read().decode())
    except Exception as e:
        log("ACT ERR", e)
        return None

def latest(offset):
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

def parse_range(text):
    """从线索文本解析数值区间 (lo, hi)，返回 None 表示无法解析"""
    t = text.replace('，', ' ').replace('。', ' ').replace('；',' ')
    # 位数+数位约束: "千位是 8" "百位是 4"
    digit_pos = {}
    for name, mult in [('千位', 1000), ('百位', 100), ('十位', 10), ('个位', 1)]:
        m = re.search(name + r'[^0-9]{0,6}(\d+)', t)
        if m: digit_pos[mult] = int(m.group(1))
    nd = None
    for name, lo, hi in [('五位数',10000,99999),('四位数',1000,9999),('三位数',100,999),('两位数',10,99),('个位数',1,9),('一位数',1,9)]:
        if name in t: nd = (lo, hi); break
    lo, hi = None, None
    if digit_pos:
        lo = 0; hi = 0
        for mult in (10000,1000,100,10,1):
            if mult in digit_pos: lo += digit_pos[mult]*mult; hi += digit_pos[mult]*mult
            else: hi += 9*mult if mult != 1 else 9
        # 个位若约束则精确
        lo = max(lo, 1) if nd else lo
        return (lo, hi)
    if nd:
        lo, hi = nd
    # "比X多...不到Y" / "不到Y"
    m1 = re.search(r'比\s*(\d+)\s*多', t)
    m2 = re.search(r'不到\s*(\d+)', t)
    if m1: lo = int(m1.group(1))
    if m2: hi = int(m2.group(1)) - 1
    if lo is not None and hi is not None and lo < hi:
        return (lo, hi)
    # "X 到 Y" / "X-Y"
    m = re.search(r'(\d+)\s*(?:到|-|~)\s*(\d+)', t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if a < b: return (a, b)
    # 纯"个位数/两位数"
    if nd: return nd
    # 质数约束
    if '质数' in t:
        return None  # 需结合位数
    return None

def expected_value(lo, hi, text):
    vals = [v for v in range(lo, hi+1) if '质数' not in text or v in PRIMES]
    if not vals: return None
    return sum(vals)/len(vals)

def main():
    offset = os.path.getsize(SSE_LOG)
    last_sig_key = None
    cur_range = None; cur_E = None
    while True:
        st, offset = latest(offset)
        if not st:
            time.sleep(0.3); continue
        g = st['game']; me = g['me']
        ph = g['phase']
        if ph == 'settled':
            log("SETTLED:", g.get('resolution'))
            return
        if ph != 'trading':
            cur_range = None; cur_E = None
            time.sleep(0.5); continue
        sigs = g['signals']
        if sigs:
            s = sigs[-1]
            key = (s['round'], s['title'])
            if key != last_sig_key:
                last_sig_key = key
                r = parse_range(s['text'])
                if r:
                    lo, hi = r
                    E = expected_value(lo, hi, s['text'])
                    if E:
                        cur_range = r; cur_E = E
                        log(f"NEW RANGE from r{s['round']} '{s['title']}': [{lo},{hi}] E={E:.2f}")
                else:
                    cur_range = None; cur_E = None
                    log(f"signal r{s['round']} unparseable: {s['text'][:60]}")
        if cur_E is None:
            time.sleep(0.3); continue
        book = g['book']; pos = me['position']
        bb = book['bids'][0]['price']/100.0 if book['bids'] else None
        ba = book['asks'][0]['price']/100.0 if book['asks'] else None
        mid = (bb+ba)/2 if (bb and ba) else (bb or ba or cur_E)
        dev = (mid - cur_E)/cur_E*100
        # 目标仓位
        if dev > THRESH: target = -MAXPOS
        elif dev < -THRESH: target = MAXPOS
        else: target = 0
        need = target - pos
        if need == 0:
            # 有挂单但已到目标，清掉
            if me['orders']: act({"action":"cancelAll"}); log("cancelAll (at target)")
            time.sleep(0.4); continue
        side = 'sell' if need < 0 else 'buy'
        qty = min(CLIP, abs(need), me['availableSell'] if side=='sell' else me['availableBuy'])
        if qty <= 0: time.sleep(0.4); continue
        if side == 'sell':
            px = bb
            if px is None or px <= cur_E*1.005:  # 买盘太低，挂接近真值的卖单等价值派抬价
                px = round(cur_E*1.02, 2)
        else:
            px = ba
            if px is None or px >= cur_E*0.995:
                px = round(cur_E*0.98, 2)
        act({"action":"order","side":side,"price":px,"qty":qty,
             "reason":f"自动:区间{cur_range}E={cur_E:.1f}偏离{dev:.1f}%"})
        log(f"{side} {qty} @ {px} pos={pos}->{pos+(qty if side=='buy' else -qty)} dev={dev:.1f}%")
        time.sleep(0.4)

main()
