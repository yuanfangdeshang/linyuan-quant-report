#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""线索题专用：一条命令完成「读到真值 -> 改配置 -> 穿价反手 -> 清残量」。
用法: python3 react.py <推理出的真值> [局号，默认取当前]
"""
import json, os, sys, time, urllib.request

BASE = 'http://127.0.0.1:7788'
CODE = '258334'
TOKEN = '6f7e86c74d4c6657e09f663848d6995c'
D = os.path.dirname(os.path.abspath(__file__))
fair = float(sys.argv[1])


def post(payload):
    req = urllib.request.Request(BASE + '/api/act',
                                 data=json.dumps(payload, ensure_ascii=False).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.loads(r.read().decode())


def state():
    u = f'{BASE}/api/stream?code={CODE}&token={TOKEN}'
    with urllib.request.urlopen(u, timeout=6) as r:
        for raw in r:
            line = raw.decode().strip()
            if line.startswith('data: '):
                d = json.loads(line[6:])
                if d.get('t') == 'state':
                    return d['game']


g = state()
num = g['number']
me, bk = g['me'], g['book']
pos = int(me.get('position') or 0)
avail_b = int(me.get('availableBuy') or 0)
avail_s = int(me.get('availableSell') or 0)
ba = (bk.get('bestAsk') or fair * 100) / 100.0
bb = (bk.get('bestBid') or fair * 100) / 100.0
mid = (ba + bb) / 2
print(f'G{num} phase={g["phase"]} pos={pos} mid={mid:.2f} fair={fair} availB={avail_b} availS={avail_s}')

# 1) 先把估值写进配置，让常驻代理后续按新真值继续收租
cp = os.path.join(D, 'control.json')
c = json.load(open(cp, encoding='utf-8'))
c.setdefault('games', {}).setdefault(str(num), {})
c['games'][str(num)].update({
    'fair': fair, 'blendOpen': 1.0, 'mode': 'maker',
    'maxScaleGap': 2.0,
    'note': f'R3推理真值{fair}，一条命令反手后由代理继续阶梯'
})
tmp = cp + '.tmp'
json.dump(c, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
os.replace(tmp, cp)
print('配置已更新 fair =', fair)

# 2) 按真值相对现价决定方向，一次性穿价打到满仓
if g.get('phase') != 'trading':
    print('非交易阶段，跳过下单')
    sys.exit(0)
if fair > mid * 1.002:
    target = 10
elif fair < mid * 0.998:
    target = -10
else:
    target = pos
delta = target - pos
if delta > 0:
    limit = round(min(fair * 0.999, ba * 1.03), 2)
    qty = min(delta, avail_b)
    side = 'buy'
else:
    limit = round(max(fair * 1.001, bb * 0.97), 2)
    qty = min(-delta, avail_s)
    side = 'sell'
if qty <= 0:
    print('无需下单')
    sys.exit(0)
payload = {'code': CODE, 'token': TOKEN, 'action': 'order', 'side': side,
           'price': limit, 'qty': qty,
           'reason': f'线索算得真值{fair:.4g}，反手{side}'[:40]}
r = post(payload)
print('ORDER', side, qty, '@', limit, '->', r)
r2 = post({'code': CODE, 'token': TOKEN, 'action': 'cancelAll', 'reason': '清穿价残量'})
print('cancelAll ->', r2)
with open(os.path.join(D, 'actions.log.jsonl'), 'a', encoding='utf-8') as f:
    f.write(json.dumps({'at': time.strftime('%H:%M:%S'), 'game': num, 'mode': 'react',
                        'fair': fair, 'payload': payload, 'resp': r}, ensure_ascii=False) + '\n')
