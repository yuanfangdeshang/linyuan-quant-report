# -*- coding: utf-8 -*-
"""复盘数据汇总

数据来源（双源交叉校验）：
1. 我的实时落盘记录：state.json / events.log / notes.md —— 估价、操作、反思
2. 官方赛后全量导出：竞技场-258334-20261122-004051.json —— 仅取结算后公开的
   openingPrice / settlementPrice / ranking / review(逐笔) / history / signals
   未读取 token、hostKey 或题库 answer 字段。
"""

# 每局: 序号(内部game number), 题面, 我的估价, 开盘价(单位值), 结算真值, 真值说明,
#       我的核心操作, 单局pnl(分,官方), 名次, 得分, 累计分, 关键决策/教训
GAMES = [
    dict(n=1, tag="测试局", theme="上海肯德基数量",
         q="截至2025-12-11上海有多少家肯德基餐厅？",
         est=500, open=715.61, truth=700,
         note="上海第700家肯德基开业",
         op="404 bug 全程零成交（策略方向对但工程错）",
         pnl=0, rank=None, pts=0, cum=0,
         lesson="开盘价(群体中位数)偏离真值仅2.2%，远胜我的独立估值(500,错28.6%)与单线索类比(1000,错43%)。成交价取先挂方；务必带code+token。"),
    dict(n=2, tag="正式1", theme="面积第104大国家",
         q="世界面积第104大国家面积(万km²)",
         est=5.0, open=11.32, truth=10.99,
         note="线索点名：古巴",
         op="高抛低吸→低位买成+10多头@10.98≈真值",
         pnl=687, rank=4, pts=12, cum=12,
         lesson="线索直接点名答案时，立刻用领域知识切fairOverride到真值，别死守开盘价。正式局5轮不是3轮。"),
    dict(n=3, tag="正式2", theme="中国高铁里程",
         q="2024年底中国高铁营业里程(万公里)",
         est=4.8, open=4.80, truth=4.8,
         note="官方约4.8万公里",
         op="高位做空6手@4.98，回落持有",
         pnl=108, rank=7, pts=9, cum=21,
         lesson="开盘价即真值；切换题目必须清掉上一题fairOverride。"),
    dict(n=4, tag="正式3", theme="上海港集装箱",
         q="2024年上海港集装箱吞吐量(万TEU)",
         est=5150, open=5150.60, truth=5150,
         note="约5150万标准箱",
         op="窄幅波动未触2%阈值，0持仓",
         pnl=0, rank=10, pts=6, cum=27,
         lesson="真值≈开盘且波动小于阈值时策略空仓白丢一局——这是策略盲区。"),
    dict(n=5, tag="正式4", theme="民航机场数",
         q="2024年底中国颁证民用运输机场数",
         est=260, open=263.00, truth=263,
         note="共263个",
         op="高位做空3手@268.81",
         pnl=1743, rank=6, pts=10, cum=37,
         lesson="开盘263精准等于真值；空单方向正确稳定贡献。"),
    dict(n=6, tag="正式5", theme="冰箱鸡蛋数",
         q="此人冰箱现有多少个鸡蛋？",
         est=10, open=22.55, truth=30,
         note="两盒10+30枚，5天每天2个，剩30",
         op="做空→切锚错误(40)→改30→回补太慢剩-2空",
         pnl=-4249, rank=13, pts=3, cum=40,
         lesson="线索算全所有项(别忘消耗)；揭示真值后要一次性激进建仓。触发了策略升级。"),
    dict(n=7, tag="正式6", theme="今日步数",
         q="此人11-21走了多少步？",
         est=8000, open=8000.00, truth=8476,
         note="手机健康App:8476步",
         op="切锚8450→低位一次吃7手→补齐+10@8136步",
         pnl=366402, rank=2, pts=14, cum=54,
         lesson="千位8百位4→84XX。激进建仓瞬间吃满，吃到全部估值修正，全场最漂亮操作之一。"),
    dict(n=8, tag="正式7", theme="相册新增照片",
         q="今日相册新增多少张照片？",
         est=30, open=15.00, truth=7,
         note="个位数且是质数=7",
         op="切锚3→+10多头反手到-10满仓空",
         pnl=7666, rank=3, pts=13, cum=67,
         lesson="质数集合应取中值5而非最小3；方向对就大赚，取值稍偏无伤。"),
    dict(n=9, tag="正式8", theme="微信未读数",
         q="此刻微信未读消息数？",
         est=50, open=36.63, truth=0,
         note="看到红点就点掉=0",
         op="中途抄底多头摩擦→切锚5反手-10空",
         pnl=17203, rank=10, pts=6, cum=73,
         lesson="'靠近下界'可能就是0；中途反复反手磨掉已实现利润(11804→1763)。"),
    dict(n=10, tag="正式9", theme="七天屏幕时长",
         q="过去七天屏幕使用总时长(小时)",
         est=35, open=40.00, truth=25.6,
         note="每天3.5-4h×7=24.5-28",
         op="切锚26→+10多头反手-10空",
         pnl=10940, rank=2, pts=14, cum=87,
         lesson="'折算每天X小时'要乘天数换算总量再切锚。"),
    dict(n=11, tag="正式10", theme="微信好友数",
         q="微信通讯录好友数？",
         est=500, open=1036.66, truth=1001,
         note="四位数,比一千多一点=1001",
         op="切锚1040→做空；末段对手错单487/500→吃+9手@619.78",
         pnl=446354, rank=1, pts=15, cum=102,
         lesson="对手极端错单=捡漏机会；成交价取先挂方，白捡价差。单局满分冠军。"),
    dict(n=12, tag="正式11", theme="今日解锁次数",
         q="11-21手机解锁多少次？",
         est=80, open=100.00, truth=87,
         note="两位数十到九十=87",
         op="切锚85→建-10空@99.8",
         pnl=15148, rank=2, pts=14, cum=116,
         lesson="比八十多一点不到九十→87，锚85几乎完美。线索数字特征→切锚→激进建仓模式持续高效。"),
]

# 官方赛后导出中的逐局权威统计（仅结算后公开字段）
# vol=全场成交量(手), orders=全场订单数, mytr=我的成交笔数,
# champPnl/champPts=冠军 quwork-DeepSeek 的该局盈亏与得分
OFFICIAL = {
    1:  dict(vol=345, orders=27, mytr=0,  champPnl=-6600,  champPts=0),
    2:  dict(vol=629, orders=27, mytr=22, champPnl=0,      champPts=7),
    3:  dict(vol=465, orders=33, mytr=4,  champPnl=70,     champPts=8),
    4:  dict(vol=336, orders=55, mytr=0,  champPnl=39109,  champPts=11),
    5:  dict(vol=316, orders=43, mytr=3,  champPnl=3943,   champPts=14),
    6:  dict(vol=413, orders=20, mytr=12, champPnl=3280,   champPts=13),
    7:  dict(vol=403, orders=27, mytr=16, champPnl=246818, champPts=13),
    8:  dict(vol=446, orders=20, mytr=22, champPnl=6545,   champPts=11),
    9:  dict(vol=495, orders=21, mytr=45, champPnl=35421,  champPts=11),
    10: dict(vol=506, orders=17, mytr=17, champPnl=168,    champPts=11),
    11: dict(vol=388, orders=17, mytr=17, champPnl=73192,  champPts=12),
    12: dict(vol=375, orders=20, mytr=9,  champPnl=6302,   champPts=13),
}

# 最终排名（15人，官方 standings）
RANKING = [
    ("quwork-DeepSeek", 124, 1, False),
    ("豆包-远方的mac-GLM5.3", 118, 2, False),
    ("豆包-远方的mac-自动-高", 116, 3, False),
    ("Workbuddy-Hy4fla", 116, 3, True),
    ("豆包-远方的 mac-DeepS", 114, 5, False),
    ("qoder-DeepSeek f", 110, 6, False),
    ("豆包-远方的 mac-Kimi", 103, 7, False),
    ("Workbuddy-Hy4", 88, 8, False),
    ("豆包-远方的mac-DeepSe", 86, 9, False),
    ("app-Workbuddy-快速", 84, 10, False),
    ("豆包-远方的 mac-自动-高", 80, 11, False),
    ("豆包-远方的mac-豆包2.1l", 80, 11, False),
    ("远方的熵", 80, 11, False),
    ("豆包-远方的mac-Qwen4M", 67, 14, False),
    ("豆包-远方的mac-豆包2.1p", 58, 15, False),
]

# 我的实时日志统计（订单数口径，与官方"成交笔数"不同）
TOTAL_ACTS = 107
BUYS = 55
SELLS = 52
TOTAL_TRADES = 167          # 官方 review 中的我的成交笔数
MARKET_VOLUME = 4772        # 11 局正式题全场成交量(手)
MARKET_ORDERS = 300         # 11 局正式题全场订单数
