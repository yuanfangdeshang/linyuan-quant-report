# -*- coding: utf-8 -*-
"""从赛后数据（服务端全量导出 + 内存态快照）抽取复盘用数据集。"""
import json, statistics

ARCH = '/Users/yuanf/DoubaoWork/chats/2026-11-19/new-chat-1/赛后数据'
ME_ID = '63f1c2dc9a71f995'

main = json.load(open(f'{ARCH}/竞技场-258334-20261122-004051.json', encoding='utf-8'))
rooms = json.load(open(f'{ARCH}/rooms-原始快照-20261122-004051.json', encoding='utf-8'))
room = [r for r in rooms['rooms'] if r['code'] == '258334'][0]

byname = {}
for p in room['players']:
    byname[p['id']] = p['name']
for b in room['bots'].keys():
    byname[b] = '脚本·' + b.replace('bot:', '')

out = []
for g, rg in zip(main['games'], room['games']):
    number = g['number']
    me_rank = next((r for r in g['ranking'] if r['id'] == ME_ID), None)
    # 我的成交
    review = g.get('review', {}).get('players', [])
    my_tr = next((p['trades'] for p in review if p.get('id') == ME_ID), [])
    # 全市场成交（含时间戳、双方）
    trades = rg['trades']
    tick = rg['ticks']
    bots_est = {}
    for k, v in rg['states'].items():
        if isinstance(v, dict) and v.get('estimate'):
            bots_est[k] = v['estimate']
    my_flow = []
    pos = 0
    for t in my_tr:
        side = 'buy' if t.get('side') == 'buy' else 'sell'
        cp = t.get('counterparty', '')
        my_flow.append(dict(round=t['round'], at=t['at'], atRel=round((t['at'] - rg['openedAt'])/1000, 2),
                            side=side, price=t['price'], qty=t['qty'], cp=cp,
                            program=bool(t.get('program')), posAfter=t.get('positionAfter')))
    # 每轮收盘
    rounds = [dict(round=h['round'], price=h.get('closePrice'), endT=h.get('endT'), volume=h['volume'],
                   orders=h['orders'], trades=h.get('tradeCount')) for h in rg.get('rounds', [])]
    # 市场统计
    vol = sum(t['qty'] for t in trades)
    my_vol = sum(t['qty'] for t in my_flow)
    prog_vol = sum(t['qty'] for t in trades if str(t['buyerId']).startswith('bot:') or str(t['sellerId']).startswith('bot:'))
    model_vol = vol - prog_vol
    # 我的对手构成
    cp_prog = sum(t['qty'] for t in my_flow if t['program'])
    cp_model = my_vol - cp_prog
    out.append(dict(
        number=number, question=g['question'], unit=g['unit'], practice=g['practice'],
        scored=g['scoredNumber'], open=g['openingPrice'], settle=g['settlementPrice'],
        note=g['resolution'].get('note'), signals=g.get('signals', []),
        openedAt=rg.get('openedAt'),
        rounds=rounds,
        my_rank=me_rank['rank'] if me_rank else None,
        my_points=me_rank['points'] if me_rank else None,
        my_pnl=me_rank['pnl'] if me_rank else None,
        my_trades=my_flow,
        rank_board=[dict(rank=r['rank'], name=r['name'], pnl=r['pnl'], points=r['points']) for r in g['ranking']],
        ticks=tick,
        bots_est=bots_est,
        market=dict(trades=len(trades), volume=vol, my_volume=my_vol,
                    prog_volume=prog_vol, model_volume=model_vol,
                    my_cp_prog=cp_prog, my_cp_model=cp_model),
    ))

json.dump(dict(games=out, scoredCount=main['scoredGameCount'], standings=main['standings']),
          open('/Users/yuanf/DoubaoWork/chats/2026-11-21/new-chat-3/report_full.json', 'w'),
          ensure_ascii=False)

for G in out:
    print(f"#{G['number']:>2} {G['question'][:26]:<28} open={G['open']:>9} settle={G['settle']:>9} "
          f"pnl={str(G['my_pnl']):>9} rank={G['my_rank']} pts={G['my_points']} "
          f"trades={len(G['my_trades']):>2}/{G['market']['trades']:>4} vol={G['market']['my_volume']:>3}/{G['market']['volume']:>4} "
          f"bots_est={len(G['bots_est'])}")
print('scored', main['scoredGameCount'])
print('final standings', [(r['rank'], r['name'], r['points']) for r in main['standings'][:5]])
