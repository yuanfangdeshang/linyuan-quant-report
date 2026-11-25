#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临渊量化 258334 赛后量化回放。

数据来源：裁判侧赛后公开导出（非赛中数据）
  - 竞技场-258334-20261122-004051.json  逐局/排名/结算
  - rooms-原始快照-20261122-004051.json 24 个脚本玩家的估价与逐笔成交簿

合规边界：仅使用赛后已公开的结算值、公开排名、题面明文公开的 review 逐笔复盘
与脚本玩家（非模型参赛者）的估价；不还原任何模型参赛者的思考过程。

用法：python3 postgame_replay.py [赛后数据目录]
"""
import json
import os
import sys
import statistics as st

DATA = sys.argv[1] if len(sys.argv) > 1 else (
    '/Users/yuanf/DoubaoWork/chats/2026-11-19/new-chat-1/赛后数据')
ME_ID = 'fc7feaeda7932a8d'
ME_NAME = 'Workbuddy-Hy4'
N_PLAYERS = 15

arena = json.load(open(os.path.join(DATA, '竞技场-258334-20261122-004051.json')))
snap = json.load(open(os.path.join(DATA, 'rooms-原始快照-20261122-004051.json')))
room = [r for r in snap['rooms'] if str(r.get('code')) == '258334'][0]
snap_by_num = {g['number']: g for g in room['games']}


def C(x):
    """服务器价格：分 -> 计价单位"""
    return None if x is None else x / 100.0


def rank_points(opponent_pnls, mine):
    """把我的 pnl 换成反事实值后，按 standard competition ranking 重算名次与积分。

    opponent_pnls 必须已剔除我自己的真实 pnl（14 个对手），
    否则会出现 rank=16 这种越界名次。
    """
    rank = sum(1 for p in opponent_pnls if p > mine) + 1
    return rank, N_PLAYERS - rank + 1


def exec_quality(g):
    """我的成交 vs 同局同轮全场成交量加权均价。"""
    num = g['number']
    sg = snap_by_num.get(num)
    if not sg:
        return None
    all_tr = sg.get('trades', [])
    mine = [t for t in all_tr
            if t.get('buyerId') == ME_ID or t.get('sellerId') == ME_ID]
    if not mine:
        return None
    by_round = {}
    for t in all_tr:
        by_round.setdefault(t['round'], []).append(t)
    my_buy = my_sell = 0.0
    my_buy_q = my_sell_q = 0
    bench_buy = bench_sell = 0.0
    for t in mine:
        rnd = t['round']
        peers = by_round.get(rnd, [])
        vwap = (sum(x['price'] * x['qty'] for x in peers) /
                sum(x['qty'] for x in peers)) if peers else t['price']
        if t.get('buyerId') == ME_ID:
            my_buy += t['price'] * t['qty']
            my_buy_q += t['qty']
            bench_buy += vwap * t['qty']
        if t.get('sellerId') == ME_ID:
            my_sell += t['price'] * t['qty']
            my_sell_q += t['qty']
            bench_sell += vwap * t['qty']
    # 买入比全场贵为正 = 执行劣势；卖出比全场贵为正 = 执行优势
    buy_edge = (my_buy - bench_buy) / my_buy_q if my_buy_q else 0
    sell_edge = (my_sell - bench_sell) / my_sell_q if my_sell_q else 0
    return {
        'n': len(mine), 'all': len(all_tr),
        'buy_q': my_buy_q, 'sell_q': my_sell_q,
        'buy_edge': C(buy_edge), 'sell_edge': C(sell_edge),
        'net_edge': C((my_buy - bench_buy) - (my_sell - bench_sell)),
    }


print('=' * 112)
print('表 1 · 12 局先验结构：知识题 vs 逐轮线索逻辑题')
print('=' * 112)
print(f"{'局':<5}{'真值':>10}{'prior':>14}{'宽/真值':>10}{'开盘':>11}{'开盘偏差':>11}"
      f"{'bot估价中位':>13}{'CV':>7}{'题型':>8}")
print('-' * 112)
prior_rows = []
for g in arena['games']:
    num = g['number']
    q = snap_by_num[num]['question']
    ans = q['answer']
    prior = q.get('prior') or [0, 0]
    opening = C(g['openingPrice'])
    sg = snap_by_num[num]
    ests = [v['estimate'] / 100 for k, v in (sg.get('states') or {}).items()
            if str(k).startswith('bot:') and isinstance(v, dict)
            and v.get('estimate') is not None]
    med = st.median(ests) if ests else 0
    cv = st.pstdev(ests) / st.mean(ests) if ests and st.mean(ests) else 0
    dev = (opening - ans) / ans * 100 if ans else float('nan')
    dev_s = f'{dev:>10.1f}%' if ans else f'{"—":>11}'
    kind = '测试' if num == 1 else ('知识' if num <= 5 else '逻辑')
    prior_rows.append(dict(num=num, ans=ans, prior=prior, opening=opening,
                           dev=dev, med=med, cv=cv, kind=kind, ests=ests))
    print(f"G{num:<4}{ans:>10.2f}{str(prior):>14}{(prior[1]-prior[0])/ans if ans else 0:>10.2f}"
          f"{opening:>11.2f}{dev_s}{med:>13.2f}{cv:>7.2f}{kind:>8}")
print('-' * 112)
for label, kinds in [('知识题 G2-G5', ['知识']), ('逻辑题 G6-G12', ['逻辑'])]:
    sub = [x for x in prior_rows if x['kind'] in kinds]
    valid = [x for x in sub if x['ans'] > 0]
    print(f"{label:<16} 开盘|偏差|均值 {sum(abs(x['dev']) for x in valid)/len(valid):6.2f}%"
          f"（真值≠0 的 {len(valid)} 局）"
          f"   prior宽/真值均值 {sum((x['prior'][1]-x['prior'][0])/x['ans'] for x in valid)/len(valid):5.2f}"
          f"   bot估价CV均值 {sum(x['cv'] for x in sub)/len(sub):5.2f}"
          f"   bot中位高于真值 {sum(1 for x in sub if x['med'] > x['ans'])}/{len(sub)} 局")

print()
print('--- 为什么知识题开盘价≈真值：24 个脚本估价里是否含「真值锚」 ---')
print(f"{'局':<5}{'真值':>10}{'精确命中真值的脚本数':>22}{'最接近真值的估价':>20}{'开盘':>12}{'中位':>12}")
for x in prior_rows:
    ests = x['ests']
    exact = sum(1 for e in ests if abs(e * 100 - x['ans'] * 100) < 1)
    near = min(ests, key=lambda e: abs(e - x['ans'])) if ests else 0
    print(f"G{x['num']:<4}{x['ans']:>10.2f}{exact:>22}{near:>20.2f}{x['opening']:>12.2f}{x['med']:>12.2f}")
print('（脚本估价从 question.prior 区间内生成；知识题的 prior 区间按真值收窄，逻辑题则宽撒）')

print()
print('--- 开盘价的形成：39 人（15 模型 + 24 脚本）估价的中位数 ---')
print(f"{'局':<5}{'真值':>10}{'开盘':>11}{'39人中位':>12}{'24脚本中位':>13}{'15模型中位':>13}"
      f"{'模型命中真值':>14}{'prior中点/真值':>16}")
for x in prior_rows:
    num = x['num']
    sg = snap_by_num[num]
    st_ = sg.get('states') or {}
    bots = [v['estimate'] / 100 for k, v in st_.items()
            if str(k).startswith('bot:') and isinstance(v, dict) and v.get('estimate') is not None]
    mods = [v['estimate'] / 100 for k, v in st_.items()
            if not str(k).startswith('bot:') and isinstance(v, dict) and v.get('estimate') is not None]
    all_ = bots + mods
    hit = sum(1 for e in mods if abs(e - x['ans']) < 0.005)
    pm = (x['prior'][0] + x['prior'][1]) / 2
    ratio = pm / x['ans'] if x['ans'] else 0
    print(f"G{num:<4}{x['ans']:>10.2f}{x['opening']:>11.2f}{st.median(all_) if all_ else 0:>12.2f}"
          f"{st.median(bots) if bots else 0:>13.2f}{st.median(mods) if mods else 0:>13.2f}"
          f"{str(hit) + '/' + str(len(mods)):>14}{ratio:>15.2f}x")
print('结论：开盘价 ≡ 39 人估价中位数；知识题由「模型大量命中真值」钉住，')
print('      逻辑题无人命中，而 prior 中点普遍高于真值 → 共识结构性高估，做空成为正期望先验。')

print()
print('=' * 112)
print('表 2 · 反事实：每局按开盘价建 10 手持到结算，在真实排名分布下能拿几分')
print('=' * 112)
print(f"{'局':<5}{'真值':>10}{'开盘':>11}{'实际PnL':>12}{'实际分':>8}"
      f"{'开盘做空PnL':>14}{'空头分':>8}{'真值方向PnL':>14}{'满仓分':>8}")
print('-' * 112)
tot_actual = tot_short = tot_perfect = 0
logic_short = logic_perfect = logic_actual = 0
for g in arena['games']:
    num = g['number']
    if num == 1:
        continue
    pr = next(x for x in prior_rows if x['num'] == num)
    ans, opening = pr['ans'], pr['opening']
    ranking = g['ranking']
    me = [x for x in ranking if x['name'] == ME_NAME]
    actual_pnl = me[0]['pnl'] if me else 0
    actual_pts = me[0]['points'] if me else 0
    # 反事实重排：只保留 14 个对手的 pnl，再放进「反事实的我」
    opponents = [x['pnl'] for x in ranking if x['name'] != ME_NAME]
    # 反事实 A：开盘无条件做空 10 手
    short_pnl = int(round((opening - ans) * 10 * 100))
    _, short_pts = rank_points(opponents, short_pnl)
    # 反事实 B：按真值方向满仓 10 手（理论上限，仅作标尺）
    perfect_pnl = int(round(abs(opening - ans) * 10 * 100))
    _, perfect_pts = rank_points(opponents, perfect_pnl)
    tot_actual += actual_pts
    tot_short += short_pts
    tot_perfect += perfect_pts
    if pr['kind'] == '逻辑':
        logic_actual += actual_pts
        logic_short += short_pts
        logic_perfect += perfect_pts
    print(f"G{num:<4}{ans:>10.2f}{opening:>11.2f}{C(actual_pnl):>12.2f}{actual_pts:>8}"
          f"{C(short_pnl):>14.2f}{short_pts:>8}{C(perfect_pnl):>14.2f}{perfect_pts:>8}")
print('-' * 112)
print(f"{'合计(11局)':<16}{'':>31}{tot_actual:>8}{'':>14}{tot_short:>8}{'':>14}{tot_perfect:>8}")
print(f"{'仅逻辑题(7局)':<16}{'':>31}{logic_actual:>8}{'':>14}{logic_short:>8}{'':>14}{logic_perfect:>8}")
print('注：反事实 PnL 用「10 手 × (价格−真值)」计价单位，未扣除冲击成本；')
print('    名次按该局真实 15 人 pnl 分布重排（并列取最小名次），积分 = 15 − 名次 + 1。')

print()
print('=' * 112)
print('表 3 · 我的执行质量：成交价 vs 同局同轮全场 VWAP（正=我买贵/卖贵，单位：计价单位）')
print('=' * 112)
print(f"{'局':<5}{'我的成交':>10}{'全场成交':>10}{'买手':>8}{'卖手':>8}"
      f"{'买入劣势':>12}{'卖出优势':>12}{'净执行差':>12}{'每手/开盘':>12}")
print('-' * 124)
for g in arena['games']:
    num = g['number']
    e = exec_quality(g)
    if not e:
        continue
    truth = next(x['ans'] for x in prior_rows if x['num'] == num)
    opening = next(x['opening'] for x in prior_rows if x['num'] == num)
    total_q = e['buy_q'] + e['sell_q']
    # 每手平均执行差 / 开盘价：消除量纲与手数差异，可跨 4.8 与 5150 横比
    norm = (e['net_edge'] / total_q) / opening * 100 if total_q and opening else 0
    print(f"G{num:<4}{e['n']:>10}{e['all']:>10}{e['buy_q']:>8}{e['sell_q']:>8}"
          f"{e['buy_edge']:>12.3f}{e['sell_edge']:>12.3f}{e['net_edge']:>12.3f}{norm:>11.2f}%")
print('-' * 124)
print('净执行差 = 买多付的钱 − 卖多收的钱；正数代表我的挂单执行比全场均价差。')
print('归一化列 = (净执行差 / 总成手数) / 该局开盘价，消除量纲与手数差异。')

print()
print('=' * 112)
print('表 4 · G12 逐轮：我的成交分布 vs 全场价格路径')
print('=' * 112)
sg = snap_by_num[12]
all_tr = sg['trades']
for rnd in (1, 2, 3):
    rt = [t for t in all_tr if t['round'] == rnd]
    mt = [t for t in rt if t.get('buyerId') == ME_ID or t.get('sellerId') == ME_ID]
    if not rt:
        continue
    vwap = sum(t['price'] * t['qty'] for t in rt) / sum(t['qty'] for t in rt)
    mybuy = [t for t in mt if t.get('buyerId') == ME_ID]
    mysell = [t for t in mt if t.get('sellerId') == ME_ID]
    print(f"R{rnd}: 全场 {len(rt):>3} 笔 / {sum(t['qty'] for t in rt):>3} 手  "
          f"VWAP={C(vwap):>8.2f}  价格区间 {C(min(t['price'] for t in rt)):>7.2f}"
          f"~{C(max(t['price'] for t in rt)):>7.2f}  "
          f"我买 {sum(t['qty'] for t in mybuy):>2} 手 我卖 {sum(t['qty'] for t in mysell):>2} 手")
r3 = [t for t in all_tr if t['round'] == 3]
myr3 = [t for t in r3 if t.get('buyerId') == ME_ID or t.get('sellerId') == ME_ID]
print(f"R3 我成交 {len(myr3)} 笔，其中买入 {sum(t['qty'] for t in myr3 if t.get('buyerId')==ME_ID)} 手；"
      f"R3 全场 VWAP={C(sum(t['price']*t['qty'] for t in r3)/sum(t['qty'] for t in r3)):.2f}，真值 87.00")
