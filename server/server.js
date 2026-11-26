'use strict';

/**
 * 临渊量化 · 交易实验室 —— 本地服务器
 * 无第三方依赖：node:http + SSE + 自建连续竞价撮合引擎
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');
const crypto = require('crypto');

const PORT = Number(process.env.PORT || 7788);
const DEFAULT_ROUND_SECONDS = 60;
const LIMIT = 10;                 // 净持仓上限 ±10 手
const DATA_DIR = path.join(__dirname, 'data');
const ROOMS_FILE = path.join(DATA_DIR, 'rooms.json');
const PUBLIC_DIR = path.join(__dirname, 'public');

/* ------------------------------- 基础工具 ------------------------------- */

const now = () => Date.now();
const rid = (n = 8) => crypto.randomBytes(n).toString('hex');
const cents = (v) => Math.round(Number(v) * 100);
const yuan = (c) => (c == null ? null : c / 100);

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk) => {
      data += chunk;
      if (data.length > 1e7) req.destroy();
    });
    req.on('end', () => {
      if (!data) return resolve({});
      try { resolve(JSON.parse(data)); } catch (e) { reject(new Error('JSON 解析失败')); }
    });
    req.on('error', reject);
  });
}

function sendJson(res, code, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(code, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
  });
  res.end(body);
}

/* ------------------------------- 房间与题目 ------------------------------- */

const BANK = require('./questions');

function makeRoom(code) {
  return {
    code,
    hostKey: rid(12),
    createdAt: now(),
    players: [],                // {id, token, name, joinedAt, online, lastSeen}
    games: [],
    currentIndex: -1,
    roundSeconds: DEFAULT_ROUND_SECONDS,
    bots: { ...DEFAULT_BOTS },
    queue: []                   // 待开赛题目 id 队列（可留空则按题库顺序）
  };
}

const rooms = new Map();

function loadRooms() {
  try {
    const raw = JSON.parse(fs.readFileSync(ROOMS_FILE, 'utf8'));
    for (const r of raw.rooms || []) {
      // 重置在线状态，避免重启后残留
      r.players.forEach((p) => { p.online = false; });
      rooms.set(r.code, r);
    }
    console.log(`[持久化] 已恢复 ${rooms.size} 个房间`);
  } catch (e) { /* 首次运行无文件 */ }
}

let saveTimer = null;
function scheduleSave() {
  if (saveTimer) return;
  saveTimer = setTimeout(() => {
    saveTimer = null;
    try {
      fs.mkdirSync(DATA_DIR, { recursive: true });
      fs.writeFileSync(ROOMS_FILE, JSON.stringify({ rooms: [...rooms.values()] }, null, 1));
    } catch (e) { console.error('[持久化] 写入失败', e.message); }
  }, 800);
}

function ensureCode() {
  let code;
  do { code = String(Math.floor(100000 + Math.random() * 900000)); } while (rooms.has(code));
  return code;
}

function getRoom(code) {
  return rooms.get(String(code || '').trim()) || null;
}

function findPlayer(room, token) {
  if (!token) return null;
  return room.players.find((p) => p.token === token) || null;
}

/* ------------------------------- 撮合引擎 ------------------------------- */

/* ------------------------------- 交易机器人 ------------------------------- */

/**
 * 场内程序账户（不计入人类积分榜，但成交与持仓全部进入盘口与复盘）
 *  - 流动性程序：双边做市，保证任何时刻都有对手价
 *  - 趋势猎手：顺短期动量追价
 *  - 均值回归：价格偏离短均线时反向
 *  - 噪声交易员：随机方向小额试单，制造摩擦
 */
/* 脚本玩家：4 个原生 + 补齐到 24 人的人口包
 * 价值派 12：各有自己的锚，价格偏离就朝锚推 2 手
 * 噪声派  8：随机方向、随机手数
 * 原有 4 个：做市 / 趋势 / 均值回归
 */
const VALUE_BOTS = Array.from({ length: 12 }, (_, i) => ({
  id: `bot:v${i + 1}`,
  name: `价值派${i + 1}`,
  kind: 'value',
  desc: '朝自己的估值分批推单',
  bias: (i + 0.5) / 12          // 在题目先验区间里的相对位置
}));

const NOISE_BOTS = Array.from({ length: 8 }, (_, i) => ({
  id: `bot:n${i + 1}`,
  name: `噪声${i + 1}`,
  kind: 'noise',
  desc: '随机方向随机手数'
}));

const BOTS = [
  { id: 'bot:liq', name: '流动性程序', kind: 'mm', desc: '双边报价，承接流动性', bias: 0.5 },
  { id: 'bot:mom', name: '趋势猎手', kind: 'momentum', desc: '顺着短期动量追价', bias: 0.62 },
  { id: 'bot:mom2', name: '趋势猎手乙', kind: 'momentum', desc: '顺着短期动量追价', bias: 0.7 },
  { id: 'bot:mrv', name: '均值回归', kind: 'meanrev', desc: '价格偏离均值时反向', bias: 0.25 },
  ...VALUE_BOTS,
  ...NOISE_BOTS
];
const BOT_IDS = BOTS.map((b) => b.id);
const DEFAULT_BOTS = Object.fromEntries(BOT_IDS.map((id) => [id, true]));

function botEnabled(room, id) {
  if (!room.bots) room.bots = { ...DEFAULT_BOTS };
  return !!room.bots[id];
}

function botPost(game, botId, side, price, qty) {
  const avail = available(game, botId, side);
  const q = Math.min(qty, avail);
  if (q <= 0) return null;
  const p = Math.max(1, Math.round(price));
  game.orderSeq += 1;
  const order = {
    id: game.orderSeq,
    playerId: botId,
    side,
    price: p,
    qty: q,
    remaining: q,
    seq: game.orderSeq,
    createdAt: now(),
    round: game.round,
    program: true
  };
  game.book.orders.push(order);
  return order;
}

function botMid(game) {
  return game.lastPrice || game.openingPrice || 0;
}

function botMean(game, n = 24) {
  const pts = game.ticks.slice(-n);
  if (!pts.length) return botMid(game);
  return pts.reduce((s, x) => s + x.p, 0) / pts.length;
}

/** 做市：撤旧报价，围绕中间价挂四档 */
function botMarketMake(game) {
  game.book.orders = game.book.orders.filter((o) => !(o.playerId === 'bot:liq'));
  const mid = botMid(game);
  if (!mid) return;
  const spread = Math.max(1, Math.round(mid * 0.008));
  const ladder = [
    { d: -1, q: 2 + Math.floor(Math.random() * 4) },
    { d: -2, q: 3 + Math.floor(Math.random() * 5) },
    { d: 1, q: 2 + Math.floor(Math.random() * 4) },
    { d: 2, q: 3 + Math.floor(Math.random() * 5) }
  ];
  for (const lv of ladder) {
    botPost(game, 'bot:liq', lv.d < 0 ? 'buy' : 'sell', mid + lv.d * spread, lv.q);
  }
  match(game, () => {});
  game.botRefreshAt = now();
}

/** 主动方向单：尽量吃到对手价，保证成交 */
function botAggress(game, botId, side, qty) {
  const view = bookView(game);
  const target = side === 'buy' ? view.bestAsk : view.bestBid;
  const price = target != null ? target : (side === 'buy' ? botMid(game) + 1 : botMid(game) - 1);
  const before = game.book.orders.length;
  botPost(game, botId, side, price, qty);
  match(game, () => {});
  return game.book.orders.length !== before;
}

function botCancelOlder(game, botId, ms = 9000) {
  const ts = now();
  game.book.orders = game.book.orders.filter(
    (o) => !(o.playerId === botId && ts - o.createdAt > ms)
  );
}

function runBots(room, game) {
  if (!game || game.phase !== 'trading') return false;
  const ts = now();
  let changed = false;
  if (!room.bots) room.bots = { ...DEFAULT_BOTS };

  for (const bot of BOTS) {
    if (!botEnabled(room, bot.id)) continue;
    const st = stateOf(game, bot.id);

    if (bot.kind === 'mm') {
      if (ts - (game.botRefreshAt || 0) > 11000) {
        botMarketMake(game);
        changed = true;
      }
      continue;
    }

    const lastAct = st.lastBotAct || 0;
    const period = bot.period || (bot.period = 3500 + (BOT_IDS.indexOf(bot.id) % 5) * 700);
    if (ts - lastAct < period) continue;
    st.lastBotAct = ts;

    if (bot.kind === 'momentum') {
      const pts = game.ticks.slice(-8);
      if (pts.length < 4) continue;
      const delta = pts[pts.length - 1].p - pts[0].p;
      const scale = Math.max(1, Math.round(botMid(game) * 0.004));
      if (delta > scale && st.pos < LIMIT - 1) {
        botCancelOlder(game, bot.id);
        botAggress(game, bot.id, 'buy', Math.min(2, LIMIT - st.pos));
        changed = true;
      } else if (delta < -scale && st.pos > -LIMIT + 1) {
        botCancelOlder(game, bot.id);
        botAggress(game, bot.id, 'sell', Math.min(2, LIMIT + st.pos));
        changed = true;
      }
      continue;
    }

    if (bot.kind === 'meanrev') {
      const mean = botMean(game);
      const mid = botMid(game);
      if (!mean || !mid) continue;
      const dev = (mid - mean) / mean;
      if (dev > 0.012 && st.pos > -LIMIT + 1) {
        botCancelOlder(game, bot.id);
        botAggress(game, bot.id, 'sell', Math.min(2, LIMIT + st.pos));
        changed = true;
      } else if (dev < -0.012 && st.pos < LIMIT - 1) {
        botCancelOlder(game, bot.id);
        botAggress(game, bot.id, 'buy', Math.min(2, LIMIT - st.pos));
        changed = true;
      }
      continue;
    }

    if (bot.kind === 'value') {
      const anchor = Number.isFinite(st.estimate) ? st.estimate : null;
      const mid = botMid(game);
      if (!anchor || !mid) continue;
      const dev = (mid - anchor) / anchor;
      if (dev > 0.02 && st.pos > -LIMIT + 1) {
        botCancelOlder(game, bot.id, 12000);
        botAggress(game, bot.id, 'sell', Math.min(2, LIMIT + st.pos));
        changed = true;
      } else if (dev < -0.02 && st.pos < LIMIT - 1) {
        botCancelOlder(game, bot.id, 12000);
        botAggress(game, bot.id, 'buy', Math.min(2, LIMIT - st.pos));
        changed = true;
      }
      continue;
    }

    if (bot.kind === 'noise') {
      if (Math.random() < 0.45) continue;
      const side = Math.random() < 0.5 ? 'buy' : 'sell';
      const qty = 1 + Math.floor(Math.random() * 2);
      if (side === 'buy' && st.pos < LIMIT) { botAggress(game, bot.id, 'buy', Math.min(qty, LIMIT - st.pos)); changed = true; }
      else if (side === 'sell' && st.pos > -LIMIT) { botAggress(game, bot.id, 'sell', Math.min(qty, LIMIT + st.pos)); changed = true; }
      continue;
    }
  }
  return changed;
}

function createGame(room, q, number) {
  return {
    id: rid(6),
    number,
    questionId: q.id,
    question: q,                 // 含 answer，快照中会剔除
    practice: !!q.practice,
    phase: 'estimate',           // estimate | trading | closed | settled
    notice: null,
    reports: {},
    round: 0,
    maxRound: q.signals.length,
    roundSeconds: room.roundSeconds,
    openingPrice: null,
    lastPrice: null,
    openedAt: null,
    roundStartedAt: null,
    roundEndsAt: null,
    book: { orders: [] },        // 静止委托
    orderSeq: 0,
    tradeSeq: 0,
    trades: [],
    states: {},                  // playerId -> {pos, avgCost, realized, estimate, estimateAt}
    ticks: [],                   // {t, p}
    rounds: [],                  // {round,startT,endT,closePrice,volume,orders}
    resolution: null,
    ranking: null,
    botRefreshAt: 0,
    closedAt: null,
    settledAt: null
  };
}

function stateOf(game, pid) {
  if (!game.states[pid]) {
    game.states[pid] = { pos: 0, avgCost: 0, realized: 0, estimate: null, estimateAt: null };
  }
  return game.states[pid];
}

/** 成交后更新持仓：均价成本法，支持反手 */
function applyFill(game, pid, side, price, qty) {
  const st = stateOf(game, pid);
  const signed = side === 'buy' ? qty : -qty;
  const pos = st.pos;

  if (pos === 0 || Math.sign(pos) === Math.sign(signed)) {
    const abs = Math.abs(pos);
    st.avgCost = (abs * st.avgCost + qty * price) / (abs + qty);
    st.pos = pos + signed;
    if (st.pos === 0) st.avgCost = 0;
    return 0;
  }

  // 反向成交：先平仓，剩余开新仓
  const closeQty = Math.min(qty, Math.abs(pos));
  const realized = side === 'sell'
    ? (price - st.avgCost) * closeQty
    : (st.avgCost - price) * closeQty;
  st.realized += realized;

  const newPos = pos + signed;
  if (newPos === 0) {
    st.pos = 0;
    st.avgCost = 0;
  } else if (Math.sign(newPos) === Math.sign(signed) && qty > closeQty) {
    // 反手建仓，剩余量按本次成交价成仓
    st.pos = newPos;
    st.avgCost = price;
  } else {
    st.pos = newPos;           // 部分平仓，均价不变
  }
  return realized;
}

function pendingQty(game, pid, side) {
  return game.book.orders
    .filter((o) => o.playerId === pid && o.side === side)
    .reduce((s, o) => s + o.remaining, 0);
}

function available(game, pid, side) {
  const st = stateOf(game, pid);
  if (side === 'buy') return Math.max(0, LIMIT - st.pos - pendingQty(game, pid, 'buy'));
  return Math.max(0, LIMIT + st.pos - pendingQty(game, pid, 'sell'));
}

function pushTick(game, price) {
  if (game.openedAt == null) return;
  const t = Math.round((now() - game.openedAt) / 100) / 10;
  const last = game.ticks[game.ticks.length - 1];
  if (last && Math.abs(last.t - t) < 0.2 && last.p === price) return;
  game.ticks.push({ t, p: price });
  if (game.ticks.length > 900) game.ticks.splice(0, game.ticks.length - 900);
}

/**
 * 连续撮合：价格优先、时间优先；成交价取被动方（更早挂出）的价格
 */
function match(game, notify) {
  const orders = game.book.orders;
  let guard = 0;

  while (guard++ < 5000) {
    const live = orders.filter((o) => o.remaining > 0);
    if (!live.length) break;
    const bids = live.filter((o) => o.side === 'buy').sort((a, b) => b.price - a.price || a.seq - b.seq);
    const asks = live.filter((o) => o.side === 'sell').sort((a, b) => a.price - b.price || a.seq - b.seq);
    if (!bids.length || !asks.length) break;

    // 找一组不同玩家的可成交对手单（跨过自己的挂单，避免自成交）
    let hitBid = null;
    let hitAsk = null;
    for (const b of bids.slice(0, 10)) {
      let done = false;
      for (const a of asks.slice(0, 10)) {
        if (a.price > b.price) break;
        if (a.playerId === b.playerId) continue;
        hitBid = b; hitAsk = a; done = true; break;
      }
      if (done) break;
    }
    if (!hitBid) break;

    const qty = Math.min(hitBid.remaining, hitAsk.remaining);
    const passive = hitBid.seq < hitAsk.seq ? hitBid : hitAsk;
    const price = passive.price;

    hitBid.remaining -= qty;
    hitAsk.remaining -= qty;

    const buyId = hitBid.playerId;
    const sellId = hitAsk.playerId;

    const buyerReal = applyFill(game, buyId, 'buy', price, qty);
    const sellerReal = applyFill(game, sellId, 'sell', price, qty);

    game.tradeSeq += 1;
    const trade = {
      id: game.tradeSeq,
      round: game.round,
      at: now(),
      price,
      qty,
      buyerId: buyId,
      sellerId: sellId,
      buyOrderId: hitBid.id,
      sellOrderId: hitAsk.id,
      buyerPos: stateOf(game, buyId).pos,
      sellerPos: stateOf(game, sellId).pos,
      buyerRealized: Math.round(buyerReal || 0),
      sellerRealized: Math.round(sellerReal || 0)
    };
    game.trades.push(trade);
    game.lastPrice = price;
    pushTick(game, price);

    if (notify) notify(trade);
  }

  game.book.orders = game.book.orders.filter((o) => o.remaining > 0);
  trimBook(game);
}

function trimBook(game) {
  // 防止无限挂单堆积：单侧最多保留 60 档价格
  const bySide = { buy: new Map(), sell: new Map() };
  for (const o of game.book.orders) {
    const m = bySide[o.side];
    m.set(o.price, (m.get(o.price) || 0) + o.remaining);
  }
  const keep = (side) => {
    const prices = [...bySide[side].keys()].sort((a, b) => (side === 'buy' ? b - a : a - b));
    return new Set(prices.slice(0, 60));
  };
  const keepBuy = keep('buy');
  const keepSell = keep('sell');
  game.book.orders = game.book.orders.filter((o) => (o.side === 'buy' ? keepBuy : keepSell).has(o.price));
}

function placeOrder(room, game, playerId, side, priceCents, qty) {
  const rounded = Math.round(priceCents);
  if (!Number.isFinite(rounded) || rounded <= 0) throw new Error('价格无效');
  const q = Math.floor(qty);
  if (!Number.isFinite(q) || q <= 0) throw new Error('手数无效');
  const avail = available(game, playerId, side);
  if (q > avail) throw new Error(`超出可${side === 'buy' ? '买' : '卖'}手数（${avail} 手）`);

  game.orderSeq += 1;
  const order = {
    id: game.orderSeq,
    playerId,
    side,
    price: rounded,
    qty: q,
    remaining: q,
    seq: game.orderSeq,
    createdAt: now(),
    round: game.round
  };
  game.book.orders.push(order);
  match(game, () => {});
  return order;
}

/* ------------------------------- 轮次控制 ------------------------------- */

function startRound(room, game, round) {
  game.round = round;
  game.roundStartedAt = now();
  game.roundEndsAt = now() + game.roundSeconds * 1000;
  const startT = Math.round((now() - game.openedAt) / 100) / 10;
  game.rounds.push({ round, startT, endT: null, closePrice: null, volume: 0, orders: 0, tradeCount: 0 });
  if (botEnabled(room, 'bot:liq')) botMarketMake(game);
  scheduleSave();
}

function closeRound(game) {
  const rec = game.rounds[game.rounds.length - 1];
  if (!rec) return;
  rec.endT = Math.round((now() - game.openedAt) / 100) / 10;
  rec.closePrice = game.lastPrice;
  const trades = game.trades.filter((t) => t.round === rec.round);
  rec.volume = trades.reduce((s, t) => s + t.qty, 0);
  rec.orders = game.book.orders.filter((o) => o.remaining > 0).length;
  rec.tradeCount = trades.length;
}

/* 机器人在集合竞价里也要报价：按题目的合理猜测区间各报一个（不知道答案，只是各有偏好） */
function seedBotEstimates(room, game) {
  const prior = Array.isArray(game.question.prior) ? game.question.prior : null;
  if (!prior) return;
  const [lo, hi] = prior;
  const span = Math.max(1, hi - lo);
  for (const b of BOTS) {
    if (!botEnabled(room, b.id)) continue;
    const st = stateOf(game, b.id);
    if (Number.isFinite(st.estimate)) continue;
    let v;
    if (b.kind === 'noise') {
      v = lo + span * Math.random();
    } else {
      // 每人一个稳定的锚：先验区间的 bias 位置 + 每题 ±12% 的抖动
      const jitter = 0.88 + Math.random() * 0.24;
      v = (lo + span * (b.bias != null ? b.bias : 0.5)) * jitter;
    }
    st.estimate = cents(v);
    st.estimateAt = now();
  }
}

function openMarket(room, game) {
  seedBotEstimates(room, game);
  const ids = [...room.players.map((p) => p.id), ...BOT_IDS.filter((id) => botEnabled(room, id))];
  const estimates = ids
    .map((id) => stateOf(game, id).estimate)
    .filter((v) => Number.isFinite(v));
  if (!estimates.length) throw new Error('尚无人提交估价，无法开盘');
  const sorted = [...estimates].sort((a, b) => a - b);
  const mid = sorted.length % 2
    ? sorted[(sorted.length - 1) / 2]
    : Math.round((sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2);

  game.openingPrice = mid;
  game.lastPrice = mid;
  game.openedAt = now();
  game.phase = 'trading';
  pushTick(game, mid);
  startRound(room, game, 1);
}

function settleGame(room, game) {
  const settlePrice = cents(game.question.answer);
  const humans = room.players.slice();
  const rows = humans.map((p) => {
    const st = stateOf(game, p.id);
    const pnl = Math.round(st.realized + st.pos * (settlePrice - st.avgCost));
    return { id: p.id, name: p.name, pnl, position: st.pos, realized: Math.round(st.realized) };
  });

  rows.sort((a, b) => b.pnl - a.pnl);
  let lastPnl = null;
  let lastRank = 0;
  rows.forEach((r, i) => {
    if (lastPnl !== null && r.pnl === lastPnl) r.rank = lastRank;
    else { r.rank = i + 1; lastRank = r.rank; lastPnl = r.pnl; }
  });
  const n = rows.length;
  rows.forEach((r) => {
    r.points = game.practice ? 0 : (n - r.rank + 1);
  });

  game.ranking = rows;
  game.resolution = {
    type: 'resolution',
    round: game.round,
    at: now(),
    price: settlePrice,
    note: game.question.resolution || `本题按 ${game.question.answer} ${game.question.unit.split('/')[0].trim()} 结算。`,
    source: game.question.source || ''
  };
  game.phase = 'settled';
  game.settledAt = now();
  game.book.orders = [];
  closeRound(game);
  scheduleSave();
}

/* ------------------------------- 快照 ------------------------------- */

function bookView(game) {
  const agg = { buy: new Map(), sell: new Map() };
  for (const o of game.book.orders) {
    if (o.remaining <= 0) continue;
    const m = agg[o.side];
    m.set(o.price, (m.get(o.price) || 0) + o.remaining);
  }
  const asks = [...agg.sell.entries()].sort((a, b) => a[0] - b[0]).slice(0, 5)
    .map(([p, q]) => ({ price: p, qty: q }));
  const bids = [...agg.buy.entries()].sort((a, b) => b[0] - a[0]).slice(0, 5)
    .map(([p, q]) => ({ price: p, qty: q }));
  const bestAsk = asks[0] ? asks[0].price : null;
  const bestBid = bids[0] ? bids[0].price : null;
  const spread = bestAsk != null && bestBid != null ? bestAsk - bestBid : null;
  return { asks, bids, bestAsk, bestBid, spread };
}

function playerName(room, id) {
  const botSeat = BOTS.find((b) => b.id === id);
  if (botSeat) return botSeat.name;
  const p = room.players.find((x) => x.id === id);
  return p ? p.name : '（已离场）';
}

function gameView(room, game, viewerId) {
  const nowTs = now();
  const st = viewerId ? stateOf(game, viewerId) : null;
  const participants = [...room.players.map((p) => p.id), ...BOT_IDS.filter((bid) => botEnabled(room, bid))];
  const submittedCount = participants.filter((id) => Number.isFinite(stateOf(game, id).estimate)).length;
  const humansSubmitted = room.players.filter((p) => Number.isFinite(stateOf(game, p.id).estimate)).length;

  const released = game.phase === 'estimate' ? 0 : game.round;
  const signals = game.question.signals.slice(0, Math.max(released, game.phase === 'settled' ? game.maxRound : released))
    .map((s, i) => ({ round: i + 1, title: s.title, text: s.text, sourceName: s.sourceName || '' }));

  const roundRemain = game.phase === 'trading' && game.roundEndsAt
    ? Math.max(0, Math.round((game.roundEndsAt - nowTs) / 1000))
    : 0;
  const elapsed = game.openedAt ? Math.max(0, Math.round((nowTs - game.openedAt) / 1000)) : 0;
  const total = game.maxRound * game.roundSeconds;

  const myOrders = st
    ? game.book.orders.filter((o) => o.playerId === viewerId && o.remaining > 0)
        .map((o) => ({ id: o.id, side: o.side, price: o.price, qty: o.qty, remaining: o.remaining, round: o.round }))
    : [];

  const markPrice = game.phase === 'settled' && game.resolution ? game.resolution.price : game.lastPrice;
  const pnlNow = st && markPrice != null
    ? Math.round(st.realized + st.pos * (markPrice - st.avgCost))
    : 0;

  // 复盘：仅已结束轮次对所有人公开
  const publicRound = game.phase === 'settled' ? game.maxRound : Math.max(0, game.round - 1);
  const review = game.phase === 'estimate' ? null : {
    throughRound: publicRound,
    players: [...room.players.map((p) => p.id), ...BOT_IDS.filter((bid) => botEnabled(room, bid)
      || game.trades.some((t) => t.buyerId === bid || t.sellerId === bid))].map((pid) => ({
      id: pid,
      name: playerName(room, pid),
      bot: BOT_IDS.includes(pid),
      trades: game.trades.filter((t) => t.round <= publicRound && (t.buyerId === pid || t.sellerId === pid))
        .map((t) => {
          const isBuyer = t.buyerId === pid;
          return {
            id: t.id,
            round: t.round,
            at: t.at,
            side: isBuyer ? 'buy' : 'sell',
            price: t.price,
            qty: t.qty,
            counterparty: playerName(room, isBuyer ? t.sellerId : t.buyerId),
            program: BOT_IDS.includes(isBuyer ? t.sellerId : t.buyerId),
            positionAfter: null,
            realizedPnl: null
          };
        })
    }))
  };

  // 补齐复盘的 positionAfter / realizedPnl（按玩家时间序重放）
  if (review) {
    for (const pl of review.players) {
      const st2 = { pos: 0, avgCost: 0, realized: 0 };
      for (const tr of pl.trades) {
        const signed = tr.side === 'buy' ? tr.qty : -tr.qty;
        let real = 0;
        if (st2.pos === 0 || Math.sign(st2.pos) === Math.sign(signed)) {
          const abs = Math.abs(st2.pos);
          st2.avgCost = (abs * st2.avgCost + tr.qty * tr.price) / (abs + tr.qty);
          st2.pos += signed;
          if (st2.pos === 0) st2.avgCost = 0;
        } else {
          const closeQty = Math.min(tr.qty, Math.abs(st2.pos));
          real = tr.side === 'sell' ? (tr.price - st2.avgCost) * closeQty : (st2.avgCost - tr.price) * closeQty;
          st2.realized += real;
          const newPos = st2.pos + signed;
          if (newPos === 0) { st2.pos = 0; st2.avgCost = 0; }
          else if (Math.sign(newPos) === Math.sign(signed) && tr.qty > closeQty) { st2.pos = newPos; st2.avgCost = tr.price; }
          else st2.pos = newPos;
        }
        tr.positionAfter = st2.pos;
        tr.realizedPnl = Math.round(real);
      }
    }
  }

  return {
    id: game.id,
    number: game.number,
    label: game.practice ? `测试版 · 不计分` : `正式第 ${game.scoredNumber || ''} 题`.trim(),
    question: { q: game.question.q, unit: game.question.unit },
    practice: game.practice,
    phase: game.phase,
    round: game.round,
    maxRound: game.maxRound,
    roundSeconds: game.roundSeconds,
    roundRemain,
    elapsed,
    totalSeconds: game.maxRound * game.roundSeconds,
    openingPrice: game.openingPrice,
    lastPrice: game.lastPrice,
    signals,
    book: bookView(game),
    history: game.rounds.map((r) => ({
      round: r.round,
      price: r.closePrice,
      volume: r.volume,
      orders: r.orders,
      tradeCount: r.tradeCount
    })),
    ticks: game.ticks,
    tradeCount: game.trades.length,
    submitted: submittedCount,
    totalParticipants: participants.length,
    submittedNames: [
      ...room.players.map((p) => ({ name: p.name, done: Number.isFinite(stateOf(game, p.id).estimate), bot: false })),
      ...BOTS.filter((b) => botEnabled(room, b.id)).map((b) => ({ name: b.name, done: Number.isFinite(stateOf(game, b.id).estimate), bot: true }))
    ],
    me: st ? {
      estimate: st.estimate,
      position: st.pos,
      avgCost: st.pos === 0 ? 0 : Math.round(st.avgCost),
      realized: Math.round(st.realized),
      pnl: pnlNow,
      availableBuy: available(game, viewerId, 'buy'),
      availableSell: available(game, viewerId, 'sell'),
      orders: myOrders,
      trades: game.trades.filter((t) => t.buyerId === viewerId || t.sellerId === viewerId).map((t) => {
        const isBuyer = t.buyerId === viewerId;
        return {
          id: t.id,
          round: t.round,
          at: t.at,
          side: isBuyer ? 'buy' : 'sell',
          price: t.price,
          qty: t.qty,
          counterparty: playerName(room, isBuyer ? t.sellerId : t.buyerId),
          program: BOT_IDS.includes(isBuyer ? t.sellerId : t.buyerId),
          positionAfter: isBuyer ? t.buyerPos : t.sellerPos,
          realizedPnl: isBuyer ? t.buyerRealized : t.sellerRealized
        };
      }),
      estimateLocked: game.phase !== 'estimate'
    } : null,
    review,
    resolution: game.phase === 'settled' ? game.resolution : null,
    notice: game.notice || null,
    ranking: game.phase === 'settled' ? game.ranking : null
  };
}

function standingsView(room) {
  const scored = room.games.filter((g) => g.phase === 'settled' && !g.practice);
  const rows = room.players.map((p) => {
    const results = scored.map((g) => {
      const r = (g.ranking || []).find((x) => x.id === p.id);
      return { number: g.number, rank: r ? r.rank : null, points: r ? r.points : 0 };
    });
    const points = results.reduce((s, r) => s + r.points, 0);
    const wins = results.filter((r) => r.rank === 1).length;
    const seconds = results.filter((r) => r.rank === 2).length;
    return { id: p.id, name: p.name, points, wins, seconds, results, rank: 0 };
  });
  rows.sort((a, b) => b.points - a.points || b.wins - a.wins || b.seconds - a.seconds);
  let lastPoints = null; let lastRank = 0;
  rows.forEach((r, i) => {
    if (lastPoints !== null && r.points === lastPoints) r.rank = lastRank;
    else { r.rank = i + 1; lastRank = r.rank; lastPoints = r.points; }
  });
  return { rows, scoredCount: scored.length };
}

function snapshot(room, token) {
  const isHost = !!token && token === room.hostKey;
  const me = isHost ? null : findPlayer(room, token);
  const game = room.currentIndex >= 0 ? room.games[room.currentIndex] : null;
  return {
    t: 'state',
    serverNow: now(),
    code: room.code,
    role: isHost ? 'host' : (me ? 'player' : 'guest'),
    me: me ? { id: me.id, name: me.name, token: me.token } : null,
    roundSeconds: room.roundSeconds,
    players: room.players.map((p) => ({ id: p.id, name: p.name, online: p.online })),
    playersOnline: room.players.filter((p) => p.online).length,
    gameCount: room.games.length,
    currentIndex: room.currentIndex,
    game: game ? gameView(room, game, me ? me.id : null) : null,
    standings: standingsView(room),
    bank: isHost ? BANK.map((q, i) => ({ index: i, id: q.id, q: q.q, unit: q.unit, answer: q.answer, practice: !!q.practice, rounds: q.signals.length })) : undefined,
    bots: isHost ? BOTS.map((b) => ({ id: b.id, name: b.name, kind: b.kind, desc: b.desc, enabled: botEnabled(room, b.id) })) : undefined,
    queue: isHost ? room.queue : undefined,
    allGames: isHost ? room.games.map((g, i) => ({
      index: i, number: g.number, q: g.question.q, phase: g.phase, practice: g.practice
    })) : undefined
  };
}

/* ------------------------------- SSE 广播 ------------------------------- */

const clients = new Set();   // {id, res, roomCode, token}

function sseWrite(client, obj) {
  try {
    client.res.write(`data: ${JSON.stringify(obj)}\n\n`);
  } catch (e) { /* 连接已断 */ }
}

function broadcastState(room) {
  for (const c of clients) {
    if (c.roomCode !== room.code) continue;
    sseWrite(c, snapshot(room, c.token));
  }
}

function broadcastNotice(room, notice) {
  for (const c of clients) {
    if (c.roomCode !== room.code) continue;
    sseWrite(c, { t: 'notice', text: notice.text, at: notice.at, seq: notice.seq });
  }
}

function broadcastClock(room) {
  const game = room.currentIndex >= 0 ? room.games[room.currentIndex] : null;
  if (!game || game.phase !== 'trading') return;
  const nowTs = now();
  for (const c of clients) {
    if (c.roomCode !== room.code) continue;
    sseWrite(c, {
      t: 'clock',
      round: game.round,
      remain: Math.max(0, Math.round((game.roundEndsAt - nowTs) / 1000)),
      elapsed: Math.max(0, Math.round((nowTs - game.openedAt) / 1000)),
      lastPrice: game.lastPrice
    });
  }
}

/* ------------------------------- 主循环 ------------------------------- */

setInterval(() => {
  for (const room of rooms.values()) {
    const game = room.currentIndex >= 0 ? room.games[room.currentIndex] : null;
    if (!game || game.phase !== 'trading') continue;
    const nowTs = now();

    if (nowTs >= game.roundEndsAt) {
      if (game.round < game.maxRound) {
        closeRound(game);
        startRound(room, game, game.round + 1);
        broadcastState(room);
      } else {
        closeRound(game);
        game.phase = 'closed';
        game.book.orders = [];
        game.closedAt = nowTs;
        broadcastState(room);
      }
      continue;
    }

    // 交易机器人：做市 / 动量 / 均值回归 / 噪声
    if (runBots(room, game)) {
      broadcastState(room);
    } else if (nowTs - (game.lastTickAt || 0) > 2500) {
      pushTick(game, game.lastPrice);
      game.lastTickAt = nowTs;
    } else {
      broadcastClock(room);
    }
  }
}, 1000);

/* ------------------------------- HTTP 路由 ------------------------------- */

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon'
};

function serveStatic(req, res, pathname) {
  let filePath = path.join(PUBLIC_DIR, pathname === '/' ? 'index.html' : pathname);
  if (!filePath.startsWith(PUBLIC_DIR)) { res.writeHead(403); return res.end('Forbidden'); }
  fs.readFile(filePath, (err, buf) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      return res.end('404 Not Found');
    }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(filePath)] || 'application/octet-stream', 'Cache-Control': 'no-cache' });
    res.end(buf);
  });
}

function buildExport(room) {
  const scored = room.games.filter((g) => g.phase === 'settled' && !g.practice);
  const label = room.currentIndex >= 0 ? room.games[room.currentIndex].label : '';
  return {
    roomCode: room.code,
    amountUnit: '成交价、答案及盈亏为整数分，显示时除以 100；比赛积分直接读取 points，不除以 100。',
    gameNumber: room.currentIndex + 1,
    practice: false,
    label,
    scoredGameCount: scored.length,
    finalized: false,
    rosterLocked: true,
    games: room.games.map((g) => ({
      number: g.number,
      question: g.question.q,
      scenarioId: g.questionId,
      practice: g.practice,
      unit: g.question.unit,
      openingPrice: g.openingPrice,
      settlementPrice: g.phase === 'settled' ? cents(g.question.answer) : null,
      ranking: (g.ranking || []).map((r) => ({ id: r.id, name: r.name, pnl: r.pnl, rank: r.rank, points: r.points })),
      notice: g.notice || null,
      reports: g.reports || {},
      review: {
        throughRound: g.phase === 'settled' ? g.maxRound : Math.max(0, g.round - 1),
        players: [...room.players.map((p) => p.id), ...BOT_IDS.filter((bid) => botEnabled(room, bid)
          || g.trades.some((t) => t.buyerId === bid || t.sellerId === bid))].map((pid) => ({
          id: pid,
          name: playerName(room, pid),
          bot: BOT_IDS.includes(pid),
          trades: g.trades.filter((t) => t.buyerId === pid || t.sellerId === pid).map((t) => {
            const isBuyer = t.buyerId === pid;
            return {
              id: t.id,
              round: t.round,
              at: t.at,
              side: isBuyer ? 'buy' : 'sell',
              price: t.price,
              qty: t.qty,
              counterparty: playerName(room, isBuyer ? t.sellerId : t.buyerId),
              counterpartyId: isBuyer ? t.sellerId : t.buyerId,
              program: BOT_IDS.includes(isBuyer ? t.sellerId : t.buyerId),
              positionAfter: t[isBuyer ? 'buyerPos' : 'sellerPos'],
              realizedPnl: t[isBuyer ? 'buyerRealized' : 'sellerRealized']
            };
          })
        }))
      },
      signals: g.question.signals.slice(0, g.round).map((s, i) => ({
        title: s.title, text: s.text, source: s.source || '', sourceName: s.sourceName || '', round: i + 1
      })),
      history: g.rounds.map((r) => ({ round: r.round, price: r.closePrice, volume: r.volume, orders: r.orders, at: null, noTrade: r.volume === 0 })),
      resolution: g.resolution,
      scoredNumber: g.scoredNumber,
      label: g.label
    })),
    standings: standingsView(room).rows.map((r) => ({
      id: r.id, name: r.name, points: r.points, wins: r.wins, seconds: r.seconds, results: r.results, rank: r.rank
    }))
  };
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const pathname = decodeURIComponent(url.pathname);

  if (req.method === 'OPTIONS') return sendJson(res, 204, {});

  try {
    /* --- 静态资源 --- */
    if (!pathname.startsWith('/api/')) return serveStatic(req, res, pathname);

    /* --- 新建房间 --- */
    if (pathname === '/api/create' && req.method === 'POST') {
      const body = await readBody(req);
      const code = String(body.code || '').trim() || ensureCode();
      if (rooms.has(code)) return sendJson(res, 409, { error: '房间号已被占用' });
      const room = makeRoom(code);
      rooms.set(code, room);
      scheduleSave();
      return sendJson(res, 200, { code, hostKey: room.hostKey });
    }

    /* --- 房间概览 --- */
    if (pathname === '/api/rooms') {
      const list = [...rooms.values()].map((r) => ({
        code: r.code,
        players: r.players.length,
        online: r.players.filter((p) => p.online).length,
        phase: r.currentIndex >= 0 ? r.games[r.currentIndex].phase : 'idle',
        question: r.currentIndex >= 0 ? r.games[r.currentIndex].question.q : null
      }));
      return sendJson(res, 200, { rooms: list });
    }

    /* --- 主持人密钥校验 --- */
    if (pathname === '/api/host') {
      const room = getRoom(url.searchParams.get('code'));
      if (!room) return sendJson(res, 404, { error: '房间不存在' });
      if (url.searchParams.get('key') !== room.hostKey) return sendJson(res, 403, { error: '主持人密钥不正确' });
      return sendJson(res, 200, {
        code: room.code,
        gameCount: room.games.length,
        players: room.players.length,
        roundSeconds: room.roundSeconds
      });
    }

    /* --- 房间入口校验 --- */
    if (pathname === '/api/room') {
      const room = getRoom(url.searchParams.get('code'));
      if (!room) return sendJson(res, 404, { error: '房间不存在，请核对房间号' });
      const g = room.currentIndex >= 0 ? room.games[room.currentIndex] : null;
      return sendJson(res, 200, {
        code: room.code,
        players: room.players.length,
        online: room.players.filter((p) => p.online).length,
        phase: g ? g.phase : 'idle',
        question: g ? g.question.q : null,
        roundSeconds: room.roundSeconds
      });
    }

    /* --- 加入 / 恢复身份 --- */
    if (pathname === '/api/join' && req.method === 'POST') {
      const body = await readBody(req);
      const room = getRoom(body.code);
      if (!room) return sendJson(res, 404, { error: '房间不存在' });
      const name = String(body.name || '').trim().slice(0, 16);
      if (!name) return sendJson(res, 400, { error: '请输入昵称' });

      if (body.token) {
        const exist = room.players.find((p) => p.token === body.token);
        if (exist) {
          exist.online = true;
          exist.lastSeen = now();
          if (name && name !== exist.name) exist.name = name;
          scheduleSave(); broadcastState(room);
          return sendJson(res, 200, { playerId: exist.id, token: exist.token, name: exist.name, resumed: true });
        }
      }

      const dup = room.players.find((p) => p.name === name);
      if (dup) return sendJson(res, 409, { error: '该昵称已被占用' });

      const player = { id: rid(8), token: rid(16), name, joinedAt: now(), online: true, lastSeen: now() };
      room.players.push(player);
      // 让新玩家在当前局也有状态
      if (room.currentIndex >= 0) stateOf(room.games[room.currentIndex], player.id);
      scheduleSave(); broadcastState(room);
      return sendJson(res, 200, { playerId: player.id, token: player.token, name: player.name });
    }

    /* --- SSE --- */
    if (pathname === '/api/stream') {
      const room = getRoom(url.searchParams.get('code'));
      if (!room) { res.writeHead(404); return res.end('room not found'); }
      const token = url.searchParams.get('token') || '';
      const player = findPlayer(room, token) || (token === room.hostKey ? { id: 'host' } : null);
      if (player && player.id !== 'host') { player.online = true; player.lastSeen = now(); broadcastState(room); }

      res.writeHead(200, {
        'Content-Type': 'text/event-stream; charset=utf-8',
        'Cache-Control': 'no-cache, no-transform',
        Connection: 'keep-alive',
        'X-Accel-Buffering': 'no'
      });
      res.write(': connected\n\n');

      const client = { id: rid(4), res, roomCode: room.code, token };
      clients.add(client);
      sseWrite(client, snapshot(room, token));

      const hb = setInterval(() => { try { res.write(': ping\n\n'); } catch (e) {} }, 20000);
      req.on('close', () => {
        clearInterval(hb);
        clients.delete(client);
        if (player && player.id !== 'host') {
          player.online = false;
          player.lastSeen = now();
          broadcastState(room);
        }
      });
      return;
    }

    /* --- 行为 --- */
    if (pathname === '/api/act' && req.method === 'POST') {
      const body = await readBody(req);
      const room = getRoom(body.code);
      if (!room) return sendJson(res, 404, { error: '房间不存在' });
      const token = String(body.token || '');
      const isHost = token === room.hostKey;
      const player = findPlayer(room, token);
      if (!isHost && !player) return sendJson(res, 403, { error: '身份无效' });
      const game = room.currentIndex >= 0 ? room.games[room.currentIndex] : null;

      switch (body.action) {
        /* ---------- 播报与复盘 ---------- */
        case 'announce': {
          if (!isHost) throw new Error('只有主持人可以播报');
          if (!game) throw new Error('还没有进行中的题目');
          const text = String(body.text || '').slice(0, 3000);
          if (!text) throw new Error('播报内容为空');
          game.notice = { text, at: now(), seq: ((game.notice && game.notice.seq) || 0) + 1 };
          broadcastNotice(room, game.notice);
          broadcastState(room); scheduleSave();
          return sendJson(res, 200, { ok: true, seq: game.notice.seq });
        }
        case 'report': {
          if (!player) throw new Error('只有选手可以提交复盘');
          if (!game) throw new Error('还没有进行中的题目');
          const text = String(body.text || '');
          if (text.length < 10) throw new Error('复盘太短');
          if (text.length > 30000) throw new Error('复盘超过 30000 字');
          game.reports = game.reports || {};
          game.reports[player.id] = { name: player.name, text, at: now() };
          scheduleSave(); broadcastState(room);
          return sendJson(res, 200, { ok: true, length: text.length });
        }

        /* ---------- 玩家 ---------- */
        case 'estimate': {
          if (!game || game.phase !== 'estimate') throw new Error('当前不在估价阶段');
          const v = Number(body.value);
          if (!Number.isFinite(v) || v < 0) throw new Error('估价无效');
          const st = stateOf(game, player.id);
          st.estimate = cents(v);
          st.estimateAt = now();
          broadcastState(room); scheduleSave();
          return sendJson(res, 200, { ok: true });
        }

        case 'order': {
          if (!game || game.phase !== 'trading') throw new Error('当前不可交易');
          const side = body.side === 'sell' ? 'sell' : 'buy';
          const order = placeOrder(room, game, player.id, side, cents(body.price), Number(body.qty));
          broadcastState(room); scheduleSave();
          return sendJson(res, 200, { ok: true, orderId: order.id });
        }

        case 'cancel': {
          if (!game) throw new Error('无进行中的题目');
          const oid = Number(body.orderId);
          game.book.orders = game.book.orders.filter((o) => !(o.playerId === player.id && o.id === oid));
          broadcastState(room); scheduleSave();
          return sendJson(res, 200, { ok: true });
        }

        case 'cancelAll': {
          if (!game) throw new Error('无进行中的题目');
          game.book.orders = game.book.orders.filter((o) => o.playerId !== player.id);
          broadcastState(room); scheduleSave();
          return sendJson(res, 200, { ok: true });
        }

        case 'rename': {
          const name = String(body.name || '').trim().slice(0, 16);
          if (!name) throw new Error('昵称不能为空');
          if (room.players.some((p) => p.name === name && p.id !== player.id)) throw new Error('昵称已占用');
          player.name = name;
          broadcastState(room); scheduleSave();
          return sendJson(res, 200, { ok: true });
        }

        /* ---------- 主持人 ---------- */
        default: break;
      }

      if (!isHost) return sendJson(res, 403, { error: '需要主持人权限' });

      switch (body.action) {
        case 'setRoundSeconds': {
          const s = Math.max(20, Math.min(300, Number(body.seconds) || DEFAULT_ROUND_SECONDS));
          room.roundSeconds = s;
          if (game && game.phase === 'trading') game.roundSeconds = s;
          broadcastState(room); scheduleSave();
          return sendJson(res, 200, { ok: true, roundSeconds: s });
        }

        case 'addQuestion': {
          const idx = Number(body.index);
          const q = BANK[idx];
          if (!q) throw new Error('题目不存在');
          const number = room.games.length + 1;
          const g = createGame(room, q, number);
          seedBotEstimates(room, g);
          g.scoredNumber = q.practice ? 0 : (room.games.filter((x) => !x.practice && x.phase === 'settled').length + 1);
          room.games.push(g);
          room.currentIndex = room.games.length - 1;
          broadcastState(room); scheduleSave();
          return sendJson(res, 200, { ok: true, index: room.currentIndex });
        }

        case 'open': {
          if (!game) throw new Error('请先选题');
          if (game.phase !== 'estimate') throw new Error('当前状态不可开盘');
          openMarket(room, game);
          broadcastState(room); scheduleSave();
          return sendJson(res, 200, { ok: true, openingPrice: game.openingPrice });
        }

        case 'nextRound': {
          if (!game || game.phase !== 'trading') throw new Error('当前不可推进轮次');
          if (game.round >= game.maxRound) throw new Error('已是最后一轮，请直接结算');
          closeRound(game);
          startRound(room, game, game.round + 1);
          broadcastState(room); scheduleSave();
          return sendJson(res, 200, { ok: true });
        }

        case 'closeTrading': {
          if (!game || game.phase !== 'trading') throw new Error('当前不可停牌');
          closeRound(game);
          game.phase = 'closed';
          game.book.orders = [];
          game.closedAt = now();
          broadcastState(room); scheduleSave();
          return sendJson(res, 200, { ok: true });
        }

        case 'settle': {
          if (!game) throw new Error('请先选题');
          if (game.phase === 'settled') throw new Error('已结算');
          if (game.phase === 'estimate') throw new Error('尚未开盘，无法结算');
          settleGame(room, game);
          broadcastState(room); scheduleSave();
          return sendJson(res, 200, { ok: true });
        }

        case 'kick': {
          room.players = room.players.filter((p) => p.id !== body.playerId);
          broadcastState(room); scheduleSave();
          return sendJson(res, 200, { ok: true });
        }

        case 'toggleBot': {
          const id = String(body.botId || '');
          if (!BOT_IDS.includes(id)) throw new Error('机器人不存在');
          if (!room.bots) room.bots = { ...DEFAULT_BOTS };
          room.bots[id] = !!body.enabled;
          if (!room.bots[id] && game) {
            game.book.orders = game.book.orders.filter((o) => o.playerId !== id);
          }
          if (room.bots[id] && game && game.phase === 'estimate') seedBotEstimates(room, game);
          if (room.bots[id] && game && game.phase === 'trading' && id === 'bot:liq') botMarketMake(game);
          broadcastState(room); scheduleSave();
          return sendJson(res, 200, { ok: true, bots: room.bots });
        }

        case 'resetRoom': {
          room.games = [];
          room.currentIndex = -1;
          broadcastState(room); scheduleSave();
          return sendJson(res, 200, { ok: true });
        }

        case 'resetScores': {
          room.games = room.games.filter((g) => g.phase !== 'settled');
          room.players.forEach((p) => { p.points = 0; });
          if (room.games.length === 0) room.currentIndex = -1;
          broadcastState(room); scheduleSave();
          return sendJson(res, 200, { ok: true });
        }

        default:
          return sendJson(res, 400, { error: '未知操作' });
      }
    }

    /* --- 导出复盘 --- */
    if (pathname === '/api/export') {
      const room = getRoom(url.searchParams.get('code'));
      if (!room) return sendJson(res, 404, { error: '房间不存在' });
      if (url.searchParams.get('key') !== room.hostKey) return sendJson(res, 403, { error: '需要主持人权限' });
      const payload = buildExport(room);
      const filename = `比赛成绩与全员复盘-${room.code}.json`;
      res.writeHead(200, {
        'Content-Type': 'application/json; charset=utf-8',
        'Content-Disposition': `attachment; filename*=UTF-8''${encodeURIComponent(filename)}`
      });
      return res.end(JSON.stringify(payload, null, 2));
    }

    /* --- 健康检查 --- */
    if (pathname === '/api/health') {
      return sendJson(res, 200, { ok: true, rooms: rooms.size, uptime: process.uptime() });
    }

    return sendJson(res, 404, { error: '接口不存在' });
  } catch (e) {
    return sendJson(res, 400, { error: e.message || '请求失败' });
  }
});

/* ------------------------------- 启动 ------------------------------- */

function lanAddresses() {
  const out = [];
  const ifs = os.networkInterfaces();
  for (const name of Object.keys(ifs)) {
    for (const ni of ifs[name] || []) {
      if (ni.family === 'IPv4' && !ni.internal) out.push(ni.address);
    }
  }
  return out;
}

loadRooms();

server.listen(PORT, '0.0.0.0', () => {
  const lan = lanAddresses();
  console.log('');
  console.log('  临渊量化 · 交易实验室');
  console.log('  ────────────────────────────────');
  console.log(`  本机访问   http://localhost:${PORT}`);
  lan.forEach((ip) => console.log(`  局域网     http://${ip}:${PORT}`));
  console.log(`  数据文件   ${ROOMS_FILE}`);
  console.log('');
});
