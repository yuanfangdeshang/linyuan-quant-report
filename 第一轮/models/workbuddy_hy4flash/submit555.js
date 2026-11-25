// 提交估价：上海居民委员会数量（单位：个），投 4200 → 420000 分
const CODE = '517435';
const TOKEN = '5e027ab4b2bc604a4403b4f040af58b5880bed48405abf37';
const ws = new WebSocket('wss://connect-tribal-around-guided.trycloudflare.com/ws');
let done = false;

ws.onopen = () => {
  console.log('OPEN, sending hello');
  ws.send(JSON.stringify({ type: 'hello', protocol: 'delta-v1', encoding: null, code: CODE, token: TOKEN }));
  setTimeout(() => {
    const msg = {
      type: 'action', id: 'est-' + Date.now(), action: 'estimate',
      payload: { price: 420000, round: 1, gameNumber: 3 }
    };
    ws.send(JSON.stringify(msg));
    console.log('SENT', JSON.stringify(msg));
  }, 1200);
};

ws.onmessage = (ev) => {
  if (typeof ev.data !== 'string') return;
  const m = JSON.parse(ev.data);
  if (m.type === 'state') {
    console.log('STATE phase=', m.state.phase, 'mine=', JSON.stringify(m.state.opening?.mine), 'count=', m.state.opening?.count, '/', m.state.opening?.required);
  } else if (['ack', 'error', 'action', 'result'].includes(m.type)) {
    console.log('RESP', JSON.stringify(m).slice(0, 500));
    if (m.type === 'ack' || (m.action === 'estimate')) done = true;
  } else if (m.type === 'patch') {
    const s = JSON.stringify(m.changes || []);
    if (s.includes('mine') || s.includes('submitted')) console.log('PATCH', s.slice(0, 300));
  }
};
ws.onerror = e => console.log('ERR', e.message || String(e));
setTimeout(() => { try { ws.close(); } catch {} setTimeout(() => process.exit(0), 200); }, 7000);
