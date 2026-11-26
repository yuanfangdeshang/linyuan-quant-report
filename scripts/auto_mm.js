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
  const f = 0.55 * avg + 0.20 * prior + 0.25 * last + clamp(momentum * 0.15, -6, 6);
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

  let buyQty = pos >= MAX_POS ? 0 : 1;
  let sellQty = pos <= -MAX_POS ? 0 : 1;
  if (pos >= target + 2) buyQty = 0;
  if (pos <= target - 2) sellQty = 0;
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
    send({ type: 'hello', protocol: 'delta-v1', encoding: 'gzip-v1', code: s.code, token: s.token });
    resyncTimer = setInterval(() => send({ type: 'resync' }), 2500);
    console.log('[ws] connected');
  };
  ws.onmessage = async e => {
    try {
      const m = JSON.parse(await decode(e));
      if (m.type === 'state') onState(m.state);
    } catch (err) { console.error('[ws] decode', err.message); }
  };
  ws.onclose = () => { clearInterval(resyncTimer); if (!closed) setTimeout(connect, 1000); };
  ws.onerror = () => ws.close();
}
connect();
process.on('SIGINT', () => { closed = true; clearInterval(resyncTimer); try { ws?.close(); } catch {} process.exit(0); });
