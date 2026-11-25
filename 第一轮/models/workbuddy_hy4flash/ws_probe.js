// 临时探针：连接新版交易实验室 WebSocket，dump 全量 state
const fs = require('fs');
const CODE = '517435';
const TOKEN = '5e027ab4b2bc604a4403b4f040af58b5880bed48405abf37';
const URL = 'wss://connect-tribal-around-guided.trycloudflare.com/ws';

const ws = new WebSocket(URL);
let n = 0;
const seen = new Set();

ws.onopen = () => {
  console.log('OPEN');
  ws.send(JSON.stringify({ type: 'hello', protocol: 'delta-v1', encoding: null, code: CODE, token: TOKEN }));
};

ws.onmessage = async (ev) => {
  let text;
  if (typeof ev.data === 'string') text = ev.data;
  else {
    try { text = await new Response(new Blob([ev.data]).stream().pipeThrough(new DecompressionStream('gzip'))).text(); }
    catch (e) { console.log('BINARY-DECODE-FAIL', e.message); return; }
  }
  let m;
  try { m = JSON.parse(text); } catch { console.log('RAW', text.slice(0, 300)); return; }
  n++;
  if (m.type === 'state') {
    fs.writeFileSync('state555.json', JSON.stringify(m.state, null, 2));
    const s = m.state;
    console.log('=== STATE ===');
    console.log('keys:', Object.keys(s).join(','));
    console.log('phase:', s.phase, '| round:', s.round, '| config:', JSON.stringify(s.config));
    console.log('me:', JSON.stringify(s.me || s.players?.find?.(p => p.id === '8fad1a4b9a2987ac') || null).slice(0, 800));
    console.log('top prices:', JSON.stringify({ price: s.price, bestAsk: s.bestAsk, bestBid: s.bestBid, openingPrice: s.openingPrice }).slice(0, 400));
  } else if (m.type === 'patch') {
    if (!seen.has('patch')) { seen.add('patch'); console.log('PATCH sample:', JSON.stringify(m).slice(0, 1000)); }
  } else if (m.type === 'error') {
    console.log('ERROR:', JSON.stringify(m).slice(0, 500));
  } else {
    if (n < 12) console.log('MSG', m.type, JSON.stringify(m).slice(0, 220));
  }
};

ws.onerror = (e) => console.log('WS-ERR', e.message || String(e));
ws.onclose = (e) => console.log('CLOSE', e.code, e.reason);

setTimeout(() => { try { ws.close(); } catch {} setTimeout(() => process.exit(0), 300); }, 14000);
