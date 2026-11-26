#!/usr/bin/env node
const fs = require('fs');
const sessionPath = process.env.LQ_SESSION || '/tmp/lq_session.json';
const s = JSON.parse(fs.readFileSync(sessionPath, 'utf8'));
if (!s.ws || !s.code || !s.token) throw new Error('session must contain ws, code, token');

const MAX_POS = 6;
const MAX_TARGET = 4;
const HALF = 3;
const WIDE = 30;

let ws, state, closed = false, resyncTimer, seq = 0;
let lastQuoteKey = '';
let lastCancelAt = 0;
let revision = 0;
let awaitingSnapshot = false;

function applyPatch(obj, changes) {
  let out = obj;
  for (const [path, value] of changes) {
    if (!path.length) { out = value; continue; }
    if (path.some(k => ['__proto__','prototype','constructor'].includes(k))) throw Error('bad patch');
    out = Array.isArray(out) ? [...out] : { ...out };
    let t = out;
    for (const k of path.slice(0, -1)) {
      t[k] = Array.isArray(t[k]) ? [...t[k]] : { ...t[k] };
      t = t[k];
    }
    const k = path[path.length - 1];
    if (value === undefined) delete t[k]; else t[k] = value;
  }
  return out;
}

function send(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
}
function action(name, payload = {}) {
  const id = 'mm-' + Date.now().toString(36) + '-' + (++seq);
  send({
    type: 'action', id, action: name,
    payload: { ...payload, round: state?.round, ...(state?.competition ? { gameNumber: state.competition.gameNumber } : {}) }
  });
}
async function decode(event) {
  if (typeof event.data === 'string') return event.data;
  const blob = event.data instanceof Blob ? event.data : new Blob([event.data]);
  return await new Response(blob.stream().pipeThrough(new DecompressionStream('gzip'))).text();
}
function bestBid(book) {
  const rows = (book && book.buy) || [];
  return rows.length ? Math.max(...rows.map(r => r.price)) : null;
}
function bestAsk(book) {
  const rows = (book && book.sell) || [];
  return rows.length ? Math.min(...rows.map(r => r.price)) : null;
}
function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

// Settlement proxy: blend of settled average, opening prior and current price,
// plus a small momentum term. It is deliberately transparent, not a black box.
function forecast(st) {
  const last = Number(st.price || st.openingPrice || 0);
  const prior = Number(st.openingPrice || last);
  const avg = Number(st.average || prior);
  const hist = (st.history || []).map(h => Number(h.price)).filter(Number.isFinite);
  const prev = hist.length ? hist[hist.length - 1] : prior;
  const momentum = last - prev;
  // 已结算均价是均价博弈的主锚；最新价只给低权重，避免把一笔异常成交当成趋势。
  const f = 0.70 * avg + 0.20 * prior + 0.10 * last;
  return Math.round(f);
}
function targetFor(st, fair) {
  const last = Number(st.price || st.openingPrice || 0);
  const edge = fair - last;
  return clamp(Math.round(edge / 4), -MAX_TARGET, MAX_TARGET);
}
function quotes(st) {
  const pos = Number(st.me?.position || 0);
  const fair = forecast(st);
  const target = targetFor(st, fair);
  const bb = bestBid(st.book), ba = bestAsk(st.book);
  const gap = bb != null && ba != null ? ba - bb : 0;

  let bid = fair - HALF;
  let ask = fair + HALF;
  if (bb != null) bid = Math.max(bid, bb + 1);
  if (ba != null) ask = Math.min(ask, ba - 1);
  if (pos > target) { ask = Math.min(ask, fair - 1); bid = fair - HALF - 1; }
  if (pos < target) { bid = Math.max(bid, fair + 1); ask = fair + HALF + 1; }
  if (ba != null && bid >= ba) bid = ba - 1;
  if (bb != null && ask <= bb) ask = bb + 1;
  if (ask <= bid) ask = bid + 2;
  const tick = Math.pow(10, 2 - (st.config?.priceDecimals ?? 2));
  bid = Math.max(tick, Math.round(bid / tick) * tick);
  ask = Math.max(bid + tick, Math.round(ask / tick) * tick);

  let buyQty = pos >= MAX_POS ? 0 : 1;
  let sellQty = pos <= -MAX_POS ? 0 : 1;
  if (pos >= target + 2) buyQty = 0;
  if (pos <= target - 2) sellQty = 0;
  // If the market is far from the forecast, take the touch instead of waiting forever.
  const last = Number(st.price || st.openingPrice || 0);
  if (fair < last - 2 * tick && bb != null && pos > target - 1) { sellQty = 1; ask = bb; }
  if (fair > last + 2 * tick && ba != null && pos < target + 1) { buyQty = 1; bid = ba; }
  if (gap > WIDE) { buyQty = 0; sellQty = 0; }
  return { fair, target, bid, ask, buyQty, sellQty, pos, gap };
}
function ownKey(st) {
  if (st.phase !== 'trading') return 'not-trading';
  const q = quotes(st);
  return [st.round, q.fair, q.target, q.bid, q.ask, q.buyQty, q.sellQty, q.pos].join('|');
}
function place(st) {
  const q = quotes(st);
  const key = ownKey(st);
  if (key === lastQuoteKey) return;
  lastQuoteKey = key;
  const now = Date.now();
  if (now - lastCancelAt > 700) { action('cancel-all'); lastCancelAt = now; }
  if (q.buyQty) action('order', { side: 'buy', price: q.bid, qty: q.buyQty });
  if (q.sellQty) action('order', { side: 'sell', price: q.ask, qty: q.sellQty });
  console.log(`[quote] r${st.round} fc=${q.fair} target=${q.target} bid=${q.bid} ask=${q.ask} pos=${q.pos} pnl=${st.me?.pnl ?? 0}`);
}
function onState(st) {
  state = st;
  if (st.phase === 'trading') place(st);
  else {
    lastQuoteKey = 'not-trading';
    if (st.phase === 'intermission' || st.phase === 'finished' || st.phase === 'paused') action('cancel-all');
  }
}
function connect() {
  if (closed) return;
  ws = new WebSocket(s.ws);
  ws.onopen = () => {
    revision = 0; awaitingSnapshot = false;
    send({ type: 'hello', protocol: 'delta-v1', encoding: 'gzip-v1', code: s.code, token: s.token });
    resyncTimer = setInterval(() => send({ type: 'resync' }), 5000);
    console.log('[ws] connected');
  };
  ws.onmessage = async e => {
    try {
      const m = JSON.parse(await decode(e));
      if (m.type === 'state') {
        state = m.state; revision = m.revision || 0; awaitingSnapshot = false;
        onState(state);
      } else if (m.type === 'patch') {
        if (awaitingSnapshot) return;
        if (m.base !== revision) { awaitingSnapshot = true; send({ type: 'resync' }); return; }
        try { state = applyPatch(state, m.changes); revision = m.revision; onState(state); }
        catch { awaitingSnapshot = true; send({ type: 'resync' }); }
      } else if (m.type === 'error') {
        console.error('[server]', m.message);
      }
    } catch (err) { console.error('[ws] decode', err.message); }
  };
  ws.onclose = () => { clearInterval(resyncTimer); if (!closed) setTimeout(connect, 1000); };
  ws.onerror = () => ws.close();
}
connect();
process.on('SIGINT', () => { closed = true; clearInterval(resyncTimer); try { ws?.close(); } catch {} process.exit(0); });
