#!/usr/bin/env python3
import json, time, urllib.request, urllib.parse, threading, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = 'http://192.168.1.7:7788'
CODE = '258334'
TOKEN = '5ad7fbdea14fad7bdba06ba46e65e6f7'
STATE_FILE = ROOT / 'latest_state.json'
LOG_FILE = ROOT / 'events.jsonl'
REVIEW_FILE = ROOT / '复盘记录.md'
CONFIG_FILE = ROOT / 'strategy.json'

DEFAULT_CONFIG = {
    'enabled': True,
    'fair_override': None,
    'own_estimate': 560.0,
    'opening_weight': 0.90,
    'quote_offset_pct': 0.010,
    'take_threshold_pct': 0.012,
    'quote_qty': 2,
    'max_abs_position': 8,
    'min_action_interval': 2.5,
    'paused_games': []
}
config_lock = threading.Lock()
state_lock = threading.Lock()
latest = None
last_action = 0.0
last_signature = None
last_game = None
fair_memory = {}


def log(kind, obj):
    rec = {'at': time.time(), 'kind': kind, 'data': obj}
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')


def load_config():
    try:
        with open(CONFIG_FILE, encoding='utf-8') as f:
            c = json.load(f)
        out = DEFAULT_CONFIG.copy(); out.update(c)
        return out
    except Exception:
        return DEFAULT_CONFIG.copy()


def post_act(payload, reason):
    body = {'code': CODE, 'token': TOKEN, 'reason': reason[:40]}
    body.update(payload)
    req = urllib.request.Request(BASE + '/api/act', data=json.dumps(body).encode(),
                                 headers={'Content-Type':'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=4) as r:
            ans = json.loads(r.read().decode())
        log('act', {'request': {k:v for k,v in body.items() if k != 'token'}, 'response': ans})
        return ans
    except Exception as e:
        log('act_error', {'request': {k:v for k,v in body.items() if k != 'token'}, 'error': str(e)})
        return None


def money(x):
    return None if x is None else x / 100.0


def decide(state):
    global last_action, last_signature, last_game
    g = state.get('game') or {}
    me = g.get('me') or {}
    phase = g.get('phase')
    gid = g.get('id')
    rnd = g.get('round')
    if not gid or phase != 'trading':
        return
    cfg = load_config()
    if not cfg.get('enabled', True) or gid in cfg.get('paused_games', []):
        return
    opening = money(g.get('openingPrice'))
    if cfg.get('fair_override') is not None:
        fair = float(cfg['fair_override'])
    elif gid in fair_memory:
        fair = fair_memory[gid]
    elif opening:
        fair = cfg['opening_weight'] * opening + (1-cfg['opening_weight']) * float(cfg['own_estimate'])
        fair_memory[gid] = fair
        log('fair_initialized', {'game':gid, 'fair':fair, 'opening':opening})
    else:
        return
    fair_memory[gid] = fair
    book = g.get('book') or {}
    asks = book.get('asks') or []
    bids = book.get('bids') or []
    best_ask = money(book.get('bestAsk'))
    best_bid = money(book.get('bestBid'))
    pos = me.get('position', 0) or 0
    avail_buy = me.get('availableBuy', 0) or 0
    avail_sell = me.get('availableSell', 0) or 0
    remain = g.get('roundRemain', 0) or 0
    sig = (gid, rnd, g.get('lastPrice'), best_ask, best_bid, pos,
           tuple((o.get('id'),o.get('remaining')) for o in me.get('orders',[])),
           round(fair,4), cfg.get('quote_offset_pct'), cfg.get('take_threshold_pct'))
    now = time.time()
    if sig == last_signature or now - last_action < float(cfg['min_action_interval']):
        return
    last_signature = sig
    last_action = now
    maxpos = int(cfg.get('max_abs_position', 8))
    take = float(cfg['take_threshold_pct'])
    # 只在明显偏离公允值时吃单，数量不超过可见档与风险预算。
    if best_ask is not None and best_ask < fair * (1-take) and pos < maxpos and avail_buy > 0:
        visible = sum(max(0, int(a.get('qty',0))) for a in asks if money(a.get('price')) < fair*(1-take))
        qty = min(visible or 1, avail_buy, maxpos-pos, 3)
        if qty > 0:
            post_act({'action':'order','side':'buy','price':round(best_ask,2),'qty':qty},
                     f'卖盘低于公允值{fair:.1f}，小仓买入')
            return
    if best_bid is not None and best_bid > fair * (1+take) and pos > -maxpos and avail_sell > 0:
        visible = sum(max(0, int(b.get('qty',0))) for b in bids if money(b.get('price')) > fair*(1+take))
        qty = min(visible or 1, avail_sell, maxpos+pos, 3)
        if qty > 0:
            post_act({'action':'order','side':'sell','price':round(best_bid,2),'qty':qty},
                     f'买盘高于公允值{fair:.1f}，小仓卖出')
            return
    # 估值偏移时先撤旧单，再围绕公允值双边报价；仓位越大越偏向减仓。
    if me.get('orders'):
        post_act({'action':'cancelAll'}, '盘口或估值变化，撤旧单再报价')
    offset = float(cfg['quote_offset_pct'])
    inventory_skew = pos / max(maxpos,1) * offset * 1.5
    center = fair * (1 - inventory_skew)
    tick = 0.5 if fair >= 100 else 0.05
    bid = math_floor(center*(1-offset), tick)
    ask = math_ceil(center*(1+offset), tick)
    q = max(1, min(int(cfg.get('quote_qty',2)), 2))
    if pos < maxpos and avail_buy > 0:
        post_act({'action':'order','side':'buy','price':bid,'qty':min(q,avail_buy,maxpos-pos)},
                 '公允值下方收租，控制多头敞口')
    if pos > -maxpos and avail_sell > 0:
        post_act({'action':'order','side':'sell','price':ask,'qty':min(q,avail_sell,maxpos+pos)},
                 '公允值上方收租，控制空头敞口')


def math_floor(x, tick):
    return round((int((x+1e-9)/tick))*tick, 2)

def math_ceil(x, tick):
    import math
    return round(math.ceil((x-1e-9)/tick)*tick, 2)


def handle_event(ev):
    global latest, last_game
    if ev.get('t') != 'state':
        return
    g = ev.get('game') or {}
    # 只保存接口明确交给自己的盘面；移除身份凭据。
    clean = dict(ev)
    if isinstance(clean.get('me'), dict):
        clean['me'] = {k:v for k,v in clean['me'].items() if k != 'token'}
    if isinstance(clean.get('game'), dict) and isinstance(clean['game'].get('me'), dict):
        clean['game'] = dict(clean['game'])
        clean['game']['me'] = {k:v for k,v in clean['game']['me'].items() if k != 'token'}
    with state_lock:
        latest = clean
        tmp = STATE_FILE.with_suffix('.tmp')
        tmp.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(tmp, STATE_FILE)
    gid = g.get('id')
    key = (gid, g.get('round'), g.get('phase'))
    if key != last_game:
        last_game = key
        log('phase', {'game':gid,'number':g.get('number'),'label':g.get('label'),
                      'question':g.get('question'),'round':g.get('round'),'phase':g.get('phase'),
                      'openingPrice':g.get('openingPrice'),'signals':g.get('signals'),
                      'history':g.get('history'),'resolution':g.get('resolution'),
                      'ranking':g.get('ranking'),'standings':ev.get('standings')})
    try:
        decide(ev)
    except Exception as e:
        log('decide_error', {'error':str(e), 'trace':traceback.format_exc()})


def run():
    url = BASE + '/api/stream?' + urllib.parse.urlencode({'code':CODE,'token':TOKEN})
    while True:
        try:
            req = urllib.request.Request(url, headers={'Accept':'text/event-stream'})
            with urllib.request.urlopen(req, timeout=30) as r:
                log('connection', {'status':'connected'})
                for raw in r:
                    line = raw.decode('utf-8', errors='replace').strip()
                    if not line.startswith('data:'):
                        continue
                    try:
                        ev = json.loads(line[5:].strip())
                        handle_event(ev)
                    except Exception as e:
                        log('parse_error', {'error':str(e)})
        except Exception as e:
            log('connection_error', {'error':str(e)})
            time.sleep(2)

if __name__ == '__main__':
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2), encoding='utf-8')
    if not REVIEW_FILE.exists():
        REVIEW_FILE.write_text('# 临渊量化复盘记录\n\n- 不联网搜索答案；只使用题面、公开线索和盘面。\n- 初估：上海肯德基约 560 家，开盘后将高权重采用脚本共识。\n\n', encoding='utf-8')
    log('startup', {'base':BASE,'code':CODE})
    run()
