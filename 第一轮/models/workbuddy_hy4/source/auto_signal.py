#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用线索推理器：监控某局全部新线索，解析出精确真值后自动重仓并暂停代理。
用法: python3 auto_signal.py <局号> [天数乘数，默认1]
覆盖：中文数字(三个半=3.5)、超过A但不到B取中值、日均乘天数、
      明确总数、位数组合、否定极值(从不/没有→0)、阿拉伯数字。
范围型线索（如「个位数且是质数」）不下注。
"""
import json, os, re, sys, time, urllib.request

BASE = 'http://127.0.0.1:7788'
CODE = '258334'
TOKEN = '6f7e86c74d4c6657e09f663848d6995c'
D = os.path.dirname(os.path.abspath(__file__))
NUM = int(sys.argv[1]) if len(sys.argv) > 1 else 11
DAYS = int(sys.argv[2]) if len(sys.argv) > 2 else 1
CN = {'零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
      '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}


def post(p):
    q = urllib.request.Request(BASE + '/api/act',
                               data=json.dumps(p, ensure_ascii=False).encode(),
                               headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(q, timeout=6) as r:
        return json.loads(r.read().decode())


def state():
    with urllib.request.urlopen(f'{BASE}/api/stream?code={CODE}&token={TOKEN}', timeout=6) as r:
        for raw in r:
            l = raw.decode().strip()
            if l.startswith('data: '):
                d = json.loads(l[6:])
                if d.get('t') == 'state':
                    return d['game']


def cn_num(seg):
    seg = seg.replace('个', '').replace('位', '').replace('成', '')
    half = 0.5 if '半' in seg else 0
    seg = seg.replace('半', '')
    m = re.match(r'([零一二两三四五六七八九十]+)', seg)
    if not m:
        return None
    w = m.group(1)
    if w == '十':
        v = 10
    elif '十' in w:
        a, b = w.split('十', 1)
        v = (CN.get(a, 1) if a else 1) * 10 + (CN.get(b, 0) if b else 0)
    elif len(w) == 1:
        v = CN.get(w)
    else:
        return None
    return None if v is None else v + half


def derive(text):
    # 位值/区间描述（「四位数」「比一千多一点点」「不到一千一」）语义复杂，
    # 交给人工判断，避免把「四」「一」误当成区间端点。
    if re.search(r'位数|千|百', text) and not re.search(r'(?:共|总共|一共|合计)\s*\d', text):
        return None
    # 否定极值：从不留未读 / 一个都没有 / 为 0
    if re.search(r'从不.*(?:未读|留)|没有.*(?:未读|好友)|一个都没有|为\s*0\s*条|零\s*条', text):
        return 0.0
    cns = []
    for m in re.finditer(r'([零一二两三四五六七八九十]+(?:个|位|成)?(?:半)?)', text):
        v = cn_num(m.group(1))
        if v is not None:
            cns.append(v)
    # 「超过 A，但不到 B」→ 取中值
    if len(cns) >= 2 and ('超过' in text or '不到' in text or '之间' in text):
        mid = (cns[0] + cns[1]) / 2
        return mid * DAYS if re.search(r'每天|日均|折算', text) else mid
    # 明确总数（阿拉伯数字）
    m = re.search(r'(?:共|总共|一共|合计|有|是|为|达到|约)\s*(\d+(?:\.\d+)?)\s*(?:个|位|条|张|小时|人)?', text)
    if m:
        return float(m.group(1))
    # 日均 × 天数
    m = re.search(r'(?:每天|日均|平均|折算到每天)[^\d]{0,8}(\d+(?:\.\d+)?)\s*(?:个)?小时', text)
    if m:
        return float(m.group(1)) * DAYS
    # 位数组合
    a = re.search(r'十位是\s*(\d)', text)
    b = re.search(r'个位是\s*(\d)', text)
    if a and b:
        return int(a.group(1)) * 10 + int(b.group(1))
    a = re.search(r'千位是\s*(\d)', text)
    b = re.search(r'百位是\s*(\d)', text)
    if a and b:
        return int(a.group(1)) * 1000 + int(b.group(1)) * 100 + 50
    # 单个中文数字 + 明确量词（视为总数）
    if len(cns) == 1 and re.search(r'(?:共|一共|有|是|为)\s*[零一二两三四五六七八九十]', text):
        return cns[0] * DAYS
    return None


def bet(val, tag):
    g = state()
    if g['phase'] != 'trading':
        print(tag, '已收盘，跳过', flush=True)
        return False
    me, bk = g['me'], g['book']
    pos = int(me.get('position') or 0)
    ba = (bk.get('bestAsk') or val * 100) / 100.0
    bb = (bk.get('bestBid') or val * 100) / 100.0
    mid = (ba + bb) / 2
    # 双向 sanity：推导值不能比市价高 5 倍，也不能低到 1/5（防「四位数」误解析成 2.5）
    if mid <= 0 or val < 0 or val > mid * 5 or val < mid / 5:
        print(tag, '解析异常(与市价不同量级)，不下注', val, mid, flush=True)
        return False
    target = 8 if val > mid * 1.03 else (-8 if val < mid * 0.97 else pos)
    delta = target - pos
    if delta > 0:
        side, limit = 'buy', round(min(val * 0.999, ba * 1.08), 2)
        qty = min(delta, int(me.get('availableBuy') or 0))
    else:
        side, limit = 'sell', round(max(val * 1.001, bb * 0.90), 2)
        qty = min(-delta, int(me.get('availableSell') or 0))
    if qty > 0:
        r = post({'code': CODE, 'token': TOKEN, 'action': 'order', 'side': side,
                  'price': limit, 'qty': qty,
                  'reason': f'{tag}推出真值{val:.4g}，重仓{side}'[:40]})
        print(tag, 'ORDER', side, qty, '@', limit, '->', r, flush=True)
        print(tag, 'cleanup', post({'code': CODE, 'token': TOKEN, 'action': 'cancelAll',
                                    'reason': '清残量'}), flush=True)
        with open(os.path.join(D, 'actions.log.jsonl'), 'a', encoding='utf-8') as f:
            f.write(json.dumps({'at': time.strftime('%H:%M:%S'), 'game': NUM,
                                'mode': 'auto_signal', 'signal': tag, 'val': val,
                                'side': side, 'qty': qty, 'price': limit, 'resp': r},
                               ensure_ascii=False) + '\n')
    cp = os.path.join(D, 'control.json')
    c = json.load(open(cp, encoding='utf-8'))
    c['games'].setdefault(str(NUM), {}).update({
        'fair': float(val), 'blendOpen': 1.0, 'mode': 'pause', 'maxScaleGap': 5.0,
        'note': f'{tag}自动推理真值{val}，重仓后暂停代理'})
    tmp = cp + '.tmp'
    json.dump(c, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    os.replace(tmp, cp)
    print(tag, '配置锁定 fair=', val, 'mode=pause', flush=True)
    return True


def main():
    seen, done = set(), False
    deadline = time.time() + 260
    prefix = f'G{NUM} R'
    while time.time() < deadline and not done:
        try:
            lines = open(os.path.join(D, 'signals.txt'), encoding='utf-8').read().splitlines()
        except Exception:
            lines = []
        for i, l in enumerate(lines):
            m = re.search(re.escape(prefix) + r'(\d+)', l)
            if not m:
                continue
            tag = f'R{m.group(1)}'
            if tag in seen:
                continue
            seen.add(tag)
            text = ' '.join(lines[i:i + 3])
            print(tag, '=', text, flush=True)
            v = derive(text)
            print(tag, '推导 val =', v, flush=True)
            if v is not None:
                done = bet(v, tag)
        time.sleep(0.3)
    print('推理器结束 done=', done, flush=True)


if __name__ == '__main__':
    main()
