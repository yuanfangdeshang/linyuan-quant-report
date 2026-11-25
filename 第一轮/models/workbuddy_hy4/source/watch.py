#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阻塞等待新线索 / 新局 / 阶段变化，打印出来供上层推理；超时也打印当前心跳。"""
import json, os, sys, time

D = os.path.dirname(os.path.abspath(__file__))
secs = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
quiet = '--quiet' in sys.argv

sig = os.path.join(D, 'signals.txt')
alert = os.path.join(D, 'alert.json')
refl = os.path.join(D, 'reflect.md')


def nlines(p):
    try:
        with open(p, encoding='utf-8') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


s0, r0 = nlines(sig), nlines(refl)
try:
    a0 = json.dumps(json.load(open(alert, encoding='utf-8')), ensure_ascii=False)
except Exception:
    a0 = ''

deadline = time.time() + secs
found = False
while time.time() < deadline:
    s1, r1 = nlines(sig), nlines(refl)
    try:
        a1 = json.dumps(json.load(open(alert, encoding='utf-8')), ensure_ascii=False)
    except Exception:
        a1 = a0
    if s1 > s0 or a1 != a0 or r1 > r0:
        found = True
        break
    time.sleep(0.25)

if s1 > s0:
    with open(sig, encoding='utf-8') as f:
        lines = f.readlines()
    print('=== 新线索 ===')
    print(''.join(lines[s0:]).strip())
if a1 != a0:
    print('=== 告警 ===')
    print(a1)
if r1 > r0:
    with open(refl, encoding='utf-8') as f:
        lines = f.readlines()
    new = [x.strip() for x in lines[r0:] if x.strip()]
    print('=== 复盘新增 ===')
    print('\n'.join(new[-12:]))

print(f'=== watch: {"有变化" if found else "超时无变化"} ===')
try:
    h = json.load(open(os.path.join(D, 'heartbeat.json'), encoding='utf-8'))
    keys = ['at', 'game', 'label', 'phase', 'round', 'remain', 'openingPrice', 'lastPrice',
            'bestAsk', 'bestBid', 'position', 'avgCost', 'pnl', 'realized']
    print(' | '.join(f'{k}={json.dumps(h.get(k), ensure_ascii=False)}' for k in keys))
    print('asks=', json.dumps(h.get('asks'), ensure_ascii=False), 'bids=', json.dumps(h.get('bids'), ensure_ascii=False))
    print('clock=', json.dumps(h.get('clock'), ensure_ascii=False))
    print('signals=', json.dumps(h.get('signals'), ensure_ascii=False)[:1200])
except Exception as e:
    print('heartbeat err', e)
