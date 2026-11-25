#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临渊量化 · Workbuddy-Hy4 常驻交易代理
SSE 长连接 + 估值驱动的策略 + 全程留痕 / 自我迭代记录
价格：服务器返回「分」，内部一律 /100 换成「家」；下单时传「家」。
"""
import json, os, sys, time, urllib.request, urllib.error, traceback
from datetime import datetime

BASE = os.environ.get('LY_BASE', 'http://127.0.0.1:7788')
CODE = '258334'
TOKEN = '6f7e86c74d4c6657e09f663848d6995c'
D = os.path.dirname(os.path.abspath(__file__))

DEFAULT_CONTROL = {
    'fair': None,          # 我的公允估值（家）
    'band': 25,            # 偏离多少家对应满仓
    'conf': 0.6,           # 信心系数 0~1
    'maxPos': 6,           # 允许的最大净持仓（手）
    'threshold': 6,        # 最小偏离（家）才动手
    'slip': 3,             # 穿价余量（价格单位）
    'bufPct': 0.002,       # 相对公允价的最小让利比例
    'maxScaleGap': 0.5,    # 估值与开盘价允许的最大相对偏离
    'rungs': [0.08, 0.16, 0.26, 0.38],  # 阶梯偏移（价格单位）
    'rungsPct': None,      # 若设置则按估值比例生成阶梯，自动适配量纲
    'anchor': None,        # 'opening' = 未指定估值时以开盘共识为锚
    'baseQty': 1,          # 每档手数
    'warmupSeconds': 20,   # 低置信度局的开局分批建仓窗口
    'newsFlat': True,      # 新线索到达时自动降暴露（仅无可靠先验的局）
    'newsFlatMax': 3,      # 冲击后允许保留的最大净持仓
    'maxCrossGap': 0.15,   # 市价偏离估值超过此比例时禁止穿价单
    'makerCooldown': 2.0,  # 阶梯调仓最小间隔
    'minStep': 1,          # 最小再平衡手数
    'cooldown': 1.8,       # 两次动作最小间隔（秒）
    'mode': 'auto',        # auto | flat | pause
    'estimate': None,      # 新一局估价阶段的自动报价
    'note': ''
}


def ts():
    return datetime.now().strftime('%H:%M:%S.%f')[:-3]


def p(*a):
    print(f'[{ts()}]', *a, flush=True)


def append(name, obj):
    with open(os.path.join(D, name), 'a', encoding='utf-8') as f:
        f.write(json.dumps(obj, ensure_ascii=False) + '\n')


def write(name, obj):
    tmp = os.path.join(D, name + '.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, os.path.join(D, name))


def post(payload, timeout=6):
    req = urllib.request.Request(
        BASE + '/api/act',
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return {'error': e.read().decode('utf-8')[:300], 'code': e.code}
    except Exception as e:
        return {'error': repr(e)}


def read_control():
    try:
        with open(os.path.join(D, 'control.json'), encoding='utf-8') as f:
            c = json.load(f)
        return {**DEFAULT_CONTROL, **c}
    except Exception:
        return dict(DEFAULT_CONTROL)


def control_for(g):
    """按局号自动套用预设估值，避免换题时人工反应不过来。"""
    c = read_control()
    ov = (c.get('games') or {}).get(str(g.get('number')))
    if ov:
        c = {**c, **ov}
    op = g.get('openingPrice')
    op = op / 100.0 if op else None
    if c.get('fair') is None and c.get('anchor') == 'opening' and op:
        c['fair'] = op
    # 独立先验（融合前）与共识是否相互印证，决定开局能否快速满仓
    c['priorIndependent'] = bool(ov and ov.get('fair') is not None)
    c['fairPrior'] = c.get('fair')
    c['opening'] = op
    # 我的估值与开盘共识加权融合，避免单点误判
    w = c.get('blendOpen')
    if w is not None and c.get('fair') is not None and op:
        c['fair'] = float(w) * float(c['fair']) + (1 - float(w)) * op
    return c


def C(x):
    return None if x is None else x / 100.0


class Bot:
    def __init__(self):
        self.game_id = None
        self.phase = None
        self.round = None
        self.signals = []
        self.estimate_done_for = None
        self.last_act = 0.0
        self.trade_count = 0
        self.last_state_dump = 0.0

    # ---------- 记录 ----------
    def reflect(self, text):
        append('reflect.md.jsonl', {'at': ts(), 'text': text})
        with open(os.path.join(D, 'reflect.md'), 'a', encoding='utf-8') as f:
            f.write(f'\n- **{ts()}** {text}\n')
        p('REFLECT:', text)

    def snapshot(self, g, meta):
        me = g.get('me') or {}
        bk = g.get('book') or {}
        hb = {
            'at': ts(), 'serverNow': meta.get('serverNow'),
            'game': g.get('number'), 'id': g.get('id'), 'label': g.get('label'),
            'practice': g.get('practice'), 'phase': g.get('phase'),
            'round': g.get('round'), 'maxRound': g.get('maxRound'),
            'remain': g.get('roundRemain'), 'elapsed': g.get('elapsed'),
            'question': (g.get('question') or {}).get('q'),
            'openingPrice': C(g.get('openingPrice')),
            'lastPrice': C(g.get('lastPrice')),
            'bestAsk': C(bk.get('bestAsk')), 'bestBid': C(bk.get('bestBid')),
            'spread': C(bk.get('spread')),
            'asks': [{'p': C(a.get('price')), 'q': a.get('qty')} for a in (bk.get('asks') or [])],
            'bids': [{'p': C(b.get('price')), 'q': b.get('qty')} for b in (bk.get('bids') or [])],
            'signals': [{'r': s.get('round'), 't': s.get('title'), 'x': s.get('text'), 'src': s.get('sourceName')} for s in (g.get('signals') or [])],
            'position': me.get('position'), 'avgCost': C(me.get('avgCost')),
            'realized': C(me.get('realized')), 'pnl': C(me.get('pnl')),
            'availBuy': me.get('availableBuy'), 'availSell': me.get('availableSell'),
            'orders': me.get('orders'), 'trades': me.get('trades'),
            'resolution': g.get('resolution'), 'ranking': g.get('ranking'),
            'standings': meta.get('standings'),
        }
        write('heartbeat.json', hb)
        return hb

    def log_state(self, hb):
        append('states.jsonl', hb)

    # ---------- 事件 ----------
    def on_state(self, d):
        g = d.get('game') or {}
        meta = {k: d.get(k) for k in ('serverNow', 'standings', 'playersOnline', 'gameCount', 'currentIndex')}
        hb = self.snapshot(g, meta)
        gid = g.get('id')
        phase = g.get('phase')

        # 新的一局
        if gid and gid != self.game_id:
            prev = self.game_id
            self.game_id = gid
            self.signals = []
            self.estimate_done_for = None
            self.trade_count = 0
            self.game_start = time.time()
            self.warmup_logged = False
            self.reflect(f'新一局 G{g.get("number")}（{"测试" if g.get("practice") else "正式"}）开题：{(g.get("question") or {}).get("q")}；上一局 id={prev}')
            write('alert.json', {'at': ts(), 'type': 'new_game', 'question': (g.get('question') or {}).get('q'),
                                 'game': g.get('number'), 'practice': g.get('practice')})

        if phase != self.phase:
            self.reflect(f'阶段 {self.phase} → {phase}；轮次 {g.get("round")}/{g.get("maxRound")}，开盘价 {C(g.get("openingPrice"))}，最新价 {C(g.get("lastPrice"))}')
            self.phase = phase
            if phase == 'estimate':
                write('alert.json', {'at': ts(), 'type': 'estimate_phase', 'game': g.get('number'),
                                     'question': (g.get('question') or {}).get('q')})

        if g.get('round') != self.round:
            self.round = g.get('round')

        # 新线索
        sigs = g.get('signals') or []
        if len(sigs) > len(self.signals):
            for s in sigs[len(self.signals):]:
                append('signals.log.jsonl', {'at': ts(), 'game': g.get('number'), 'round': s.get('round'),
                                            'title': s.get('title'), 'text': s.get('text'), 'src': s.get('sourceName'),
                                            'opening': C(g.get('openingPrice')), 'last': C(g.get('lastPrice'))})
                with open(os.path.join(D, 'signals.txt'), 'a', encoding='utf-8') as f:
                    f.write(f'\n[{ts()}] G{g.get("number")} R{s.get("round")} 《{s.get("title")}》 来源:{s.get("sourceName")}\n{s.get("text")}\n')
                self.reflect(f'新线索 R{s.get("round")}《{s.get("title")}》：{str(s.get("text"))[:110]}')
                write('alert.json', {'at': ts(), 'type': 'signal', 'game': g.get('number'), 'round': s.get('round'),
                                     'title': s.get('title'), 'text': s.get('text'), 'src': s.get('sourceName'),
                                     'opening': C(g.get('openingPrice')), 'last': C(g.get('lastPrice'))})
            self.signals = sigs
            self.news_shock(g)

        # 估价阶段自动报价
        if phase == 'estimate' and self.estimate_done_for != gid:
            c = control_for(g)
            if c.get('estimate') is not None:
                r = post({'code': CODE, 'token': TOKEN, 'action': 'estimate', 'value': c['estimate'],
                          'reason': '先验中枢，等线索修正'})
                self.estimate_done_for = gid
                append('actions.log.jsonl', {'at': ts(), 'action': 'estimate', 'value': c['estimate'], 'resp': r})
                p('ESTIMATE', c['estimate'], r)

        # 结算
        if phase in ('settled', 'closed') and g.get('resolution') is not None and not getattr(self, 'settled_' + str(gid), False):
            setattr(self, 'settled_' + str(gid), True)
            self.reflect(f'G{g.get("number")} 结算：resolution={json.dumps(g.get("resolution"), ensure_ascii=False)[:400]}；我的 pnl={C((g.get("me") or {}).get("pnl"))}')
            write('alert.json', {'at': ts(), 'type': 'settled', 'game': g.get('number'),
                                 'resolution': g.get('resolution'), 'ranking': g.get('ranking'),
                                 'my_pnl': C((g.get('me') or {}).get('pnl'))})

        # 落盘 + 决策
        now = time.time()
        if now - self.last_state_dump > 0.4 or phase != 'trading':
            self.log_state(hb)
            self.last_state_dump = now
        self.decide(g, hb)

    # ---------- 策略 ----------
    def decide(self, g, hb):
        c = control_for(g)
        if c['mode'] == 'pause' or c.get('fair') is None or g.get('phase') != 'trading':
            return
        fair = float(c['fair'])
        if fair <= 0:
            return
        # 量纲保险：换题后若估值与开盘价差一个量级，停手并告警
        opening = C(g.get('openingPrice'))
        if opening and abs(fair - opening) / opening > float(c.get('maxScaleGap', 0.5)):
            if not getattr(self, 'scale_warned', False):
                self.scale_warned = True
                self.reflect(f'量纲保险触发：估值{fair} 与开盘价{opening} 偏离过大，暂停交易待人工重标定')
                write('alert.json', {'at': ts(), 'type': 'scale_guard', 'fair': fair,
                                     'opening': opening, 'question': (g.get('question') or {}).get('q')})
            return
        self.scale_warned = False
        if c['mode'] == 'maker':
            self.maker(g, hb, c)
            return
        now = time.time()
        if now - self.last_act < float(c['cooldown']):
            return

        bk = g.get('book') or {}
        me = g.get('me') or {}
        asks = bk.get('asks') or []
        bids = bk.get('bids') or []
        best_ask, best_bid = C(bk.get('bestAsk')), C(bk.get('bestBid'))
        last = C(g.get('lastPrice')) or C(g.get('openingPrice')) or fair
        mid = (best_ask + best_bid) / 2 if (best_ask and best_bid) else last
        pos = int(me.get('position') or 0)
        maxPos = int(c['maxPos'])
        edge = fair - mid                      # >0 市场低估 -> 做多
        band = max(1.0, float(c['band']))
        conf = max(0.0, min(1.0, float(c['conf'])))

        if c['mode'] == 'flat':
            target = 0
        else:
            target = max(-maxPos, min(maxPos, round(edge / band * maxPos * conf)))
        delta = target - pos
        if abs(delta) < int(c['minStep']) or abs(edge) < float(c['threshold']):
            return

        slip = float(c['slip'])
        buf = max(0.005, fair * float(c['bufPct']))
        reason = ''
        if delta > 0:
            limit = min(fair - buf, (best_ask + slip) if best_ask else fair - buf)
            depth = sum(int(a.get('qty') or 0) for a in asks if C(a.get('price')) <= limit)
            qty = min(delta, depth, int(me.get('availableBuy') or 0))
            if qty <= 0:
                return
            payload = {'code': CODE, 'token': TOKEN, 'action': 'order', 'side': 'buy',
                       'price': round(limit, 2), 'qty': qty}
            reason = f'低估{edge:.3g}，吃卖盘建多(估值{fair:.4g})'
        else:
            limit = max(fair + buf, (best_bid - slip) if best_bid else fair + buf)
            depth = sum(int(b.get('qty') or 0) for b in bids if C(b.get('price')) >= limit)
            qty = min(-delta, depth, int(me.get('availableSell') or 0))
            if qty <= 0:
                return
            payload = {'code': CODE, 'token': TOKEN, 'action': 'order', 'side': 'sell',
                       'price': round(limit, 2), 'qty': qty}
            reason = f'高估{-edge:.3g}，打买盘建空(估值{fair:.4g})'

        payload['reason'] = reason[:40]
        resp = post(payload)
        self.last_act = now
        self.trade_count += 1
        append('actions.log.jsonl', {'at': ts(), 'game': g.get('number'), 'round': g.get('round'),
                                     'fair': fair, 'mid': mid, 'edge': round(edge, 2),
                                     'pos_before': pos, 'target': target, 'payload': payload, 'resp': resp})
        p('ACT', payload['side'], payload['qty'], '@', payload['price'], 'fair', fair,
          'mid', round(mid, 2), 'pos', pos, '->', target, '|', resp, '|', reason)

        # 清理穿价后残留的挂单（避免留下不想要的报价）
        if resp.get('ok'):
            r2 = post({'code': CODE, 'token': TOKEN, 'action': 'cancelAll', 'reason': '清理穿价残留挂单'})
            append('actions.log.jsonl', {'at': ts(), 'action': 'cancelAll', 'resp': r2})

    # ---------- 线索冲击保护：人来不及反应时，代理先自己降暴露 ----------
    def news_shock(self, g):
        """新线索=不确定性跳升。若本局没有相互印证的独立先验，
        立刻撤掉旧估值挂单并把净持仓压回 newsFlatMax 以内。
        知识题（先验与共识互证）不触发，让盈利仓位继续奔跑。"""
        if g.get('phase') != 'trading':
            return
        c = control_for(g)
        if not c.get('newsFlat', True):
            return
        prior, op = c.get('fairPrior'), c.get('opening')
        agree = bool(c.get('priorIndependent') and prior and op
                     and abs(float(prior) - float(op)) / float(op) < 0.01)
        if agree:
            return
        cap = int(c.get('newsFlatMax', 3))
        me = g.get('me') or {}
        pos = int(me.get('position') or 0)
        r0 = post({'code': CODE, 'token': TOKEN, 'action': 'cancelAll',
                   'reason': '新线索到达，撤旧估值挂单'})
        append('actions.log.jsonl', {'at': ts(), 'action': 'news_cancelAll', 'resp': r0})
        if abs(pos) <= cap:
            return
        bk = g.get('book') or {}
        qty = abs(pos) - cap
        if pos < 0:
            ba = C(bk.get('bestAsk'))
            limit = round(ba * 1.03, 2) if ba else None
            side = 'buy'
            qty = min(qty, int(me.get('availableBuy') or 0))
        else:
            bb = C(bk.get('bestBid'))
            limit = round(bb * 0.97, 2) if bb else None
            side = 'sell'
            qty = min(qty, int(me.get('availableSell') or 0))
        if not limit or qty <= 0:
            return
        payload = {'code': CODE, 'token': TOKEN, 'action': 'order', 'side': side,
                   'price': limit, 'qty': qty,
                   'reason': f'线索冲击，仓位{pos}降至±{cap}'[:40]}
        r = post(payload)
        r2 = post({'code': CODE, 'token': TOKEN, 'action': 'cancelAll', 'reason': '清线索冲击残量'})
        self.reflect(f'线索冲击保护：撤旧挂单，仓位 {pos} → 目标±{cap}（{side} {qty}手）')
        append('actions.log.jsonl', {'at': ts(), 'game': g.get('number'), 'mode': 'news_shock',
                                     'pos_before': pos, 'payload': payload,
                                     'resp': r, 'cleanup': r2})
        p('NEWS_SHOCK', side, qty, '@', limit, 'pos', pos, '|', r)

    # ---------- 阶梯做市：在区间里收租 ----------
    def maker(self, g, hb, c):
        fair = float(c['fair'])
        now = time.time()
        if now - self.last_act < float(c['makerCooldown']):
            return
        # 估值跳变保护：改配置后先撤旧阶梯、空一个周期，避免新旧价位互相打架
        prev_fair = getattr(self, 'maker_fair', None)
        self.maker_fair = fair
        if prev_fair and abs(fair - prev_fair) / max(abs(prev_fair), 1e-9) > 0.10:
            r = post({'code': CODE, 'token': TOKEN, 'action': 'cancelAll',
                      'reason': '估值跳变，撤旧阶梯'})
            self.reflect(f'估值跳变 {prev_fair:.4g} → {fair:.4g}，撤旧阶梯并空一周期')
            append('actions.log.jsonl', {'at': ts(), 'action': 'fair_jump_cancelAll', 'resp': r})
            self.last_act = now
            return
        bk = g.get('book') or {}
        me = g.get('me') or {}
        best_ask, best_bid = C(bk.get('bestAsk')), C(bk.get('bestBid'))
        mid_now = (best_ask + best_bid) / 2 if (best_ask and best_bid) else fair
        far_from_fair = abs(mid_now - fair) / max(fair, 1e-9) > float(c['maxCrossGap'])
        pos = int(me.get('position') or 0)
        maxPos = max(1, int(c['maxPos']))
        base = int(c['baseQty'])
        bias = max(-1.0, min(1.0, pos / maxPos))
        rungs = c['rungs']
        if c.get('rungsPct'):
            rungs = [round(fair * x, 4) for x in c['rungsPct']]

        asks = bk.get('asks') or []
        bids = bk.get('bids') or []
        desired = {}
        for off in rungs:
            pb = round(fair - off, 2)
            ps = round(fair + off, 2)
            qb = max(0, round(base * (1 - bias)))
            qs = max(0, round(base * (1 + bias)))
            if qb > 0 and pb > 0:
                # 若买档会穿卖盘：卖一必须仍低于估值才算有利，且按可见深度限量
                if best_ask is not None and pb >= best_ask:
                    if (not far_from_fair) and best_ask < fair - 0.001:
                        dep = sum(int(a.get('qty') or 0) for a in asks if C(a.get('price')) <= pb)
                        desired[('buy', pb)] = min(qb, dep)
                else:
                    desired[('buy', pb)] = qb
            if qs > 0:
                # 若卖档会穿买盘：买一必须仍高于估值才算有利
                if best_bid is not None and ps <= best_bid:
                    if (not far_from_fair) and best_bid > fair + 0.001:
                        dep = sum(int(b.get('qty') or 0) for b in bids if C(b.get('price')) >= ps)
                        desired[('sell', ps)] = min(qs, dep)
                else:
                    desired[('sell', ps)] = qs
        desired = {k: v for k, v in desired.items() if v > 0}

        # 容量约束：挂单总量不能吃掉可用额度
        avail_b = int(me.get('availableBuy') or 0)
        avail_s = int(me.get('availableSell') or 0)
        my = {}
        for o in (me.get('orders') or []):
            key = (o.get('side'), round(C(o.get('price')) or 0, 2))
            my[key] = o
        kept_b = sum(int(o.get('remaining') or 0) for (s, _), o in my.items() if s == 'buy' and (s, _) in desired)
        kept_s = sum(int(o.get('remaining') or 0) for (s, _), o in my.items() if s == 'sell' and (s, _) in desired)
        add_b = max(0, avail_b)
        add_s = max(0, avail_s)

        # 先撤掉不再需要的挂单
        for key, o in my.items():
            if key not in desired:
                r = post({'code': CODE, 'token': TOKEN, 'action': 'cancel',
                          'orderId': o.get('id'), 'reason': '阶梯过期撤单'})
                append('actions.log.jsonl', {'at': ts(), 'action': 'cancel', 'key': list(key), 'resp': r})

        # 置信度自适应：独立先验与开盘共识相互印证，才允许开局瞬间打满仓
        prior, opening = c.get('fairPrior'), c.get('opening')
        agree = bool(c.get('priorIndependent') and prior and opening
                     and abs(float(prior) - float(opening)) / float(opening) < 0.01)
        age = now - getattr(self, 'game_start', now)
        limited = (not agree) and age < float(c['warmupSeconds'])
        eff = max(2, maxPos // 2) if limited else maxPos
        taker_budget = max(0, eff - abs(pos))
        if limited and not getattr(self, 'warmup_logged', False):
            self.warmup_logged = True
            self.reflect(f'低置信度开局：{c["warmupSeconds"]:.0f}秒内净持仓限{eff}手，分批建仓')

        # 再补齐缺失的档位
        for (side, pr), q in desired.items():
            if (side, pr) in my:
                continue
            crossed_now = ((side == 'buy' and best_ask is not None and pr >= best_ask) or
                           (side == 'sell' and best_bid is not None and pr <= best_bid))
            if crossed_now:
                q = min(q, taker_budget)
                if q <= 0:
                    continue
                taker_budget -= q
            if side == 'buy' and add_b < q:
                continue
            if side == 'sell' and add_s < q:
                continue
            reason = (f'低估区挂买{pr:.4g}(估值{fair:.4g})' if side == 'buy'
                      else f'高估区挂卖{pr:.4g}(估值{fair:.4g})')[:40]
            payload = {'code': CODE, 'token': TOKEN, 'action': 'order', 'side': side,
                       'price': pr, 'qty': q, 'reason': reason}
            r = post(payload)
            append('actions.log.jsonl', {'at': ts(), 'game': g.get('number'), 'round': g.get('round'),
                                         'mode': 'maker', 'fair': fair, 'pos': pos, 'payload': payload, 'resp': r})
            p('MAKER', side, q, '@', pr, 'F', fair, 'pos', pos, '|', r, '|', reason)
            if r.get('ok'):
                if side == 'buy':
                    add_b -= q
                else:
                    add_s -= q
                # 穿价单可能留下残量，立刻单独撤销（不误伤其他阶梯挂单）
                if crossed_now and r.get('orderId'):
                    rc = post({'code': CODE, 'token': TOKEN, 'action': 'cancel',
                               'orderId': r['orderId'], 'reason': '撤穿价单残留'})
                    append('actions.log.jsonl', {'at': ts(), 'action': 'cancel_residual',
                                                 'orderId': r['orderId'], 'resp': rc})
        self.last_act = now

    # ---------- 主循环 ----------
    def run(self):
        url = f'{BASE}/api/stream?code={CODE}&token={TOKEN}'
        self.reflect('代理启动：SSE 常驻，估值驱动，穿价后立即清残留；未联网搜索题目答案')
        while True:
            try:
                req = urllib.request.Request(url, headers={'Accept': 'text/event-stream'})
                with urllib.request.urlopen(req, timeout=95) as r:
                    p('SSE connected')
                    for raw in r:
                        try:
                            line = raw.decode('utf-8').strip()
                        except Exception:
                            continue
                        if not line.startswith('data: '):
                            continue
                        try:
                            d = json.loads(line[6:])
                        except Exception:
                            continue
                        if d.get('t') == 'state':
                            self.on_state(d)
                        elif d.get('t') == 'clock':
                            # 轻量：仅刷新心跳，不做空转决策
                            hb_path = os.path.join(D, 'heartbeat.json')
                            try:
                                with open(hb_path, encoding='utf-8') as f:
                                    hb = json.load(f)
                                hb['clock'] = {'round': d.get('round'), 'remain': d.get('remain'),
                                               'elapsed': d.get('elapsed'), 'lastPrice': C(d.get('lastPrice')),
                                               'at': ts()}
                                write('heartbeat.json', hb)
                            except Exception:
                                pass
            except Exception as e:
                p('SSE disconnected:', repr(e))
                append('errors.log.jsonl', {'at': ts(), 'err': repr(e)})
                time.sleep(1.0)


if __name__ == '__main__':
    try:
        Bot().run()
    except KeyboardInterrupt:
        p('stopped')
    except Exception:
        traceback.print_exc()
