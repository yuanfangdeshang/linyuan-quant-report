// 555 房间常驻交易终端（WebSocket delta-v1）
// 默认只监控；交易开关在 config555.json 中热更新
const fs = require('fs');
const CODE = '517435';
const TOKEN = '5e027ab4b2bc604a4403b4f040af58b5880bed48405abf37';
const URL = 'wss://connect-tribal-around-guided.trycloudflare.com/ws';
const STATE_FILE = 'state555.json';
const LOG_FILE = 'events555.log';
const CFG_FILE = 'config555.json';

let state = null, ws = null, revision = 0, awaiting = false;
let lastDecision = 0, lastPhase = null, lastRound = null, lastSigCount = -1;

function log(line) {
  try { fs.appendFileSync(LOG_FILE, `[${new Date().toISOString()}] ${line}\n`); } catch {}
}
function cfg() {
  try { return JSON.parse(fs.readFileSync(CFG_FILE, 'utf8')); } catch { return {}; }
}
function save() {
  try { fs.writeFileSync(STATE_FILE + '.tmp', JSON.stringify(state, null, 2)); fs.renameSync(STATE_FILE + '.tmp', STATE_FILE); } catch {}
}
function applyPatch(changes) {
  for (const [path, value] of changes) {
    if (!path.length) { state = value; continue; }
    if (path.some(k => ['__proto__','prototype','constructor'].includes(k))) continue;
    let t = state;
    for (const k of path.slice(0, -1)) { if (!t || typeof t !== 'object') return; t = t[k]; }
    if (!t || typeof t !== 'object') return;
    const k = path.at(-1);
    if (value === undefined) delete t[k]; else t[k] = value;
  }
}
function send(msg) {
  if (ws && ws.readyState === WebSocket.OPEN) { ws.send(JSON.stringify(msg)); return true; }
  return false;
}
let actionSeq = 0;
function act(action, payload, reason = '') {
  const id = `a${Date.now().toString(36)}${(actionSeq++).toString(36)}`;
  const round = state?.round ?? 1;
  const gameNumber = state?.competition?.gameNumber;
  const full = { type:'action', id, action, payload: { ...payload, round, ...(gameNumber ? {gameNumber} : {}) } };
  if (send(full)) { log(`ACT ${JSON.stringify(full.payload)} || ${reason}`); return true; }
  return false;
}

function onState(m) {
  state = m.state; revision = m.revision || 0; awaiting = false;
  save();
  const s = state;
  if (s.phase !== lastPhase || s.round !== lastRound) {
    log(`PHASE ${lastPhase}->${s.phase} round=${s.round} open=${s.openingPrice} price=${s.price} deadline=${s.deadline}`);
    lastPhase = s.phase; lastRound = s.round; lastSigCount = -1;
  }
  const sigs = s.signals || [];
  if (sigs.length !== lastSigCount) {
    log(`SIGNALS n=${sigs.length}`);
    for (const g of sigs) log(`  SIG r${g.round} ${g.title}: ${String(g.text||'').slice(0,180)}`);
    lastSigCount = sigs.length;
  }
}

async function decode(ev) {
  if (typeof ev.data === 'string') return ev.data;
  try { return await new Response(new Blob([ev.data]).stream().pipeThrough(new DecompressionStream('gzip'))).text(); }
  catch { return null; }
}

function connect() {
  ws = new WebSocket(URL);
  ws.onopen = () => {
    log('OPEN');
    send({ type:'hello', protocol:'delta-v1', encoding:null, code:CODE, token:TOKEN });
  };
  ws.onmessage = async (ev) => {
    const text = await decode(ev); if (!text) return;
    let m; try { m = JSON.parse(text); } catch { return; }
    if (m.type === 'state') onState(m);
    else if (m.type === 'patch') {
      if (awaiting) return;
      if (!state || m.base !== revision) { awaiting = true; send({type:'resync'}); return; }
      try { applyPatch(m.changes); revision = m.revision; save(); }
      catch { awaiting = true; send({type:'resync'}); }
    } else if (m.type === 'error') log('ERR ' + JSON.stringify(m).slice(0,400));
    else if (m.type === 'ack') { /* confirmed */ }
  };
  ws.onerror = e => log('WS-ERR ' + (e.message || String(e)));
  ws.onclose = e => { log(`CLOSE ${e.code} ${e.reason||''}`); setTimeout(connect, 1500); };
}

// ---------- 决策 ----------
function decide() {
  const c = cfg();
  if (!c.enabled || !state || state.phase !== 'trading') return;
  const now = Date.now();
  if (now - lastDecision < (c.cooldown || 1500)) return;
  const s = state;
  const me = s.me || {};
  const fair = c.fair || s.openingPrice || s.price;
  if (!fair || !s.price) return;
  const th = c.threshold || 0.03;
  const dev = (s.price - fair) / fair;
  const ab = me.available?.buyLots || 0, asell = me.available?.sellLots || 0;
  const book = s.book || {};
  const bestAsk = (book.sell && book.sell[0] && book.sell[0].price) || s.bestAsk;
  const bestBid = (book.buy && book.buy[0] && book.buy[0].price) || s.bestBid;
  if (!bestAsk || !bestBid) return;
  const maxOrder = c.maxOrder || 2;
  let side = null, px = null, qty = 0, why = '', kind = 'order';
  // 真人房间盘口极宽（曾见买一4000/卖一10000）：只在对手价本身合理时才吃单，
  // 否则把单挂在自己想要的价格上等待对方来成交（成交价取先挂方 = 对我有利）。
  if (dev <= -th && ab > 0) {
    side = 'buy'; qty = Math.min(maxOrder, ab);
    if (bestAsk <= fair * (1 - th * 0.5)) {
      kind = 'take'; px = Math.round(bestAsk);
      why = `低估 吃卖一${bestAsk} 锚${fair}`;
    } else {
      kind = 'order'; px = Math.min(Math.round(bestAsk - 1), Math.round(fair * (1 - th)));
      why = `低估 挂买${px} 锚${fair} 买一${bestBid}`;
    }
  } else if (dev >= th && asell > 0) {
    side = 'sell'; qty = Math.min(maxOrder, asell);
    if (bestBid >= fair * (1 + th * 0.5)) {
      kind = 'take'; px = Math.round(bestBid);
      why = `高估 砸买一${bestBid} 锚${fair}`;
    } else {
      kind = 'order'; px = Math.max(Math.round(bestBid + 1), Math.round(fair * (1 + th)));
      why = `高估 挂卖${px} 锚${fair} 卖一${bestAsk}`;
    }
  }
  if (side && qty > 0) {
    if (act(kind, { side, price: px, qty }, why)) lastDecision = now;
  }
}

connect();
setInterval(() => { if (ws && ws.readyState === WebSocket.OPEN) send({type:'ping', sent:Date.now()}); }, 4000);
setInterval(() => { try { decide(); } catch(e) { log('DECIDE-ERR ' + e.message); } }, 500);
log('BOOT terminal555 ready');
