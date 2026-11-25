import { MODES } from './modes.js';
const $ = id => document.getElementById(id);
const money = n => n === null || n === undefined ? '待形成' : (n / 100).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const signed = n => (n > 0 ? '+' : '') + money(n);
const phases = { lobby: '等待入场', reading: '阅读本轮消息', opening:'真人开盘估价', election: '公开竞报价差', 'maker-quote': '等待做市商报价', trading: '交易进行中', paused: '交易已暂停', intermission: '轮间休息', resolution: '等待公布答案', finished: '本局已结束' };
let mountedAccounting, mountedStructure, mountedGame;
let competitionKey = '', reviewKey = '', reviewGame = '', reviewRound = '', reviewPlayer = '';
const reviewCache=new Map(), reviewLoading=new Set(), reviewErrors=new Map();
let competitionPhase = '', competitionFinalized = false;
let compactPanel = '', compactPhase = '', compactFinalized = false, compactBookKey = '', compactTicket = null;
let chartEnd = 0, chartSecond = -1, lastOrderInput = 'm-qty';
const dealerMode = () => s?.config.mode === 'dealer';
const timedElection = () => s?.config.electionRule === 'quiet-15-v1';
const compact = () => ['continuous', 'dealer'].includes(s?.config.mode);
const capacity = (side, price) => lotMode() ? lotFree(side) : side === 'buy' ? Math.floor(s.me.available.cash / Math.max(1, price)) : s.me.available.shares;
// Dealer quotes are public; customer orders remain private and settle at round end.
function terminalBook() {
  if (!dealerMode()) return s.book;
  const q = s.makerQuote;
  if (!q || !['trading','paused'].includes(s.phase)) return {buy:[],sell:[]};
  const level = price => ({price,qty:q.qty,ownQty:s.me.id===s.makerId?q.qty:0,programQty:0});
  return {buy:[level(q.bid)],sell:[level(q.ask)]};
}
let s, api, mounted = false, lastRound = -1, lastSignal = '', bookKey = '', newsRound = -1;
const humanMode = () => s?.config.marketStructure === 'human-v1';
const lotMode = () => s?.config.accounting === 'lots-v1';
const unit = () => lotMode() ? '手' : '份';
const quoteDecimals = () => [0,1,2].includes(s?.config.priceDecimals)?s.config.priceDecimals:2;
const quoteTick = () => 10 ** (2-quoteDecimals());
const precisionLabel = () => quoteDecimals()===0?'仅限整数':'最多 '+quoteDecimals()+' 位小数';
const quotePrice = n => n===null||n===undefined?'待形成':(n/100).toLocaleString('zh-CN',{maximumFractionDigits:quoteDecimals()});
const inputPrice = n => (Math.round(n/quoteTick())*quoteTick()/100).toFixed(quoteDecimals());
function applyPricePrecision(){
  const tick=quoteTick(),step=String(tick/100);
  for(const id of ['m-estimate','m-order-price','m-ticket-price','m-bid','m-ask','m-spread','m-answer']){
    const el=$(id);if(!el)continue;
    el.step=step;el.inputMode=quoteDecimals()===0?'numeric':'decimal';el.placeholder=precisionLabel();
    const bounded=['m-order-price','m-ticket-price','m-bid','m-ask'].includes(id);
    el.min=String(Math.ceil((bounded?s.bounds.low:id==='m-spread'?1:0)/tick)*tick/100);
    if(bounded)el.max=String(Math.floor(s.bounds.high/tick)*tick/100);
  }
  for(const b of document.querySelectorAll('[data-c-step^="m-order-price:"]')){
    const direction=Number(b.dataset.cStep.split(':')[1])<0?-1:1;
    b.dataset.cStep='m-order-price:'+direction*Number(step);
    b.setAttribute('aria-label','价格'+(direction>0?'增加':'减少')+step);
  }
}

const position = () => s.me.shares > 0 ? '多头 ' + s.me.shares + ' 手' : s.me.shares < 0 ? '空头 ' + -s.me.shares + ' 手' : '空仓';
const lotFree = side => s.me.available[side === 'buy' ? 'buyLots' : 'sellLots'];
const axisPrice = n => Math.abs(n/100) >= 100000000 ? (n/10000000000).toFixed(2)+'亿' : Math.abs(n/100) >= 10000 ? (n/1000000).toFixed(2)+'万' : money(n);
const sourceLink = x => x?.source && /^https:\/\//.test(x.source) ? '<a href="' + esc(x.source) + '" target="_blank" rel="noopener noreferrer">' + esc(x.sourceName || '统计来源') + '</a>' : '';
export function marketFeedback(message, request = null) {
  if (compact() && ['order','take'].includes(request?.action) && s.phase === 'trading') {
    // A submitted quantity can exceed the remaining capacity after its fill.
    // Prepare another order without overwriting edits made while awaiting the ACK.
    const input = $(lastOrderInput);
    if (input && Number(input.value) === Number(request.payload.qty)) input.value = 1;
    if (request.action === 'take' || (dealerMode() && lastOrderInput === 'm-ticket-qty')) compactCloseTicket();
    message += '；可继续交易';
    updateQuick(); updateTicket();
  }
  if ($('m-feedback')) $('m-feedback').textContent = message;
  if (compact() && $('c-ticket-status')) $('c-ticket-status').textContent = message;
}
function ask(message) {
  const dialog = $('m-confirm');
  $('m-confirm-text').textContent = message;
  return new Promise(resolve => {
    const finish = value => { dialog.close(); resolve(value); };
    $('m-confirm-yes').onclick = () => finish(true);
    $('m-confirm-no').onclick = () => finish(false);
    dialog.oncancel = () => resolve(false);
    dialog.showModal();
  });
}
const button = (action, label, style = '') => '<button type="button" class="' + style + '" data-market-action="' + action + '">' + label + '</button>';
const row = (a, b) => '<div class="trade-row"><span>' + a + '</span><span>' + b + '</span></div>';
const input = (id, label, value, step = '0.01') => '<div><label for="' + id + '">' + label + '</label><input id="' + id + '" type="number" step="' + step + '" value="' + value + '" required inputmode="decimal"></div>';
function cents(id) {
  const raw = $(id).value.trim();
  if (!/^\d+(\.\d{1,2})?$/.test(raw)) throw new Error('数值需为非负数，最多保留两位小数');
  const price=Math.round(Number(raw)*100);
  if(price%quoteTick()!==0)throw new Error('本题'+precisionLabel());
  return price;
}
function renderRules() {
  const initial = lotMode() ? '初始空仓，无现金门槛。净持仓最多多头 10 手或空头 10 手，未成交挂单也占用对应额度。每手价格变化 1，盈亏变化 1 盈亏点。单位：' + esc(s.config.unit) + '。' : '初始 100 份标的＋' + money(s.config.initialPrice * 100) + ' 现金，初始总资产 ' + money(s.initialWealth) + '。每份按答案的数值计价；单位：' + esc(s.config.unit) + '。';
  const settlement = s.config.scenario === 'cards' ? '基础价值 100 元；每张信息卡独立等概率取 −5 至 +5 元（0.5 元一档），每轮揭晓一张，最后再揭晓收盘卡。全部加总为兑现价值，未来卡片不向任何玩家或机器人泄露。' : s.config.scenario === 'script' ? '每轮自动揭晓一条统计线索；提示公布时立即开放交易。全部 ' + s.config.rounds + ' 轮结束后自动公布统计答案并结算。' : '主持人逐步发布线索；全部轮次结束后，由主持人输入非负答案作为每' + unit() + '标的的兑现价值。';
  const mechanics = s.config.mode === 'continuous' ? '限价单即时撮合：' + (humanMode() ? '价格优先，同价真人优先、同类先到先得。' : '价格优先、同价先到先得。') + '按簿上原挂单价格成交。未成交限价单跨轮保留；吃单为限价 IOC，剩余量取消。每轮内可反复买卖，不限成交次数；每轮休息期间暂停交易。' : (timedElection() ? '所有人均可提交价差，已报价格只能调小；同价按服务器收到顺序优先。第一份报价后开始 15 秒倒计时，每次出现更小价差重新计时，到时自动选出最小价差者。' : '公开竞报价差，可多次修改；同价先提交者优先，主持人叫价结束后确认。') + '赢家整局任职，第一组双边报价不能宽于承诺价差。每轮先由做市商报买卖价并锁定，再由其他玩家报价，轮末只与做市商成交：客户买入按卖价，客户卖出按买价。价格优先、同价先到先得。每边标准数量 10 份，余额不足时同步缩量；没有双边履约能力或超时，跳过本轮。';
  return '<ol class="rules"><li>' + initial + '</li><li>' + mechanics + (humanMode() ? '先只看题目，各人独立估价；主持人可随时按已提交估价的中位数开盘并公布第一条提示；开盘后仍可加入交易，估价本身不成交。流动性程序只挂少量单，不主动吃单；每 2 秒检查盘口，价差大或缺单时每边补 1 手，成交后休息 6 秒；真人盘口接近时让开。' : '') + '</li><li>' + (humanMode() ? '不设涨跌幅限制；价格可为 0，'+precisionLabel()+'，技术上限为 10 亿。' : '新委托价格在本轮参考价 ±20% 内；') + '可挂不交叉的双边单，' + (lotMode() ? '可以买入做多、卖出做空；反向交易先平仓，再开反向仓位。不能自成交，无手续费。' : '不能自成交、借钱或卖空，无手续费。') + (s.config.mode === 'dealer' ? '做市商已锁定的报价不可撤销；客户未成交委托当轮失效。' : '挂单持续到撤销、成交或全局结束。') + '</li><li>' + settlement + '</li><li><strong>' + (lotMode() ? '最终收益＝已平仓盈亏（做 T）＋剩余持仓按实际答案结算的盈亏。平仓按先进先出配对；多头赚答案上涨，空头赚答案下跌。' : '最终收益＝现金＋持有份数×兑现价值−初始总资产。交易价格与答案不同；最终不按各轮均价结算。') + '</strong></li></ol>';
}
function mount() {
  chartEnd = 0; chartSecond = -1;
  mounted = true; mountedAccounting = s.config.accounting; mountedStructure = s.config.marketStructure; mountedGame = s.competition?.gameNumber; lastRound = -1; lastSignal = ''; bookKey = ''; newsRound = -1;
  competitionKey = ''; reviewKey = ''; reviewGame = ''; reviewRound = ''; reviewPlayer = '';
  competitionPhase = ''; competitionFinalized = false;
  $('app').innerHTML = '<div class="room-top"><div><h2>' + MODES[s.config.mode].name + ' <span class="pill">' + s.code + '</span></h2><p class="room-sub" id="m-status"></p></div><div class="actions">' + button('share', '邀请朋友 ↗') + button('home', '回到首页') + '</div></div>' +
    '<section class="question-banner"><h2 id="m-question"></h2><p class="help" id="m-question-note"></p></section><div id="m-offline" class="banner disconnected-banner" hidden>连接中断，正在重连。计时以服务器为准；恢复后再提交。</div><div id="m-notice" class="banner" hidden></div>' +
    '<div class="room-layout"><div class="stack"><section id="m-lobby" class="card"><div class="card-head"><h3>等待大家入场</h3><span class="pill">四种模式 · 同一交易室</span></div><div id="m-players" class="player-grid"></div><div id="m-start" class="host-controls" style="margin-top:20px"></div></section>' +
    '<section class="hero-panel" id="m-market"><div class="card-head"><span id="m-round" class="card-label"></span><span id="m-timer" class="timer" style="color:var(--lime)"></span></div><div class="metrics"><div><span class="metric-label">最新成交 / 参考价</span><span id="m-price" class="metric-value"></span></div><div><span id="m-value-label" class="metric-label"></span><span id="m-value" class="metric-value"></span></div><div><span class="metric-label">本轮成交' + unit() + '数</span><span id="m-volume" class="metric-value"></span></div></div><p id="m-valuation-note" class="help"></p></section>' +
    '<section id="m-election" class="card" hidden><div class="card-head"><h3>谁愿意报更窄的价差？</h3><span class="pill">主持人叫一圈后确认</span></div><p class="help">Spread＝卖价−买价。大家先竞价差，当选者再决定第一组买卖价。首组报价必须兑现承诺，每边 10 份。</p><form id="m-spread-form"><div class="form-row">' + input('m-spread', '我承诺的价差', '') + '<div class="form-end"><button id="m-spread-submit" class="primary wide">提交 / 更新价差</button></div></div></form><div id="m-election-list" style="margin-top:20px"></div><div id="m-elect-control" style="margin-top:15px"></div></section>' +
    '<section id="m-maker" class="card" hidden><div class="card-head"><h3 id="m-maker-title"></h3><span id="m-maker-role" class="pill"></span></div><p id="m-maker-note" class="help"></p><div id="m-quote-display"></div><form id="m-quote-form" hidden><div class="form-row">' + input('m-bid', '我的买入价', '99.00') + input('m-ask', '我的卖出价', '101.00') + '</div><button id="m-quote-submit" class="primary wide" style="margin-top:16px">锁定双边报价，开放本轮交易</button></form></section>' +
    '<section id="m-book-card" class="card" hidden><div class="card-head"><h3>公开订单簿</h3><span class="small">前 10 档 · 按价格聚合</span></div><div class="split"><div><h3 class="positive">买盘 Bid</h3><div id="m-bids"></div></div><div><h3 class="negative">卖盘 Ask</h3><div id="m-asks"></div></div><p class="section-note">点击“吃单”填入限价和当前可交易数量，再确认。期间盘口可能变化，剩余未成交量直接取消。</p></section>' +
    '<section id="m-order-card" class="card"><div class="card-head"><h3>交易委托</h3><span id="m-range" class="small"></span></div><p id="m-order-note" class="help"></p><form id="m-order-form"><div class="form-row"><div><label for="m-side">方向</label><select id="m-side"><option value="buy">买入</option><option value="sell">卖出</option></select></div><div><label for="m-kind">委托方式</label><select id="m-kind"><option value="order">限价挂单</option><option value="take">吃单（剩余取消）</option></select></div></div><div class="form-row" style="margin-top:15px">' + input('m-order-price', '限价', '100.00') + input('m-qty', '数量（' + unit() + '）', lotMode() ? '1' : '10', '1') + '</div><p id="m-free" class="help"></p><button id="m-order-submit" class="primary wide">确认提交</button></form><div class="card-head" style="margin-top:22px"><h3>我的未成交委托</h3>' + button('cancel-all', '全部撤单', 'text-button') + '</div><div id="m-orders"></div></section>' +
    '<section id="m-resolution" class="card" hidden><div class="card-head"><h3>公布答案，结算本局</h3></div><p class="help">所有交易已停止。结算值是每' + unit() + '标的兑现的数值，输入后本局锁定。</p><form id="m-resolve-form"><div class="form-row">' + input('m-answer', '答案 / 结算值', '100.00') + '<div><label for="m-source">答案说明（可选）</label><input id="m-source" maxlength="300" placeholder="来源、测量或计算方法"></div></div><button id="m-resolve-submit" class="primary wide" style="margin-top:16px">公布并结算</button></form><p id="m-wait-answer" class="empty">等待主持人公布答案。</p></section>' +
    '<section id="m-final" class="card" hidden></section><section class="card"><div class="card-head"><h3>逐轮记录</h3></div><div id="m-history" class="scroll"></div></section></div>' +
    '<aside class="stack"><section id="m-host" class="card" hidden><div class="card-head"><h3>主持人控制</h3></div><div id="m-controls" class="host-controls"></div><form id="m-news-form"><label for="m-news-text">向全场发布新信息</label><textarea id="m-news-text" rows="3" maxlength="500" placeholder="补充线索、宣布消息……" required></textarea><button id="m-news-submit" class="wide" style="margin-top:10px">发布信息</button></form></section>' +
    '<section class="card" id="m-account-card"><div class="card-head"><h3>我的账户</h3><span id="m-name" class="pill"></span></div><div id="m-account"></div></section><section class="card"><div class="card-head"><h3>信息时间线</h3></div><div id="m-signals" class="scroll"></div></section><section class="card"><div class="card-head"><h3 id="m-ranking-title">浮动收益排名</h3><span class="small">仅真人</span></div><div id="m-ranking" class="scroll"></div></section><section class="card"><div class="card-head"><h3>我的成交</h3></div><div id="m-fills" class="scroll"></div></section><section class="card"><div class="card-head"><h3>规则速查</h3></div><div id="m-rules"></div></section></aside></div>';
  $('app').insertAdjacentHTML('beforeend', '<dialog id="m-confirm"><h3>确认操作</h3><p id="m-confirm-text" class="help"></p><div class="host-controls"><button id="m-confirm-no" type="button">取消</button><button id="m-confirm-yes" type="button" class="primary">确认</button></div></dialog>');
  if (compact()) mountTerminal();
  if (s.competition) mountCompetition();
  $('m-rules').innerHTML = renderRules();
  $('m-spread-form').onsubmit = e => submitForm(e, () => api.sendAction('spread', { spread: cents('m-spread') }));
  $('m-quote-form').onsubmit = e => submitForm(e, () => api.sendAction('maker-quote', { bid: cents('m-bid'), ask: cents('m-ask') }));
  $('m-order-form').onsubmit = e => submitForm(e, () => { lastOrderInput='m-qty'; return api.sendAction($('m-kind').value, { side: $('m-side').value, price: cents('m-order-price'), qty: Number($('m-qty').value) }); });
  $('m-news-form').onsubmit = e => submitForm(e, () => { api.sendAction('news', { text: $('m-news-text').value }); });
  $('m-resolve-form').onsubmit = e => submitForm(e, async () => { const price = cents('m-answer'); if (await ask('以 ' + quotePrice(price) + ' 为每' + unit() + '最终结算值？公布后不能修改。')) api.sendAction('resolve', { price, note: $('m-source').value }); });
  $('m-qty').min = 1;
  $('m-kind').querySelector('option[value="take"]').hidden = s.config.mode === 'dealer';
  $('m-spread').max = (Math.floor(s.config.initialPrice * .4) / 100).toFixed(2); $('m-spread').min = '.01';
  $('m-order-price').value = s.price === null ? '' : inputPrice(s.price);
  $('m-answer').value = humanMode() ? '' : inputPrice(s.config.initialPrice);
  $('app').removeEventListener('click', marketClick);
  $('app').addEventListener('click', marketClick);
  if (compact()) mountCompact();
}
async function submitForm(e, fn) { e.preventDefault(); try { await fn(); } catch (error) { api.toast(error.message); } }
async function marketClick(e) {
  if (!mounted || !s || s.config.mode === 'call') return;
  if (compact() && compactClick(e)) return;
  const cancelLevel = e.target.closest('[data-c-cancel-level]');
  if (cancelLevel && compactTicket) return api.sendAction('cancel-level', { side: compactTicket.side === 'buy' ? 'sell' : 'buy', price: compactTicket.price });
  const cancel = e.target.closest('[data-market-cancel]');
  if (cancel) return api.sendAction('cancel', { id: cancel.dataset.marketCancel });
  const take = e.target.closest('[data-take-side]');
  if (take) {
    if ($('m-ticket')) {
      $('m-ticket-side').value = take.dataset.takeSide;
      $('m-ticket-price').value = inputPrice(Number(take.dataset.price));
      $('m-ticket-qty').value = Math.max(1, Math.min(Number($('m-ticket-qty').value) || 1, Number(take.dataset.qty), lotMode() ? lotFree(take.dataset.takeSide) : Infinity));
      $('m-ticket').hidden = false;
      if (compact()) { compactTicket = { side: take.dataset.takeSide, price: Number(take.dataset.price) }; $('c-ticket').hidden = false; $('c-ticket-status').textContent = ''; $('c-ticket').focus({preventScroll:true}); }
      updateTicket();
      if (compact()) { renderCompactTicket(); positionCompactTicket(); return; }
      if (window.innerWidth < 700) $('m-ticket').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else {
      $('m-side').value = take.dataset.takeSide; $('m-kind').value = 'take';
      $('m-order-price').value = inputPrice(Number(take.dataset.price)); $('m-qty').value = take.dataset.qty;
    }
    return;
  }
  const quickSide = e.target.closest('[data-quick-side]');
  if (quickSide) { $('m-side').value = quickSide.dataset.quickSide; if(compact() && $('m-kind').value==='take') fillMarketPrice(); updateQuick(); return; }
  const qty = e.target.closest('[data-quick-qty]');
  if (qty) {
    const price = Number($('m-order-price').value) * 100;
    $('m-qty').value = qty.dataset.quickQty === 'max' ? Math.max(0, lotMode() ? lotFree($('m-side').value) : $('m-side').value === 'buy' ? Math.floor(s.me.available.cash / Math.max(1, price)) : s.me.available.shares) : qty.dataset.quickQty;
    return;
  }
  if (compact() && e.target.closest('[data-best-price]')) { fillMarketPrice(); updateQuick(); return; }
  if (e.target.closest('[data-best-price]')) {
    const levels = s.book?.[$('m-side').value === 'buy' ? 'sell' : 'buy'] || [];
    const best = levels.find(x => x.qty > x.ownQty);
    if (best) $('m-order-price').value = inputPrice(best.price);
    else api.toast('当前没有对手报价，可自行填写限价');
    return;
  }
  const target = e.target.closest('[data-market-action]'); if (!target) return;
  const action = target.dataset.marketAction;
  if (action === 'share') return api.showShare();
  if (action === 'home') { location.href = '/'; return; }
  if (action === 'next-game') return api.sendAction(action, { scenarioId: $('m-next-question').value });
  if (action === 'retry-review') {reviewErrors.clear();renderPublicReview();return;}
  if (action === 'export-competition') {
    let competition=s.competition;
    try{if(s.lazyHistory)competition=await api.requestResource('export-competition');}catch(error){api.toast(error.message);return;}
    const data = { roomCode: s.code, amountUnit: '成交价、答案及盈亏为整数分，显示时除以 100；比赛积分直接读取 points，不除以 100。', ...competition };
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    const a = document.createElement('a'); a.href = url; a.download = '比赛成绩与全员复盘-' + s.code + '.json'; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 5000); return;
  }
  if (action === 'export') {
    let full=s;
    try{if(s.lazyHistory)full=await api.requestResource('export-current');}catch(error){api.toast(error.message);return;}
    const data = { game: MODES[full.config.mode].name, config: full.config, openingPrice:full.openingPrice, liquidity:full.liquidity, settlementPrice: full.settlementPrice, ranking: full.ranking,
      history: full.history, signals: full.signals, messages: full.messages, trades: full.trades, review: full.review, myFills: full.me.fills, myAccount: { position:full.me.shares, averageEntry:full.me.averageEntry, realizedPnl:full.me.realizedPnl, settlementPnl:full.me.unrealizedPnl, totalPnl:full.me.pnl }, replay: full.replay, moneyUnit: '所有金额为整数分，显示时除以 100' };
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    const a = document.createElement('a'); a.href = url; a.download = '交易复盘-' + s.code + '.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 5000); return;
  }
  const questions = { start: s.competition ? '开始本题？无需等齐所有人，开盘和每轮推进都由你决定，玩家可随时加入。' : '所有人已入场？开始后本局不能再新增玩家。', 'close-election': '叫价结束，确认由当前最窄价差者当选？', 'close-round': s.phase === 'maker-quote' ? '做市商尚未报价，确定跳过本轮？' : '立即结束本轮交易？', reset: s.competition ? '保留本局积分和复盘，准备再玩同一道题？' : '清空本局记录并重新开局？请先导出复盘。', 'finalize-competition': '结束本场比赛并向所有人展示总排名？确认后成绩锁定，仍可查看所有复盘。' };
  if (questions[action] && !await ask(questions[action])) return;
  api.sendAction(action);
}
export function renderMarket(state, callbacks) {
  s = state; api = callbacks;
  if (!mounted || !$('m-question') || mountedAccounting !== s.config.accounting || mountedStructure !== s.config.marketStructure || mountedGame !== s.competition?.gameNumber) mount();
  const isDealer = s.config.mode === 'dealer', trading = s.phase === 'trading', final = s.phase === 'finished', lobby = s.phase === 'lobby';
  const canOrder = trading && (!isDealer || s.me.id !== s.makerId);
  if ($('m-terminal')) { $('m-terminal').hidden = lobby || (humanMode() && s.openingPrice === null); renderTerminal(); }
  if ($('m-opening')) renderOpening();
  $('m-status').textContent = s.humans + ' 位真人 · ' + (humanMode() ? (s.config.liquidity ? '低频流动性辅助' : '仅真人交易') : s.bots + ' 个机器人') + ' · ' + phases[s.phase];
  $('m-question').textContent = s.config.question;
  $('m-question-note').textContent = '单位：' + s.config.unit + (humanMode() ? s.openingPrice === null ? ' · 开盘价等待真人估价' : ' · 真人开盘参考价 ' + quotePrice(s.openingPrice) : ' · 初始参考价 ' + money(s.config.initialPrice)) + ' · ' + s.config.rounds + ' 轮，每轮交易 ' + s.config.seconds + ' 秒' + (s.config.readingSeconds ? ' · 先读消息 ' + s.config.readingSeconds + ' 秒' : '') + ' · 按最终答案兑现' + (lotMode() ? ' · 净持仓上限 ±10 手，无现金门槛' : '');
  $('m-offline').hidden = api.connected;
  $('m-notice').hidden = !s.notice; $('m-notice').textContent = s.notice;
  $('m-lobby').hidden = !lobby;
  if(lobby) $('m-players').innerHTML = s.ranking.map(p => '<div class="player"><div><span class="player-name">' + esc(p.name) + '</span><div class="player-meta">' + (p.online ? '在线' : '离线') + (p.isHost ? ' · 主持人' : '') + '</div></div></div>').join('');
  $('m-start').innerHTML = s.competition?.finalized ? '<p class="help">比赛已结束，可查看总排名和历史复盘。</p>' : s.isHost ? button('start', isDealer ? '开始竞报价差' : humanMode() ? '开始本题：提交估价' : '所有人准备好，开市', 'primary wide') : '<p class="help">等待主持人开始。</p>';
  $('m-market').hidden = lobby;
  $('m-round').textContent = 'ROUND ' + s.round + ' / ' + s.config.rounds + ' · ' + phases[s.phase];
  $('m-price').textContent = quotePrice(s.price);
  $('m-value-label').textContent = final ? '最终兑现价值' : s.config.scenario === 'cards' ? '已知信息对应价值' : '最终答案';
  $('m-value').textContent = final ? quotePrice(s.settlementPrice) : s.publicValue === null ? '待揭晓' : money(s.publicValue);
  $('m-volume').textContent = s.roundVolume ?? s.trades.filter(t => t.round === s.round).reduce((n, t) => n + t.qty, 0);
  $('m-valuation-note').textContent = final ? '最终成绩按兑现价值结算。' : s.config.scenario === 'cards' ? '还有 ' + s.unrevealed + ' 张卡未揭晓。信息改变估值，成交价格由订单决定。' : s.config.scenario === 'script' ? s.config.rounds + ' 轮逐条揭晓线索，结束后自动公布答案。' : '市场成交价不代表答案。交易结束后，主持人公布结算值。';
  $('m-election').hidden = s.phase !== 'election';
  $('m-election-list').innerHTML = s.election.length ? s.election.map((x, i) => row((i + 1) + '. ' + esc(x.name) + (i ? '' : ' <span class="tag">当前最窄</span>'), '<strong>' + money(x.spread) + '</strong>')).join('') : '<p class="empty">等待第一位玩家报价差。</p>';
  $('m-elect-control').innerHTML = timedElection() ? '<p id="m-election-clock" class="ct-election-clock" role="timer"></p>' : s.isHost ? button('close-election', '叫价结束，确认最窄价差者', 'primary wide') : '';
  if(dealerMode()) {
    $('m-election').querySelector('.help').textContent=timedElection()?'更小价差出现后重新计时 15 秒，到时自动选出做市商。':'价差最小者当选，同价先到优先。可修改报价。';
    const mine=s.election.find(x=>x.playerId===s.me.id);
    $('m-spread').max=((timedElection()&&mine?mine.spread:Math.floor(s.config.initialPrice*.4))/100).toFixed(2);
    $('m-spread-submit').textContent=mine?'更新价差':'提交价差';
  }
  $('m-maker').hidden = !isDealer || !s.makerId;
  $('m-maker-title').textContent = '做市商：' + (s.makerName || '待选出');
  $('m-maker-role').textContent = s.makerId === s.me.id ? '你负责双边报价' : '整局任职';
  const commitment = s.election.find(x => x.playerId === s.makerId)?.spread;
  $('m-maker-note').textContent = s.phase === 'maker-quote' ? (s.round === 1 ? '首次报价价差不超过 ' + money(commitment) + '。' : '根据新信息与库存，调整本轮买卖价。') + '每边标准 10 份；余额不足会同步缩量。超时未报价则跳过本轮。' : s.makerQuote ? '本轮报价已锁定。客户买入按做市商卖价、卖出按做市商买价成交。' : '本轮没有提交双边报价，未发生做市商交易。';
  $('m-quote-display').innerHTML = s.makerQuote ? '<div class="split">' + row('买价 × 数量', money(s.makerQuote.bid) + ' × ' + s.makerQuote.qty) + row('卖价 × 数量', money(s.makerQuote.ask) + ' × ' + s.makerQuote.qty) + '</div>' : '';
  $('m-quote-form').hidden = s.phase !== 'maker-quote' || s.me.id !== s.makerId;
  $('m-book-card').hidden = isDealer || lobby;
  const nextBookKey = JSON.stringify([s.book, trading]);
  if (!compact() && s.book && bookKey !== nextBookKey) for (const side of ['buy', 'sell']) {
    $('m-' + (side === 'buy' ? 'bids' : 'asks')).innerHTML = s.book[side].length ? '<table class="book"><thead><tr><th>价格 / ' + unit() + '数</th><th>操作</th></tr></thead><tbody>' + s.book[side].map(x => '<tr><td><strong>' + quotePrice(x.price) + '</strong><div class="small">' + x.qty + ' ' + unit() + (x.ownQty ? ' · 自己 ' + x.ownQty : '') + (humanMode() ? ' · 真人 ' + (x.qty-x.programQty) + ' / 程序 ' + x.programQty : '') + '</div></td><td><button type="button" data-take-side="' + (side === 'buy' ? 'sell' : 'buy') + '" data-price="' + x.price + '" data-qty="' + (x.qty - x.ownQty) + '" ' + (!trading || x.qty === x.ownQty ? 'disabled' : '') + '>' + (side === 'buy' ? '卖出' : '买入') + '</button></td></tr>').join('') + '</tbody></table>' : '<p class="empty">暂无挂单</p>';
  }
  bookKey = nextBookKey;
  $('m-order-card').hidden = lobby || s.phase === 'election';
  $('m-range').textContent = humanMode() ? '无涨跌幅限制 · '+precisionLabel() : '新委托 ' + money(s.bounds.low) + '～' + money(s.bounds.high);
  $('m-order-form').hidden = isDealer ? !canOrder : lobby || final || s.phase === 'resolution';
  $('m-order-note').textContent = canOrder ? isDealer ? '提交买单或卖单，轮末按做市商报价成交。可以撤单，也可以挂不交叉的双边单。' : '可立即成交，也可挂单等待。未成交限价单跨轮保留；请在新信息到来后检查旧单。' : final ? '本局交易与结算已完成。' : s.phase === 'resolution' ? '交易结束，等待答案。' : isDealer && s.makerId === s.me.id && trading ? '你的双边报价已锁定，本轮无需再操作。' : s.phase === 'reading' ? '先阅读本轮线索，倒计时后自动开市。可提前填写委托。' : '当前阶段暂不接受委托。';
  $('m-free').textContent = lotMode() ? position() + ' · 还可买 ' + lotFree('buy') + ' 手 / 卖 ' + lotFree('sell') + ' 手（已扣挂单：买 ' + s.me.available.pendingBuyLots + ' / 卖 ' + s.me.available.pendingSellLots + ' 手）' : '可用现金 ' + money(s.me.available.cash) + ' · 可用持有 ' + s.me.available.shares + ' ' + unit();
  $('m-orders').innerHTML = s.me.orders.length ? s.me.orders.map(o => row((o.side === 'buy' ? '买' : '卖') + ' ' + quotePrice(o.price) + ' × ' + o.qty, '<button type="button" data-market-cancel="' + o.id + '" ' + (!canOrder ? 'disabled' : '') + '>撤单</button>')).join('') : '<p class="empty">没有未成交委托。</p>';
  $('m-resolution').hidden = s.phase !== 'resolution'; $('m-resolve-form').hidden = !s.isHost; $('m-wait-answer').hidden = s.isHost;
  $('m-final').hidden = !final;
  if (final) $('m-final').innerHTML = '<h3>' + (s.ranking.some(p => p.id === s.me.id) ? '本局成绩 · 第 ' + s.ranking.find(p => p.id === s.me.id).rank + ' 名' : '本题已结束 · 未参与本题计分') + '</h3><div class="result-value">' + signed(s.me.pnl) + '</div><p class="section-note">' + (lotMode() ? '已平仓 ' + signed(s.me.realizedPnl) + ' ＋ 持仓结算 ' + signed(s.me.unrealizedPnl) + ' ＝ ' + signed(s.me.pnl) + ' 盈亏点。' : money(s.me.cash) + ' 现金＋' + s.me.shares + ' 份 × ' + quotePrice(s.settlementPrice) + ' 兑现价值 − ' + money(s.initialWealth) + ' 初始资产。') + '</p><p class="help">' + esc(s.resolution?.note || '') + ' ' + sourceLink(s.resolution) + '</p>' + button('export', '下载本局复盘记录', 'wide');
  $('m-history').innerHTML = s.history.length ? [...s.history].reverse().map(h => row('第 ' + h.round + ' 轮 · ' + (h.noTrade ? '无成交' : h.volume + ' ' + unit()), '收盘 / 参考 ' + quotePrice(h.price))).join('') : '<p class="empty">尚无已结束轮次。</p>';
  $('m-host').hidden = !s.isHost || lobby;
  let actions = '';
  if (s.phase === 'reading') actions = button('pause', '暂停读消息');
  if (['trading', 'maker-quote'].includes(s.phase)) actions = button('pause', '暂停') + button('close-round', s.phase === 'maker-quote' ? '跳过未报价轮次' : '结束本轮');
  if (s.phase === 'paused') actions = button('resume', '恢复交易', 'primary');
  if (s.phase === 'intermission') actions = button('next', '开始下一轮', 'primary');
  if (final) actions = s.competition ? '' : button('reset', '同房间再玩一局', 'primary');
  $('m-controls').innerHTML = actions;
  $('m-news-form').hidden = final || s.phase === 'resolution' || (humanMode() && s.openingPrice === null);
  $('m-name').textContent = s.me.name;
  $('m-account').innerHTML = lotMode() ? row('净持仓（上限 ±10 手）', position()) + row('持仓均价', s.me.averageEntry === null ? '—' : money(s.me.averageEntry)) + row('已平仓盈亏（做 T）', signed(s.me.realizedPnl)) + row(final ? '持仓结算盈亏' : '持仓浮动盈亏', signed(s.me.unrealizedPnl)) + row('总盈亏（盈亏点）', '<strong class="' + (s.me.pnl >= 0 ? 'positive' : 'negative') + '">' + signed(s.me.pnl) + '</strong>') + '<p class="section-note">平仓按先进先出计算；1 手价格变化 1，盈亏变化 1 盈亏点。' + (final ? '多头按答案减成本价，空头按成本价减答案结算。' : '浮盈按最新成交价估值，最终按实际答案结算。') + '</p>' : row('现金', money(s.me.cash)) + row('持有标的', s.me.shares + ' ' + unit()) + row(final ? '最终收益' : '浮动收益', '<strong class="' + (s.me.pnl >= 0 ? 'positive' : 'negative') + '">' + signed(s.me.pnl) + '</strong>') + '<p class="section-note">' + (final ? '按公布的兑现价值结算。' : '浮动收益按最新成交价估值，最终排名可能变化。') + '</p>';
  const signals = [...s.signals.map(x => ({ ...x, text: x.title + '：' + x.text })), ...s.messages].reverse().sort((a, b) => b.round - a.round || b.at - a.at);
  $('m-signals').innerHTML = signals.length ? signals.map(x => '<div class="signal"><span class="small">第 ' + x.round + ' 轮</span><p>' + esc(x.text) + '</p><p class="help">' + sourceLink(x) + '</p></div>').join('') : '<p class="empty">等待新线索。</p>';
  $('m-ranking-title').textContent = final ? '本局收益排名' : '浮动收益排名';
  if(!compact() || dealerMode() || final) $('m-ranking').innerHTML = s.ranking.map(p => row(p.rank + '. ' + esc(p.name) + (p.isMaker ? '<span class="tag">做市商</span>' : ''), '<span class="' + (p.pnl >= 0 ? 'positive' : 'negative') + '">' + signed(p.pnl) + '</span>')).join('');
  $('m-fills').innerHTML = s.me.fills.length ? [...s.me.fills].reverse().slice(0, 100).map(f => row('第 ' + f.round + ' 轮 · ' + (f.side === 'buy' ? '买入' : '卖出') + ' ' + f.filled + ' ' + unit() + (f.counterparty ? ' · 对手：' + esc(f.counterparty) : ''), quotePrice(f.clearingPrice))).join('') : '<p class="empty">成交后显示在这里。</p>';
  if (lastRound !== s.round) {
    lastRound = s.round;
    const gap = s.round === 1 && commitment ? commitment : Math.max(2, Math.round(s.price * .02));
    $('m-bid').value = inputPrice(s.price - Math.floor(gap / 2)); $('m-ask').value = inputPrice(s.price + Math.ceil(gap / 2));
  }
  for (const id of ['m-order-price', 'm-bid', 'm-ask']) { $(id).min = (s.bounds.low / 100).toFixed(2); $(id).max = (s.bounds.high / 100).toFixed(2); }
  if ($('m-terminal')) { updateQuick(); updateTicket(); }
  if (s.competition) renderCompetition();
  if (compact()) renderCompact();
  applyPricePrecision();
  updateMarketControls(api.connected, api.busy);
  updateMarketTimer(api.clockOffset);
}
export function updateMarketControls(connected, busy) {
  if (api) { api.connected = connected; api.busy = busy; }
  if (!$('m-question')) return;
  $('m-offline').hidden = connected;
  for (const element of document.querySelectorAll('#app form button, [data-quick-side], [data-quick-qty], [data-best-price], [data-market-cancel], [data-take-side], [data-market-action]')) {
    if (['home', 'share', 'export', 'export-competition', 'retry-review'].includes(element.dataset.marketAction)) continue;
    const isCancel = element.dataset.marketCancel || element.dataset.marketAction === 'cancel-all';
    const noTrade = s.phase !== 'trading' || (s.config.mode === 'dealer' && s.me.id === s.makerId);
    const electionBlocked = element.id === 'm-spread-submit' && timedElection() && (s.phase !== 'election' || (s.deadline !== null && Date.now()+(api.clockOffset||0)>=s.deadline));
    const openingBlocked = (element.id === 'm-estimate-submit' && (s.phase !== 'opening' || !s.opening?.ready)) || (element.dataset.marketAction === 'open-market' && (s.phase !== 'opening' || s.opening.count < s.opening.required));
    const tradingSubmit = ['m-order-submit', 'm-ticket-submit'].includes(element.id);
    const noCapacity = lotMode() && tradingSubmit && lotFree($(element.id === 'm-ticket-submit' ? 'm-ticket-side' : 'm-side').value) < 1;
    element.disabled = electionBlocked || openingBlocked || noCapacity || (tradingSubmit && noTrade) || !connected || busy || (isCancel && (noTrade || !s.me.orders.length)) || (element.dataset.takeSide && (noTrade || Number(element.dataset.qty) <= 0)) || (element.dataset.marketAction === 'close-election' && !s.election.length);
  }
  if (compact()) compactControls(connected, busy);
}
export function updateMarketTimer(offset = 0) {
  if (!$('m-timer') || !s) return;
  const target = (['trading', 'maker-quote', 'reading'].includes(s.phase) || (timedElection() && s.phase === 'election')) ? s.deadline : s.phase === 'intermission' ? s.nextAt : null;
  if ($('m-election-clock')) {
    const seconds=s.deadline===null?null:Math.max(0,Math.ceil((s.deadline-Date.now()-offset)/1000));
    $('m-election-clock').textContent=seconds===null?'等待第一份价差':seconds>0?'还剩 '+seconds+' 秒 · 无更小价差即结束':'竞价已截止，正在确定做市商';
    if(s.phase==='election'&&seconds===0)$('m-spread-submit').disabled=true;
  }
  if (s.phase === 'reading' && $('m-news-state')) $('m-news-state').textContent = '读消息倒计时 ' + Math.max(0, Math.ceil((target - Date.now() - offset) / 1000)) + ' 秒 · ' + (humanMode() && s.openingPrice === null ? '随后由真人估价，主持人确认开盘。' : '随后开放完整的 ' + s.config.seconds + ' 秒交易。');
  if (compact() && s.phase === 'trading' && api.connected && Math.floor((Date.now() + offset) / 1000) !== chartSecond) renderPriceChart();
  if (compact()) { const seconds = target ? Math.max(0, Math.ceil((target - Date.now() - offset) / 1000)) : null; $('m-timer').textContent = seconds === null ? ({lobby:'待开局',opening:'待开盘',election:'竞价差',paused:'暂停',intermission:'复盘',resolution:'待答案',finished:'已结算'}[s.phase] || '') : (s.phase === 'reading' ? '读消息 ' : '') + String(Math.floor(seconds/60)).padStart(2,'0') + ':' + String(seconds%60).padStart(2,'0'); return; }
  $('m-timer').textContent = target ? (s.phase === 'intermission' ? '下轮 ' : s.phase === 'reading' ? '读消息 ' : '') + Math.max(0, Math.ceil((target - Date.now() - offset) / 1000)) + 's' : phases[s.phase];
}

function mountTerminal() {
  $('app').classList.add('market-app');
  const oldLayout = $('app').querySelector('.room-layout');
  oldLayout.classList.add('market-secondary');
  oldLayout.insertAdjacentHTML('beforebegin', '<section id="m-live-news" class="live-news" aria-live="polite"><div class="card-head"><h3 id="m-news-title">本轮消息</h3><span id="m-news-round"></span></div><p id="m-news-body"></p><p id="m-news-source" class="help"></p><p id="m-news-state" class="help"></p></section><div id="m-terminal" class="market-terminal"><div id="m-terminal-left" class="terminal-left"></div><div id="m-terminal-right" class="terminal-right"></div></div>');
  if(humanMode()) {
    $('m-live-news').insertAdjacentHTML('afterend','<section id="m-opening" class="card opening-panel" hidden><div class="card-head"><h3>报出你的估价</h3><span id="m-opening-count" class="pill"></span></div><p class="help">· 类似集合竞价<br>· 取中位数作为开盘参考价<br>· 不会买卖或占用仓位</p><form id="m-estimate-form"><div class="form-row">' + input('m-estimate','你的估价（与题目单位一致）','') + '<div class="form-end"><button id="m-estimate-submit" class="primary wide">提交 / 修改估价</button></div></div></form><p id="m-estimate-note" class="help" role="status"></p><div id="m-opening-players" class="opening-players"></div><div id="m-opening-host" class="host-controls"></div><p id="m-opening-help" class="help"></p></section>');
    $('m-estimate').min=0;$('m-estimate').max=1000000000;
    $('m-estimate').value=s.opening.mine === null ? '' : inputPrice(s.opening.mine);
    $('m-estimate-form').onsubmit=e=>submitForm(e,()=>api.sendAction('estimate',{price:cents('m-estimate')}));
    $('m-book-card').insertAdjacentHTML('beforeend','<p id="m-liquidity-note" class="help" aria-live="polite"></p>');
  }
  $('m-terminal-left').append($('m-market'), $('m-order-card'));
  $('m-terminal-right').append($('m-book-card'), $('m-account-card'));
  $('m-market').className = 'card terminal-chart';
  $('m-market').insertAdjacentHTML('beforeend', '<div class="card-head chart-title"><h3>成交价格走势</h3><span class="small">横轴：时间 · 纵轴：价格</span></div><div id="m-chart"></div><div id="m-chart-note" class="help"></div>');
  $('m-book-card').querySelector('h3').textContent = '盘口 · Bid / Ask';
  $('m-book-card').querySelector('.section-note').textContent = '点一档价格旁的买入 / 卖出，在下方确认。选中的限价保留，盘口变化不会改写。';
  $('m-book-card').insertAdjacentHTML('beforeend', '<form id="m-ticket"><h3>盘口直接交易</h3><div class="form-row"><div><label for="m-ticket-side">方向</label><select id="m-ticket-side"><option value="buy">买入</option><option value="sell">卖出</option></select></div>' + input('m-ticket-price','限价',s.price === null ? '' : inputPrice(s.price)) + '</div>' + input('m-ticket-qty','数量（' + unit() + '）',lotMode() ? '1' : '5','1') + '<p id="m-ticket-state" class="help"></p><button id="m-ticket-submit" class="primary wide">确认买入</button><p class="help">即时成交，未成交部分取消；不追价。</p></form>');
  $('m-ticket').querySelector('.form-row').append($('m-ticket-qty').parentElement);
  $('m-ticket-qty').min = 1;
  $('m-ticket').onsubmit = e => submitForm(e, () => { lastOrderInput='m-ticket-qty'; return api.sendAction(dealerMode() ? 'order' : 'take', { side: $('m-ticket-side').value, price: cents('m-ticket-price'), qty: Number($('m-ticket-qty').value) }); });
  for (const id of ['m-ticket-side','m-ticket-price','m-ticket-qty']) $(id).oninput = updateTicket;
  $('m-order-card').querySelector('h3').textContent = '快速买卖';
  $('m-order-form').insertAdjacentHTML('afterbegin', '<div class="quick-sides"><button type="button" data-quick-side="buy">买入</button><button type="button" data-quick-side="sell">卖出</button></div>');
  $('m-side').parentElement.hidden = true;
  $('m-kind').parentElement.parentElement.classList.add('single-field');
  $('m-order-submit').insertAdjacentHTML('beforebegin','<div class="quick-amounts"><button type="button" data-quick-qty="1">1 ' + unit() + '</button><button type="button" data-quick-qty="5">5 ' + unit() + '</button><button type="button" data-quick-qty="10">10 ' + unit() + '</button><button type="button" data-quick-qty="max">最大数量</button><button type="button" data-best-price>填入对手最优价</button></div>');
  $('m-order-submit').insertAdjacentHTML('afterend','<p id="m-feedback" class="help" role="status">填写限价和数量后提交。行情更新不会清空输入。</p>');
}
function updateQuick() {
  const side = $('m-side').value;
  for (const b of document.querySelectorAll('[data-quick-side]')) { b.classList.toggle('selected', b.dataset.quickSide === side); b.setAttribute('aria-pressed', String(b.dataset.quickSide === side)); }
  if (lotMode()) $('m-qty').max = lotFree(side);
  $('m-order-submit').textContent = side === 'buy' ? '提交买入' : '提交卖出';
  if (dealerMode()) renderDealerCapacity();
  if (compact()) { $('m-order-submit').textContent = ($('m-kind').value==='take'?'市价':'') + (side === 'buy' ? '买入' : '卖出'); if($('c-market-price'))$('c-market-price').setAttribute('aria-pressed',String($('m-kind').value==='take')); $('m-order-submit').classList.toggle('selling',side === 'sell'); $('c-max').textContent = side === 'buy' ? '全部可买' : '全部可卖'; }
  updateMarketControls(api.connected, api.busy);
}
function updateTicket() {
  if (!$('m-ticket')) return;
  const side = $('m-ticket-side').value, price = Number($('m-ticket-price').value) * 100;
  const levels = terminalBook()?.[side === 'buy' ? 'sell' : 'buy'] || [];
  const qty = levels.filter(x => side === 'buy' ? x.price <= price : x.price >= price).reduce((n,x)=>n+x.qty-x.ownQty,0);
  $('m-ticket-qty').max = capacity(side,price);
  $('m-ticket-state').textContent = '该限价内当前对手挂单 ' + qty + ' ' + unit() + (lotMode() ? ' · 本方向还可交易 ' + lotFree(side) + ' 手' : ' · 可用现金 ' + money(s.me.available.cash) + ' · 可卖 ' + s.me.available.shares + ' 份');
  updateMarketControls(api.connected, api.busy);
  $('m-ticket-submit').textContent = side === 'buy' ? '确认买入 · 剩余取消' : '确认卖出 · 剩余取消';
  if (compact()) { $('m-ticket-state').textContent = '可' + (side === 'buy' ? '买 ' : '卖 ') + capacity(side,price) + ' ' + unit() + (dealerMode() ? ' · 轮末成交' : ' · 对手 ' + qty + ' 手'); $('m-ticket-submit').textContent = (dealerMode() ? '提交' : '确认') + (side === 'buy' ? '买入' : '卖出'); $('c-ticket').classList.toggle('selling',side==='sell'); $('c-ticket-label').textContent = (side === 'buy' ? '买入 ' : '卖出 ') + money(Number($('m-ticket-price').value)*100); if(compactTicket) positionCompactTicket(); }
  applyPricePrecision();
}
function renderOpening() {
  const show=s.openingPrice === null && !['lobby','finished'].includes(s.phase);
  $('m-opening').hidden=!show;
  $('m-opening-count').textContent=s.opening.count+' / '+s.humans+' 人已提交';
  $('m-estimate-note').textContent=s.opening.mine===null ? '尚未提交估价。第一条提示将在开盘时公布。' : '你的已提交估价：'+quotePrice(s.opening.mine)+'；可修改后再次提交。';
  $('m-opening-players').innerHTML=s.opening.players.map(p=>'<span>'+esc(p.name)+' · '+(p.submitted?'已提交':'待提交')+'</span>').join('');
  $('m-opening-host').innerHTML=s.isHost?button('open-market','公布第一条提示，开始交易','primary'):'';
  $('m-opening-help').textContent=s.isHost ? (s.opening.count ? '已有 '+s.opening.count+' 人估价，可直接确认开盘，无需等齐。' : '任意一人提交估价后即可确认开盘，无需等齐。') : '估价可跳过；主持人确认开盘后即可交易。';
}
function renderTerminal() {
  if ($('m-liquidity-note')) $('m-liquidity-note').textContent = s.liquidity.enabled ? s.liquidity.status + '。真人互相成交 ' + s.liquidity.humanVolume + ' 手 · 程序成交 ' + s.liquidity.programVolume + ' 手 · 单次最多补 ' + s.liquidity.remaining + ' 手。' : '流动性辅助已关闭，全部由真人交易。';
  if (humanMode() && s.openingPrice !== null) for(const id of ['m-order-price','m-ticket-price']) if(!$(id).value && document.activeElement!==$(id)) $(id).value=inputPrice(s.openingPrice);
  const signals = [...s.signals, ...s.messages].reverse().sort((a,b)=>b.round-a.round||b.at-a.at);
  const latest = signals[0];
  $('m-live-news').hidden = s.phase === 'lobby';
  const key = JSON.stringify(latest ?? null);
  if (key !== lastSignal) {
    $('m-news-title').textContent = latest?.title || '主持人消息';
    $('m-news-round').textContent = latest ? '第 ' + latest.round + ' 轮 · 已公开 ' + signals.length + ' 条' : '第 ' + s.round + ' 轮';
    $('m-news-body').textContent = latest?.text || '本轮暂无新线索，等待主持人发布。';
    $('m-news-source').innerHTML = sourceLink(latest);
    if (latest && compact() && ['reading','maker-quote','trading'].includes(s.phase)) {
      const news = $('c-news');
      news.classList.remove('is-new');
      void news.offsetWidth;
      news.classList.add('is-new');
      news.onanimationend = event => {
        if (event.animationName !== 'ct-news-arrival') return;
        news.classList.remove('is-new');
        $('c-round').textContent = $('c-round').textContent.replace('新消息', '消息');
      };
    }
    if (lastSignal && latest) api.toast('第 ' + latest.round + ' 轮新消息已发布，请看顶部线索');
    if (!compact() && latest && latest.round !== newsRound && s.phase === 'reading' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)) $('m-live-news').scrollIntoView({behavior:'smooth',block:'start'});
    newsRound = latest?.round ?? -1;
    lastSignal = key;
  }
  $('m-news-state').textContent = s.phase === 'reading' ? (humanMode() && s.openingPrice === null ? '先读消息，随后提交开盘估价；确认开盘后再开始交易计时。' : '先读消息，倒计时结束后开放完整的 ' + s.config.seconds + ' 秒交易。') : s.phase === 'finished' ? '交易结束，答案及来源见下方结算。' : latest && latest.round < s.round ? '本轮尚未发布新线索，上方为上一条公开消息。' : '历史消息保留在下方信息时间线。';
  if (humanMode() && s.openingPrice === null) { $('m-chart').innerHTML='<p class="empty">等待真人估价形成开盘参考价。</p>'; $('m-chart-note').textContent=''; return; }
  renderPriceChart();
}

function renderPriceChart() {
  if (!$('m-chart') || s.price === null) return;
  const now = Date.now() + (api.clockOffset || 0);
  chartSecond = Math.floor(now / 1000);
  const start = s.roundStarts?.[0]?.at;
  const values = s.priceSeries || s.trades || [];
  const data = [{at: start || values[0]?.at || 0, price: humanMode() ? s.openingPrice : s.config.initialPrice}, ...values];
  const min = Math.min(...data.map(x=>x.price)), max = Math.max(...data.map(x=>x.price));
  const pad = Math.max(1, (max-min)*.15, (humanMode() ? s.openingPrice : s.config.initialPrice)*.003), lo=min-pad, hi=max+pad;
  const t0=data[0].at;
  chartEnd = Math.max(chartEnd, data.at(-1).at, s.history?.at(-1)?.at || 0, s.roundStarts?.at(-1)?.at || 0);
  if (s.phase === 'trading' && api.connected) chartEnd = Math.max(chartEnd, Math.min(now, s.deadline || now));
  // Keep a full-round time axis so the live point visibly advances each second.
  const t1 = Math.max(t0 + 1000, chartEnd, s.deadline || 0);
  if (data.at(-1).at < chartEnd) data.push({at:chartEnd,price:data.at(-1).price});
  // Connect actual timestamped prices diagonally. Simultaneous fills share one
  // chart point (the last price); their individual executions remain in review.
  const points = [...new Map(data.map(p => [p.at, p])).values()];
  const w = window.innerWidth < 700 ? (compact() ? 250 : 350) : 710, left = compact() && window.innerWidth < 700 ? 57 : 66, right = w - 12;
  const x=t=>left+(t-t0)/(t1-t0)*(right-left), y=p=>214-(p-lo)/(hi-lo)*184;
  const grid=Array.from({length:5},(_,i)=>{const p=lo+(hi-lo)*i/4;return '<line x1="'+left+'" x2="'+right+'" y1="'+y(p)+'" y2="'+y(p)+'" stroke="#dce2d9"/><text x="'+(left-8)+'" y="'+(y(p)+4)+'" text-anchor="end">'+axisPrice(p)+'</text>';}).join('');
  const markers=(s.roundStarts||[]).filter(r=>r.at<=t1).map(r=>'<line x1="'+x(r.at)+'" x2="'+x(r.at)+'" y1="24" y2="214" stroke="#9aa9a3" stroke-dasharray="3 5"/><text x="'+Math.min(right-42,x(r.at)+4)+'" y="16">第 '+r.round+' 轮</text>').join('');
  const last=data.at(-1);
  $('m-chart').innerHTML='<svg '+(compact()?'preserveAspectRatio="none" ':'')+'viewBox="0 0 '+w+' 250" role="img" aria-label="成交价格随时间变化；虚线表示每轮开始。">'+grid+markers+'<polyline points="'+points.map(p=>x(p.at)+','+y(p.price)).join(' ')+'" fill="none" stroke="#167b5b" stroke-width="2.5"/><circle cx="'+x(last.at)+'" cy="'+y(last.price)+'" r="3" fill="#167b5b"/><text x="'+left+'" y="240">开局</text><text x="'+right+'" y="240" text-anchor="end">'+Math.max(0,Math.round((chartEnd-t0)/1000))+' / '+Math.round((t1-t0)/1000)+' 秒</text></svg>';
  $('m-chart-note').textContent = values.length ? '按实际成交绘制，虚线标记换轮；无成交时不虚构价格变化。' : (humanMode() ? '尚未成交，当前显示真人估价形成的开盘参考价。' : '尚未成交，当前显示初始参考价。');
}

window.addEventListener('resize', () => { if ($('m-chart') && s) renderTerminal(); });

function mountCompetition() {
  $('m-live-news').insertAdjacentHTML('beforebegin', '<section id="m-competition" class="card competition-panel" aria-label="本场比赛"><div id="m-competition-content"></div></section><section id="m-public-review" class="card competition-panel" hidden><details id="m-review-details"><summary>全员逐笔交易复盘</summary><p class="help">已结束轮次的成交向所有人公开。选玩家与轮次，一起分析交易；新题开始后仍可回看历史。宽表格可左右滑动。</p><div class="review-filters"><div><label for="m-review-game">题目</label><select id="m-review-game"></select></div><div><label for="m-review-round">轮次</label><select id="m-review-round"></select></div><div><label for="m-review-player">玩家</label><select id="m-review-player"></select></div></div><p id="m-review-note" class="help"></p><div id="m-review-rows"></div></details></section>');
  for (const field of ['game', 'round', 'player']) $('m-review-' + field).onchange = () => {
    if (field === 'game') { reviewGame = $('m-review-game').value; reviewRound = ''; reviewPlayer = ''; }
    if (field === 'round') reviewRound = $('m-review-round').value;
    if (field === 'player') reviewPlayer = $('m-review-player').value;
    renderPublicReview();
  };
}
const points = n => Number(n).toLocaleString('zh-CN', { maximumFractionDigits: 1 });
function standingsTable(c) {
  return '<div class="competition-scroll" tabindex="0" aria-label="累计积分表，可横向滚动"><table class="competition-table"><thead><tr><th>名次</th><th>玩家</th>' + c.games.filter(g => !g.practice).map(g => '<th>' + esc(g.label) + '</th>').join('') + '<th>总积分</th><th>第一 / 第二次数</th></tr></thead><tbody>' + c.standings.map(p => '<tr' + (p.id === s.me.id ? ' class="my-result"' : '') + '><td>' + p.rank + '</td><th scope="row">' + esc(p.name) + '</th>' + p.results.map(r => '<td>' + points(r.points) + '<span class="result-detail">' + (r.rank === null ? '未参加' : '第 ' + r.rank + ' 名') + '</span></td>').join('') + '<td><strong>' + points(p.points) + '</strong></td><td>' + p.wins + ' / ' + p.seconds + '</td></tr>').join('') + '</tbody></table></div>';
}
function renderCompetition() {
  const c = s.competition, final = s.phase === 'finished', between = final || s.phase === 'lobby';
  const key = JSON.stringify([c.gameNumber, c.label, c.finalized, s.phase, c.standings, s.isHost]);
  if (key !== competitionKey) {
    const current = c.games.find(g => g.number === c.gameNumber);
    let html = '<div class="card-head"><h2>' + (c.finalized ? '本场总排名' : esc(c.label) + ' · ' + (final ? '结算与复盘' : s.phase === 'intermission' ? '轮间复盘' : s.phase === 'lobby' ? '等待主持人开始' : '比赛进行中')) + '</h2><span class="small">已完成 ' + c.scoredGameCount + ' 道正式题</span></div>';
    if (c.finalized) {
      const winners = c.standings.filter(p => p.rank === 1);
      html += '<p class="competition-winner">' + (winners.length > 1 ? '并列总冠军：' : '总冠军：') + winners.map(p => esc(p.name)).join('、') + '</p><p class="help">本场成绩已锁定，所有人可以继续查看和下载复盘。</p>';
    }
    if (final && current && !c.finalized) {
      html += '<h3>' + (current.practice ? '测试版排名 · 不计分' : '本局排名') + '</h3><div class="competition-scroll" tabindex="0" aria-label="本局排名"><table class="competition-table"><thead><tr><th>名次</th><th>玩家</th><th>最终盈亏</th><th>本局积分</th></tr></thead><tbody>' + current.ranking.map(p => '<tr' + (p.id === s.me.id ? ' class="my-result"' : '') + '><td>' + p.rank + '</td><th scope="row">' + esc(p.name) + '</th><td>' + signed(p.pnl) + '</td><td><strong>' + (current.practice ? '不计分' : '+' + points(p.points)) + '</strong></td></tr>').join('') + '</tbody></table></div>';
    }
    if (c.scoredGameCount) {
      const table = standingsTable(c);
      html += between || c.finalized ? '<h3 class="competition-subtitle">' + (c.finalized ? '最终成绩' : '累计积分榜') + '</h3>' + table : '<details><summary>累计积分榜 · 已完成 ' + c.scoredGameCount + ' 道正式题</summary>' + table + '</details>';
    } else html += '<p class="help">' + (c.practice ? '测试版不计入累计积分，交易记录可在下方复盘。' : '本题答案公布后计入正式积分。' + s.humans + ' 位真人参与，第一名 ' + s.humans + ' 分，依次递减至 1 分。') + '</p>';
    html += '<p class="help">正式题各计一次积分，题内轮次不重复计分；测试版不计分，也不累计第一、第二名次数。并列名次平分所占名次的积分；总分相同比第一名次数，再比第二名次数，仍相同则并列。交易盈亏与比赛积分分别计算。</p>';
    if (!c.finalized && s.phase === 'intermission') html += '<p class="competition-pause">第 ' + s.round + ' 轮已结束，交易暂停。请查看下方全员复盘，等待主持人开始下一轮。</p>' + (s.isHost ? button('next', '发布下一条线索，开始第 ' + (s.round + 1) + ' 轮', 'primary') : '');
    if (!c.finalized && final && s.isHost) {
      const played = new Set(c.games.map(g => g.scenarioId));
      const options = [...s.nextScenarios].sort((a, b) => Number(played.has(a.id)) - Number(played.has(b.id)));
      html += '<div class="next-question"><label for="m-next-question">下一道题</label><select id="m-next-question">' + options.map(x => '<option value="' + esc(x.id) + '">' + esc(x.name) + ' · ' + x.rounds + ' 轮' + (played.has(x.id) ? '（已玩，可重玩）' : '') + '</option>').join('') + '</select><div class="host-controls">' + button('next-game', '准备下一题', 'primary') + (s.config.scenario !== 'script' ? button('reset', '再玩当前题目') : '') + '</div><p class="help">准备后保留房间和玩家，账户从空仓重新开始；由你点击“开始本题”进入估价，开盘后发布线索。</p></div>';
    } else if (!c.finalized && final) html += '<p class="competition-pause">等待主持人选择下一道题，或展示本场总排名。</p>';
    if (c.games.length) html += '<div class="host-controls competition-actions">' + (c.scoredGameCount && !c.finalized && between && s.isHost ? button('finalize-competition', '结束比赛，展示总排名') : '') + button('export-competition', '下载比赛成绩与全员复盘') + '</div>';
    $('m-competition-content').innerHTML = html;
    competitionKey = key;
  }
  const nextReviewKey = JSON.stringify([c.gameNumber, s.review, c.games.length]);
  if (nextReviewKey !== reviewKey) {
    if (s.review?.throughRound) reviewGame = String(c.gameNumber);
    renderPublicReview();
    if (['intermission', 'resolution', 'finished'].includes(s.phase)) $('m-review-details').open = true;
    reviewKey = nextReviewKey;
  }
  if (c.finalized) { $('m-terminal').hidden = true; $('m-live-news').hidden = true; $('m-lobby').hidden = true; $('m-host').hidden = true; }
  if (competitionPhase !== s.phase || competitionFinalized !== c.finalized) {
    if (!compact() && (['intermission', 'finished'].includes(s.phase) || c.finalized)) $('m-competition').scrollIntoView({ block: 'start' });
    else if (['reading', 'opening', 'trading'].includes(s.phase)) {
      $('m-review-details').open = false;
      if (!compact() && ['intermission', 'lobby'].includes(competitionPhase)) $('m-live-news').scrollIntoView({ block: 'start' });
    }
    competitionPhase = s.phase; competitionFinalized = c.finalized;
  }
}
function renderPublicReview() {
  const c = s.competition;
  const games = c.games.map(g => ({ ...g }));
  if (s.review?.throughRound && !games.some(g => g.number === c.gameNumber)) games.push({ number: c.gameNumber, label: c.label, question: s.config.question, review: s.review });
  $('m-public-review').hidden = !games.length;
  if (!games.length) return;
  let selected = games.find(g => String(g.number) === reviewGame) || games.at(-1);
  reviewGame = String(selected.number);
  const cacheKey=s.code+':'+selected.number+':'+selected.review.revision;
  const data=selected.review.lazy ? reviewCache.get(cacheKey) : selected.review;
  $('m-review-game').innerHTML = games.map(g => '<option value="' + g.number + '">' + esc(g.label) + ' · ' + esc(g.question) + '</option>').join('');
  $('m-review-game').value = reviewGame;
  if(!data){
    const visible=!compact() || compactPanel==='review';
    $('m-review-round').innerHTML='<option value="">全部已结束轮次</option>';
    $('m-review-player').innerHTML='<option value="">全部真人</option>';
    $('m-review-rows').innerHTML='';
    const error=reviewErrors.get(cacheKey);
    $('m-review-note').textContent=error|| (visible?'正在加载逐笔交易记录…':'打开复盘后加载逐笔交易记录。');
    if(error)$('m-review-rows').innerHTML=button('retry-review','重新加载');
    if(visible&&!error&&!reviewLoading.has(cacheKey)){
      reviewLoading.add(cacheKey);const code=s.code;
      api.requestResource('review',{gameNumber:selected.number}).then(result=>{
        reviewCache.set(code+':'+result.gameNumber+':'+result.revision,result.review);
        // Old responses never replace a newly selected question or a newer round.
      }).catch(error=>reviewErrors.set(cacheKey,error.message)).finally(()=>{
        reviewLoading.delete(cacheKey);
        if(s.code===code&&$('m-public-review')&&(!compact()||compactPanel==='review'))renderPublicReview();
      });
    }
    return;
  }
  $('m-review-round').disabled=false;$('m-review-player').disabled=false;
  $('m-review-round').innerHTML = '<option value="">全部已结束轮次</option>' + Array.from({ length: data.throughRound }, (_, i) => '<option value="' + (i + 1) + '">第 ' + (i + 1) + ' 轮</option>').join('');
  $('m-review-round').value = reviewRound;
  $('m-review-player').innerHTML = '<option value="">全部真人</option>' + data.players.map(p => '<option value="' + esc(p.id) + '">' + esc(p.name) + '</option>').join('');
  $('m-review-player').value = reviewPlayer;
  const players = data.players.filter(p => reviewPlayer ? p.id === reviewPlayer : !p.bot);
  $('m-review-note').textContent = '已公开至第 ' + data.throughRound + ' 轮。每笔平仓盈亏按先进先出计算，最终持仓另按答案结算；未成交委托不计入成交明细。';
  $('m-review-rows').innerHTML = players.map(p => {
    const trades = p.trades.filter(t => !reviewRound || t.round === Number(reviewRound));
    return '<section class="review-player"><h3>' + esc(p.name) + ' <span class="small">' + trades.length + ' 笔成交</span></h3>' + (trades.length ? '<div class="competition-scroll" tabindex="0" aria-label="' + esc(p.name) + '的逐笔成交，可横向滚动"><table class="competition-table review-table"><thead><tr><th>轮次 / 时间</th><th>方向</th><th>成交价 × 手数</th><th>交易对手</th><th>成交后持仓</th><th>本笔平仓盈亏</th></tr></thead><tbody>' + trades.map(t => '<tr><td>第 ' + t.round + ' 轮<span class="result-detail">' + new Date(t.at).toLocaleTimeString('zh-CN', { hour12: false }) + ' · #' + t.id + '</span></td><td>' + (t.side === 'buy' ? '买入' : '卖出') + '</td><td>' + money(t.price) + ' × ' + t.qty + '</td><td>' + esc(t.counterparty) + '</td><td>' + (t.positionAfter > 0 ? '多 ' + t.positionAfter : t.positionAfter < 0 ? '空 ' + -t.positionAfter : '空仓') + (t.positionAfter ? ' 手' : '') + '</td><td>' + signed(t.realizedPnl) + '</td></tr>').join('') + '</tbody></table></div>' : '<p class="help">所选轮次没有成交。</p>') + '</section>';
  }).join('');
}

// Compact terminal reuses the authenticated forms and original competition/review panels.
function mountCompact() {
  compactPanel='';compactPhase='';compactFinalized=false;compactBookKey='';compactTicket=null;
  document.body.classList.add('compact-active');$('app').classList.add('compact-market');$('app').classList.toggle('dealer-terminal',dealerMode());
  const legacy=document.createElement('div');legacy.id='c-legacy';legacy.hidden=true;
  for(const child of [...$('app').children])if(child.id!=='m-confirm')legacy.append(child);
  $('app').prepend(legacy);
  const closeIcon='<svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 5 10 10M15 5 5 15"/></svg>';
  legacy.insertAdjacentHTML('beforebegin',`<section id="c-terminal" class="ct-shell"><header class="ct-instrument"><div id="c-title"><p id="c-unit"></p></div><button type="button" data-market-action="share" id="c-room"></button></header><div id="c-warnings"></div><section id="c-answer" class="ct-answer" aria-live="polite" hidden><h2>最终答案</h2><p><strong id="c-answer-value"></strong><span id="c-answer-unit"></span></p><div id="c-answer-note"></div></section><div id="c-lobby"></div><div id="c-quote-news" class="ct-quote-news"><div class="ct-quote"><span id="c-price-label">最新成交</span><div id="c-price"></div><p id="c-price-note"></p></div><section class="ct-news" id="c-news" aria-live="polite"><div class="ct-news-meta"><strong id="c-round"></strong><span id="c-clock"></span></div><div id="c-news-body"></div><button type="button" data-c-panel="messages" aria-label="查看历史消息">›</button></section></div><div id="c-opening"></div><div id="c-trading"><section class="ct-market"><div class="ct-chart"><div class="ct-market-heading"><strong>分时</strong><span id="c-open-price"></span></div><div id="c-chart"></div></div><div class="ct-book"><div class="ct-market-heading"><strong>Bid / Ask</strong><span>手</span></div><div id="c-asks"></div><div class="ct-spread"><span>价差</span><span id="c-spread"></span></div><div id="c-bids"></div></div></section><section class="ct-dock"><div id="c-order"></div><aside class="ct-capacity"><p id="c-position"></p><small>净持仓 ±10 手</small><small>本轮可多次交易</small><div><span>可买</span><strong id="c-buy-free"></strong><small>手</small></div><div><span>可卖</span><strong id="c-sell-free"></strong><small>手</small></div><p class="ct-pnl"><span>盈亏</span><strong id="c-pnl"></strong></p></aside></section></div><nav class="ct-tabs" aria-label="交易工具"><button data-c-panel="orders">委托 / 撤单 <span id="c-order-count">0</span></button><button data-c-panel="fills">成交</button><button data-c-panel="ranking">积分榜</button><button data-c-panel="review">复盘</button><button data-c-panel="host" id="c-host-tab">主持人</button><button data-c-panel="rules">更多</button></nav></section><section class="ct-drawer" id="c-drawer" hidden><header><h2 id="c-panel-title"></h2><button type="button" data-c-close aria-label="收起面板">${closeIcon}</button></header><div id="c-panel-orders" hidden><div class="host-controls">${button('cancel-all','全部撤单')}</div></div><div id="c-panel-fills" hidden></div><div id="c-panel-ranking" hidden></div><div id="c-panel-review" hidden><div id="c-review-next"></div></div><div id="c-panel-host" hidden></div><div id="c-panel-messages" hidden></div><div id="c-panel-rules" hidden>${button('share','邀请朋友')}${button('home','返回首页')}</div></section><div id="c-ticket" class="ct-ticket" role="dialog" aria-label="盘口下单" tabindex="-1" hidden><header><strong id="c-ticket-label"></strong><button type="button" data-c-ticket-close aria-label="关闭盘口下单">${closeIcon}</button></header><div id="c-ticket-own" class="ct-ticket-own" hidden></div><div id="c-ticket-form"></div><p id="c-ticket-status" role="status"></p></div>`);
  const move=(id,to)=>{if($(id))$(to).append($(id));};
  $('c-title').prepend($('m-question'));move('m-offline','c-warnings');move('m-notice','c-warnings');move('m-lobby','c-lobby');
  move('m-price','c-price');move('m-timer','c-clock');move('m-news-body','c-news-body');move('m-opening','c-opening');move('m-chart','c-chart');
  const form=$('m-order-form');move('m-order-form','c-order');form.hidden=false;
  const field=(id,label,step)=>{const wrapper=document.createElement('div');wrapper.className='ct-field';wrapper.innerHTML='<label for="'+id+'">'+label+'</label><button type="button" data-c-step="'+id+':-'+step+'" aria-label="'+label+'减一">−</button>';wrapper.append($(id));wrapper.insertAdjacentHTML('beforeend','<button type="button" data-c-step="'+id+':'+step+'" aria-label="'+label+'加一">+</button>');return wrapper;};
  legacy.append($('m-free'));
  const sides=form.querySelector('.quick-sides');sides.className='ct-sides';
  const price=field('m-order-price','价格',1), qty=field('m-qty',lotMode()?'手数':'份数',1), submit=$('m-order-submit'), feedback=$('m-feedback');
  // Retain the direction and order-kind controls for the existing submit handler.
  const hidden=document.createElement('div');hidden.hidden=true;hidden.append($('m-side'),$('m-kind'));hidden.querySelector('#m-kind').value='order';
  const sideRow=document.createElement('div');sideRow.className='ct-side-row';sideRow.append(sides);sideRow.insertAdjacentHTML('beforeend','<button type="button" id="c-market-price" data-best-price aria-pressed="false" title="填入对手最优价，未成交部分取消">市价</button>');form.replaceChildren(sideRow,hidden);price.querySelector('input').addEventListener('input',()=>{ $('m-kind').value='order';updateQuick(); });const fields=document.createElement('div');fields.className='ct-fields';fields.append(price,qty);form.append(fields);
  form.insertAdjacentHTML('beforeend','<div class="ct-quick"><button type="button" data-quick-qty="1">1 手</button><button type="button" data-quick-qty="5">5 手</button><button type="button" data-quick-qty="max" id="c-max">全部可买</button></div>');form.append(submit,feedback);
  move('m-orders','c-panel-orders');move('m-fills','c-panel-fills');move('m-account-card','c-panel-fills');move('m-competition','c-panel-ranking');move('m-final','c-panel-ranking');move('m-public-review','c-panel-review');move('m-host','c-panel-host');move('m-resolution','c-panel-host');move('m-signals','c-panel-messages');move('m-rules','c-panel-rules');move('m-history','c-panel-rules');
  const ticket=$('m-ticket');move('m-ticket','c-ticket-form');const ticketHidden=document.createElement('div');ticketHidden.hidden=true;ticketHidden.append($('m-ticket-side'),$('m-ticket-price'));const ticketQty=field('m-ticket-qty',lotMode()?'手数':'份数',1),ticketState=$('m-ticket-state'),ticketSubmit=$('m-ticket-submit');
  ticket.replaceChildren(ticketHidden,ticketQty);ticket.insertAdjacentHTML('beforeend','<div class="ct-quick"><button type="button" data-c-ticket-qty="1">1 手</button><button type="button" data-c-ticket-qty="5">5 手</button><button type="button" data-c-ticket-qty="max">最大</button></div>');ticket.append(ticketState,ticketSubmit);
  if(dealerMode()) mountDealerCompact(move);
  for(const id of ['m-order-price','m-qty']) $(id).addEventListener('input',()=>{if(dealerMode())renderDealerCapacity();});
}
function fillMarketPrice() {
  const side=$('m-side').value, best=(terminalBook()?.[side==='buy'?'sell':'buy']||[]).find(l=>l.qty>l.ownQty);
  if(!best){$('m-kind').value='order';$('m-feedback').textContent='暂无可成交的对手报价';api.toast('暂无可成交的对手报价');return;}
  $('m-kind').value=dealerMode()?'order':'take';$('m-order-price').value=inputPrice(best.price);
  $('m-feedback').textContent=dealerMode()?'已填入做市商报价，提交后轮末撮合':'按 '+quotePrice(best.price)+' 即时成交，未成交部分取消；修改价格可恢复挂单';
  if(dealerMode())renderDealerCapacity();
}
function renderCompactTicket() {
  if(!compactTicket)return;
  const {side,price}=compactTicket, bookSide=side==='buy'?'sell':'buy';
  const own=s.me.orders.filter(o=>o.side===bookSide&&o.price===price), ownQty=own.reduce((n,o)=>n+o.qty,0);
  const level=(terminalBook()?.[bookSide]||[]).find(l=>l.price===price), others=level?level.qty-level.ownQty:0;
  const content=ownQty ? '<p>我的'+(bookSide==='buy'?'买单':'卖单')+' · '+ownQty+' 手</p><button type="button" data-c-cancel-level>撤销此价位我的 '+ownQty+' 手</button>' : '';
  if($('c-ticket-own').innerHTML!==content)$('c-ticket-own').innerHTML=content;
  $('c-ticket-own').hidden=!ownQty;
  $('c-ticket-form').hidden=ownQty>0&&others<=0;
  $('c-ticket-label').textContent=(ownQty?'价位 ':side==='buy'?'买入 ':'卖出 ')+quotePrice(price);
  if(!ownQty&&others<=0){$('c-ticket-form').hidden=true;$('c-ticket-status').textContent='该价位已无挂单';}
  compactControls(api.connected,api.busy);
}
function compactCloseTicket(){compactTicket=null;if($('c-ticket'))$('c-ticket').hidden=true;}
function compactSetPanel(name, scroll=false){compactPanel=name;const titles={orders:'当前委托',fills:'成交与账户',ranking:dealerMode()?'本局排名':'比赛积分',review:dealerMode()?'逐轮复盘':'全员交易复盘',host:'主持人控制',messages:'消息记录',rules:'规则与记录'};for(const key of Object.keys(titles))$('c-panel-'+key).hidden=key!==name;$('c-drawer').hidden=!name;$('c-panel-title').textContent=titles[name]||'';for(const b of document.querySelectorAll('[data-c-panel]'))b.setAttribute('aria-expanded',String(b.dataset.cPanel===name));if(name==='review'&&$('m-review-details')){$('m-review-details').open=true;renderPublicReview();}if(scroll&&name)$('c-drawer').scrollIntoView({block:'nearest',behavior:'smooth'});}
function compactClick(e){
  const panel=e.target.closest('[data-c-panel]');if(panel){compactCloseTicket();compactSetPanel(compactPanel===panel.dataset.cPanel?'':panel.dataset.cPanel,true);return true;}
  if(e.target.closest('[data-c-close]')){compactSetPanel('');return true;}
  if(e.target.closest('[data-c-ticket-close]')){compactCloseTicket();return true;}
  const step=e.target.closest('[data-c-step]');if(step){const [id,delta]=step.dataset.cStep.split(':');const el=$(id);if(id==='m-order-price'){$('m-kind').value='order';updateQuick();}el.value=Math.max(Number(el.min)||0,Math.min(el.max===''?Infinity:Number(el.max),Math.round(((Number(el.value)||0)+Number(delta))*100)/100));if(dealerMode())renderDealerCapacity();return true;}
  const qty=e.target.closest('[data-c-ticket-qty]');if(qty){$('m-ticket-qty').value=qty.dataset.cTicketQty==='max'?capacity($('m-ticket-side').value,Number($('m-ticket-price').value)*100):Math.min(Number(qty.dataset.cTicketQty),capacity($('m-ticket-side').value,Number($('m-ticket-price').value)*100));return true;}
  return false;
}
function positionCompactTicket(){if(!compactTicket||!$('c-ticket'))return;const anchor=[...document.querySelectorAll('.ct-level[data-take-side]')].find(e=>e.dataset.takeSide===compactTicket.side&&Number(e.dataset.price)===compactTicket.price);if(!anchor)return;const r=anchor.getBoundingClientRect(),p=$('c-ticket'),width=p.offsetWidth,height=p.offsetHeight;let left=r.left-width-8;if(left<8)left=Math.max(8,Math.min(innerWidth-width-8,r.right+8));p.style.left=left+'px';p.style.top=Math.max(8,Math.min(innerHeight-height-8,r.top-height/2+r.height/2))+'px';}
function compactControls(connected,busy){if(!$('c-terminal'))return;const trading=s.phase==='trading'&&(!dealerMode()||s.me.id!==s.makerId);for(const b of document.querySelectorAll('[data-c-step], [data-c-ticket-qty]'))b.disabled=!connected||busy||!trading;for(const b of document.querySelectorAll('.ct-level[data-take-side]'))b.disabled=!connected||busy||!trading||(Number(b.dataset.qty)<=0 && Number(b.dataset.ownQty||0)<=0);if($('c-market-price'))$('c-market-price').disabled=!connected||busy||!trading;for(const b of document.querySelectorAll('[data-c-cancel-level]'))b.disabled=!connected||busy||!trading;if(compactTicket){const levels=terminalBook()?.[compactTicket.side==='buy'?'sell':'buy']||[];const total=levels.filter(l=>compactTicket.side==='buy'?l.price<=compactTicket.price:l.price>=compactTicket.price).reduce((n,l)=>n+l.qty-l.ownQty,0);$('m-ticket-submit').disabled=!connected||busy||!trading||total<=0||capacity(compactTicket.side,compactTicket.price)<=0;}}
function renderCompact(){
  const lobby=s.phase==='lobby', discover=humanMode()&&s.openingPrice===null, final=s.phase==='finished', finalized=s.competition?.finalized;
  $('c-answer').hidden=!final;
  if(final){$('c-answer-value').textContent=(s.settlementPrice/100).toLocaleString('zh-CN',{maximumFractionDigits:2});$('c-answer-unit').textContent=s.config.unit.split('/')[0].trim();$('c-answer-note').textContent=s.resolution?.note||'';}
  $('c-unit').innerHTML='<strong>单位：'+esc(s.config.unit)+'</strong><span>'+esc((s.competition?.label || MODES[s.config.mode].name)+' · '+precisionLabel())+'</span>';$('c-room').textContent=s.code+' · '+s.humans+' 人';
  $('c-quote-news').hidden=lobby||discover;$('c-trading').hidden=lobby||discover||finalized;$('c-host-tab').hidden=!s.isHost||lobby||finalized;
  $('m-price').textContent=s.price===null?'待形成':(s.price/100).toLocaleString('zh-CN',{maximumFractionDigits:2});
  $('c-price-label').textContent=s.trades.length?'最新成交':'开盘参考';$('c-price-note').textContent=discover?'等待真人估价':s.trades.length?'本轮 '+s.roundVolume+' '+unit():'尚无成交';
  $('c-round').textContent=($('c-news').classList.contains('is-new')?'新消息 ':'消息 ')+s.round+' / '+s.config.rounds;$('c-open-price').textContent='开盘 '+(s.openingPrice===null?'—':quotePrice(humanMode()?s.openingPrice:s.config.initialPrice));
  if(!dealerMode()){$('c-position').textContent='持仓 '+position().replace('头','');$('c-buy-free').textContent=lotFree('buy');$('c-sell-free').textContent=lotFree('sell');}$('c-pnl').textContent=signed(s.me.pnl);
  $('c-order-count').textContent=s.me.orders.length;const side=$('m-side').value;$('m-order-submit').textContent=($('m-kind').value==='take'?'市价':'')+(side==='buy'?'买入':'卖出');$('c-market-price').setAttribute('aria-pressed',String($('m-kind').value==='take'));$('m-order-submit').classList.toggle('selling',side==='sell');$('c-max').textContent=side==='buy'?'全部可买':'全部可卖';
  $('m-order-form').hidden=false;$('c-order').hidden=final||s.phase==='resolution';$('c-host-tab').textContent=s.phase==='resolution'?'公布答案':'主持人';
  const displayBook=terminalBook();
  const key=JSON.stringify([displayBook,s.phase]);if(compactBookKey!==key){for(const side of ['sell','buy']){const levels=(displayBook?.[side]||[]).slice(0,5),ordered=side==='sell'?[...levels].reverse():levels;const max=Math.max(1,...levels.map(l=>l.qty));const rows=ordered.map(l=>{const name=(side==='buy'?'买':'卖')+(dealerMode()?'价':levels.indexOf(l)+1),take=side==='buy'?'sell':'buy';return '<button type="button" class="ct-level '+(side==='buy'?'bid':'ask')+'" data-take-side="'+take+'" data-price="'+l.price+'" data-qty="'+(l.qty-l.ownQty)+'" data-own-qty="'+l.ownQty+'" aria-label="'+(l.ownQty?'我的挂单，可撤单；':'')+(take==='buy'?'买入':'卖出')+'，价格 '+quotePrice(l.price)+'，对手 '+(l.qty-l.ownQty)+' 手" title="自己 '+l.ownQty+' 手 · 程序 '+l.programQty+' 手" style="--depth:'+l.qty/max*100+'%"><span>'+name+(l.ownQty?'<small class="ct-own-mark">我</small>':'')+'</span><strong>'+(l.price/100).toLocaleString('zh-CN',{maximumFractionDigits:2})+'</strong><span>'+l.qty+'</span></button>';});while(rows.length<(dealerMode()?1:5)){const blank='<div class="ct-level ct-empty"><span>—</span><span>—</span><span>—</span></div>';side==='sell'?rows.unshift(blank):rows.push(blank);}$(side==='sell'?'c-asks':'c-bids').innerHTML=rows.join('');}compactBookKey=key;}
  $('c-spread').textContent=displayBook?.sell.length&&displayBook?.buy.length?quotePrice(displayBook.sell[0].price-displayBook.buy[0].price):'—';
  $('c-review-next').innerHTML=s.isHost&&s.phase==='intermission'?button('next','发布下一条线索，开始第 '+(s.round+1)+' 轮','primary'):'';
  if(s.phase!=='trading')compactCloseTicket();
  if(compactPhase!==s.phase||compactFinalized!==finalized){
    $('m-feedback').textContent='';
    if(final||finalized){compactSetPanel('ranking',false);if(final)$('c-answer').scrollIntoView({block:'start'});}
    else if(s.phase==='intermission')compactSetPanel('review',true);
    else if(s.phase==='resolution')compactSetPanel(s.isHost?'host':'review',true);
    else if(['lobby','election','maker-quote','reading','opening','trading'].includes(s.phase)){compactSetPanel('');if(compactPhase)$('c-terminal').scrollIntoView({block:'start'});}
    compactPhase=s.phase;compactFinalized=finalized;
  }
  $('m-host').hidden=!s.isHost||lobby||finalized;
  if(dealerMode())renderDealerCompact();
  if(compactTicket){renderCompactTicket();positionCompactTicket();}
}
document.addEventListener('click',e=>{if(compactTicket&&!e.target.closest('#c-ticket,[data-take-side]'))compactCloseTicket();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&compactTicket)compactCloseTicket();});
window.addEventListener('resize',()=>{if(compactTicket)positionCompactTicket();});
window.addEventListener('scroll',()=>{if(compactTicket)positionCompactTicket();},{passive:true});

function mountDealerCompact(move) {
  $('app').classList.add('dealer-terminal');
  $('c-opening').insertAdjacentHTML('beforebegin','<div id="c-election"></div><div id="c-dealer-status" class="ct-dealer-status" role="status"></div>');
  move('m-election','c-election');move('m-maker','c-order');
  $('m-election').querySelector('h3').textContent='竞选做市商';
  $('m-election').querySelector('.pill').remove();
  $('m-election').querySelector('.help').textContent='价差最小者当选，同价先到优先。可修改报价。';
  $('m-spread-submit').textContent='提交价差';
  $('m-spread').placeholder='请输入价差';
  $('m-maker').querySelector('label[for="m-bid"]').textContent='买价 Bid';
  $('m-maker').querySelector('label[for="m-ask"]').textContent='卖价 Ask';
  $('m-quote-submit').textContent='锁定报价，开始交易';
  $('m-quote-display').hidden=true;
  $('c-market-price').textContent='对手价';
  $('c-market-price').title='填入做市商报价，提交后轮末撮合';
  $('c-order').insertAdjacentHTML('beforeend','<p id="c-dealer-order-note" class="ct-dealer-order-note"></p>');
  $('c-panel-ranking').append($('m-ranking-title'),$('m-ranking'));
  move('m-history','c-panel-review');
  $('c-panel-review').insertAdjacentHTML('beforeend','<p class="help">逐轮成交与收盘价；个人明细见「成交」。结算后可下载本局复盘。</p>');
  $('c-panel-orders').insertAdjacentHTML('afterbegin','<p class="help">客户委托可撤单；做市商双边报价锁定至本轮结束。</p>');
  document.querySelector('[data-c-panel="ranking"]').textContent='排名';
  document.querySelector('.ct-book .ct-market-heading strong').textContent='做市报价';
  document.querySelector('.ct-book .ct-market-heading span').textContent='份';
  document.querySelector('.ct-capacity>small').textContent='按可用资金与持仓';
  for(const e of document.querySelectorAll('.ct-capacity>div>small')) e.textContent='份';
  for(const e of document.querySelectorAll('[data-quick-qty], [data-c-ticket-qty]')) e.textContent=e.textContent.replace('手','份');
  document.querySelector('#m-lobby .pill').textContent='做市商挑战';
}
function renderDealerCapacity() {
  if(!$('c-buy-free'))return;
  $('c-position').textContent='持有 '+s.me.shares+' 份';
  const price=Math.round(Number($('m-order-price').value)*100);
  $('c-buy-free').textContent=Number.isFinite(price)&&price>=s.bounds.low?capacity('buy',price):'—';
  $('c-sell-free').textContent=capacity('sell',price);
  $('m-qty').max=capacity($('m-side').value,price);
}
function renderDealerCompact() {
  const phase=s.phase, maker=s.me.id===s.makerId, quoting=phase==='maker-quote', trading=phase==='trading';
  const commitment=s.election.find(x=>x.playerId===s.makerId)?.spread;
  $('c-trading').hidden=['lobby','election','finished'].includes(phase);
  document.querySelector('.ct-dock').hidden=phase==='resolution';
  $('c-dealer-status').hidden=['lobby','election','finished'].includes(phase);
  $('c-dealer-status').textContent=(s.makerName?'做市商 '+s.makerName+' · ':'')+(quoting?(maker?'请提交本轮双边报价':'等待双边报价'):trading?'报价已锁定 · 轮末成交':phases[phase]);
  const latest=[...s.signals,...s.messages].sort((a,b)=>b.round-a.round||b.at-a.at)[0];
  $('c-round').textContent='第 '+s.round+' / '+s.config.rounds+' 轮'+(latest&&latest.round<s.round?' · 上条消息':'');
  document.querySelectorAll('.ct-capacity>small')[1].textContent=maker?'每轮锁定一次报价':'本轮可多次挂单';
  if(phase==='election')$('c-round').textContent='竞选做市商';
  $('c-price-label').textContent=s.trades.length?'最新成交':'初始参考';
  $('c-open-price').textContent='初始 '+axisPrice(s.config.initialPrice);
  $('m-maker').hidden=!(maker&&quoting);
  $('m-maker-title').textContent='双边报价';$('m-maker-role').textContent='你是做市商';
  $('m-maker-note').textContent='范围 '+money(s.bounds.low)+'–'+money(s.bounds.high)+(s.round===1?' · 价差 ≤ '+money(commitment):'')+' · 每边最多 10 份';
  $('c-order').hidden=['finished','resolution'].includes(phase);
  $('m-order-form').hidden=maker||!trading;
  $('c-dealer-order-note').textContent=quoting?(maker?'锁定后本轮不可撤销。':'等待做市商报价后即可提交委托。'):trading?(maker?'双边报价已锁定，等待本轮结束撮合。':'本轮限价 '+money(s.bounds.low)+'–'+money(s.bounds.high)+' · 可撤单'):phase==='paused'?'已暂停，恢复后继续操作。':phase==='intermission'?'本轮已结束，等待下一轮报价。':'';
  $('c-review-next').innerHTML=s.isHost&&phase==='intermission'?button('next','开始下一轮','primary'):'';
  $('c-price-note').textContent=s.trades.length?'本轮 '+s.roundVolume+' 份':'尚无成交 · 轮末撮合';
  renderDealerCapacity();
  if(s.makerQuote&&['trading','paused'].includes(phase)) {
    for(const el of document.querySelectorAll('.ct-level[data-take-side]')) {
      el.setAttribute('aria-label',(el.dataset.takeSide==='buy'?'买入':'卖出')+'，做市报价 '+money(Number(el.dataset.price))+'，轮末撮合');
      el.title='做市商 '+s.makerName+' · 每边 '+s.makerQuote.qty+' 份';
    }
  }
}
