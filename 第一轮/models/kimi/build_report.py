#!/usr/bin/env python3
import json, html, math
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent
EVENTS = ROOT / 'events.jsonl'
EXPORT = Path('/Users/yuanf/DoubaoWork/chats/2026-11-19/new-chat-1/赛后数据/竞技场-258334-20261122-004051.json')
OUT = ROOT / '临渊量化全场详细复盘-逐轮逐笔版.html'
MY_NAME = '豆包-远方的 mac-Kimi '

events = [json.loads(line) for line in EVENTS.open(encoding='utf-8') if line.strip()]
phase_entries = [e for e in events if e.get('kind') == 'phase']
trading_windows = {}
for e in phase_entries:
    d = e.get('data') or {}
    if d.get('phase') == 'trading' and d.get('number') is not None and d.get('round') is not None:
        trading_windows.setdefault(d['number'], []).append((e['at'], d['round']))
for n in trading_windows:
    trading_windows[n].sort()

def action_round(n, at):
    if at is None:
        return None
    wins = trading_windows.get(n, [])
    for t, r in reversed(wins):
        if t <= at + 0.05:
            return r
    return None
settled = [e['data'] for e in phase_entries if e['data'].get('phase') == 'settled']
settled.sort(key=lambda g: g['number'])

starts = []
seen = set()
for e in phase_entries:
    g = e['data']
    if g['number'] not in seen:
        seen.add(g['number'])
        starts.append((e['at'], g['number']))
starts.sort()
actions_by_game = {n: [] for _, n in starts}
for e in events:
    if e.get('kind') != 'act':
        continue
    n = next((n for t, n in reversed(starts) if t <= e['at']), 1)
    req = e['data']['request']
    actions_by_game[n].append({
        'at': e['at'], 'action': req.get('action'), 'side': req.get('side', ''),
        'price': req.get('price'), 'qty': req.get('qty'), 'orderId': req.get('orderId'),
        'reason': req.get('reason', ''), 'response': e['data'].get('response', {}),
        'source': '自动策略日志'
    })
# 手工接口调用不经过自动策略日志，单独补记；时间留空，避免伪造精确时间戳。
actions_by_game[12].append({
    'at': None, 'action': 'order', 'side': 'sell', 'price': 98.5, 'qty': 6,
    'orderId': 393, 'reason': '真值约85次，现价显著高估，单次建空持有',
    'response': {'ok': True, 'filled': 0, 'remaining': 6}, 'source': '人工接口复核'
})

# 赛后导出只提取本方真实成交。对手保留比赛公开显示的参赛名，不写内部 ID、持仓或思考。
export_data = json.loads(EXPORT.read_text(encoding='utf-8'))

def match_execution(n, trade):
    """把一笔成交关联到同场、同方向、相近时间、限价可成交的最近一条委托。
    只作为“执行理由”的证据链，不声称服务器把成交与委托做了唯一主键绑定。
    """
    fill = trade['price'] / 100
    at = trade['at'] / 1000
    qty = trade['qty']
    side = trade['side']
    candidates = []
    for a in actions_by_game.get(n, []):
        if a.get('action') != 'order' or a.get('at') is None:
            continue
        if a.get('side') != side or (a.get('qty') or 0) < qty:
            continue
        gap = abs(a['at'] - at)
        if gap > 5:
            continue
        limit = a.get('price')
        if limit is None:
            continue
        if side == 'buy' and limit < fill - 1e-9:
            continue
        if side == 'sell' and limit > fill + 1e-9:
            continue
        candidates.append((gap, abs(limit - fill), a))
    if not candidates:
        return None
    gap, _, a = min(candidates, key=lambda x: (x[0], x[1]))
    return {
        'reason': a.get('reason') or '',
        'orderId': a.get('orderId') or (a.get('response') or {}).get('orderId'),
        'gap': gap, 'limit': a.get('price'), 'at': a.get('at'),
    }

trades_by_game = {}
matched_exec = 0
for exported_game in export_data['games']:
    n = exported_game['number']
    me = next(p for p in exported_game['review']['players'] if p.get('name') == MY_NAME)
    trades = []
    for t in me['trades']:
        m = match_execution(n, t)
        if m:
            matched_exec += 1
        trades.append({
            'id': t['id'], 'round': t['round'], 'at': t['at'] / 1000,
            'side': t['side'], 'price': t['price'] / 100, 'qty': t['qty'],
            'positionAfter': t['positionAfter'], 'realizedPnl': t['realizedPnl'] / 100,
            'counterpartyType': '脚本' if t['program'] else '模型',
            'counterparty': t.get('counterparty') or '未知对手',
            'execReason': m['reason'] if m and m['reason'] else '日志中无同向可成交委托，按持仓与公允值反推',
            'execOrderId': m['orderId'] if m else None,
            'execGap': round(m['gap'], 2) if m else None,
            'execLimit': m['limit'] if m else None,
            'execMatched': bool(m)
        })
    buy = [t for t in trades if t['side'] == 'buy']
    sell = [t for t in trades if t['side'] == 'sell']
    buy_qty = sum(t['qty'] for t in buy)
    sell_qty = sum(t['qty'] for t in sell)
    volume = buy_qty + sell_qty
    # 全市场逐轮成交回报：同一笔成交在买卖双方各出现一次，按 trade id 去重，只取买方腿。
    market_prints = {}
    for pl in exported_game['review']['players']:
        for tx in pl['trades']:
            key = (tx['round'], tx['id'])
            if key not in market_prints or tx['side'] == 'buy':
                market_prints[key] = tx
    market_by_round = {}
    for r in sorted({k[0] for k in market_prints}):
        rows = sorted([v for (rr, _), v in market_prints.items() if rr == r], key=lambda x: x['at'])
        prices = [x['price'] / 100 for x in rows]
        mvol = sum(x['qty'] for x in rows)
        vwap = sum(x['price'] * x['qty'] for x in rows) / sum(x['qty'] for x in rows) / 100 if rows else None
        close_row = next((h for h in exported_game.get('history', []) if h.get('round') == r), None)
        orders = [a for a in actions_by_game.get(n, []) if a.get('action') == 'order' and action_round(n, a.get('at')) == r]
        if n == 12 and r == 3:
            orders = orders + [{'price': 98.5, 'side': 'sell', 'qty': 6, 'reason': '真值约85次，现价显著高估，单次建空持有', 'at': None, 'source': '人工接口复核'}]
        cancels = [a for a in actions_by_game.get(n, []) if a.get('action') == 'cancelAll' and action_round(n, a.get('at')) == r]
        buys = [a['price'] for a in orders if a.get('side') == 'buy' and a.get('price') is not None]
        sells = [a['price'] for a in orders if a.get('side') == 'sell' and a.get('price') is not None]
        own_round_trades = [t for t in trades if t['round'] == r]
        prior = [t for t in trades if t['round'] < r]
        start_pos = prior[-1]['positionAfter'] if prior else 0
        no_fill = ''
        if not own_round_trades:
            cap_note = ''
            if start_pos <= -8 and buys and not sells:
                cap_note = f'轮初已持有 {start_pos} 手空仓，达到当时 8 手库存上限，不能再加空，只能挂买回单。'
            if not orders:
                no_fill = (f'本轮没有新委托，只有 {len(cancels)} 次撤单，因此不可能产生本方成交。' if cancels else '本轮没有新委托：自动交易已停用或没有人工下单，因此不会产生本方成交。')
            elif buys and not sells and rows and max(buys) < min(prices):
                no_fill = cap_note + f'最高买价 {max(buys):g} 仍低于市场最低成交价 {min(prices):g}，价差 {min(prices)-max(buys):.2f}；没有卖方愿意卖到这个价位。'
            elif sells and not buys and rows and min(sells) > max(prices):
                no_fill = f'只挂了卖单，最低卖价 {min(sells):g} 仍高于市场最高成交价 {max(prices):g}，价差 {min(sells)-max(prices):.2f}；没有买方愿意买到这个价位。'
            elif buys and sells and rows and max(buys) < min(prices) and min(sells) > max(prices):
                no_fill = f'双向报价都落在市场成交区间之外：买价上限 {max(buys):g} 低于最低成交 {min(prices):g}，卖价下限 {min(sells):g} 高于最高成交 {max(prices):g}。'
            elif rows:
                buy_txt = f'买 {min(buys):g}–{max(buys):g}' if buys else '未挂买'
                sell_txt = f'卖 {min(sells):g}–{max(sells):g}' if sells else '未挂卖'
                no_fill = f'报价落在市场区间内（{buy_txt}；{sell_txt}），但对手没有扫到本方挂单，属于排队/时点未成交，不是价格判断被否定。'
            else:
                no_fill = '本轮全市场没有成交回报，无法从成交价判断；只能确认本方没有成交。'
            if n == 12 and r == 3:
                no_fill = '人工接口在 98.5 挂出 6 手卖单，未成交；' + no_fill
        market_by_round[str(r)] = {
            'round': r, 'open': prices[0] if prices else None, 'high': max(prices) if prices else None,
            'low': min(prices) if prices else None,
            'close': close_row['price'] / 100 if close_row and close_row.get('price') is not None else (prices[-1] if prices else None),
            'vwap': vwap, 'volume': mvol, 'prints': len(rows),
            'buyLo': min(buys) if buys else None, 'buyHi': max(buys) if buys else None,
            'sellLo': min(sells) if sells else None, 'sellHi': max(sells) if sells else None,
            'orderCount': len(orders), 'cancelCount': len(cancels), 'noFillReason': no_fill
        }
    program_qty = sum(t['qty'] for t in trades if t['counterpartyType'] == '脚本')
    vwap = lambda rows: (sum(t['price'] * t['qty'] for t in rows) / sum(t['qty'] for t in rows)) if rows else None
    rounds = []
    for r in sorted(set(t['round'] for t in trades)):
        rows = [t for t in trades if t['round'] == r]
        rounds.append({
            'round': r, 'tradeCount': len(rows),
            'buyQty': sum(t['qty'] for t in rows if t['side'] == 'buy'),
            'sellQty': sum(t['qty'] for t in rows if t['side'] == 'sell'),
            'endPosition': rows[-1]['positionAfter'],
            'realized': sum(t['realizedPnl'] for t in rows)
        })
    trades_by_game[n] = {
        'trades': trades, 'tradeCount': len(trades), 'actualBuyQty': buy_qty,
        'actualSellQty': sell_qty, 'actualVolume': volume,
        'buyVWAP': vwap(buy), 'sellVWAP': vwap(sell),
        'programQty': program_qty, 'modelQty': volume - program_qty,
        'programShare': program_qty / volume * 100 if volume else None,
        'tradeRealized': sum(t['realizedPnl'] for t in trades),
        'roundStats': rounds, 'marketByRound': market_by_round,
        'positionSeries': [{'x': '开局', 'y': 0, 'xLabel': '开局'}] + [
            {'x': i + 1, 'y': t['positionAfter'],
             'xLabel': str(i + 1) if (i + 1) % max(1, math.ceil(len(trades) / 10)) == 0 or i + 1 == len(trades) else ''}
            for i, t in enumerate(trades)
        ]
    }

# 逐轮注记：只写可审计的公开线索、当时公允值变化与事后归因，不冒充逐字内部推理。
round_notes = {
1: {
 1:'初始锚为700.049，价格上冲后锚上移至约715.6。本轮成交18笔，已实现达到158.68，但空仓一度到-10手；按本轮收盘744.74静态计量，反而约为-15.02。',
 2:'第二轮全市场在 733.34—790.00 之间成交，开 744.75、收 733.34；空仓已到 -8 手的库存上限，策略不能再加空，只能挂买回单。买价从 703 抬到 729.50，仍低于市场最低成交价 733.34，差 3.84，因此零成交。必胜客 4168 家无法映射到上海肯德基数量，也没有据此改锚；按收盘 733.34 静态计量约 +76.18。',
 3:'麦当劳600家只支持“肯德基可能高于600”，被用作把锚上移至735的理由。三笔回补4手，已实现减少12.39，最终-4手按真值700结算，整局+238.40。'
},
2: {
 1:'非洲总面积3020万平方公里只是弱背景，不能唯一确定国家。围绕开盘11.32与个人初估11.09交易，净多最高3手，未把开局的浮盈当成新信息。',
 2:'人口约975万开始指向古巴，面积可重估为10.99；这是本轮真正的强识别线索，策略由围绕开盘收租转为优先降低多头。',
 3:'海岸线约5746千米继续确认岛国特征，锚保持10.99；价格仍在真值附近时双向交易，不为已有盈利拒绝反手。',
 4:'西班牙是第50名、面积50.6万平方公里，只能提供位次尺度，不能推出第104名的精确面积；本轮继续以10.99为锚。',
 5:'末轮直接公布国家为古巴，真值收敛到10.99。价格跌到10.64后由空转多，最终净多8手，是“强线索确认后允许方向反转”的典型。'
},
3: {
 1:'全国铁路16.2万公里是总口径，高铁约占三成可交叉校验4.8。个人初估与开盘同为4.80，本轮围绕固定锚低买高卖。',
 2:'高铁占比约三成继续支持4.8附近，没有出现要求改锚的证据；降低吃单阈值后，小幅偏离也能形成成交。',
 3:'2024年投产新线超过3000公里、其中高铁过半，仍与4.8相容；重点由猜答案转为在固定锚附近完成兑现。'
},
4: {
 1:'上海港连续多年全球第一，支持千万级TEU量级，但不足以给出精确值。价格上冲至5183.49时做空，是围绕5150.6固定锚的逆向交易。',
 2:'洋山港区贡献四成以上只描述内部结构，不能推出总量；价格回落至5141.50附近后兑现并考虑反手，库存偏移开始影响报价。',
 3:'同比增速约5%不改变当年吞吐量答案；价格回到5120附近转为净多，尾盘修正库存偏移，避免在高置信度锚下方过早卖出。'
},
5: {
 1:'机场分布在全国30多个省级行政区只提供覆盖背景，不能推出总数；个人与开盘均为263，本轮在价格上冲时做空。',
 2:'千万级机场约40个是结构信息，不改变263的存量判断；策略继续围绕固定锚交易并逐步兑现。',
 3:'“2024年新投产3个”被错误理解为存量净增3个，锚下调至262；但颁证存量与投产时点并非简单相加，结算仍为263。'
},
6: {
 1:'只知道上周买了两盒，购入量不等于剩余量，消耗完全未知；开盘锚22.55，弱先验阶段本应保持更小库存。',
 2:'一盒10枚、一盒30枚确认总购入40枚，但仍不知道已吃多少；本轮只补了两笔，持仓风险已经偏高。',
 3:'五天每天2个给出可计算消耗10个，剩余40-10=30；锚立即改为30并回补空仓，方向在末轮才真正确定。'
},
7: {
 1:'周六没有体育课、跑步或骑行，只能排除高步数活动，不能推出精确步数；以8000为弱锚，仓位保持克制。',
 2:'步行往返图书馆与宿舍、只乘一次地铁，仍不足以得到精确数字；本轮成交少，等待更强约束。',
 3:'四位数、千位8、百位4把支持域压缩到8400—8499，以8450为中值；价格8599已超出上界，做空具有区间外赔率。'
},
8: {
 1:'活动范围只在校园与住处、在外不足三小时，支持照片不多，但仍无法精确；以15为弱锚，仅做小仓试探。',
 2:'照片全部同机拍摄、一半以上为同景连拍，提示存在大量连拍冗余；仍不足以确定个位数。',
 3:'“个位数且为质数”给出2、3、5、7，结合连拍选择7；方向正确，但27笔成交把快速回归做成了反复回补与反手。'
},
9: {
 1:'“看到红点就点掉、从不留未读”几乎直接给出0，开盘36.63因此可被推翻；本轮20笔主要用于从旧锚转向空头。',
 2:'过去二十四小时不静音、提示音一响就看，继续支持下界；只成交2笔，持仓方向已经明确。',
 3:'线索再次强调靠近区间下界，结算为0；策略保持净空8手，问题不在方向，而在建仓速度慢于更早做空的对手。'
},
10: {
 1:'周六无网课、白天在图书馆，只能说明使用结构，不能给出七天总时长；以40小时为弱锚，仓位有限。',
 2:'学习与通讯为主、娱乐不足两成，仍不能推出精确小时数；本轮13笔更多是围绕旧锚的双边交易。',
 3:'日均3.5—4小时对应七天24.5—28小时，取中值26.25；区间判断正确，但21笔在改锚后反复反手，已实现被消耗。'
},
11: {
 1:'“只增不删”支持好友数量较大，但无法推出精确四位数；开盘1036.66附近没有足够赔率，人工选择不交易。',
 2:'同学约占四分之一、其余为社团、实习同事与家人，只描述结构，不改变总量判断；继续空仓。',
 3:'四位数、1000—1100把支持域缩窄，真值1001；现价约1045位于区间中部，买卖赔率都不清晰，零成交是主动决策。'
},
12: {
 1:'上午两节课、下午图书馆、晚上回住处，只是日程背景，不能推出解锁次数；空仓等待。',
 2:'每次解锁基本只做一件事，说明单次使用较短，但仍不能推出总次数；继续不交易。',
 3:'两位数、比80多一点且不到90，估值取85；人工在98.5挂卖6手但未成交，价格随即回到84—86，放弃追价，最终空仓。'
}
}

estimates = {1:560, 2:11.09, 3:4.8, 4:5150.6, 5:263, 6:10, 7:8000, 8:15, 9:30, 10:42, 11:400, 12:70}
short_titles = {
    1:'上海肯德基门店数', 2:'面积第104大的国家', 3:'中国高铁营业里程',
    4:'上海港集装箱吞吐量', 5:'民用运输机场数量', 6:'冰箱里的鸡蛋',
    7:'当天步行步数', 8:'相册新增照片', 9:'微信未读消息',
    10:'七天屏幕使用时长', 11:'微信通讯录好友', 12:'手机解锁次数'
}

# 这里记录的是可审计的决策依据、策略参数和事后归因，不是逐字内部推理。
narratives = {
1:{
 'stage':'自动做市 V1：开盘加权、库存偏移、双边收租',
 'decision':[
  '初估 560 家，开盘后看到全场中位数 715.61，说明个人先验与房间共识差距很大。策略最初采用 90% 开盘价与 10% 个人估价，得到约 700.04 的公允值。这个数字事后几乎正中 700 的结算值，但当时并不知道它如此准确。',
  '第一轮价格快速上冲，策略在高位做空并靠低位回补取得已实现收益；随后把公允值上调到 715.6，第二轮又把常规库存上限从 8 降到 4。第三轮上海麦当劳 600 家的线索出现后，公允值进一步上调到 735，试图兼顾竞品锚与价格动量。',
  '尾盘价格达到 800.01，相对真值出现约 14.3% 的溢价。最终净空 4 手，结算仍盈利 238.40、排名第 4。这里要把“事后命中”与“过程正确”分开：700.04 只是最接近真值的事后结果，含运气成分，不等于越早的估值天然越优；715.6 更像发现个人先验不可靠后向开盘共识的合理回归；735 才是被“上海麦当劳 600 家”这一弱线索与价格动量共同推着走。真正的问题不在改不改锚，而在低置信度下把空仓加到 10 手、缺少独立风险刹车。'
 ],
 'flow':'56 笔委托、40 次全撤；买入委托 94 手、卖出委托 18 手。先高位做空，再在均值回归中回补，尾盘保留空仓。委托量远大于最终仓位，体现早期高频撤改单特征。',
 'lesson':'弱相关经营数据不应单独改写估值；但开盘价是市场证据，向它适度回归不算追随动量。真正需要限制的是低置信度下被价格牵引的连续加仓，以及库存过大后被迫单向交易。'
},
2:{
 'stage':'自动做市 V2：尊重开盘，识别强线索后双向交易',
 'decision':[
  '初估 11.09 万平方公里，开盘 11.32。第一轮只有非洲总面积这一弱背景信息，策略没有据此改动估值，而是在开盘附近低买高卖。',
  '第二轮“2024 年人口约 975 万”是识别人口下降后的古巴的重要线索；第三轮海岸线约 5746 千米继续支持这一判断。古巴面积 109,884 平方千米，即 10.9884 万平方公里，保留两位小数为 10.99，于是把公允值从开盘价下调到 10.99。',
  '末轮直接公布国家为古巴，估值得到完全确认。价格先高于真值，后跌至 10.64，策略没有执着原有空仓，而是在低位反向买入，最终净多 8 手。'
 ],
 'flow':'166 笔委托、91 次全撤，是全场动作最密集的一局。买入委托 176 手、卖出委托 139 手。先围绕开盘收租，人口线索后减多，数字真值确认后先空后多，结算净多 8 手。',
 'lesson':'强线索可以推翻开盘共识，而且交易方向必须可逆：高于真值时卖、低于真值时买。最终第 2 名来自“估值识别”和“低价接多”的共同作用，而非单纯高频。'
},
3:{
 'stage':'自动做市 V2：高置信度固定锚、降低吃单阈值',
 'decision':[
  '初估 4.8 万公里，开盘价也正好 4.80，个人先验与全场共识一致，因此直接把 4.8 作为高置信度固定锚，不再让开盘价覆盖独立判断。',
  '第一轮全国铁路总里程 16.2 万公里，第二轮高铁占比约三成，第三轮新线投产信息均与 4.8 相容。没有新信息要求改变估值，重点变成如何提高对小幅偏离的利用率。',
  '吃单阈值由 1.2% 降至 0.5%，在 4.75 附近回补并接多，在 4.80 上方逐步兑现。最终持仓归零，全部收益落袋。'
 ],
 'flow':'120 笔委托、57 次全撤；买入委托 113 手、卖出委托 124 手。先高位卖出，再在低于固定锚时买入，最终零持仓，结算盈亏 2.48。',
 'lesson':'当独立估价、开盘共识和后续线索三者一致时，较窄的吃单阈值是合理的。小幅均值回归也能取得第 2 名，不必依赖大方向赌注。'
},
4:{
 'stage':'自动做市 V2：固定锚与库存偏移冲突',
 'decision':[
  '初估 5150.6 万 TEU，开盘恰好 5150.60。第一轮全球排名、第二轮洋山港区占比、第三轮同比增速都没有推翻这一估计。',
  '价格上冲至 5183.49 时策略做空，回落至 5141.50 后兑现并反手，第三轮在 5120 附近转为净多 4 手。方向切换总体符合“高于锚卖、低于锚买”。',
  '尾盘发现库存偏移会让卖价低于高置信度真值，造成过早兑现，于是临时把报价中心上调到 5180，用来抵消库存 skew 的副作用。最终净多 1 手，结算口径取约数 5150。'
 ],
 'flow':'114 笔委托、60 次全撤；买入委托 117 手、卖出委托 91 手。高位空、低位多，最终净多 1 手，结算盈亏 466.30。',
 'lesson':'要区分精确值与公开约数的结算口径；库存偏移不能穿越高置信度公允值。修正报价中心的目的应是防止错误减仓，而不是重新猜测真值。'
},
5:{
 'stage':'自动做市 V2：固定锚被间接线索错误推翻',
 'decision':[
  '初估与开盘均为 263。第一轮覆盖范围、第二轮千万级机场数量都没有改变估值，策略在价格上冲时做空并兑现。',
  '第三轮给出“2024 年新投产运输机场 3 个”，当时用 2023 年 259 个简单相加，把公允值下调到 262，认为存量也应减少一个单位。',
  '结算真值却仍是 263。这说明新增投产与颁证存量之间不是简单算术关系，可能涉及颁证时点、退出或统计口径。尽管估值调整错误，原有空仓仍有盈利，最终第 5。'
 ],
 'flow':'120 笔委托、58 次全撤；买入委托 124 手、卖出委托 107 手。最终净空 3 手，已实现 24.13、结算盈亏 27.39。',
 'lesson':'“新增 3 个”不等于“存量净增 3 个”。初始估价与开盘共识一致时，单一间接线索不足以轻易改锚。这局盈利不能掩盖推理错误。'
},
6:{
 'stage':'自动做市 V3：弱先验小仓，末轮算术改锚',
 'decision':[
  '初估 10 个，开盘 22.55。第一轮只知道上周买了两盒，第二轮确认一盒 10 枚、另一盒 30 枚，总购入量为 40，但消耗仍未知。',
  '前两轮沿用开盘锚并逆向交易，空仓一度达到 4 手。末轮明确五天每天煎 2 个、没有其他消耗，因此真值可以直接计算为 40 − 5 × 2 = 30。',
  '公允值立即改为 30，策略开始回补空仓并买入，最终净多 3 手。方向判断在末轮是正确的，但前期空头回补成本较高，最终亏损 16.75。'
 ],
 'flow':'94 笔委托、58 次全撤；买入委托 128 手、卖出委托 50 手。先空后多，结算净多 3 手，已实现 −17.95。',
 'lesson':'鸡蛋这类题目把决定性信息放在末轮，前两轮的价格并不包含完整答案。弱先验阶段应把库存上限降到 2，而不是在消耗未知时积累较大空仓。'
},
7:{
 'stage':'自动做市 V3：区间中值交易，弱先验限仓 2 手',
 'decision':[
  '初估和开盘均为 8000 步。前两轮只排除体育训练，并确认步行往返图书馆、宿舍与一次地铁，无法推出精确步数，仓位控制在 2 手。',
  '末轮给出四位数、千位 8、百位 4，支持域一下压缩到 8400–8499。以区间中值 8450 改锚，并把上限恢复至 4 手。',
  '价格先低于区间，随后冲至 8599，策略完成低位买入与高位反向，最终净空 4 手。结算真值 8476，空仓方向正确，单局收益 911.22。'
 ],
 'flow':'109 笔委托、61 次全撤；买入委托 136 手、卖出委托 77 手。先低位接多，再在区间上方做空，结算净空 4 手。',
 'lesson':'不精确的数字特征也能形成可交易支持域。应按区间中值定价、在区间外寻找机会，而不是等待不存在的精确答案。这局证明“弱先验小仓、强区间加仓”是有效的。'
},
8:{
 'stage':'自动做市 V3：正确估值被高频回归执行吞噬',
 'decision':[
  '初估与开盘均为 15 张。前两轮只说明活动少、同一景物连拍占一半以上，没有精确数量，保持小仓。',
  '末轮限定个位质数，只可能是 2、3、5、7。结合连拍占半数以上，7 最符合情境，因此把公允值改为 7，结算也证实了这一判断。',
  '问题出在执行：价格由 14–15 快速跌向 7 时，策略不断吃单、回补、反手，最终净多 2 手。虽然最终多头的结算价值接近成本，但过程中已实现亏损较大，整局亏损 7.63。'
 ],
 'flow':'89 笔委托、56 次全撤；买入委托 45 手、卖出委托 130 手。先高位做空，后在下跌途中不断回补并转为净多 2 手。',
 'lesson':'估值正确不等于交易正确。强线索后的目标应是保留方向利润，而不是围绕新锚反复做价差。快速回归阶段尤其要减少反手。'
},
9:{
 'stage':'自动做市 V3：直接答案线索，尽早建立大空仓',
 'decision':[
  '初估 30 条，开盘 36.63。第一轮“看到红点就点掉，从不在列表里留未读”几乎直接给出 0 条，因此开盘共识可以被果断推翻。',
  '策略改为接近 0 的公允值并做空。后两轮继续说明提示音一响就看、数字靠近下界，没有例外条件。末轮把高确定性空仓上限由 4 提高到 8。',
  '最终净空 8 手，结算 0，单局盈利 252.54。虽然只排第 8，但这是方向、仓位与结算完全一致的案例。'
 ],
 'flow':'79 笔委托、55 次全撤；买入委托 124 手、卖出委托 30 手。买入委托用于高位空头回补和低位报价，最终净空 8 手。',
 'lesson':'对几乎直接揭示答案的首轮线索，应更早达到目标仓位。本局收益不及部分对手，差距在于他们更早建立大空仓，而不是我们的结算方向错误。'
},
10:{
 'stage':'自动做市 V3：区间改锚与自动反手再次冲突',
 'decision':[
  '初估 42 小时，开盘 40。前两轮仅描述图书馆日程和应用用途，没有足够信息改锚，保持小仓。',
  '末轮给出日均 3.5–4 小时，对应七天 24.5–28 小时，以 26.25 为中值。结算真值 25.6，确实落在区间内，估值方向正确。',
  '策略从原有多头快速反手并围绕新锚持续交易，最终净空 2 手，但已实现亏损 13.69，整局亏损 11.38。和照片题一样，主要亏损来自执行过程，而非区间判断。'
 ],
 'flow':'99 笔委托、51 次全撤；买入委托 65 手、卖出委托 122 手。先平多、再做空，最终净空 2 手。',
 'lesson':'这是停用自动做市的直接触发点。强区间线索出现后，不应让算法同时处理库存回归与价差收租；一次方向建仓并持有，比连续反手更符合题目结构。'
},
11:{
 'stage':'人工低频 V4：没有赔率就不交易',
 'decision':[
  '初估 400 个，开盘却达到 1036.66，表明个人先验严重偏低。第一轮只增不删、第二轮好友构成都支持较大规模，但无法给出精确值。',
  '末轮只限定四位数、1000–1100，当前约 1045 已位于合理区间。此时买入或卖出都没有清晰赔率，因此保持空仓。',
  '最终真值 1001，空仓排名第 10、获得 6 分。虽然没有盈利，但避免了在区间中部因噪声交易造成亏损。'
 ],
 'flow':'自动策略停用，无委托、无撤单、无成交，最终持仓为 0。',
 'lesson':'不交易也是有效决策。复盘不能把“零收益”简单视为失败，应比较它相对于可选交易的反事实风险。'
},
12:{
 'stage':'人工低频 V4：单次方向委托，不追已消失的价格',
 'decision':[
  '结合此人每日屏幕使用约 3.5–4 小时的情境，初估 70 次，开盘 100。前两轮日程和使用习惯没有提供精确数量。',
  '末轮限定 80–90 且比 80 多一点，取 85 为估值，尝试在 98.5 卖出 6 手。可是下单前价格已迅速回到 84–86，委托没有成交。',
  '此时最佳卖价已经消失，追单会把正确估值变成差价格，因此不再追补。最终真值 87，空仓仍排名第 6、获得 10 分。'
 ],
 'flow':'仅有 1 笔人工卖出委托，价格 98.5、数量 6 手，未成交并保留至收盘；无实际持仓。',
 'lesson':'强线索后的盘口反应极快。放弃已经消失的收益，比用更差价格追补更重要。低频策略避免了上一轮那样的反手亏损，但也意味着放弃部分潜在收益。'
}
}

games = []
for g in settled:
    n = g['number']
    my = next(r for r in g['ranking'] if r['name'] == MY_NAME)
    acts = actions_by_game.get(n, [])
    cnt = Counter(a['action'] for a in acts)
    buy_qty = sum(a.get('qty') or 0 for a in acts if a['action']=='order' and a['side']=='buy')
    sell_qty = sum(a.get('qty') or 0 for a in acts if a['action']=='order' and a['side']=='sell')
    hist = [{'round':h['round'], 'price':None if h.get('price') is None else h['price']/100,
             'volume':h.get('volume',0), 'orders':h.get('orders',0), 'tradeCount':h.get('tradeCount',0)} for h in g.get('history',[])]
    standing_me = next((r for r in g.get('standings',{}).get('rows',[]) if r['name']==MY_NAME), {})
    games.append({
        'number':n, 'formal':n-1, 'label':g['label'], 'title':short_titles[n],
        'question':g['question']['q'], 'unit':g['question']['unit'], 'practice':n==1,
        'estimate':estimates[n], 'opening':g['openingPrice']/100,
        'truth':g['resolution']['price']/100, 'note':g['resolution']['note'],
        'signals':g['signals'], 'history':hist, 'rank':my['rank'], 'points':my['points'],
        'pnl':my['pnl']/100, 'realized':my['realized']/100, 'position':my['position'],
        'totalPoints':standing_me.get('points'), 'overallRank':standing_me.get('rank'),
        'actionCount':len(acts), 'orderCount':cnt.get('order',0), 'cancelCount':cnt.get('cancelAll',0),
        'buyQty':buy_qty, 'sellQty':sell_qty, 'narrative':narratives[n], 'actions':acts,
        'roundNotes':round_notes[n], **trades_by_game[n]
    })

DATA = json.dumps(games, ensure_ascii=False, separators=(',',':')).replace('</','<\\/')

CSS = r'''
:root{--paper:#f4f0e7;--card:#fffdf8;--ink:#213139;--muted:#68767a;--line:#d9d1c2;--red:#a34e3c;--gold:#b08a4b;--teal:#356d6a;--navy:#172a33;--green:#32705b;--shadow:0 12px 34px rgba(31,42,45,.08)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font-family:"Times New Roman","Kaiti SC","KaiTi",serif;line-height:1.85;font-size:17px}h1,h2,h3,h4{font-weight:700;line-height:1.35;margin:0 0 16px}h2{font-size:32px;margin-top:8px}h3{font-size:24px}h4{font-size:19px}p{margin:10px 0}a{color:inherit}.hero{background:linear-gradient(135deg,#142832,#28444a 70%,#3b5b58);color:#f8f2e6;padding:72px max(5vw,24px) 56px;position:relative;overflow:hidden}.hero:after{content:"";position:absolute;width:520px;height:520px;border:1px solid rgba(255,255,255,.1);border-radius:50%;right:-120px;top:-180px;box-shadow:0 0 0 70px rgba(255,255,255,.025),0 0 0 140px rgba(255,255,255,.02)}.eyebrow{letter-spacing:.22em;color:#d6ba80;font-size:13px;text-transform:uppercase}.hero h1{font-size:clamp(40px,6vw,72px);letter-spacing:.05em;margin:18px 0 12px;position:relative;z-index:1}.hero .sub{font-size:20px;color:#d8e0dd;max-width:900px}.hero-meta{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}.pill{display:inline-block;padding:4px 12px;border-radius:999px;background:#e9e1d2;color:#425054;font-size:13px;line-height:1.6}.hero .pill{background:rgba(255,255,255,.1);color:#f5e9d2;border:1px solid rgba(255,255,255,.14)}.layout{max-width:1460px;margin:0 auto;display:grid;grid-template-columns:240px minmax(0,1fr);gap:36px;padding:34px 28px 80px}.toc{position:sticky;top:22px;align-self:start;max-height:calc(100vh - 44px);overflow:auto;padding:22px 18px;background:rgba(255,253,248,.72);border:1px solid var(--line);border-radius:16px}.toc strong{display:block;margin-bottom:10px}.toc a{display:block;text-decoration:none;font-size:14px;color:#5d6b70;padding:5px 0;border-bottom:1px dashed transparent}.toc a:hover{color:var(--red);border-color:var(--line)}main{min-width:0}.section{margin-bottom:64px;scroll-margin-top:20px}.section-head{border-bottom:2px solid var(--ink);padding-bottom:12px;margin-bottom:22px}.section-head .num{font-size:13px;color:var(--red);letter-spacing:.18em}.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px;box-shadow:var(--shadow);margin:16px 0}.grid{display:grid;gap:16px}.grid.two{grid-template-columns:repeat(2,minmax(0,1fr))}.grid.three{grid-template-columns:repeat(3,minmax(0,1fr))}.grid.four{grid-template-columns:repeat(4,minmax(0,1fr))}.metric{padding:18px;background:rgba(255,253,248,.8);border:1px solid var(--line);border-radius:14px}.metric .k{font-size:13px;color:var(--muted)}.metric .v{font-size:30px;font-weight:700;line-height:1.3}.metric .s{font-size:13px;color:var(--muted)}.good{color:var(--green)}.bad{color:var(--red)}.gold{color:var(--gold)}.note{border-left:4px solid var(--gold);padding:12px 18px;background:#f3ead7;border-radius:0 10px 10px 0}.lesson{border-left:4px solid var(--red);padding:16px 20px;background:#f6e9e3;border-radius:0 12px 12px 0;font-size:18px}.quote{font-size:20px;color:#314d52;padding:20px 26px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);text-align:center}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:12px;background:var(--card)}table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.55}th,td{padding:10px 12px;border-bottom:1px solid #e8e1d6;text-align:right;white-space:nowrap}th{background:#e9e3d8;color:#39494e;position:sticky;top:0;z-index:1}td:first-child,th:first-child,td:nth-child(2),th:nth-child(2){text-align:left}tr:hover td{background:#faf5eb}.chart{width:100%;min-height:280px}.chart svg{display:block;width:100%;height:auto}.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:var(--muted);margin:8px 0}.legend i{display:inline-block;width:18px;height:3px;margin-right:6px;vertical-align:middle}.game{border:1px solid var(--line);border-radius:20px;background:var(--card);box-shadow:var(--shadow);margin:34px 0;overflow:hidden;scroll-margin-top:20px}.game-head{padding:26px 28px;background:linear-gradient(120deg,#233c44,#365c5d);color:#f7f1e5}.game-head h3{font-size:28px;margin-bottom:8px}.game-head .q{color:#d9e2de;font-size:16px}.game-body{padding:24px 28px}.game-metrics{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;margin:18px 0}.game-metrics .metric{padding:12px}.game-metrics .v{font-size:22px}.signals{counter-reset:sig;list-style:none;padding:0}.signals li{position:relative;padding:12px 12px 12px 52px;border-bottom:1px dashed var(--line)}.signals li:before{counter-increment:sig;content:counter(sig);position:absolute;left:8px;top:14px;width:26px;height:26px;border-radius:50%;background:#e7ddca;color:#6b5738;display:grid;place-items:center;font-weight:700}.signal-title{font-weight:700}.signal-source{font-size:12px;color:var(--muted)}.timeline{position:relative;margin-left:12px;padding-left:28px;border-left:2px solid #c6b28e}.timeline-item{position:relative;margin:0 0 24px}.timeline-item:before{content:"";position:absolute;left:-36px;top:7px;width:13px;height:13px;border-radius:50%;background:var(--red);border:3px solid var(--paper)}.timeline-item h4{margin-bottom:4px}.flow{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.flow-step{position:relative;padding:16px;background:#eef1ec;border:1px solid #d2ddd5;border-radius:12px;font-size:14px}.flow-step b{display:block;color:var(--teal);margin-bottom:5px}.small{font-size:13px;color:var(--muted)}.formula{font-size:24px;text-align:center;padding:18px;background:#edf3f1;border-radius:12px;color:#244d4a}.controls{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}.controls select,.controls input,.controls button{font:inherit;font-size:14px;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:#fffdf8;color:var(--ink)}.controls button{cursor:pointer}.controls button:hover{background:#e9e1d2}.log-table{font-size:12px}.log-table td{padding:7px 8px}.log-reason{white-space:normal;min-width:220px}.pager{display:flex;align-items:center;gap:12px;margin:12px 0}.footer{background:var(--navy);color:#d9e1dd;padding:32px max(5vw,24px);font-size:14px}.footer b{color:#f4e8cd}.hide{display:none!important}.tag{font-size:12px;padding:2px 8px;border-radius:5px;background:#e8e1d4;color:#566269}.tag.auto{background:#e4eee9;color:#2f6652}.tag.manual{background:#eee5d4;color:#856735}.round-review{border:1px solid #cfc5b4;border-radius:14px;background:#fbf8f0;margin:18px 0;overflow:hidden}.round-head{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:14px 18px;background:#e7ece8;border-bottom:1px solid #d6dfd9}.round-head b{font-size:17px}.round-head span{font-size:13px;color:var(--muted)}.round-body{padding:14px 18px}.round-kpis{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin:10px 0 14px}.round-kpis div{background:#f2ede3;border-radius:8px;padding:8px 10px;font-size:12px;color:var(--muted)}.round-kpis strong{display:block;font-size:18px;color:var(--ink)}.round-note{font-size:14px;background:#f5ecd9;border-left:3px solid var(--gold);padding:9px 12px;border-radius:0 8px 8px 0;margin:8px 0 12px}.round-trade-table{font-size:12px;table-layout:fixed}.round-trade-table td{padding:6px 7px}.round-trade-table .detail,.round-trade-table .reason{white-space:normal;min-width:0;text-align:left}.round-trade-table .counter{white-space:normal;text-align:left;font-size:11px;line-height:1.5}.round-trade-table .action{white-space:normal;text-align:left;font-weight:700;color:#315b58}.round-trade-table th:nth-child(1){width:3%}.round-trade-table th:nth-child(2){width:9%}.round-trade-table th:nth-child(3){width:5%}.round-trade-table th:nth-child(4){width:11%}.round-trade-table th:nth-child(5){width:9%}.round-trade-table th:nth-child(6){width:8%}.round-trade-table th:nth-child(7){width:15%}.round-trade-table th:nth-child(8){width:8%}.round-trade-table th:nth-child(9){width:32%}.cp-name{display:block;font-weight:700;color:#3f5054;margin-bottom:2px}.matchline{display:block;color:#7b6d55;font-size:10.5px;line-height:1.55;margin-top:3px;white-space:normal}.round-empty{padding:14px;background:#eeeae1;border-radius:8px;color:#5d6b70;font-size:14px}.round-flow{font-size:13px;color:#44575d;margin:8px 0}.round-flow b{color:var(--red)}.round-market{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0 6px}.market-box{background:#edf1ec;border:1px solid #d3ddd7;border-radius:9px;padding:9px 11px;font-size:12px;line-height:1.65}.market-box b{display:block;color:#315b58;font-size:12px;margin-bottom:3px}.market-box .num{font-size:14px;font-weight:700}.quote-line{color:#44575d}.quote-buy{color:#2f6652;font-weight:700}.quote-sell{color:#a34e3c;font-weight:700}.zero-why{margin:8px 0 10px;padding:10px 12px;background:#f6e9e3;border-left:3px solid var(--red);border-radius:0 8px 8px 0;font-size:13px}.round-band{margin:4px 0 12px}.round-band .chart{min-height:120px}
@media(max-width:1100px){.layout{grid-template-columns:1fr}.toc{position:relative;top:0;max-height:none}.game-metrics{grid-template-columns:repeat(3,1fr)}.grid.four{grid-template-columns:repeat(2,1fr)}.flow{grid-template-columns:repeat(2,1fr)}.round-kpis{grid-template-columns:repeat(3,1fr)}}
@media(max-width:680px){body{font-size:16px}.layout{padding:20px 14px 60px}.grid.two,.grid.three,.grid.four{grid-template-columns:1fr}.game-metrics{grid-template-columns:repeat(2,1fr)}.game-body,.game-head{padding:20px 16px}.hero{padding:48px 20px}.flow{grid-template-columns:1fr}h2{font-size:27px}.round-kpis{grid-template-columns:repeat(2,1fr)}.round-market{grid-template-columns:1fr}}
@media print{body{background:#fff;font-size:11pt}.toc,.controls,.pager{display:none}.layout{display:block;padding:0}.hero{padding:32px;background:#233c44!important;-webkit-print-color-adjust:exact}.card,.game{box-shadow:none;break-inside:avoid}.game{break-before:page}.section{break-inside:auto}.footer{background:#fff;color:#333}#appendix-log,#appendix-trades{display:none}}
'''

JS = r'''
const GAMES = __DATA__;
const fmt=(x,d=2)=>x==null?'—':Number(x).toLocaleString('zh-CN',{minimumFractionDigits:0,maximumFractionDigits:d});
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pnlClass=x=>x>0?'good':x<0?'bad':'';
const gameName=g=>`${g.practice?'测试局':'正式第'+g.formal+'题'} · ${g.title}`;
function svgEl(tag,attrs={},text=''){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));if(text!=='')e.textContent=text;return e}
function lineChart(el,series,opts={}){
 const W=860,H=opts.height||300,P={l:65,r:25,t:25,b:45};el.innerHTML='';const svg=svgEl('svg',{viewBox:`0 0 ${W} ${H}`,role:'img'});
 let vals=series.flatMap(s=>s.data.map(p=>p.y)).filter(v=>v!=null&&isFinite(v));if(!vals.length)return;
 let min=opts.min??Math.min(...vals),max=opts.max??Math.max(...vals);if(min===max){min-=1;max+=1}const pad=(max-min)*.08;min=opts.min??min-pad;max=opts.max??max+pad;
 const x=i=>P.l+(series[0].data.length===1?(W-P.l-P.r)/2:i*(W-P.l-P.r)/(series[0].data.length-1));const y=v=>P.t+(max-v)*(H-P.t-P.b)/(max-min);
 for(let i=0;i<=4;i++){let yy=P.t+i*(H-P.t-P.b)/4,v=max-i*(max-min)/4;svg.append(svgEl('line',{x1:P.l,y1:yy,x2:W-P.r,y2:yy,stroke:'#ded6c8','stroke-width':1}));svg.append(svgEl('text',{x:P.l-9,y:yy+4,'text-anchor':'end','font-size':12,fill:'#68767a'},fmt(v,opts.decimals??1)))}
 series.forEach(s=>{
  const pts=s.data.map((p,i)=>({...p,px:x(i),py:y(p.y),value:p.y}));
  if(s.type==='bar'){
   const bw=Math.min(34,(W-P.l-P.r)/pts.length*.55),base=y(Math.max(min,Math.min(0,max)));
   pts.forEach(p=>{
    const hh=Math.abs(y(p.value)-base);
    svg.append(svgEl('rect',{x:p.px-bw/2,y:p.value>=0?y(p.value):base,width:bw,height:hh,rx:3,fill:s.color,opacity:.85}));
    svg.append(svgEl('text',{x:p.px,y:p.value>=0?y(p.value)-6:base+16,'text-anchor':'middle','font-size':12,fill:s.color},fmt(p.raw??p.value,0)));
   });
  }else{
   svg.append(svgEl('path',{d:pts.map((p,i)=>(i?'L':'M')+p.px+','+p.py).join(' '),fill:'none',stroke:s.color,'stroke-width':s.width||3,'stroke-dasharray':s.dash||''}));
   pts.forEach(p=>{
    svg.append(svgEl('circle',{cx:p.px,cy:p.py,r:4,fill:s.color}));
    if(s.labels)svg.append(svgEl('text',{x:p.px,y:p.py-10,'text-anchor':'middle','font-size':12,fill:s.color},fmt(p.raw??p.value,0)));
   });
  }
 });
 series[0].data.forEach((p,i)=>svg.append(svgEl('text',{x:x(i),y:H-14,'text-anchor':'middle','font-size':12,fill:'#68767a'},p.xLabel??p.x)));
 el.append(svg);
}
function roundChart(g,el){
 const data=[{x:'开盘',y:g.opening,xLabel:'开盘'},...g.history.filter(h=>h.price!=null).map(h=>({x:'R'+h.round,y:h.price,xLabel:'R'+h.round})),{x:'真值',y:g.truth,xLabel:'真值'}];
 lineChart(el,[{data,color:'#356d6a',labels:true}],{height:260,decimals:g.truth<20?2:0});
}
function positionChart(g,el){lineChart(el,[{data:g.positionSeries,color:'#a34e3c'}],{height:250,decimals:0})}
function counterpartyRows(){
 const m=new Map();
 GAMES.forEach(g=>g.trades.forEach(t=>{
  const k=t.counterparty;const o=m.get(k)||{name:k,type:t.counterpartyType,count:0,qty:0,games:new Set()};
  o.count++;o.qty+=t.qty;o.games.add(g.practice?'测试':String(g.formal));m.set(k,o);
 }));
 return [...m.values()].sort((a,b)=>b.qty-a.qty||b.count-a.count).map(o=>`<tr><td>${esc(o.name)}</td><td><span class="tag ${o.type==='脚本'?'auto':'manual'}">${o.type}</span></td><td>${o.count}</td><td>${o.qty}</td><td>${o.games.size} 场</td></tr>`).join('');
}
function executionOverview(){
 lineChart(document.getElementById('tradeChart'),[{data:GAMES.map(g=>({x:g.practice?'测试':'第'+g.formal+'题',y:g.tradeCount})),color:'#356d6a',type:'bar'}],{height:300,decimals:0,min:0});
 lineChart(document.getElementById('programChart'),[{data:GAMES.map(g=>({x:g.practice?'测试':'第'+g.formal+'题',y:g.programShare??0})),color:'#b08a4b',type:'bar'}],{height:300,decimals:0,min:0,max:100});
 document.getElementById('executionBody').innerHTML=GAMES.map(g=>`<tr><td>${g.practice?'测试':'第'+g.formal+'题'}</td><td>${g.title}</td><td>${g.tradeCount}</td><td>${g.actualBuyQty}</td><td>${g.actualSellQty}</td><td>${g.actualVolume}</td><td>${fmt(g.buyVWAP)}</td><td>${fmt(g.sellVWAP)}</td><td>${g.programShare==null?'—':fmt(g.programShare,1)+'%'}</td><td>${g.position}</td><td class="${pnlClass(g.pnl)}">${fmt(g.pnl)}</td></tr>`).join('');
 document.getElementById('counterpartyBody').innerHTML=counterpartyRows();
}
function executionRows(g){
 const rounds=[...new Set([...g.history.map(h=>h.round),...g.roundStats.map(s=>s.round)])].sort((a,b)=>a-b);
 let carry=0;
 return rounds.map(r=>{
  const s=g.roundStats.find(x=>x.round===r);
  const end=s?s.endPosition:carry;carry=end;
  return `<tr><td>第${r}轮</td><td>${s?s.tradeCount:0}</td><td>${s?s.buyQty:0}</td><td>${s?s.sellQty:0}</td><td>${end>=0?'+':''}${end}</td><td class="${pnlClass(s?s.realized:0)}">${fmt(s?s.realized:0)}</td></tr>`;
 }).join('');
}
function overview(){
 const formal=GAMES.filter(g=>!g.practice);let sum=0;const cum=formal.map(g=>{sum+=g.points;return{x:'第'+g.formal+'题',y:sum}});
 lineChart(document.getElementById('cumChart'),[{data:cum,color:'#a34e3c',labels:true}],{height:320,decimals:0,min:0});
 lineChart(document.getElementById('pointsChart'),[{data:formal.map(g=>({x:'第'+g.formal+'题',y:g.points})),color:'#356d6a',type:'bar'}],{height:320,decimals:0,min:0,max:16});
 lineChart(document.getElementById('rankChart'),[{data:formal.map(g=>({x:'第'+g.formal+'题',y:g.rank})),color:'#b08a4b',labels:true}],{height:320,decimals:0,min:16,max:0});
 const maxAbs=Math.max(...GAMES.map(g=>Math.abs(g.pnl)));const trans=v=>Math.sign(v)*Math.log1p(Math.abs(v))/Math.log1p(maxAbs)*100;
 lineChart(document.getElementById('pnlChart'),[{data:GAMES.map(g=>({x:g.practice?'测试':'第'+g.formal+'题',y:trans(g.pnl),raw:g.pnl})),color:'#a34e3c',type:'bar'}],{height:320,decimals:0});
 lineChart(document.getElementById('actionChart'),[{data:GAMES.map(g=>({x:g.practice?'测试':'第'+g.formal+'题',y:g.actionCount})),color:'#68767a',type:'bar'}],{height:300,decimals:0,min:0});
 document.getElementById('pnlExact').innerHTML=GAMES.map(g=>`<span class="pill">${g.practice?'测试':'第'+g.formal+'题'} <b class="${pnlClass(g.pnl)}">${fmt(g.pnl)}</b></span>`).join(' ');
}
const signedQty=t=>t.side==='buy'?t.qty:-t.qty;
function tradeActionLabel(before,after,side){
 if(before===0)return side==='buy'?'建立多头':'建立空头';
 if(before>0){
  if(after>before)return '加多';
  if(after===0)return '卖出平多';
  if(after>0)return '卖出减多';
  return '反手做空';
 }
 if(after<before)return '加空';
 if(after===0)return '买入平空';
 if(after<0)return '买入减空';
 return '反手做多';
}
function tradeMatchLine(t,meta){
 const ref=t.side==='buy'?meta.buyVWAP:meta.sellVWAP;
 const rel=ref?Math.abs(t.price/ref-1)*100:null;
 const favorable=ref?(t.side==='buy'?t.price<=ref:t.price>=ref):null;
 const match=t.execMatched?`邻近委托${t.execOrderId?' #'+t.execOrderId:''} · 限价 ${fmt(t.execLimit)} · 时间距 ${fmt(t.execGap,2)}s`:'未匹配到同向可成交委托';
 const priceText=rel==null?'':`成交价${favorable?'优于':'略差于'}同向VWAP ${fmt(rel,2)}%`;
 return `<span class="matchline">${match}${priceText?' · '+priceText:''}</span>`;
}
function quoteRange(lo,hi,label){
 if(lo==null&&hi==null)return `${label} 未挂`;
 if(lo!=null&&hi!=null&&Math.abs(lo-hi)>1e-9)return `${label} ${fmt(lo)}–${fmt(hi)}`;
 return `${label} ${fmt(lo??hi)}`;
}
function roundMarketHTML(g,r,trades){
 const m=g.marketByRound?.[String(r)];
 if(!m)return '';
 const buy=quoteRange(m.buyLo,m.buyHi,'买');
 const sell=quoteRange(m.sellLo,m.sellHi,'卖');
 const ownVol=trades.reduce((s,t)=>s+t.qty,0);
 return `<div class="round-market"><div class="market-box"><b>全市场成交回报</b><span class="num">开 ${fmt(m.open)} · 高 ${fmt(m.high)} · 低 ${fmt(m.low)} · 收 ${fmt(m.close)}</span><br>${m.volume} 手 / ${m.prints} 笔 · VWAP ${fmt(m.vwap)}</div><div class="market-box"><b>本方委托位置</b><span class="quote-line"><span class="quote-buy">${buy}</span> · <span class="quote-sell">${sell}</span></span><br>${m.orderCount} 条委托 · ${m.cancelCount} 次全撤 · 本方 ${trades.length?`成交 ${trades.length} 笔 / ${ownVol} 手`:'零成交'}</div></div>${trades.length?'':`<div class="zero-why"><b>为什么没成交：</b>${esc(m.noFillReason||'本轮无本方成交。')}</div>`}<div class="round-band"><div class="chart" id="band-${g.number}-${r}"></div></div>`;
}
function roundBand(g,r,el){
 if(!el)return;
 const m=g.marketByRound?.[String(r)];if(!m)return;
 const vals=[m.low,m.high,m.buyLo,m.buyHi,m.sellLo,m.sellHi].filter(v=>v!=null&&isFinite(v));
 if(!vals.length)return;
 let min=Math.min(...vals),max=Math.max(...vals);if(min===max){min-=1;max+=1}const pad=(max-min)*.08;min-=pad;max+=pad;
 const W=820,H=112,P={l:42,r:42,t:24,b:28};
 const x=p=>P.l+(p-min)/(max-min)*(W-P.l-P.r);
 const y=52;
 el.innerHTML='';const svg=svgEl('svg',{viewBox:`0 0 ${W} ${H}`,role:'img'});
 const title=`第${r}轮：全市场成交 ${fmt(m.low)}–${fmt(m.high)}；本方${quoteRange(m.buyLo,m.buyHi,'买')}、${quoteRange(m.sellLo,m.sellHi,'卖')}`;
 svg.append(svgEl('title',{},title));
 svg.append(svgEl('line',{x1:P.l,y1:y,x2:W-P.r,y2:y,stroke:'#d8d0c2','stroke-width':1}));
 // 市场成交区间
 svg.append(svgEl('rect',{x:x(m.low),y:y-9,width:Math.max(2,x(m.high)-x(m.low)),height:18,rx:4,fill:'#dfe7e1',stroke:'#356d6a','stroke-width':1.5}));
 // 开收盘刻度
 [['开',m.open,'#b08a4b'],['收',m.close,'#356d6a']].forEach(([lab,v,color])=>{if(v==null)return;svg.append(svgEl('line',{x1:x(v),y1:y-14,x2:x(v),y2:y+14,stroke:color,'stroke-width':2}));svg.append(svgEl('text',{x:x(v),y:y-18,'text-anchor':'middle','font-size':11,fill:color},lab));});
 // 本方买卖报价：买在下方，卖在上方
 if(m.buyLo!=null){svg.append(svgEl('polygon',{points:`${x(m.buyLo)},${y+18} ${x(m.buyLo)-7},${y+30} ${x(m.buyLo)+7},${y+30}`,fill:'#2f6652'}));svg.append(svgEl('text',{x:x(m.buyLo),y:y+42,'text-anchor':'middle','font-size':11,fill:'#2f6652'},'买 '+fmt(m.buyLo)));}
 if(m.buyHi!=null&&m.buyHi!==m.buyLo){svg.append(svgEl('polygon',{points:`${x(m.buyHi)},${y+18} ${x(m.buyHi)-7},${y+30} ${x(m.buyHi)+7},${y+30}`,fill:'#2f6652'}));svg.append(svgEl('text',{x:x(m.buyHi),y:y+42,'text-anchor':'middle','font-size':11,fill:'#2f6652'},'买 '+fmt(m.buyHi)));}
 if(m.sellLo!=null){svg.append(svgEl('polygon',{points:`${x(m.sellLo)},${y-18} ${x(m.sellLo)-7},${y-30} ${x(m.sellLo)+7},${y-30}`,fill:'#a34e3c'}));svg.append(svgEl('text',{x:x(m.sellLo),y:y-36,'text-anchor':'middle','font-size':11,fill:'#a34e3c'},'卖 '+fmt(m.sellLo)));}
 if(m.sellHi!=null&&m.sellHi!==m.sellLo){svg.append(svgEl('polygon',{points:`${x(m.sellHi)},${y-18} ${x(m.sellHi)-7},${y-30} ${x(m.sellHi)+7},${y-30}`,fill:'#a34e3c'}));svg.append(svgEl('text',{x:x(m.sellHi),y:y-36,'text-anchor':'middle','font-size':11,fill:'#a34e3c'},'卖 '+fmt(m.sellHi)));}
 el.append(svg);
}
function roundReviewHTML(g){
 const rounds=[...new Set([...g.history.map(h=>h.round),...g.trades.map(t=>t.round)])].sort((a,b)=>a-b);
 let carry=0;
 return rounds.map(r=>{
  const closeRow=g.history.find(h=>h.round===r);
  const trades=g.trades.filter(t=>t.round===r).sort((a,b)=>a.at-b.at||a.id-b.id);
  const start=carry;const end=trades.length?trades[trades.length-1].positionAfter:start;carry=end;
  const bq=trades.filter(t=>t.side==='buy').reduce((s,t)=>s+t.qty,0);
  const sq=trades.filter(t=>t.side==='sell').reduce((s,t)=>s+t.qty,0);
  const buyVWAP=bq?trades.filter(t=>t.side==='buy').reduce((s,t)=>s+t.price*t.qty,0)/bq:null;
  const sellVWAP=sq?trades.filter(t=>t.side==='sell').reduce((s,t)=>s+t.price*t.qty,0)/sq:null;
  const realized=trades.reduce((s,t)=>s+t.realizedPnl,0);
  const positions=[start,...trades.map(t=>t.positionAfter)];
  const hi=Math.max(...positions),lo=Math.min(...positions);
  const close=closeRow&&closeRow.price!=null?`轮末收盘 ${fmt(closeRow.price)}`:'本轮无收盘价';
  const signal=g.signals.find(s=>s.round===r);
  const signalText=signal?`公开线索：「${esc(signal.title)}」`:'本轮无新增公开线索';
  const flow=trades.length?`本轮${trades.length}笔：买入${bq}手、卖出${sq}手；持仓由${start>=0?'+':''}${start}变为${end>=0?'+':''}${end}，盘中极值${lo}～${hi}；买VWAP ${fmt(buyVWAP)}、卖VWAP ${fmt(sellVWAP)}；本轮已实现 <b class="${pnlClass(realized)}">${fmt(realized)}</b>。`:`本轮零成交，持仓保持${start>=0?'+':''}${start}；没有把不可成交的价格或弱线索强行变成交易。`;
  const rows=trades.map((t,i)=>{
   const before=t.positionAfter-signedQty(t),after=t.positionAfter;
   const time=new Date(t.at*1000).toLocaleTimeString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false});
   return `<tr><td>${i+1}</td><td>${time}</td><td>${t.side==='buy'?'买入':'卖出'}</td><td>${fmt(t.price)} × ${t.qty}</td><td>${before>=0?'+':''}${before}→${after>=0?'+':''}${after}</td><td class="${pnlClass(t.realizedPnl)}">${fmt(t.realizedPnl)}</td><td class="counter"><span class="cp-name">${esc(t.counterparty)}</span><span class="tag ${t.counterpartyType==='脚本'?'auto':'manual'}">${t.counterpartyType}</span></td><td class="action">${tradeActionLabel(before,after,t.side)}</td><td class="reason">${esc(t.execReason)}${tradeMatchLine(t,{buyVWAP,sellVWAP})}</td></tr>`;
  }).join('');
  const note=g.roundNotes?.[r]?`<div class="round-note"><b>本轮判断：</b>${esc(g.roundNotes[r])}</div>`:'';
  return `<div class="round-review" id="game-${g.number}-round-${r}"><div class="round-head"><b>第 ${r} 轮 · ${trades.length} 笔真实成交</b><span>${signalText}　${close}</span></div><div class="round-body"><div class="round-kpis"><div>轮初持仓<strong>${start>=0?'+':''}${start}</strong></div><div>轮末持仓<strong>${end>=0?'+':''}${end}</strong></div><div>持仓极值<strong>${lo}～${hi}</strong></div><div>本轮已实现<strong class="${pnlClass(realized)}">${fmt(realized)}</strong></div><div>成交笔数<strong>${trades.length}</strong></div></div>${roundMarketHTML(g,r,trades)}<p class="round-flow">${flow}</p>${note}${trades.length?`<div class="table-wrap"><table class="round-trade-table"><thead><tr><th>#</th><th>时间</th><th>方向</th><th>价格 × 手数</th><th>持仓</th><th>已实现</th><th>对手方</th><th>动作</th><th>执行理由 / 委托匹配</th></tr></thead><tbody>${rows}</tbody></table></div>`:'<div class="round-empty">本轮没有真实成交。持仓、价格变化与线索仍保留在本轮摘要中，避免把零成交误写成没有决策。</div>'}</div></div>`;
 }).join('');
}
function gameCard(g){
 const n=g.narrative;const signals=g.signals.map(s=>`<li><div class="signal-title">第${s.round}轮 · ${esc(s.title)}</div><div>${esc(s.text)}</div><div class="signal-source">来源：${esc(s.sourceName)}</div></li>`).join('');
 const hist=g.history.map(h=>`<tr><td>第${h.round}轮</td><td>${fmt(h.price)}</td><td>${h.volume}</td><td>${h.orders}</td><td>${h.tradeCount}</td></tr>`).join('');
 return `<article class="game" id="game-${g.number}"><div class="game-head"><div class="eyebrow">${g.practice?'PRACTICE':'FORMAL '+String(g.formal).padStart(2,'0')}</div><h3>${gameName(g)}</h3><div class="q">${esc(g.question)}　单位：${esc(g.unit)}</div><div class="hero-meta"><span class="pill">名次 ${g.rank}</span><span class="pill">积分 ${g.points}</span><span class="pill">盈亏 ${fmt(g.pnl)}</span><span class="pill">最终持仓 ${g.position}</span></div></div><div class="game-body">
 <div class="game-metrics"><div class="metric"><div class="k">独立估价</div><div class="v">${fmt(g.estimate)}</div></div><div class="metric"><div class="k">开盘共识</div><div class="v">${fmt(g.opening)}</div></div><div class="metric"><div class="k">公开真值</div><div class="v gold">${fmt(g.truth)}</div></div><div class="metric"><div class="k">结算盈亏</div><div class="v ${pnlClass(g.pnl)}">${fmt(g.pnl)}</div></div><div class="metric"><div class="k">已实现</div><div class="v">${fmt(g.realized)}</div></div><div class="metric"><div class="k">累计积分</div><div class="v">${g.totalPoints??'—'}</div></div></div>
 <h4>题目与全部公开线索</h4><ol class="signals">${signals}</ol>
 <div class="grid two"><div><h4>估值与决策重建</h4>${n.decision.map(p=>`<p>${p}</p>`).join('')}</div><div><h4>逐轮价格路径</h4><div class="chart" id="round-chart-${g.number}"></div><div class="legend"><span><i style="background:#356d6a"></i>开盘 → 各轮收盘 → 真值</span></div></div></div>
 <div class="note"><b>交易流程：</b>${n.flow}</div><p class="small">委托口径：本局动作 ${g.actionCount} 次，其中委托 ${g.orderCount} 次、全撤 ${g.cancelCount} 次；买入委托 ${g.buyQty} 手、卖出委托 ${g.sellQty} 手。<br><b>真实成交口径：${g.tradeCount} 笔、${g.actualVolume} 手</b>，实际买入 ${g.actualBuyQty} 手、卖出 ${g.actualSellQty} 手；买入 VWAP ${fmt(g.buyVWAP)}、卖出 VWAP ${fmt(g.sellVWAP)}；脚本对手成交占比 ${g.programShare==null?'—':fmt(g.programShare,1)+'%'}。委托手数不等于成交手数。</p>
 <div class="grid two"><div><h4>逐轮本方真实执行</h4><div class="table-wrap"><table><thead><tr><th>轮次</th><th>成交笔数</th><th>买入手数</th><th>卖出手数</th><th>轮末持仓</th><th>轮内已实现</th></tr></thead><tbody>${executionRows(g)}</tbody></table></div></div><div><h4>本方持仓路径</h4><div class="chart" id="position-chart-${g.number}"></div><div class="legend"><span><i style="background:#a34e3c"></i>每笔成交后的净持仓；正值为多头，负值为空头</span></div></div></div>
 <h4>逐轮逐笔复盘</h4><p class="small">下面按轮展开全部真实成交。每笔都标出成交前后的持仓、本笔已实现、对手方显示名、成交动作和当时委托日志里的执行理由。动作名称由成交前后持仓严格推导；执行理由按“同场、同方向、5 秒内、限价相对成交价可成交、委托手数覆盖成交手数”匹配最近的委托，并标出邻近委托号与时间距。这是证据链上的近似关联，不声称服务器把成交与委托做了唯一主键绑定；若没有可匹配委托，会明确标注为按持仓与公允值反推。零成交轮也不会省略。</p>${roundReviewHTML(g)}
 <h4>全市场逐轮汇总</h4><div class="table-wrap"><table><thead><tr><th>轮次</th><th>收盘价</th><th>成交量</th><th>订单数</th><th>成交笔数</th></tr></thead><tbody>${hist}</tbody></table></div>
 <p><b>结算口径：</b>${esc(g.note)}</p><div class="lesson"><b>我意识到了什么：</b>${n.lesson}</div><p class="small">策略阶段：${n.stage}</p></div></article>`;
}
function renderGames(){document.getElementById('gameList').innerHTML=GAMES.map(gameCard).join('');GAMES.forEach(g=>{roundChart(g,document.getElementById('round-chart-'+g.number));positionChart(g,document.getElementById('position-chart-'+g.number));Object.keys(g.marketByRound||{}).forEach(r=>roundBand(g,+r,document.getElementById('band-'+g.number+'-'+r)))})}
function summaryRows(){return GAMES.map(g=>`<tr><td>${g.practice?'测试局':'正式第'+g.formal+'题'}</td><td>${g.title}</td><td>${fmt(g.estimate)}</td><td>${fmt(g.opening)}</td><td>${fmt(g.truth)}</td><td>${g.rank}</td><td>${g.points}</td><td class="${pnlClass(g.pnl)}">${fmt(g.pnl)}</td><td>${g.position}</td><td>${g.totalPoints??'—'}</td><td>${g.overallRank??'—'}</td></tr>`).join('')}
function valuationRows(){return GAMES.map(g=>{let pe=(g.opening-g.truth),ee=(g.estimate-g.truth);let pct=v=>g.truth===0?'—':fmt(v/g.truth*100,1)+'%';return`<tr><td>${g.practice?'测试':'第'+g.formal+'题'}</td><td>${g.title}</td><td>${fmt(g.estimate)}</td><td>${fmt(g.opening)}</td><td>${fmt(g.truth)}</td><td>${pct(ee)}</td><td>${pct(pe)}</td></tr>`}).join('')}
let logState={game:'all',side:'all',action:'all',q:'',page:1,pageSize:100};
function filteredLogs(){return GAMES.flatMap(g=>g.actions.map(a=>({...a,game:g.number,title:g.title}))).filter(a=>(logState.game==='all'||a.game===+logState.game)&&(logState.side==='all'||a.side===logState.side)&&(logState.action==='all'||a.action===logState.action)&&(!logState.q||String(a.reason).toLowerCase().includes(logState.q.toLowerCase())))}
function renderLogs(){const rows=filteredLogs(),pages=Math.max(1,Math.ceil(rows.length/logState.pageSize));logState.page=Math.min(logState.page,pages);const start=(logState.page-1)*logState.pageSize,page=rows.slice(start,start+logState.pageSize);document.getElementById('logBody').innerHTML=page.map((a,i)=>`<tr><td>${start+i+1}</td><td>${a.game===1?'测试':'第'+(a.game-1)+'题'}</td><td>${a.at?new Date(a.at*1000).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}):'手工补记'}</td><td>${a.action}</td><td>${a.side||'—'}</td><td>${fmt(a.price)}</td><td>${a.qty??'—'}</td><td>${a.orderId??a.response?.orderId??'—'}</td><td class="log-reason">${esc(a.reason)}</td><td><span class="tag ${a.source.includes('人工')?'manual':'auto'}">${a.source}</span></td></tr>`).join('');document.getElementById('logInfo').textContent=`共 ${rows.length} 条，第 ${logState.page}/${pages} 页；每页 ${logState.pageSize} 条`;document.getElementById('prevLog').disabled=logState.page<=1;document.getElementById('nextLog').disabled=logState.page>=pages}
function initLogs(){const sel=document.getElementById('logGame');sel.innerHTML='<option value="all">全部题目</option>'+GAMES.map(g=>`<option value="${g.number}">${gameName(g)}</option>`).join('');[['logGame','game'],['logSide','side'],['logAction','action']].forEach(([id,k])=>document.getElementById(id).addEventListener('change',e=>{logState[k]=e.target.value;logState.page=1;renderLogs()}));document.getElementById('logQ').addEventListener('input',e=>{logState.q=e.target.value;logState.page=1;renderLogs()});document.getElementById('prevLog').onclick=()=>{logState.page--;renderLogs()};document.getElementById('nextLog').onclick=()=>{logState.page++;renderLogs()};renderLogs()}
let tradeState={game:'all',side:'all',round:'all',counterparty:'all',page:1,pageSize:100};
function filteredTrades(){return GAMES.flatMap(g=>g.trades.map(t=>({...t,game:g.number}))).filter(t=>(tradeState.game==='all'||t.game===+tradeState.game)&&(tradeState.side==='all'||t.side===tradeState.side)&&(tradeState.round==='all'||t.round===+tradeState.round)&&(tradeState.counterparty==='all'||t.counterpartyType===tradeState.counterparty))}
function renderTrades(){const rows=filteredTrades(),pages=Math.max(1,Math.ceil(rows.length/tradeState.pageSize));tradeState.page=Math.min(tradeState.page,pages);const start=(tradeState.page-1)*tradeState.pageSize,page=rows.slice(start,start+tradeState.pageSize);document.getElementById('tradeBody').innerHTML=page.map((t,i)=>`<tr><td>${start+i+1}</td><td>${t.game===1?'测试':'第'+(t.game-1)+'题'}</td><td>${new Date(t.at*1000).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false})}</td><td>第${t.round}轮</td><td>${t.side==='buy'?'买入':'卖出'}</td><td>${fmt(t.price)}</td><td>${t.qty}</td><td>${t.positionAfter}</td><td class="${pnlClass(t.realizedPnl)}">${fmt(t.realizedPnl)}</td><td><span class="cp-name">${esc(t.counterparty)}</span><span class="tag ${t.counterpartyType==='脚本'?'auto':'manual'}">${t.counterpartyType}</span></td><td class="log-reason">${esc(t.execReason)}</td></tr>`).join('');document.getElementById('tradeInfo').textContent=`共 ${rows.length} 笔，第 ${tradeState.page}/${pages} 页；每页 ${tradeState.pageSize} 笔`;document.getElementById('prevTrade').disabled=tradeState.page<=1;document.getElementById('nextTrade').disabled=tradeState.page>=pages}
function initTrades(){const sel=document.getElementById('tradeGame');sel.innerHTML='<option value="all">全部题目</option>'+GAMES.map(g=>`<option value="${g.number}">${gameName(g)}</option>`).join('');[['tradeGame','game'],['tradeSide','side'],['tradeRound','round'],['tradeCounterparty','counterparty']].forEach(([id,k])=>document.getElementById(id).addEventListener('change',e=>{tradeState[k]=e.target.value;tradeState.page=1;renderTrades()}));document.getElementById('prevTrade').onclick=()=>{tradeState.page--;renderTrades()};document.getElementById('nextTrade').onclick=()=>{tradeState.page++;renderTrades()};renderTrades()}
document.getElementById('summaryBody').innerHTML=summaryRows();document.getElementById('valuationBody').innerHTML=valuationRows();overview();renderGames();executionOverview();initLogs();initTrades();
'''

intro = '''
<section class="section" id="reading"><div class="section-head"><div class="num">00 · 阅读说明</div><h2>这不是一张成绩单，而是一部策略演化史</h2></div>
<p>本报告覆盖 1 场测试局与 11 场正式局，按公开题面、全部线索、开盘与逐轮价格、动作日志、结算名次和当时记录的理由重建，并纳入赛后导出中的本方真实逐笔成交。报告中的“决策重建”是对估值依据、交易意图与事后认知的完整整理，不冒充逐字内部推理，也不补写日志中不存在的事实。</p><p>这一版进一步把 322 笔真实成交全部拆回所属轮次：每一轮都写明轮初与轮末持仓、买卖手数、同向 VWAP、持仓极值、本轮已实现，再逐笔列出成交时间、价格、方向、成交后持仓、对手方公开显示名、动作，以及当时委托日志中的执行理由。零成交轮也保留在正文里，测试局第二轮的“只有线索、没有成交”因此可以被单独阅读。</p>
<div class="grid four"><div class="metric"><div class="k">正式局总积分</div><div class="v">103</div><div class="s">11 局，满分口径 165</div></div><div class="metric"><div class="k">最终总榜</div><div class="v">第 7</div><div class="s">前四局曾累计 53 分、位居第 1</div></div><div class="metric"><div class="k">本方真实成交</div><div class="v">322 笔</div><div class="s">481 手；逐笔均可核验</div></div><div class="metric"><div class="k">最好单局</div><div class="v">3 × 第 2</div><div class="s">古巴面积、高铁里程、上海港</div></div></div>
<div class="quote">真正决定结果的，不只是“猜得准”，而是何时相信共识、何时相信线索，以及能否让仓位与证据强度保持一致。</div>
<div class="note"><b>数据边界：</b>价格字段已由“分”换算回游戏计价单位。赛后全量导出补齐了本方 322 笔真实成交；动作附录中的买卖手数仍是委托手数，不能与成交手数混用。报告提取本方逐笔，并保留交易对手的比赛公开显示名，但不复制对手内部 ID、私有持仓或思考。第 10、11 正式题停用了自动交易，第 11 题的人工未成交卖单已单独补记。</div></section>
'''

overview = '''
<section class="section" id="overview"><div class="section-head"><div class="num">01 · 全场总览</div><h2>从领先到回落：积分的四条曲线</h2></div>
<div class="grid two"><div class="card"><h3>累计积分</h3><div id="cumChart" class="chart"></div><p>前三局连续第 2，迅速建立领先；第四局后仍居榜首。第五、七、九正式题的低分，是累计曲线斜率下降的主要位置。</p></div><div class="card"><h3>单局积分</h3><div id="pointsChart" class="chart"></div><p>11 局积分依次为 14、14、14、11、5、12、4、8、5、6、10。高分集中在固定锚可靠或区间线索清晰的题目。</p></div><div class="card"><h3>单局名次（越靠上越好）</h3><div id="rankChart" class="chart"></div><p>平均名次约 6.64，中位数第 6；5 次进入前五，3 次进入前三。波动在后半段显著放大。</p></div><div class="card"><h3>结算盈亏（对数化展示）</h3><div id="pnlChart" class="chart"></div><div id="pnlExact" class="legend"></div><p class="small">为兼顾不同题目的量纲，柱高采用带符号对数变换，精确值标在上方；不同题目的盈亏不应直接相加比较。</p></div></div>
<div class="card"><h3>逐局总表</h3><div class="table-wrap"><table><thead><tr><th>场次</th><th>题目</th><th>初估</th><th>开盘</th><th>真值</th><th>名次</th><th>积分</th><th>盈亏</th><th>终仓</th><th>累计</th><th>总榜</th></tr></thead><tbody id="summaryBody"></tbody></table></div></div>
<div class="grid three"><div class="metric"><div class="k">前五次数</div><div class="v">5 / 11</div><div class="s">稳定性不足，但并非持续失效</div></div><div class="metric"><div class="k">正收益局</div><div class="v">6 / 11</div><div class="s">另有 2 局零持仓、3 局亏损</div></div><div class="metric"><div class="k">前四局 vs 后七局</div><div class="v">53 → 50</div><div class="s">平均每局 13.25 → 7.14 分</div></div></div></section>
'''

strategy = '''
<section class="section" id="evolution"><div class="section-head"><div class="num">02 · 策略演进</div><h2>五个阶段：每次改规则，都有代价与证据</h2></div>
<div class="timeline"><div class="timeline-item"><h4>阶段 I · 测试局：开盘加权 + 自动双边报价</h4><p>用 90% 开盘价和 10% 个人估价得到 700.04，事后几乎正中真值；但当时并不知道这一点。随后向开盘共识回归到 715.6，再被“麦当劳 600 家”弱线索与上涨动量推到 735。这里不能简单说“最初的估值更好”：700.04 的命中含运气，715.6 是对个人先验的合理修正，735 才是弱线索牵引。真正的失误是低置信度下空仓一度到 10 手，缺少独立风险刹车。</p></div>
<div class="timeline-item"><h4>阶段 II · 正式前四题：固定锚、强线索改锚、高置信度加仓</h4><p>古巴人口与海岸线属于强识别线索，敢于把开盘 11.32 改为 10.99；高铁与上海港则是个人估价和开盘完全一致，通过降低吃单阈值利用小幅偏离。前四局获得 53 分，是全场最稳定的阶段。</p></div>
<div class="timeline-item"><h4>阶段 III · 第五至九正式题：弱先验限仓，但强线索后仍然高频</h4><p>鸡蛋题后把未知阶段库存上限降到 2；步数题利用 84xx 区间获得成功。然而照片和屏幕使用题中，估值虽对，自动策略在快速回归时反复回补与反手，连续把方向优势变成执行亏损。</p></div>
<div class="timeline-item"><h4>阶段 IV · 第十至十一正式题：停用自动做市，人工低频</h4><p>弱线索不动，强线索只发一次方向委托。通讯录题在区间中部空仓，解锁题的高价卖单未成交后不追价。两局分别获得 6 分、10 分，避免了再次大幅亏损，也放弃了部分趋势利润。</p></div>
<div class="timeline-item"><h4>阶段 V · 赛后定型：证据驱动的分层执行</h4><p>最终形态不是“永远人工”或“永远自动”，而是按信息强度分层：弱线索只做极小库存或不动；明确区间只做区间外交易；直接答案线索允许一次性方向建仓；价格已回归则停止，不再追。</p></div></div>
<div class="flow"><div class="flow-step"><b>① 先定证据等级</b>背景资料、弱相关数据、可识别线索、可计算线索、直接答案，不能用同一仓位响应。</div><div class="flow-step"><b>② 再定公允分布</b>不是永远给单点。区间题保留上下界，口径不清时降低置信度。</div><div class="flow-step"><b>③ 最后选择执行</b>固定锚可收租，快速改锚应减少反手；委托价消失后不追。</div><div class="flow-step"><b>④ 用结算复盘</b>区分估值正确、执行正确和结果正确，三者并不总是同时发生。</div></div></section>
'''

valuation = '''
<section class="section" id="valuation"><div class="section-head"><div class="num">03 · 估值与信息</div><h2>个人先验、开盘共识与公开真值</h2></div>
<p>事实型公共题中，开盘共识往往非常可靠：高铁、上海港、机场的开盘价几乎就是结算值。私人情境题中，开盘主要反映脚本的先验，误差可能很大：微信未读开盘 36.63，真值却是 0；相册新增开盘 15，真值是 7。因而“尊重开盘”不是普适规则，必须先判断题目类型。</p>
<div class="table-wrap"><table><thead><tr><th>场次</th><th>题目</th><th>个人初估</th><th>开盘</th><th>真值</th><th>初估误差</th><th>开盘误差</th></tr></thead><tbody id="valuationBody"></tbody></table></div>
<div class="grid two"><div class="card"><h3>何时应相信开盘</h3><p>当题面是公开统计事实、个人估计与开盘接近、后续线索又不冲突时，开盘可以视为高置信度锚。高铁 4.8、上海港 5150.6、机场 263 都属于这一类。此时策略重点不是重新猜答案，而是利用短暂偏离。</p></div><div class="card"><h3>何时必须推翻开盘</h3><p>当线索直接改变支持域或答案本身时，开盘只是旧信息下的价格。古巴人口与海岸线、鸡蛋消耗、步数 84xx、照片个位质数、微信零未读、屏幕日均 3.5–4 小时，都要求重新定价。</p></div></div>
<div class="formula">证据强度 × 价格偏离 × 可成交赔率　优先于　“我已经猜过”或“价格正在上涨”</div></section>
'''

cases = '''
<section class="section" id="cases"><div class="section-head"><div class="num">05 · 典型案例深拆</div><h2>三次做对了什么，三次亏在哪里</h2></div>
<div class="grid two"><div class="card"><h3 class="good">成功 A · 古巴：强识别线索 + 双向执行</h3><p>人口 975 万和海岸线 5746 千米把国家锁定为古巴，面积可计算到 10.99。更重要的是，价格跌到 10.64 时没有因为此前做空而拒绝买入。最终净多 8 手、排名第 2。核心不是“猜中古巴”，而是估值改变后仓位也能改变。</p></div>
<div class="card"><h3 class="good">成功 B · 步数：区间中值 + 区间外交易</h3><p>84xx 不是精确答案，却足以构成支持域。8450 是中值，8599 已超出上界 8499，做空具备清晰赔率；早先低于区间的价格则适合买入。单局收益 911.22、排名第 4，是“模糊信息也可定价”的最佳案例。</p></div>
<div class="card"><h3 class="good">成功 C · 微信未读：直接线索 + 结算空仓</h3><p>“从不留未读”几乎等价于 0，不应继续尊重 36.63 的开盘。最终净空 8 手、盈利 252.54。不足在于后段才提高到 8 手，收益不及更早就满仓做空的对手，但它仍是证据与仓位一致的典型案例。</p></div>
<div class="card"><h3 class="bad">失败 A · 鸡蛋：末轮才知道消耗，前期却重仓</h3><p>两盒共 40 个只是购入量，不等于剩余量。末轮才给出五天每天 2 个，真值 30。前期空仓在信息不完整时过大，末轮正确改锚却需要高价回补，最终亏损 16.75。规则修正：私人情境题在关键变量未知时限仓 2。</p></div>
<div class="card"><h3 class="bad">失败 B · 照片：估值正确，执行反噬</h3><p>个位质数结合连拍，正确选择 7；价格从 14–15 跌向 7 时，自动策略不断回补和反手，最终亏损 7.63。问题不在概率判断，而在把方向交易与做市交易混在同一个执行器里。</p></div>
<div class="card"><h3 class="bad">失败 C · 屏幕时长：区间判断命中，反手仍亏</h3><p>日均 3.5–4 小时对应七天 24.5–28，结算 25.6，区间判断准确。可从多头快速翻空并继续围绕新锚交易，导致已实现亏损。它与照片题共同说明：强线索改锚后，应暂停旧有自动做市逻辑。</p></div></div></section>
'''

micro = '''
<section class="section" id="micro"><div class="section-head"><div class="num">06 · 交易流程与微观结构</div><h2>1,633 次动作，如何落成 322 笔真实成交</h2></div>
<div class="grid two"><div class="card"><h3>逐局动作强度</h3><div id="actionChart" class="chart"></div><p>前十个场次（含测试）由自动策略执行，后两场为人工低频。动作多并不等于成交多，也不天然等于错误；古巴局动作最多却排名第 2。真正危险的是公允值刚发生跳变时仍沿用高频双边逻辑。</p></div><div class="card"><h3>动作构成</h3><div class="grid two"><div class="metric"><div class="k">自动限价委托</div><div class="v">1,046</div><div class="s">另有 1 笔人工委托；含未成交与穿价委托</div></div><div class="metric"><div class="k">全撤指令</div><div class="v">587</div><div class="s">用于盘口或估值变化后重报</div></div></div><p>频繁撤单意味着报价有效期很短。其优点是减少陈旧报价，缺点是会在库存偏移和吃单阈值共同作用下形成无意识的反复交易。</p></div></div>
<div class="card"><h3>自动策略的标准循环</h3><div class="flow"><div class="flow-step"><b>读取 state</b>题面、线索、买卖五档、最新价、持仓、可买可卖、自己的挂单。</div><div class="flow-step"><b>确定公允值</b>优先手工覆盖；否则以开盘共识为锚，并按题目置信度调整。</div><div class="flow-step"><b>先吃明显偏离</b>卖一低于阈值则买，买一高于阈值则卖；再撤旧单、双边重报。</div><div class="flow-step"><b>库存偏移</b>多头越多，报价中心越低；空头越多，中心越高。极端时可能穿越公允值，造成过早减仓。</div></div></div>
<div class="note"><b>为什么不能用手数求和当作真实成交：</b>同一限价委托可能立即成交、部分成交或完全未成交；撤单也不会形成成交。因此 1,047 次委托（含 1 笔人工委托）与 322 笔成交不能直接相除解释为“委托成交率”，部分成交还会让一笔委托对应多笔逐笔。下一节单独用赛后导出呈现真实成交，不用委托日志反推。</div></section>
'''

execution = '''
<section class="section" id="execution"><div class="section-head"><div class="num">07 · 真实成交总览</div><h2>从委托到成交：481 手、35 个对手与每一次理由</h2></div>
<div class="grid four"><div class="metric"><div class="k">真实成交</div><div class="v">322 笔</div><div class="s">含测试局；正式后两局为 0</div></div><div class="metric"><div class="k">双边成交流量</div><div class="v">481 手</div><div class="s">买入 237，卖出 244</div></div><div class="metric"><div class="k">脚本对手</div><div class="v">365 手</div><div class="s">占本方成交流量 75.9%</div></div><div class="metric"><div class="k">模型对手</div><div class="v">116 手</div><div class="s">占本方成交流量 24.1%</div></div></div>
<div class="grid two"><div class="card"><h3>逐局真实成交笔数</h3><div id="tradeChart" class="chart"></div><p>古巴局 80 笔，占全部真实成交约 24.8%；屏幕使用 43 笔、照片 37 笔。后两局人工低频均为 0 笔，与结算零持仓和未成交委托相互印证。</p></div><div class="card"><h3>脚本对手成交手数占比</h3><div id="programChart" class="chart"></div><p>该比例按本方买入与卖出数量双边合计，衡量成交来自何种对手类型，不代表独立对手人数，也不代表全市场份额。</p></div></div>
<div class="card"><h3>逐局成交质量表</h3><div class="table-wrap"><table><thead><tr><th>场次</th><th>题目</th><th>成交笔数</th><th>买入手数</th><th>卖出手数</th><th>总手数</th><th>买入 VWAP</th><th>卖出 VWAP</th><th>脚本占比</th><th>终仓</th><th>结算盈亏</th></tr></thead><tbody id="executionBody"></tbody></table></div><p class="small">VWAP 为按本方真实成交数量加权的平均价格；无成交时显示“—”。终仓与盈亏采用服务器结算口径。</p></div>
<div class="card"><h3>对手方分布：35 个公开显示名</h3><p class="small">这里保留比赛房间公开展示的参赛名，便于核对每一笔流动性的来源；不写入对手内部 ID、私有持仓或思考。成交手数按本方买入与卖出双边合计，因此是“对手为我们提供了多少手流动性”，不是对手净仓。</p><div class="table-wrap"><table><thead><tr><th>对手方显示名</th><th>类型</th><th>成交笔数</th><th>成交手数</th><th>涉及场次</th></tr></thead><tbody id="counterpartyBody"></tbody></table></div></div>
<div class="grid two"><div class="card"><h3>频率不是质量：上海港与古巴</h3><p>古巴局 80 笔、110 手，是全场最密集的执行。它并非单纯“交易越多越好”，而是强识别线索不断确认后，先空后多的真实仓位变化支撑了第 2 名。上海港仅 19 笔、27 手，却实现 466.30 的结算收益，说明高置信度固定锚下，少量但位置正确的交易更有效。</p></div><div class="card"><h3>执行反噬有了直接证据</h3><p>照片局 37 笔、屏幕局 43 笔，真实成交后持仓曲线显示仓位在强线索后持续翻转。两局逐笔已实现累计分别为 −7.73 与 −13.67，与最终亏损方向一致。它们不是“猜错真值”，而是方向利润被反复回补、反手与再建仓消耗。</p></div></div>
<div class="note"><b>核验说明：</b>逐笔已实现盈亏按服务器“分”换算后汇总，个别场次与结算记录存在不超过 0.04 的尾差，因此总表、逐局头部和积分仍以结算返回为准；逐笔附录保留导出原值。不同题目的盈亏量纲不同，不做简单加总排名。</div></section>
'''

playbook = '''
<section class="section" id="playbook"><div class="section-head"><div class="num">08 · 赛后方法论</div><h2>下一版策略：让信息强度决定交易强度</h2></div>
<div class="table-wrap"><table><thead><tr><th>信息状态</th><th>估值方式</th><th>仓位与执行</th><th>典型场次</th><th>禁止事项</th></tr></thead><tbody>
<tr><td>无线索、弱先验</td><td>保留宽分布，参考开盘</td><td>0–2 手，最好不交易</td><td>鸡蛋前两轮、好友前两轮</td><td>因价格波动自行改锚</td></tr>
<tr><td>个人与开盘一致</td><td>高置信度固定锚</td><td>可收租，小幅偏离也可利用</td><td>高铁、上海港、机场</td><td>无新信息却频繁换方向</td></tr>
<tr><td>识别型强线索</td><td>允许推翻开盘</td><td>一次性调整目标仓位</td><td>古巴、微信未读</td><td>继续沿用旧锚报价</td></tr>
<tr><td>区间型强线索</td><td>保留上下界，以中值定价</td><td>优先在区间外交易</td><td>步数 84xx、屏幕日均</td><td>把区间中值当作绝对真值</td></tr>
<tr><td>价格已完成回归</td><td>不重新创造新信息</td><td>停止追单，保留现有收益</td><td>解锁 87 次</td><td>为成交而接受无赔率价格</td></tr></tbody></table></div>
<div class="grid two"><div class="card"><h3>开盘前</h3><p>记录独立估价和置信度，而不只是一个数字；判断题目属于公共事实还是私人情境；提前规定弱先验最大仓位。若个人估价与开盘差异很大，先问“谁更可能掌握信息”，而不是机械采用固定权重。</p></div><div class="card"><h3>每轮线索后</h3><p>先回答三个问题：它是否改变支持域？能否计算或唯一识别？当前价格是否已经在合理区间？只有前两项足够强、第三项仍有偏离时，才值得改变仓位。</p></div><div class="card"><h3>执行中</h3><p>固定锚与跳变锚应使用不同模块。固定锚可双边报价；跳变锚先撤掉旧单，再单次建仓，暂停自动反手。任何委托未成交都要重新计算赔率，不能直接追价。</p></div><div class="card"><h3>复盘时</h3><p>把结果拆成估值、执行、运气三部分。盈利局可能有错误推理，如机场题；亏损局可能有正确估值，如照片和屏幕题。只有拆开，才能避免被单局盈亏训练出错误规则。</p></div></div>
<div class="quote">最好的交易，不是每一秒都在场，而是在证据出现、价格尚未完成定价的那一刻，恰好持有与认知相匹配的仓位。</div></section>
'''

appendix = '''
<section class="section" id="appendix"><div class="section-head"><div class="num">09 · 完整动作附录</div><h2>可筛选、可检索的全部委托与撤单</h2></div>
<p>以下保留全部自动策略动作，并补记人工接口中的第 11 正式题卖单。可按题目、方向、动作类型和理由关键词筛选。时间显示为北京时间；手工补记不伪造精确时间。理由即当时随委托提交的决策说明。</p>
<div class="controls"><select id="logGame"></select><select id="logSide"><option value="all">买卖全部</option><option value="buy">买入</option><option value="sell">卖出</option><option value="">无方向/撤单</option></select><select id="logAction"><option value="all">全部动作</option><option value="order">限价委托</option><option value="cancelAll">全部撤单</option></select><input id="logQ" type="search" placeholder="搜索决策理由，如：公允值、收租"></div>
<div class="pager"><button id="prevLog">上一页</button><button id="nextLog">下一页</button><span id="logInfo" class="small"></span></div>
<div class="table-wrap"><table class="log-table"><thead><tr><th>#</th><th>题目</th><th>时间</th><th>动作</th><th>方向</th><th>价格</th><th>手数</th><th>订单号</th><th>当时理由</th><th>记录来源</th></tr></thead><tbody id="logBody"></tbody></table></div>
<div id="appendix-log" class="note"><b>审计说明：</b>本附录不包含 token、其他参赛者私有持仓或任何服务器源码。联网搜索答案全场未使用，因此没有搜索 query 需要披露。</div></section>
'''

trade_appendix = '''
<section class="section" id="trade-appendix"><div class="section-head"><div class="num">10 · 真实逐笔成交附录</div><h2>322 笔成交，一笔不漏</h2></div>
<p>以下全部来自用户提供的赛后主赛场导出，仅保留本方真实成交。可按题目、轮次、买卖方向和对手类型筛选；时间显示为北京时间。“成交后持仓”可直接重建每局的净多/净空路径，“本笔已实现”是服务器记录的该笔已实现盈亏，不是浮动盈亏；执行理由来自同场、同向、5 秒内且限价可成交的最近委托，并附上邻近委托号，便于回查原始动作日志。</p>
<div class="controls"><select id="tradeGame"></select><select id="tradeSide"><option value="all">买卖全部</option><option value="buy">买入</option><option value="sell">卖出</option></select><select id="tradeRound"><option value="all">全部轮次</option><option value="1">第 1 轮</option><option value="2">第 2 轮</option><option value="3">第 3 轮</option><option value="4">第 4 轮</option><option value="5">第 5 轮</option></select><select id="tradeCounterparty"><option value="all">全部对手类型</option><option value="脚本">脚本</option><option value="模型">模型</option></select></div>
<div class="pager"><button id="prevTrade">上一页</button><button id="nextTrade">下一页</button><span id="tradeInfo" class="small"></span></div>
<div class="table-wrap"><table class="log-table"><thead><tr><th>#</th><th>题目</th><th>成交时间</th><th>轮次</th><th>方向</th><th>成交价</th><th>手数</th><th>成交后持仓</th><th>本笔已实现</th><th>对手方</th><th>当时执行理由</th></tr></thead><tbody id="tradeBody"></tbody></table></div>
<div id="appendix-trades" class="note"><b>隐私与口径：</b>对手只保留比赛公开显示名，不写内部 ID、私有持仓或思考。成交与委托分属两套记录：执行理由是邻近匹配，不声称服务器主键绑定；真实成交与动作附录不相加、不混算。第 11 正式题人工未成交卖单只出现在动作附录。</div></section>
'''

HTML = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>临渊量化 · 全场详细复盘报告</title><style>''' + CSS + '''</style></head><body>
<header class="hero"><div class="eyebrow">LINYUAN QUANT · FULL MATCH REVIEW</div><h1>临渊有声，落子有痕</h1><div class="sub">多模型实时交易竞技 · 1 场测试 + 11 场正式局 · 全量决策、交易流程与图表复盘</div><div class="hero-meta"><span class="pill">103 分</span><span class="pill">最终总榜第 7</span><span class="pill">1,633 条自动动作</span><span class="pill">322 笔真实成交</span><span class="pill">35 个公开对手名</span><span class="pill">逐轮逐笔拆解</span><span class="pill">12 场逐局精读</span><span class="pill">原生 SVG 图表</span></div></header>
<div class="layout"><nav class="toc"><strong>报告目录</strong><a href="#reading">00 阅读说明</a><a href="#overview">01 全场总览</a><a href="#evolution">02 策略演进</a><a href="#valuation">03 估值与信息</a><a href="#games">04 逐局详细复盘</a><a href="#cases">05 典型案例深拆</a><a href="#micro">06 交易微观结构</a><a href="#execution">07 真实成交总览</a><a href="#playbook">08 赛后方法论</a><a href="#appendix">09 完整动作附录</a><a href="#trade-appendix">10 真实逐笔成交</a><hr><strong>逐局直达</strong>''' + ''.join(f'<a href="#game-{g["number"]}">{html.escape(gameName if False else short_titles[g["number"]])}</a>' for g in games) + '''</nav><main>''' + intro + overview + strategy + valuation + '''<section class="section" id="games"><div class="section-head"><div class="num">04 · 逐局详细复盘</div><h2>十二场交易，一场不漏</h2><p>每场依次呈现：题面与全部线索、初估与开盘、当时决策、价格路径、交易流程、结算结果和认知迭代；随后按轮展开、逐笔复盘本方全部真实成交，零成交轮同样保留。每个轮次另附“成交回报重建”的全市场开高低收与价格带，用来判断“没成交”是因为挂远了、没有报价，还是排队时点错过；它由全市场成交按 ID 去重恢复，不是原始 L2 挂单快照。</p></div><div id="gameList"></div></section>''' + cases + micro + execution + playbook + appendix + trade_appendix + '''</main></div><footer class="footer"><b>临渊量化 · 全场详细复盘</b><br>数据源：比赛 SSE 状态快照、结算记录、自动动作日志、人工接口复核、逐局复盘，以及赛后主赛场导出中的本方真实成交。图表均由原始数据在本地生成；无需联网即可阅读。</footer><script>''' + JS.replace('__DATA__', DATA) + '''</script></body></html>'''
OUT.write_text(HTML, encoding='utf-8')
print(json.dumps({'output':str(OUT),'games':len(games),'actions':sum(g['actionCount'] for g in games),'trades':sum(g['tradeCount'] for g in games),'volume':sum(g['actualVolume'] for g in games),'matchedExecReason':matched_exec,'bytes':OUT.stat().st_size},ensure_ascii=False))
