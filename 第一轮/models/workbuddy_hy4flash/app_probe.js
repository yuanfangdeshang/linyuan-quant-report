import { applyStatePatch } from './state-sync.js';
import { renderFiggie, updateFiggieControls, updateFiggieTimer, downloadFiggie } from './figgie-ui.js';
import { MODES } from './modes.js';
import { renderMarket, updateMarketControls, updateMarketTimer, marketFeedback } from './market-ui.js';
const $ = id => document.getElementById(id);
const money = cents => (cents / 100).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const signed = cents => `${cents > 0 ? '+' : ''}${money(cents)}`;
const esc = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const phaseNames = { lobby: '等待入场', trading: '集合竞价中', intermission: '本轮已结算', paused: '主持人已暂停', finished: '比赛已结束' };
let mode = 'join', session, state, ws, reconnectTimer, connected = false, retry = 0, clockOffset = 0, lastRound = -1, side = 'buy', pending = new Map(), shareMode = 'public', network;
let toastTimer;
let stateRevision=0, awaitingSnapshot=false;
const resourceRequests=new Map();
function requestResource(resource, payload={}) {
  if (!connected || !state) return Promise.reject(Error('连接中断，请恢复连接后重试'));
  const id='resource-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2);
  return new Promise((resolve,reject)=>{
    const timeout=setTimeout(()=>{resourceRequests.delete(id);reject(Error('记录加载超时，请重试'));},15000);
    resourceRequests.set(id,{resolve,reject,timeout});
    ws.send(JSON.stringify({type:'resource',id,resource,...payload}));
  });
}
let lastSeen = Date.now();
function toast(text) { $('toast').textContent = text; $('toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').hidden = true, 4200); }
function storage(key, value) { try { if (value !== undefined) localStorage.setItem(key, value); else return localStorage.getItem(key); } catch {} }
function readSession(code) { try { return JSON.parse(storage(`anxian:${code}`) || 'null'); } catch { return null; } }
function setConnection(text, status) { $('connection').textContent = text; $('connection').className = 'connection ' + status; }
function sendAction(action, payload = {}) {
  if (!connected || !state) { toast('连接中断，正在重连；请等连接恢复再操作'); return; }
  const id = Date.now().toString(36) + '-' + Math.random().toString(36).slice(2);
  const timeout = setTimeout(() => {
    pending.delete(id); updateButtons(); toast('暂未收到确认，请查看“本轮委托”后再操作，避免重复下单');
  }, 15000);
  pending.set(id, { timeout, action, payload });
  ws.send(JSON.stringify({ type: 'action', id, action, payload: { ...payload, round: state.round, ...(state.competition ? { gameNumber: state.competition.gameNumber } : {}) } }));
  updateButtons();
}
function connect() {
  clearTimeout(reconnectTimer);
  if (ws) { ws.onclose = null; ws.close(); }
  connected = false; setConnection('正在连接交易室…', '');
  const current = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws`);
  ws = current;current.binaryType='arraybuffer';
  let incoming=Promise.resolve();
  lastSeen = Date.now();
  stateRevision=0;awaitingSnapshot=false;
  current.onopen = () => current.send(JSON.stringify({ type: 'hello', protocol:'delta-v1', encoding:typeof DecompressionStream==='function'?'gzip-v1':null, code: session.code, token: session.token }));
  current.onmessage = event => {
    if(ws!==current)return;
    lastSeen=Date.now();
    // Binary decompression is asynchronous; preserve WebSocket frame order.
    incoming=incoming.then(async()=>{
    if(ws!==current)return;
    const text=typeof event.data==='string'?event.data:await new Response(new Blob([event.data]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
    if(ws!==current)return;
    const msg = JSON.parse(text);
    if (msg.type === 'resource' || (msg.type === 'error' && resourceRequests.has(msg.id))) {
      const request=resourceRequests.get(msg.id);
      if(request){clearTimeout(request.timeout);resourceRequests.delete(msg.id);msg.type==='error'?request.reject(Error(msg.message)):request.resolve(msg.data);}
    } else if (msg.type === 'patch') {
      if(awaitingSnapshot)return;
      if(!state || msg.base!==stateRevision){awaitingSnapshot=true;current.send(JSON.stringify({type:'resync'}));return;}
      try{state=applyStatePatch(state,msg.changes);stateRevision=msg.revision;clockOffset=msg.serverTime-Date.now();render();}
      catch{awaitingSnapshot=true;current.send(JSON.stringify({type:'resync'}));}
    } else if (msg.type === 'state') {
      stateRevision=msg.revision||0;awaitingSnapshot=false;
      connected = true; retry = 0; state = msg.state; clockOffset = msg.serverTime - Date.now();
      setConnection('已连接 · 实时同步', 'online'); render();
    } else if (msg.type === 'pong') {
      const rtt = Date.now() - msg.sent;
      clockOffset = msg.serverTime - (msg.sent + rtt / 2);
      setConnection(`已连接 · ${rtt} ms`, 'online');
    } else if (msg.type === 'error' || msg.type === 'ack') {
      const request = pending.get(msg.id);
      if (request) { clearTimeout(request.timeout); pending.delete(msg.id); }
      updateButtons();
      if (msg.result?.exportData) downloadFiggie(msg.result.exportData, state.code);
      toast(msg.type === 'error' ? msg.message : msg.result?.message || '操作成功');
      marketFeedback(msg.type === 'error' ? msg.message : msg.result?.message || '操作成功', msg.type === 'ack' ? request : null);
      if (msg.type === 'error' && !state) {
        current.onclose = null; current.close();
        $('app').innerHTML = `<div class="card"><h2>无法恢复房间</h2><p class="help">${esc(msg.message)}</p><a href="/">回到首页，重新加入</a></div>`;
      }
    }
    }).catch(error=>{
      console.error('同步数据读取失败',error);
      if(ws===current)current.close();
    });
  };
  current.onclose = () => {
    if (ws !== current) return;
    for(const r of resourceRequests.values()){clearTimeout(r.timeout);r.reject(Error('连接中断，请恢复后重新加载'));}resourceRequests.clear();
    connected = false; setConnection('连接断开 · 正在重连', 'offline'); updateButtons();
    if ($('connection-notice')) $('connection-notice').hidden = false;
    reconnectTimer = setTimeout(connect, Math.min(10000, 800 * 2 ** Math.min(retry++, 4)));
  };
  current.onerror = () => current.close();
}
function enter(data) {
  session = data; storage(`anxian:${data.code}`, JSON.stringify(data)); storage('anxian:last', data.code);
  history.replaceState(null, '', `?r=${data.code}`);
  $('app').innerHTML = '<div class="card empty">正在进入交易室…</div>';
  connect();
}
function entryMode(next) {
  mode = next;
  $('join-tab').classList.toggle('active', mode === 'join'); $('create-tab').classList.toggle('active', mode === 'create');
  $('join-fields').hidden = mode !== 'join'; $('create-fields').hidden = mode !== 'create'; $('room-code').required = mode === 'join';
  $('entry-submit').innerHTML = mode === 'join' ? '进入交易室 <span>→</span>' : '创建交易室 <span>→</span>';
  $('entry-error').textContent = '';
  refreshMode();
}
$('config-fields').innerHTML = `<div class="form-row"><div><label for="rounds">交易轮数</label><select id="rounds"><option value="12">12 轮 · 完整场</option><option value="3">3 轮 · 快速测试</option><option value="4">4 轮 · 逐步揭晓</option><option value="5">5 轮 · 逐步揭晓</option><option value="6">6 轮 · 练习</option></select></div><div><label for="seconds">每轮时长</label><select id="seconds"><option value="60">60 秒 · 标准</option><option value="15">15 秒 · 快速测试</option><option value="30">30 秒</option><option value="90">90 秒</option></select></div></div><div class="form-row"><div><label for="bots">报价机器人</label><select id="bots"><option value="150">150 个 · 大市场</option><option value="30">30 个</option><option value="10">10 个</option><option value="0">关闭 · 仅真人</option></select></div><div><label for="auto-next">轮次推进</label><select id="auto-next"><option value="yes">自动 · 间隔 8 秒</option><option value="no">主持人手动</option></select></div></div><p class="help">机器人随机报价，不预设涨跌走势。真人单独排名。</p>`;
const genericConfig = document.createElement('div');
genericConfig.id = 'generic-config';
while ($('config-fields').firstChild) genericConfig.append($('config-fields').firstChild);
$('config-fields').append(genericConfig);
const figgieConfig = document.createElement('div');
figgieConfig.id = 'figgie-config';
figgieConfig.hidden = true;
figgieConfig.innerHTML = `<label for="fig-kind">牌局模式</label><select id="fig-kind"><option value="standard">标准局 · 暗牌</option><option value="open">教学局 · 全员明牌</option><option value="learning">教学局 · 暗牌</option></select><div class="form-row"><div><label for="fig-seats">席位数</label><select id="fig-seats"><option value="4">4 人 · 每人 10 张</option><option value="5">5 人 · 每人 8 张</option></select></div><div><label for="fig-seconds">每局时长</label><select id="fig-seconds"><option value="120">2 分钟</option><option value="240">4 分钟</option><option value="1200">20 分钟 · 教学</option><option value="30">30 秒 · 体验</option><option value="15">15 秒 · 测试</option></select></div></div><div class="form-row"><div><label for="fig-rounds">本场局数</label><select id="fig-rounds"><option value="0">不限 · 主持人结束</option><option value="3">3 局</option><option value="6">6 局</option><option value="12">12 局</option></select></div><div><label for="fig-bots">开局空位</label><select id="fig-bots"><option value="yes">自动补机器人</option><option value="no">等齐玩家</option></select></div></div><label for="fig-listed">房间可见范围</label><select id="fig-listed"><option value="no">私人 · 通过房间号邀请</option><option value="yes">公开 · 显示在下方牌桌大厅</option></select><p class="help">每人 350 筹码，4 / 5 人每局各付 50 / 40 筹码。支持观战、局间候补、全场同步复盘。机器人采用本平台独立策略。</p>`;
$('config-fields').append(figgieConfig);
$('fig-kind').onchange = () => { $('fig-seconds').value = $('fig-kind').value === 'standard' ? '120' : '1200'; };
const modeFields = document.createElement('div');
modeFields.innerHTML = '<label for="game-mode">本局玩法</label><select id="game-mode">' + Object.entries(MODES).map(([key, value]) => '<option value="' + key + '">' + value.name + ' · ' + value.tag + '</option>').join('') + '</select><p id="mode-description" class="help"></p><div id="scenario-fields" hidden><label for="scenario">交易内容</label><select id="scenario"><option value="question">主持人出题与公布答案</option><option value="script">预设题库 · 逐轮自动发布</option><option value="cards">自动信息卡 · 直接试玩</option></select><div id="preset-fields" hidden><label for="scenario-id">选择题目</label><select id="scenario-id"><option value="">加载题库中…</option></select><p id="preset-description" class="help"></p></div><div id="question-fields"><label for="question">要交易的问题（全场置顶）</label><textarea id="question" rows="3" maxlength="240" placeholder="例如：这罐糖果一共有多少颗？"></textarea><div class="form-row"><div><label for="unit">答案单位</label><input id="unit" maxlength="30" value="颗 / 份"></div><div><label for="initial-price">初始参考价</label><input id="initial-price" type="number" value="100" min="1" max="100000" step="0.01"></div></div><p id="question-help" class="help">每份标的最终按答案数值兑现。初始现金＝参考价×100，另持有 100 份。首轮新报价范围为参考价 ±20%，请选择合适的量纲；答案须为非负数。</p></div></div>';
$('config-fields').prepend(modeFields);
$('initial-price').parentElement.id='initial-price-field';
$('question-fields').insertAdjacentHTML('beforeend','<div id="first-clue-field"><label for="first-clue">第一条线索（也可开局后发布）</label><textarea id="first-clue" rows="3" maxlength="500" placeholder="开盘时公布，估价阶段不显示"></textarea></div>');
$('config-fields').insertAdjacentHTML('beforeend','<div id="liquidity-field" hidden><label for="liquidity">流动性辅助</label><select id="liquidity"><option value="yes">开启 · 一个低频做市程序</option><option value="no">关闭 · 仅真人交易</option></select><p class="help">以真人估价开盘，无涨跌幅限制。程序每边最多挂 1 手，不主动吃单；每 2 秒检查盘口，价差大或缺单时补单，成交后休息 6 秒。</p></div>');
let scenarioCatalog = [];
function refreshMode(changed = false) {
  const value = $('game-mode').value;
  $('mode-description').textContent = MODES[value].summary;
  $('question-help').textContent = value === 'continuous' ? '先只看题目估价，开盘时公布第一条提示，不设预设价格或涨跌幅限制。初始空仓，净持仓上限 ±10 手；每手价格变化 1，盈亏变化 1 盈亏点。' : '每份标的最终按答案数值兑现。初始现金＝参考价×100，另持有 100 份。' + '首轮新报价范围为参考价 ±20%，请选择合适的量纲；答案须为非负数。';
  if (changed && /^颗 \/ (份|手)$/.test($('unit').value)) $('unit').value = value === 'continuous' ? '颗 / 手' : '颗 / 份';
  $('scenario-fields').hidden = ['call', 'figgie'].includes(value);
  $('generic-config').hidden = value === 'figgie';
  $('figgie-config').hidden = value !== 'figgie';
  if (changed) { $('scenario').value = value === 'dealer' ? 'question' : value === 'continuous' ? 'script' : 'cards'; if (value === 'continuous') { $('rounds').value = '3'; $('seconds').value = '90'; } $('bots').value = value === 'call' ? '150' : value === 'dealer' ? '0' : '10'; }
  const needsQuestion = mode === 'create' && !['call', 'figgie'].includes(value) && $('scenario').value === 'question';
  $('question-fields').hidden = !needsQuestion;
  $('question').required = needsQuestion;
  $('initial-price').required = needsQuestion && value !== 'continuous';
  $('initial-price-field').hidden=value === 'continuous';
  $('first-clue-field').hidden=value !== 'continuous';
  $('liquidity-field').hidden=value !== 'continuous';
  $('bots').parentElement.hidden=value === 'continuous';
  $('auto-next').disabled = value === 'continuous';
  if (value === 'continuous') $('auto-next').value = 'no';
  const botHelp=[...$('generic-config').querySelectorAll('p')].find(p=>p.textContent.includes('机器人随机'));if(botHelp)botHelp.hidden=value === 'continuous';
  const preset = !['call','figgie'].includes(value) && $('scenario').value === 'script';
  $('preset-fields').hidden = !preset; $('rounds').disabled = preset;
  if (preset) $('rounds').value = String(scenarioCatalog.find(x=>x.id === $('scenario-id').value)?.rounds || 3);
  $('scenario-id').required = mode === 'create' && preset;
}
$('game-mode').onchange = () => { refreshMode(true); describeScenario(); };
$('scenario').onchange = () => refreshMode();
refreshMode();
$('join-tab').onclick = () => entryMode('join'); $('create-tab').onclick = () => entryMode('create');
$('name').value = storage('anxian:name') || '';
$('entry-form').onsubmit = async event => {
  event.preventDefault(); $('entry-submit').disabled = true; $('entry-error').textContent = '';
  const name = $('name').value.trim();
  try {
    const response = await fetch(`/api/${mode}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, role: mode === 'create' ? 'player' : $('join-role').value, code: $('room-code').value.trim(), config: $('game-mode').value === 'figgie' ? { mode:'figgie', seats:+$('fig-seats').value, seconds:+$('fig-seconds').value, rounds:+$('fig-rounds').value, learning:$('fig-kind').value !== 'standard', openHands:$('fig-kind').value === 'open', listed:$('fig-listed').value === 'yes', fillBots:$('fig-bots').value === 'yes' } : { mode: $('game-mode').value, scenario: $('scenario').value, scenarioId: $('scenario-id').value, question: $('question').value, unit: $('unit').value, initialPrice: Math.round(Number($('initial-price').value) * 100), rounds: +$('rounds').value, seconds: +$('seconds').value, bots: $('game-mode').value === 'continuous' ? ($('liquidity').value === 'yes' ? 1 : 0) : +$('bots').value, liquidity: $('liquidity').value === 'yes', firstClue:$('first-clue').value, autoNext: $('auto-next').value === 'yes' } }), signal: AbortSignal.timeout(15000) });
    const data = await response.json(); if (!response.ok) throw new Error(data.error);
    storage('anxian:name', name); enter(data);
  } catch (e) { $('entry-error').textContent = e.name === 'TimeoutError' ? '网络请求超时，请稍后重试' : e.message; $('entry-submit').disabled = false; }
};

function describeScenario() {
  if (!$('scenario-id')) return;
  const preset = scenarioCatalog.find(x=>x.id === $('scenario-id').value);
  if (preset && $('scenario').value === 'script') $('rounds').value=String(preset.rounds);
  $('preset-description').textContent = preset ? preset.description + ' ' + (preset.priceDecimals===0?'仅限整数':'最多 '+(preset.priceDecimals??2)+' 位小数') + '。单位：' + ($('game-mode').value === 'continuous' ? preset.unit.replace(/份|股/g, '手') : preset.unit) + ($('game-mode').value === 'continuous' ? '；开盘价由真人估价形成' : '') + '；' + preset.rounds + ' 轮，结束后自动结算。' : '题库暂不可用，可选择自动信息卡或主持人出题。';
}
$('scenario-id').onchange = describeScenario;
fetch('/api/scenarios').then(r=>{ if(!r.ok) throw Error(); return r.json(); }).then(data=>{
  if (!$('scenario-id')) return;
  scenarioCatalog = data.scenarios;
  $('scenario-id').innerHTML = scenarioCatalog.map(x=>'<option value="'+esc(x.id)+'">'+esc(x.name)+'</option>').join('');
  describeScenario();
}).catch(()=>{ if (!$('scenario-id')) return; $('scenario-id').innerHTML='<option value="">题库加载失败，请刷新</option>'; describeScenario(); });

const requestedRoom = new URLSearchParams(location.search).get('r');
if (requestedRoom) {
  $('room-code').value = requestedRoom;
  const previous = readSession(requestedRoom); if (previous) enter(previous);
} else {
  const previous = readSession(storage('anxian:last'));
  if (previous) { $('resume').hidden = false; $('resume').textContent = `返回上次房间 ${previous.code}`; $('resume').onclick = () => enter(previous); }
}
function rules() {
  return `<ol class="rules"><li>每人初始 ¥10,000 现金、100 股；初始总资产 ¥20,000。</li><li>每轮报价范围为上一轮价格的 ±20%。数量单位为股，最少 1 股。</li><li>每轮结束时统一集合竞价，以最大成交量确定价格；未成交委托当轮失效。</li><li>可以买入、卖出已有持股；不能借钱或卖空。</li><li><strong>最终结算价＝全部 ${state.config.rounds} 轮价格的算术平均值，不是最后一轮价格。</strong></li><li>最终收益＝现金＋持股×最终结算价−20,000。真人单独排名，前三名突出显示。</li></ol><details class="section-note"><summary>查看本测试版补充规则</summary>无成交时沿用上一轮价格并计入均价；多个价格成交量相同时，依次选择买卖差额最小、最接近上一轮价格、较低的价格。成交分配按价格优先、同价先报先得。每轮可撤单、可挂多笔同方向单，不允许自买自卖；委托提交后不会立即成交。机器人策略为本次补充实现。并列收益并列排名。</details>`;
}
let callPanel='', callPhase='', callChartKey='';
const callPanels={orders:'委托 / 撤单',fills:'成交与账户',ranking:'收益排名',review:'逐轮复盘',host:'主持人控制',rules:'规则与记录'};
const callClose='<svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 5 10 10M15 5 5 15"/></svg>';
function mountCall() {
  callPanel='';callPhase='';callChartKey='';lastRound=-1;side='buy';
  document.body.classList.add('compact-active');$('app').className='compact-market call-terminal';
  $('app').innerHTML=`<section class="ct-shell" id="call-terminal"><header class="ct-instrument"><div><h2 class="ct-title">均价博弈</h2><p class="ct-unit"><strong>单位：元 / 股</strong><span>${state.config.rounds} 轮 · 均价结算</span></p></div><button type="button" class="ct-room" data-action="share" id="call-room"></button></header><div id="connection-notice" class="banner disconnected-banner" hidden>连接中断，正在重连。恢复后再下单。</div><section class="ct-answer" id="final-card" hidden></section><section id="call-lobby" class="ct-lobby"><div class="card-head"><h3>等待入场</h3><span id="player-count" class="small"></span></div><div id="players" class="player-grid"></div><div id="lobby-start"></div></section><div id="call-live"><div class="ct-quote-news"><div class="ct-quote"><span>最新轮次价格</span><strong class="ct-price" id="call-price"></strong><p class="ct-caption" id="call-price-note"></p></div><section class="ct-news" aria-live="polite"><div class="ct-news-meta"><strong id="call-round"></strong><span class="ct-timer" id="timer"></span></div><p class="ct-news-text" id="call-news"></p></section></div><section class="ct-market"><div class="ct-chart"><div class="ct-market-heading"><strong>轮次走势</strong><span>轮末统一成交</span></div><div id="call-chart"></div></div><aside class="call-market-stats"><div><span>已结算均价</span><strong id="call-average"></strong></div><div><span>真人已挂单</span><strong id="call-submitted"></strong></div><div><span>上轮成交</span><strong id="call-volume"></strong></div></aside></section><section class="ct-dock" id="call-dock"><div><div id="order-unavailable" class="ct-caption" hidden></div><form id="order-form"><div class="ct-side-row"><div class="ct-sides"><button type="button" id="buy-side" class="selected">买入</button><button type="button" id="sell-side" data-quick-side="sell">卖出</button></div><button type="button" id="reference-price" class="ct-secondary">参考价</button></div><div class="ct-fields">${[['price','价格','0.01','decimal'],['qty','股数','1','numeric']].map(([id,label,step,mode])=>`<div class="ct-field"><label for="${id}">${label}</label><button type="button" data-call-step="${id}:-1" aria-label="${label}减一">−</button><input id="${id}" type="number" step="${step}" inputmode="${mode}" min="1" ${id==='qty'?'value="10"':''} required><button type="button" data-call-step="${id}:1" aria-label="${label}加一">+</button></div>`).join('')}</div><div class="ct-quick"><button type="button" data-call-qty="1">1 股</button><button type="button" data-call-qty="10">10 股</button><button type="button" id="max-qty">全部可买</button></div><button id="submit-order" class="ct-submit">买入</button><p id="range" class="ct-caption"></p></form></div><aside class="ct-capacity"><p id="call-position" class="ct-position"></p><small>按可用资金与持股</small><div><span>可买</span><strong id="call-buy-free"></strong><small>股</small></div><div><span>可卖</span><strong id="call-sell-free"></strong><small>股</small></div><p class="ct-pnl"><span>盈亏</span><strong id="call-pnl"></strong></p></aside></section></div><nav class="ct-tabs" aria-label="交易工具">${Object.entries(callPanels).map(([key,title])=>`<button type="button" data-call-panel="${key}" ${key==='host'?'id="call-host-tab"':''}>${key==='orders'?'委托 / 撤单 <span id="call-order-count">0</span>':key==='fills'?'成交':key==='ranking'?'排名':key==='review'?'复盘':key==='host'?'主持人':'更多'}</button>`).join('')}</nav></section><section class="ct-drawer" id="call-drawer" hidden><header><h2 id="call-panel-title"></h2><button type="button" class="ct-close" data-call-close aria-label="收起面板">${callClose}</button></header><div id="call-panel-orders" hidden><button data-action="cancel-all" id="cancel-all">全部撤单</button><div id="orders"></div></div><div id="call-panel-fills" hidden><div id="account"></div><p id="account-note" class="help"></p><h3>我的成交</h3><div id="fills"></div></div><div id="call-panel-ranking" hidden><div id="ranking"></div><p id="ranking-note" class="help"></p></div><div id="call-panel-review" hidden><div id="call-next"></div><div id="round-history"></div></div><div id="call-panel-host" hidden><div id="host-card"></div></div><div id="call-panel-rules" hidden>${rules()}<div class="host-controls"><button data-action="share">邀请朋友</button><button data-action="home">返回首页</button><button data-action="export" id="call-export">下载本局复盘</button></div></div></section>`;
  $('app').insertAdjacentHTML('beforeend', `<dialog id="call-confirm"><form method="dialog"><h2>确认操作</h2><p id="call-confirm-text"></p><div class="host-controls"><button value="cancel">取消</button><button value="confirm" class="primary">确认</button></div></form></dialog><dialog id="call-news-dialog"><form method="dialog"><h2>发布消息</h2><label for="call-news-input">最多 180 字，留空清除</label><textarea id="call-news-input" maxlength="180" rows="4"></textarea><div class="host-controls"><button value="cancel">取消</button><button value="publish" class="primary">发布</button></div></form></dialog>`);
  $('call-news-dialog').addEventListener('close',()=>{if($('call-news-dialog').returnValue==='publish')sendAction('news',{text:$('call-news-input').value});});
  $('order-form').onsubmit=e=>{e.preventDefault();const raw=$('price').value.trim();if(!/^\d+(\.\d{1,2})?$/.test(raw)){toast('报价最多保留两位小数');return;}sendAction('order',{side,price:Math.round(Number(raw)*100),qty:Number($('qty').value)});};
  $('buy-side').onclick=()=>setSide('buy');$('sell-side').onclick=()=>setSide('sell');$('price').oninput=updateAvailable;
  $('reference-price').onclick=()=>{$('price').value=(state.price/100).toFixed(2);updateAvailable();};
  $('max-qty').onclick=()=>{$('qty').value=maxQty();if(!maxQty())toast('可用资金或持股不足');};
  setSide('buy');
}
function askCall(message){
  const dialog=$('call-confirm');$('call-confirm-text').textContent=message;dialog.returnValue='';
  return new Promise(resolve=>{dialog.addEventListener('close',()=>resolve(dialog.returnValue==='confirm'),{once:true});dialog.showModal();});
}
function setCallPanel(panel,scroll=false){
  callPanel=panel;$('call-drawer').hidden=!panel;$('call-panel-title').textContent=callPanels[panel]||'';
  for(const key of Object.keys(callPanels))$('call-panel-'+key).hidden=key!==panel;
  for(const b of document.querySelectorAll('[data-call-panel]'))b.setAttribute('aria-expanded',String(b.dataset.callPanel===panel));
  if(panel&&scroll)$('call-drawer').scrollIntoView({block:'nearest',behavior:'smooth'});
}
function render() {
  if(state.config.mode==='figgie'){renderFiggie(state,{sendAction,toast,showShare,connected,busy:pending.size>0,clockOffset});return;}
  if(state.config.mode!=='call'){renderMarket(state,{sendAction,requestResource,toast,showShare,connected,busy:pending.size>0,clockOffset});return;}
  if(!$('call-terminal'))mountCall();
  const lobby=state.phase==='lobby',finished=state.phase==='finished';
  $('call-room').textContent=state.code+' · '+state.humans+' 人';$('connection-notice').hidden=connected;
  $('call-lobby').hidden=!lobby;$('call-live').hidden=lobby||finished;$('call-host-tab').hidden=!state.isHost||lobby;
  $('call-export').hidden=!finished;
  if(lobby){
    $('player-count').textContent=state.humans+' 位真人 · '+state.bots+' 个机器人';
    $('players').innerHTML=state.ranking.map(p=>`<div class="player"><div><span class="player-name">${esc(p.name)}</span><p class="player-meta">${p.online?'在线':'离线'}${p.isHost?' · 主持人':''}</p></div></div>`).join('');
    $('lobby-start').innerHTML=state.isHost?'<button class="primary wide" data-action="start">开始交易</button>':'<p class="help">等待主持人开始。</p>';
    lastRound=-1;
  }
  if(lastRound!==state.round){lastRound=state.round;$('price').value=(state.price/100).toFixed(2);}
  $('call-price').textContent=money(state.price);$('call-price-note').textContent=state.history.length?'第 '+state.history.length+' 轮收盘':'初始参考价';
  $('call-round').textContent='第 '+state.round+' / '+state.config.rounds+' 轮';
  $('call-news').textContent=state.news||(state.phase==='trading'?'本轮可多次挂单，倒计时结束统一成交。':phaseNames[state.phase]);
  $('call-average').textContent=state.average===null?'—':money(state.average);$('call-submitted').textContent=state.submitted+' / '+state.humans;
  $('call-volume').textContent=state.history.length?state.history.at(-1).volume+' 股':'—';
  const chartKey=JSON.stringify(state.history);if(callChartKey!==chartKey){$('call-chart').innerHTML=chart(state.history);callChartKey=chartKey;}
  $('range').textContent='本轮限价 '+money(state.bounds.low)+'–'+money(state.bounds.high)+' · 轮末成交';
  $('price').min=(state.bounds.low/100).toFixed(2);$('price').max=(state.bounds.high/100).toFixed(2);
  $('order-form').hidden=state.phase!=='trading';$('order-unavailable').hidden=state.phase==='trading';
  $('order-unavailable').textContent=state.phase==='paused'?'已暂停，恢复后可继续下单。':state.nextAt?'本轮已结算，稍后自动进入下一轮。':'本轮已结算，等待主持人开始下一轮。';
  $('orders').innerHTML=state.me.orders.length?state.me.orders.map(o=>`<div class="trade-row"><span class="${o.side==='buy'?'trade-buy':'trade-sell'}">${o.side==='buy'?'买入':'卖出'} ${money(o.price)} × ${o.qty} 股</span><button data-cancel="${o.id}" ${state.phase!=='trading'?'disabled':''}>撤单</button></div>`).join(''):'<p class="empty">暂无未成交委托。</p>';
  $('call-order-count').textContent=state.me.orders.length;
  $('account').innerHTML=`<div class="trade-row"><span>现金</span><strong>${money(state.me.cash)}</strong></div><div class="trade-row"><span>持股</span><strong>${state.me.shares} 股</strong></div><div class="trade-row"><span>${finished?'最终收益':'浮动收益'}</span><strong>${signed(state.me.pnl)}</strong></div>`;
  $('account-note').textContent=finished?'按全部轮次均价 '+money(state.average)+' 结算。':'浮动收益按最新轮次价计算，最终按全部轮次均价结算。';
  $('fills').innerHTML=state.me.fills.length?[...state.me.fills].reverse().map(o=>`<div class="trade-row"><div><span class="${o.side==='buy'?'trade-buy':'trade-sell'}">${o.side==='buy'?'买入':'卖出'} ${o.filled} / ${o.qty} 股</span><p class="small">第 ${o.round} 轮 · 限价 ${money(o.price)}</p></div><span>${o.filled?money(o.clearingPrice):'未成交'}</span></div>`).join(''):'<p class="empty">暂无成交记录。</p>';
  $('round-history').innerHTML=state.history.length?`<table class="book"><thead><tr><th>轮次</th><th>成交价</th><th>成交量</th></tr></thead><tbody>${[...state.history].reverse().map(h=>`<tr><td>第 ${h.round} 轮</td><td>${money(h.price)}</td><td>${h.volume} 股${h.noTrade?' · 沿用前价':''}</td></tr>`).join('')}</tbody></table>`:'<p class="empty">尚无已结束轮次。</p>';
  $('call-next').innerHTML=state.isHost&&state.phase==='intermission'?'<button class="primary" data-action="next">开始下一轮</button>':'';
  $('ranking').innerHTML=`<table class="book"><thead><tr><th>名次 / 玩家</th><th>${finished?'最终收益':'浮动收益'}</th></tr></thead><tbody>${state.ranking.map(p=>`<tr><td><span class="rank">${p.rank}</span>${esc(p.name)}${p.id===state.me.id?'<span class="tag">我</span>':''}</td><td class="${p.pnl>=0?'positive':'negative'}">${signed(p.pnl)}</td></tr>`).join('')}</tbody></table>`;
  $('ranking-note').textContent=finished?'按完整精度排名，同收益并列；机器人不计入排名。':'按最新轮次价格估值，最终按均价结算。';
  $('host-card').innerHTML=state.isHost?`<div class="host-controls">${state.phase==='trading'?'<button data-action="pause">暂停计时</button><button data-action="close-round">提前结算本轮</button>':state.phase==='paused'?'<button class="primary" data-action="resume">恢复交易</button>':state.phase==='intermission'?'<button class="primary" data-action="next">开始下一轮</button>':finished?'<button class="primary" data-action="reset">同房间再玩一局</button>':''}<button data-action="news">发布消息</button></div>`:'';
  $('final-card').hidden=!finished;
  if(finished)$('final-card').innerHTML=`<h2>最终结算均价</h2><p><strong class="ct-answer-number">${money(state.average)}</strong><span>元 / 股</span></p><p class="help">第 ${state.ranking.find(p=>p.id===state.me.id)?.rank} 名 · 最终收益 ${signed(state.me.pnl)}</p><p class="ct-caption">${money(state.me.cash)} 现金＋${state.me.shares} 股×结算均价−20,000 初始资产</p>`;
  if(callPhase!==state.phase){setCallPanel(finished?'ranking':state.phase==='intermission'?'review':'');callPhase=state.phase;}
  updateAvailable();updateButtons();updateTimer();
}
function chart(history) {
  const values=[10000,...history.map(h=>h.price)],min=Math.min(...values),max=Math.max(...values),pad=Math.max(100,(max-min)*.15),lo=min-pad,hi=max+pad;
  const w=innerWidth<700?280:620,left=58,right=w-15,x=i=>left+i*(right-left)/state.config.rounds,y=p=>208-(p-lo)/(hi-lo)*176;
  const grid=Array.from({length:5},(_,i)=>{const p=lo+(hi-lo)*i/4;return `<line x1="${left}" x2="${right}" y1="${y(p)}" y2="${y(p)}" stroke="#dce2d9"/><text x="${left-8}" y="${y(p)+4}" text-anchor="end">${money(p)}</text>`;}).join('');
  return `<svg viewBox="0 0 ${w} 244" role="img" aria-label="每轮统一成交价走势"><g>${grid}</g><polyline points="${values.map((p,i)=>x(i)+','+y(p)).join(' ')}" fill="none" stroke="#167b5b" stroke-width="2.5"/><circle cx="${x(values.length-1)}" cy="${y(values.at(-1))}" r="3" fill="#167b5b"/><text x="${left}" y="236">开局</text><text x="${right}" y="236" text-anchor="end">第 ${state.config.rounds} 轮</text></svg>`;
}
function setSide(next){side=next;for(const dir of ['buy','sell']){$(dir+'-side').classList.toggle('selected',side===dir);$(dir+'-side').setAttribute('aria-pressed',String(side===dir));}$('submit-order').textContent=side==='buy'?'买入':'卖出';$('submit-order').classList.toggle('selling',side==='sell');$('max-qty').textContent=side==='buy'?'全部可买':'全部可卖';updateAvailable();}
function maxQty(){const price=Math.round(Number($('price')?.value||0)*100);return side==='buy'?(price>0?Math.floor(state.me.available.cash/price):0):state.me.available.shares;}
function updateAvailable(){if(!$('call-terminal'))return;const p=Math.round(Number($('price').value)*100);$('call-position').textContent='持有 '+state.me.shares+' 股';$('call-buy-free').textContent=p>0?Math.floor(state.me.available.cash/p):'—';$('call-sell-free').textContent=state.me.available.shares;$('call-pnl').textContent=signed(state.me.pnl);$('qty').max=maxQty();}
function updateButtons(){
  updateMarketControls(connected,pending.size>0);updateFiggieControls(connected,pending.size>0);
  if(!$('call-terminal'))return;
  for(const b of document.querySelectorAll('#call-terminal button,#call-drawer button')){
    if(b.hasAttribute('data-call-panel')||b.hasAttribute('data-call-close')||['share','home','export'].includes(b.dataset.action))continue;
    const trade=b.closest('#order-form')||b.dataset.cancel||b.dataset.action==='cancel-all';
    b.disabled=!connected||pending.size>0||(trade&&state.phase!=='trading')||(b.dataset.action==='cancel-all'&&!state.me.orders.length);
  }
  $('connection-notice').hidden=connected;
}
function updateTimer(){
  updateMarketTimer(clockOffset);updateFiggieTimer(clockOffset);
  if(!$('timer')||!state)return;
  const target=state.phase==='trading'?state.deadline:state.nextAt;
  const sec=target?Math.max(0,Math.ceil((target-Date.now()-clockOffset)/1000)):null;
  $('timer').textContent=state.phase==='paused'?'已暂停':state.phase==='finished'?'已结算':sec===null?'待开轮':(state.phase==='intermission'?'下轮 ':'')+String(Math.floor(sec/60)).padStart(2,'0')+':'+String(sec%60).padStart(2,'0');
}

window.addEventListener('resize',()=>{if($('call-chart')&&state)$('call-chart').innerHTML=chart(state.history);});
setInterval(updateTimer, 250);
setInterval(() => {
  if (session && ws && ws.readyState < 2 && Date.now() - lastSeen > 15000) { ws.close(); return; }
  if (connected && ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping', sent: Date.now() }));
}, 4000);
document.addEventListener('visibilitychange', () => { if (!document.hidden && session && (!ws || ws.readyState > 1)) connect(); });
$('app').addEventListener('click', async event => {
  const panel=event.target.closest('[data-call-panel]');if(panel){setCallPanel(callPanel===panel.dataset.callPanel?'':panel.dataset.callPanel,true);return;}
  if(event.target.closest('[data-call-close]')){setCallPanel('');return;}
  const step=event.target.closest('[data-call-step]');if(step){const [id,delta]=step.dataset.callStep.split(':');const input=$(id);input.value=Math.max(Number(input.min)||1,Math.min(input.max===''?Infinity:Number(input.max),Math.round(((Number(input.value)||0)+Number(delta))*100)/100));updateAvailable();return;}
  const quick=event.target.closest('[data-call-qty]');if(quick){$('qty').value=quick.dataset.callQty;return;}

  const cancel = event.target.closest('[data-cancel]'); if (cancel) { sendAction('cancel', { id: cancel.dataset.cancel }); return; }
  const button = event.target.closest('[data-action]'); if (!button) return;
  const action = button.dataset.action;
  if (action === 'share') return showShare();
  if (action === 'home') { if (await askCall('返回首页后，当前房间身份会保留，可以再次进入。')) location.href = '/'; return; }
  if (action === 'close-round' && !await askCall('立即结束本轮并撮合所有委托？其他人可能还在报价。')) return;
  if (action === 'start' && !await askCall(`确认开始 ${state.config.rounds} 轮交易？开始后本局不再接受新玩家。`)) return;
  if (action === 'reset' && !await askCall('清空本局成交和成绩，所有玩家重置为初始资产？请先下载复盘记录。')) return;
  if (action === 'news') { $('call-news-input').value=state.news||'';$('call-news-dialog').returnValue='';$('call-news-dialog').showModal();return; }
  if (action === 'export') {
    const data = { game: '临渊量化小游戏', exportedAt: new Date().toISOString(), config: state.config, settlementPriceYuan: state.average / 100, rounds: state.history.map(h => ({ round: h.round, priceYuan: h.price / 100, volume: h.volume })), ranking: state.ranking.map(p => ({ rank: p.rank, name: p.name, cashYuan: p.cash / 100, shares: p.shares, profitYuan: p.pnl / 100 })), myOrders: state.me.fills };
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    const a = document.createElement('a'); a.href = url; a.download = `临渊量化-${state.code}-复盘.json`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 5000); toast('已生成复盘文件；若微信阻止下载，可在电脑浏览器下载。'); return;
  }
  sendAction(action);
});
async function showShare() {
  try { network = await (await fetch('/api/network')).json(); }
  catch { network = { lan: [], publicUrl: '' }; }
  shareMode = location.hostname.endsWith('trycloudflare.com') || network.publicUrl ? 'public' : 'lan';
  $('share-code').textContent = state.code; updateShare(); $('share-dialog').showModal();
}
function updateShare() {
  $('share-public').classList.toggle('active', shareMode === 'public'); $('share-lan').classList.toggle('active', shareMode === 'lan');
  let origin;
  if (shareMode === 'public') {
    origin = network.publicUrl || (!['localhost', '127.0.0.1'].includes(location.hostname) && !/^192\.168\.|^10\.|^172\.(1[6-9]|2\d|3[01])\./.test(location.hostname) ? location.origin : '');
    $('share-help').textContent = origin ? '朋友可用各自网络扫码。临时测试地址需要这台电脑保持联网；国内网络与微信兼容性请实测。' : '公网入口尚未启动。请在电脑双击“启动公网测试.command”，然后重新打开此窗口。';
  } else {
    origin = network.lan?.find(u => /192\.168\./.test(u)) || network.lan?.[0] || location.origin;
    $('share-help').textContent = '手机与运行游戏的电脑需连接同一个 Wi-Fi。若无法打开，请检查路由器是否隔离访客设备。';
  }
  const url = origin ? `${origin}/?r=${state.code}` : '';
  $('share-url').value = url; $('qr').hidden = !url; $('copy-link').disabled = !url;
  if (url) $('qr').src = '/api/qr?text=' + encodeURIComponent(url);
}
$('share-public').onclick = () => { shareMode = 'public'; updateShare(); };
$('share-lan').onclick = () => { shareMode = 'lan'; updateShare(); };
$('close-share').onclick = () => $('share-dialog').close();
$('copy-link').onclick = async () => { try { await navigator.clipboard.writeText($('share-url').value); toast('加入链接已复制'); } catch { $('share-url').select(); document.execCommand('copy'); toast('可长按上方链接复制'); } };

async function loadFiggieRooms() {
  if (!$('figgie-rooms')) return;
  try {
    const { rooms } = await (await fetch('/api/rooms')).json();
    if (!$('figgie-rooms')) return;
    $('figgie-rooms').innerHTML = rooms.length ? rooms.map(r => `<div class="fig-public-room"><div><strong>${esc(r.hostName)} 的牌桌</strong><p class="help">${r.code} · ${r.humans} 位真人 / ${r.seats} 席 · ${r.bots} 位机器人 · ${r.learning ? '教学' : '标准'}${r.openHands ? '明牌' : '暗牌'} · ${r.phase === 'trading' || r.phase === 'paused' ? '第 '+r.round+' 局进行中' : '局间 / 等待入场'}</p></div><div class="actions">${r.allowJoin ? `<button data-room="${r.code}" data-role="player">入座 / 候补</button>` : ''}<button data-room="${r.code}" data-role="spectator">观战</button></div></div>`).join('') : '<p class="empty">暂时没有公开牌桌。创建 Figgie 房间，邀请朋友或加入机器人即可开玩。</p>';
    $('figgie-rooms').querySelectorAll('[data-room]').forEach(b => b.onclick = () => {
      const previous = readSession(b.dataset.room);
      if (previous) return enter(previous);
      entryMode('join'); $('room-code').value=b.dataset.room; $('join-role').value=b.dataset.role; $('entry-form').scrollIntoView({behavior:'smooth',block:'center'}); $('name').focus();
    });
  } catch { if ($('figgie-rooms')) $('figgie-rooms').textContent='暂时无法获取牌桌，请点击刷新重试。'; }
}
if ($('refresh-rooms')) $('refresh-rooms').onclick=loadFiggieRooms;
void loadFiggieRooms();
