#!/usr/bin/env node
const fs = require('fs');
const sessionPath = process.env.LQ_SESSION || '/tmp/lq_session.json';
const s = JSON.parse(fs.readFileSync(sessionPath, 'utf8'));
if (!s.ws || !s.code || !s.token) throw new Error('session must contain ws, code, token');

let ws, state, closed = false, resyncTimer, quoteTimer, seq = 0;
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
function best(book, side) {
  const rows = (book && book[side]) || [];
  return rows.length ? Math.min(...rows.map(r => r.price)) : null;
}
function bestBid(book) {
  const rows = (book && book.buy) || [];
  return rows.length ? Math.max(...rows.map(r => r.price)) : null;
}
function quotes(st) {
  const pos = Number(st.me?.position || 0);
  const fair = Math.round(st.average || st.price || st.openingPrice || 0);
  const bb = bestBid(st.book), ba = best(st.book, 'sell');
  let bid = fair - 4, ask = fair + 4;
  if (bb != null && bb >= bid && bb < fair) bid = bb + 1;
  if (ba != null && ba <= ask && ba > fair) ask = ba - 1;
  if (pos > 2) { bid -= 1; ask -= 1; }
  if (pos < -2) { bid += 1; ask += 1; }
  bid = Math.min(bid, fair - 1);
  ask = Math.max(ask, fair + 1);
  if (ask <= bid) ask = bid + 2;
  const buyQty = pos >= 8 ? 0 : 1;
  const sellQty = pos <= -8 ? 0 : 1;
  return { fair, bid, ask, buyQty, sellQty, pos };
}
function ownKey(st) {
  if (st.phase !== 'trading') return 'not-trading';
  const q = quotes(st);
  return [st.round, q.fair, q.bid, q.ask, q.buyQty, q.sellQty, st.me?.position || 0].join('|');
}
function place(st) {
  const q = quotes(st);
  const key = ownKey(st);
  if (key === lastQuoteKey) return;
  lastQuoteKey = key;
  const now = Date.now();
  if (now - lastCancelAt > 700) {
    action('cancelAll');
    lastCancelAt = now;
  }
  if (q.buyQty) action('order', { side: 'buy', price: q.bid, qty: q.buyQty });
  if (q.sellQty) action('order', { side: 'sell', price: q.ask, qty: q.sellQty });
  console.log(`[quote] r${st.round} fair=${q.fair} bid=${q.bid} ask=${q.ask} pos=${q.pos} pnl=${st.me?.pnl ?? 0}`);
}
function onState(st) {
  state = st;
  if (st.phase === 'trading') place(st);
  else {
    lastQuoteKey = 'not-trading';
    if (st.phase === 'intermission' || st.phase === 'finished' || st.phase === 'paused') {
      action('cancelAll');
    }
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
  ws.onclose = () => {
    clearInterval(resyncTimer);
    if (!closed) setTimeout(connect, 1000);
  };
  ws.onerror = () => ws.close();
}
connect();
process.on('SIGINT', () => { closed = true; clearInterval(resyncTimer); try { ws?.close(); } catch {} process.exit(0); });
