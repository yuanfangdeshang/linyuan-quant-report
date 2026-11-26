/* 临渊量化 · 交易实验室 —— 玩家端 */
(() => {
  const $ = (id) => document.getElementById(id);
  const params = new URLSearchParams(location.search);
  const code = params.get('code') || '';
  const LS_T = 'lq:tok:' + code;
  const LS_N = 'lq:name:' + code;

  let token = localStorage.getItem(LS_T) || '';
  let myName = localStorage.getItem(LS_N) || '';
  let state = null;
  let es = null;
  let mountKey = '';
  let side = 'buy';
  let lastChartKey = '';

  /* ----------------------------- 工具 ----------------------------- */

  const yuan = (c) => (c == null ? '—' : (c / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
  const plain = (c) => (c == null ? '' : (c / 100).toFixed(2));
  const pct = (c) => (c == null ? '' : (c / 100).toFixed(2));

  function toast(msg) {
    const t = $('toast');
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(t._h);
    t._h = setTimeout(() => t.classList.remove('show'), 2000);
  }

  async function act(action, payload = {}) {
    const res = await fetch('/api/act', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, token, action, ...payload })
    });
    const d = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(d.error || '操作失败');
    return d;
  }

  /* ----------------------------- 入场 ----------------------------- */

  let gateOpen = false;

  function showGate() {
    if (gateOpen) return;
    gateOpen = true;
    $('gate').hidden = false;
    $('gateCode').textContent = code;
    $('gateName').value = myName || '';
    setTimeout(() => $('gateName').focus(), 100);
  }

  function hideGate() {
    gateOpen = false;
    $('gate').hidden = true;
  }

  async function doJoin() {
    const name = $('gateName').value.trim();
    $('gateErr').textContent = '';
    if (!name) { $('gateErr').textContent = '请填写昵称'; return; }
    try {
      const res = await fetch('/api/join', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, name, token: token || undefined })
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.error || '入场失败');
      token = d.token;
      myName = d.name;
      localStorage.setItem(LS_T, token);
      localStorage.setItem(LS_N, myName);
      hideGate();
      connect();
      toast(`已入座 · ${myName}`);
    } catch (e) {
      $('gateErr').textContent = e.message;
    }
  }

  $('gateBtn').onclick = doJoin;
  $('gateName').addEventListener('keydown', (e) => { if (e.key === 'Enter') doJoin(); });

  /* ----------------------------- 连接 ----------------------------- */

  function connect() {
    if (es) es.close();
    es = new EventSource(`/api/stream?code=${encodeURIComponent(code)}&token=${encodeURIComponent(token)}`);
    es.onopen = () => { $('dot').classList.remove('off'); $('connText').textContent = '已连接 · 实时同步'; };
    es.onerror = () => { $('dot').classList.add('off'); $('connText').textContent = '重连中…'; };
    es.onmessage = (ev) => {
      let d;
      try { d = JSON.parse(ev.data); } catch (e) { return; }
      if (d.t === 'state') { state = d; render(); }
      else if (d.t === 'clock') { applyClock(d); }
    };
  }

  /* ----------------------------- 渲染总入口 ----------------------------- */

  function render() {
    if (!state) return;

    // 席位失效（服务重启、被移除、密钥过期）时，回到入场浮层，绝不把人卡在“观众”态
    if (state.role !== 'player') {
      if (token) {
        token = '';
        localStorage.removeItem(LS_T);
        if (es) { es.close(); es = null; }
      }
      showGate();
    } else if (gateOpen) {
      hideGate();
    }

    $('roomCode').textContent = state.code;
    $('whoami').textContent = state.me ? state.me.name : '观众';
    if (state.me) { myName = state.me.name; localStorage.setItem(LS_N, myName); }

    const g = state.game;
    renderQuestion(g);

    if (!g) {
      mountKey = 'none';
      $('stage').innerHTML = `<section class="card"><div class="list-empty">主持人尚未出题，请稍候。</div></section>`;
      updateNav();
      return;
    }

    const key = g.id + ':' + g.phase;
    if (key !== mountKey) {
      mountKey = key;
      lastChartKey = '';
      if (g.phase === 'estimate') mountEstimate(g);
      else if (g.phase === 'trading' || g.phase === 'closed') mountTrading(g);
      else mountSettled(g);
    }

    if (g.phase === 'estimate') updateEstimate(g);
    else if (g.phase === 'trading' || g.phase === 'closed') updateTrading(g);
    else updateSettled(g);

    updateNav();
    if (openTab) renderPanel(openTab);
  }

  function renderQuestion(g) {
    const sub = $('qSub');
    const side = $('qSide');
    if (!g) {
      $('qTitle').textContent = '等待主持人出题…';
      sub.textContent = '';
      side.textContent = '';
      return;
    }
    $('qTitle').textContent = g.question.q;
    const label = g.practice ? '测试版 · 不计分' : '正式题';
    sub.innerHTML = `单位：${g.question.unit}　<span class="tag ${g.practice ? '' : 'green'}">${label}</span>`
      + (g.phase === 'estimate' ? `　<span class="tag">报价中</span>`
        : g.phase === 'trading' ? `　<span class="tag green">第 ${g.round}/${g.maxRound} 轮</span>`
        : g.phase === 'closed' ? `　<span class="tag">交易已截止</span>` : `　<span class="tag green">已结算</span>`);

    if (g.phase === 'estimate') side.innerHTML = `${g.submitted} / ${g.totalParticipants} 位已报价`;
    else side.innerHTML = `${state.players.length} 人 · ${state.playersOnline} 在线`;
  }

  /* ----------------------------- 估价阶段 ----------------------------- */

  function mountEstimate(g) {
    $('stage').innerHTML = `
      <section class="card">
        <div class="card-title">报出你的估价</div>
        <p class="est-note" style="margin-top:-6px">类似集合竞价 · 取中位数作为开盘参考价 · 不会买卖或占用仓位</p>
        <div class="est-box">
          <div class="q-sub" style="font-size:13px">你的估价（与题目单位一致）</div>
          <div class="est-row" style="margin-top:8px">
            <div class="est-input">
              <input id="estInput" inputmode="decimal" autocomplete="off" placeholder="输入数值">
              <span class="unit" id="estUnit"></span>
            </div>
            <button class="btn primary" id="estSubmit">提交 / 修改估价</button>
          </div>
          <div class="est-note" id="estMine"></div>
          <div class="submit-list" id="estList"></div>
          <div class="est-note" id="estWait" style="margin-top:14px">等待主持人确认开盘；现在没有预设市场价格。</div>
        </div>
      </section>`;

    $('estSubmit').onclick = async () => {
      const raw = $('estInput').value.trim();
      const v = Number(raw);
      if (!raw || !Number.isFinite(v) || v < 0) return toast('请输入有效估值');
      try {
        await act('estimate', { value: v });
        toast('估价已保存，可在开盘前修改；不会自动成交');
      } catch (e) { toast(e.message); }
    };
    $('estInput').addEventListener('keydown', (e) => { if (e.key === 'Enter') $('estSubmit').click(); });
  }

  function updateEstimate(g) {
    const me = g.me;
    $('estUnit').textContent = g.question.unit.split('/')[0].trim();
    if (document.activeElement !== $('estInput')) {
      $('estInput').value = me && me.estimate != null ? plain(me.estimate) : '';
    }
    $('estMine').innerHTML = me && me.estimate != null
      ? `你的已提交估价：<b class="num">${plain(me.estimate)}</b>；可修改后再次提交。`
      : '尚未提交估价。';
    $('estList').innerHTML = (g.submittedNames || [])
      .map((x) => `<span class="${x.done ? 'done' : 'wait'}">${escapeHtml(x.name)}${x.bot ? '（程序）' : ''} · ${x.done ? '已提交' : '待提交'}</span>`)
      .join('');
    $('estWait').textContent = `已报价 ${g.submitted} / ${g.totalParticipants} 位（含交易机器人） · 开盘价取全部报价的中位数`;
  }

  /* ----------------------------- 交易阶段 ----------------------------- */

  function mountTrading(g) {
    $('stage').innerHTML = `
      <div class="trade-grid">
        <section class="card">
          <div class="quote-row">
            <div class="quote-main">
              <div class="label">最新成交</div>
              <div class="price" id="lastPrice">—</div>
              <div class="quote-meta" id="roundVol">本轮 0 手</div>
            </div>
            <div class="signal">
              <div class="sig-head"><span>消息 <b id="sigIdx">1/1</b></span><span class="timer" id="sigTimer">00:00</span></div>
              <div class="sig-text" id="sigText">等待线索</div>
              <div class="sig-src" id="sigSrc"></div>
            </div>
          </div>

          <div class="chart-box">
            <div class="chart-head"><span>分时</span><span id="chartMeta">开盘 —</span></div>
            <canvas id="chart" style="height:290px"></canvas>
          </div>

          <div class="order-tabs" id="orderTabs">
            <button class="active buy" data-side="buy">买入</button>
            <button data-side="sell">卖出</button>
          </div>
          <div class="field-row">
            <div class="field">
              <button class="adj" data-adj="price" data-dir="-1">−</button>
              <input id="priceInput" inputmode="decimal" autocomplete="off">
              <button class="adj" data-adj="price" data-dir="1">＋</button>
            </div>
            <div class="field">
              <button class="adj" data-adj="qty" data-dir="-1">−</button>
              <input id="qtyInput" inputmode="numeric" autocomplete="off" value="1">
              <button class="adj" data-adj="qty" data-dir="1">＋</button>
            </div>
          </div>
          <div class="quick-row">
            <button class="btn sm" data-qty="1">1 手</button>
            <button class="btn sm" data-qty="5">5 手</button>
            <button class="btn sm" id="quickMax">全部可买</button>
          </div>
          <button class="btn buy block" id="submitOrder" style="margin-top:10px">买入</button>
          <div class="order-foot">
            <span id="orderHint">成交 0 手；剩余挂单 0 手</span>
            <span id="orderNote">净持仓上限 ±10 手</span>
          </div>
          <div class="my-orders" id="myOrders"></div>
        </section>

        <aside>
          <section class="card tight">
            <div class="card-title">Bid / Ask</div>
            <div class="book" id="book"></div>
          </section>
          <section class="card tight">
            <div class="card-title">持仓</div>
            <div class="pos-head" id="posHead">空仓</div>
            <div class="pos-grid" id="posGrid"></div>
          </section>
        </aside>
      </div>`;

    $('orderTabs').addEventListener('click', (e) => {
      const b = e.target.closest('[data-side]');
      if (!b) return;
      setSide(b.dataset.side);
    });

    $('stage').addEventListener('click', (e) => {
      const adj = e.target.closest('[data-adj]');
      if (adj) {
        if (adj.dataset.adj === 'price') {
          const cur = Number($('priceInput').value) || 0;
          const step = tickStep(cur);
          $('priceInput').value = Math.max(0, +(cur + step * Number(adj.dataset.dir)).toFixed(2));
        } else {
          const cur = Number($('qtyInput').value) || 0;
          $('qtyInput').value = Math.max(1, Math.min(10, cur + Number(adj.dataset.dir)));
        }
        return;
      }
      const qb = e.target.closest('[data-qty]');
      if (qb) { $('qtyInput').value = qb.dataset.qty; return; }
      if (e.target.id === 'quickMax') {
        const me = state.game.me;
        $('qtyInput').value = String(side === 'buy' ? me.availableBuy : me.availableSell);
      }
    });

    $('submitOrder').onclick = async () => {
      const price = Number($('priceInput').value);
      const qty = Number($('qtyInput').value);
      if (!Number.isFinite(price) || price <= 0) return toast('请输入有效价格');
      if (!Number.isFinite(qty) || qty <= 0) return toast('请输入有效手数');
      try {
        await act('order', { side, price, qty });
        toast(side === 'buy' ? '买单已提交' : '卖单已提交');
      } catch (e) { toast(e.message); }
    };

    window.addEventListener('resize', () => { lastChartKey = ''; if (state && state.game) updateTrading(state.game); });
  }

  function tickStep(price) {
    if (price >= 1000) return 5;
    if (price >= 100) return 1;
    if (price >= 10) return 0.1;
    return 0.01;
  }

  function updateTrading(g) {
    const me = g.me || {};
    const last = g.lastPrice;

    // 最新成交
    const lp = $('lastPrice');
    if (lp) {
      lp.textContent = last != null ? yuan(last) : '—';
      const prev = g.ticks && g.ticks.length > 1 ? g.ticks[g.ticks.length - 2].p : last;
      lp.classList.toggle('up', last != null && prev != null && last > prev);
      lp.classList.toggle('down', last != null && prev != null && last < prev);
    }

    const roundTrades = (me.trades || []).filter((t) => t.round === g.round);
    const roundQty = roundTrades.reduce((s, t) => s + t.qty, 0);
    if ($('roundVol')) $('roundVol').textContent = `本轮 ${roundQty} 手`;

    // 线索
    const sig = g.signals[g.signals.length - 1];
    if ($('sigIdx')) $('sigIdx').textContent = `${g.signals.length}/${g.maxRound}`;
    if ($('sigText') && sig) {
      $('sigText').textContent = sig.text;
      $('sigSrc').textContent = sig.sourceName ? `来源 · ${sig.sourceName}` : '';
    }
    if ($('sigTimer')) {
      $('sigTimer').textContent = fmtClock(g.roundRemain);
      $('sigTimer').style.color = g.roundRemain <= 10 ? 'var(--red)' : '';
    }
    if ($('chartMeta')) {
      $('chartMeta').textContent = `开盘 ${g.openingPrice != null ? yuan(g.openingPrice) : '—'}　|　${g.elapsed}/${g.totalSeconds} 秒`;
    }

    // 盘口
    renderBook(g);

    // 持仓
    renderPos(g, me);

    // 挂单撤单区
    renderMyOrders(me);

    // 下单区
    syncOrderUI();

    // 图表
    const chartKey = `${g.id}:${g.ticks.length}:${g.totalSeconds}`;
    if (chartKey !== lastChartKey) { lastChartKey = chartKey; drawChart(g); }

    // 停牌遮罩
    const form = $('submitOrder');
    if (form) {
      if (g.phase === 'closed') {
        form.classList.add('order-disabled');
        form.textContent = '交易已结束';
        $('orderTabs').classList.add('order-disabled');
        $('orderHint').textContent = '本轮交易已结束，等待主持人结算';
      } else {
        form.classList.remove('order-disabled');
      }
    }
  }

  function setSide(next) {
    side = next;
    document.querySelectorAll('#orderTabs button').forEach((x) => {
      x.classList.toggle('active', x.dataset.side === side);
      x.classList.toggle('buy', x.dataset.side === 'buy');
      x.classList.toggle('sell', x.dataset.side === 'sell');
    });
    syncOrderUI();
  }

  /* 点价成交：点卖档=买入，点买档=卖出，手数取该档可成交量与自身额度的小者，点一下即提交 */
  async function quickFill(price, bookSide, levelQty) {
    if (!state || !state.game || state.game.phase !== 'trading') return toast('当前不可交易');
    const me = state.game.me || {};
    const target = bookSide === 'bid' ? 'sell' : 'buy';
    const avail = target === 'buy' ? (me.availableBuy || 0) : (me.availableSell || 0);
    const qty = Math.min(levelQty || 1, avail);
    if (avail <= 0) return toast(`可${target === 'buy' ? '买' : '卖'}额度已用尽`);
    if (qty <= 0) return toast('这一档没有可成交量');

    setSide(target);
    $('priceInput').value = plain(price);
    $('qtyInput').value = String(qty);

    try {
      await act('order', { side: target, price, qty });
      toast(`已${target === 'buy' ? '买入' : '卖出'} ${qty} 手 · ${plain(price)}`);
    } catch (e) { toast(e.message); }
  }

  function renderMyOrders(me) {
    const box = $('myOrders');
    if (!box) return;
    const list = me.orders || [];
    if (!list.length) {
      box.innerHTML = '<div class="mo-empty">暂无挂单 · 点击盘口任意一档可直接成交</div>';
      return;
    }
    box.innerHTML = `<div class="mo-head"><span>我的挂单 <b class="num">${list.length}</b></span>
        <button class="btn sm" id="cancelAllInline">全部撤单</button></div>`
      + list.map((o) => `
        <div class="mo-row">
          <span class="side ${o.side}">${o.side === 'buy' ? '买' : '卖'}</span>
          <span class="p">${yuan(o.price)}</span>
          <span class="q">${o.remaining} / ${o.qty} 手</span>
          <button class="btn sm" data-cancel="${o.id}">撤单</button>
        </div>`).join('');

    box.querySelectorAll('[data-cancel]').forEach((b) => {
      b.onclick = async () => {
        try { await act('cancel', { orderId: Number(b.dataset.cancel) }); toast('已撤单'); } catch (e) { toast(e.message); }
      };
    });
    const ca = $('cancelAllInline');
    if (ca) ca.onclick = async () => {
      try { await act('cancelAll'); toast('已全部撤单'); } catch (e) { toast(e.message); }
    };
  }

  function syncOrderUI() {
    if (!state || !state.game) return;
    const g = state.game;
    const me = g.me || {};
    const btn = $('submitOrder');
    if (!btn) return;

    const avail = side === 'buy' ? (me.availableBuy || 0) : (me.availableSell || 0);
    const pending = (me.orders || []).reduce((s, o) => s + o.remaining, 0);

    if (g.phase !== 'closed') {
      btn.className = 'btn block ' + (side === 'buy' ? 'buy' : 'sell');
      btn.textContent = side === 'buy' ? '买入' : '卖出';
      btn.disabled = avail <= 0;
    }
    $('quickMax').textContent = side === 'buy' ? '全部可买' : '全部可卖';
    $('orderNote').textContent = `可${side === 'buy' ? '买' : '卖'} ${avail} 手 · 净持仓上限 ±${10} 手`;

    if (document.activeElement !== $('priceInput')) {
      const cur = Number($('priceInput').value);
      if (!cur || state.game.phase === 'trading') {
        $('priceInput').value = g.lastPrice != null ? plain(g.lastPrice) : '';
      }
    }
    if ($('orderHint')) {
      const tr = (me.trades || []).filter((t) => t.round === g.round).reduce((s, t) => s + t.qty, 0);
      $('orderHint').textContent = `成交 ${tr} 手；剩余挂单 ${pending} 手`;
    }
  }

  function renderBook(g) {
    const b = g.book;
    const maxQ = Math.max(1, ...[...b.asks, ...b.bids].map((x) => x.qty));
    const asks = b.asks.slice(0, 5);
    const bids = b.bids.slice(0, 5);
    const askRows = [];
    for (let i = 0; i < 5; i += 1) {
      const lv = asks[4 - i];
      if (!lv) { askRows.push(`<div class="row ask"><span class="k">卖${5 - i}</span><span class="p">—</span><span class="q">—</span></div>`); continue; }
      askRows.push(`<div class="row ask clickable" data-price="${lv.price}" data-side="ask" data-qty="${lv.qty}">
        <span class="depth" style="width:${(lv.qty / maxQ) * 100}%"></span>
        <span class="k">卖${5 - i}</span><span class="p">${yuan(lv.price)}</span><span class="q">${lv.qty}</span></div>`);
    }
    const bidRows = [];
    for (let i = 0; i < 5; i += 1) {
      const lv = bids[i];
      if (!lv) { bidRows.push(`<div class="row bid"><span class="k">买${i + 1}</span><span class="p">—</span><span class="q">—</span></div>`); continue; }
      bidRows.push(`<div class="row bid clickable" data-price="${lv.price}" data-side="bid" data-qty="${lv.qty}">
        <span class="depth" style="width:${(lv.qty / maxQ) * 100}%"></span>
        <span class="k">买${i + 1}</span><span class="p">${yuan(lv.price)}</span><span class="q">${lv.qty}</span></div>`);
    }
    const spread = b.spread != null ? yuan(b.spread) : '—';
    $('book').innerHTML = askRows.join('')
      + `<div class="spread"><span>价差</span><span>${spread}</span></div>`
      + bidRows.join('');

    $('book').querySelectorAll('[data-price]').forEach((row) => {
      row.addEventListener('click', () => {
        quickFill(Number(row.dataset.price), row.dataset.side, Number(row.dataset.qty));
      });
    });
  }

  function renderPos(g, me) {
    const pos = me.position || 0;
    const head = $('posHead');
    if (head) {
      head.innerHTML = pos === 0
        ? '持仓　<b>空仓</b>'
        : `持仓　<b>${pos > 0 ? '多' : '空'} ${Math.abs(pos)} 手</b>`;
    }
    const pnl = me.pnl || 0;
    $('posGrid').innerHTML = `
      <div class="k">净持仓</div><div class="v">${pos > 0 ? '+' : ''}${pos} 手</div>
      <div class="k">可买</div><div class="v">${me.availableBuy || 0} 手</div>
      <div class="k">可卖</div><div class="v">${me.availableSell || 0} 手</div>
      <div class="k">均价成本</div><div class="v">${me.avgCost ? yuan(me.avgCost) : '—'}</div>
      <div class="k">已平仓</div><div class="v">${yuan(me.realized || 0)}</div>
      <div class="k">盈亏</div><div class="v ${pnl >= 0 ? 'pos' : 'neg'}">${pnl >= 0 ? '+' : ''}${yuan(pnl)}</div>`;
  }

  /* ----------------------------- 图表 ----------------------------- */

  function drawChart(g) {
    const c = $('chart');
    if (!c) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const w = c.clientWidth || 600;
    const h = 290;
    c.width = Math.round(w * dpr);
    c.height = Math.round(h * dpr);
    c.style.height = h + 'px';
    const ctx = c.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const padL = 58, padR = 14, padT = 16, padB = 28;
    const iw = w - padL - padR;
    const ih = h - padT - padB;
    const total = Math.max(1, g.totalSeconds);
    const ticks = (g.ticks || []).filter((t) => Number.isFinite(t.p));

    const vals = ticks.map((t) => t.p / 100);
    if (g.openingPrice != null) vals.push(g.openingPrice / 100);
    if (g.lastPrice != null) vals.push(g.lastPrice / 100);

    ctx.font = '12px "Times New Roman", serif';
    ctx.fillStyle = '#8a938d';

    if (!vals.length) {
      ctx.textAlign = 'center';
      ctx.fillText('等待开盘', w / 2, h / 2);
      return;
    }

    let lo = Math.min(...vals);
    let hi = Math.max(...vals);
    if (hi - lo < Math.max(0.04, hi * 0.02)) {
      const d = Math.max(0.02, hi * 0.015);
      lo -= d; hi += d;
    }
    const pad = (hi - lo) * 0.12;
    lo -= pad; hi += pad;

    const X = (t) => padL + Math.min(1, t / total) * iw;
    const Y = (p) => padT + ih - ((p - lo) / (hi - lo)) * ih;

    // 网格
    ctx.strokeStyle = '#e7e4da';
    ctx.lineWidth = 1;
    ctx.textAlign = 'right';
    for (let i = 0; i <= 4; i += 1) {
      const y = padT + (ih * i) / 4;
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(padL + iw, y); ctx.stroke();
      const v = hi - ((hi - lo) * i) / 4;
      ctx.fillStyle = '#8a938d';
      ctx.fillText(v.toFixed(v >= 100 ? 0 : 2), padL - 8, y + 4);
    }

    // 轮次分割
    ctx.textAlign = 'left';
    for (let r = 1; r < g.maxRound; r += 1) {
      const x = X(r * g.roundSeconds);
      ctx.strokeStyle = '#dcd8cc';
      ctx.setLineDash([3, 4]);
      ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, padT + ih); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = '#a5ada6';
      ctx.fillText(`第${r + 1}轮`, x + 5, padT + 12);
    }

    // 开盘参考线
    if (g.openingPrice != null) {
      ctx.strokeStyle = '#c9c3b3';
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(padL, Y(g.openingPrice / 100));
      ctx.lineTo(padL + iw, Y(g.openingPrice / 100));
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // 价格曲线
    if (ticks.length) {
      ctx.strokeStyle = '#1f5643';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ticks.forEach((t, i) => {
        const x = X(t.t), y = Y(t.p / 100);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.stroke();

      const last = ticks[ticks.length - 1];
      ctx.fillStyle = '#1f5643';
      ctx.beginPath();
      ctx.arc(X(last.t), Y(last.p / 100), 3.2, 0, Math.PI * 2);
      ctx.fill();
    }

    // 轴标
    ctx.fillStyle = '#8a938d';
    ctx.textAlign = 'left';
    ctx.fillText('开局', padL, h - 8);
    ctx.textAlign = 'right';
    const el = Math.min(total, g.elapsed || 0);
    ctx.fillText(`${el}/${total} 秒`, padL + iw, h - 8);
  }

  /* ----------------------------- 结算 ----------------------------- */

  function mountSettled(g) {
    $('stage').innerHTML = `
      <section class="card">
        <div class="result-hero">
          <div class="cap">本局成绩</div>
          <div class="rank" id="resRank"></div>
          <div class="big" id="resPnl"></div>
          <div class="result-formula" id="resFormula"></div>
        </div>
        <div class="result-note" id="resNote"></div>
      </section>
      <section class="card">
        <div class="card-title">本局排名</div>
        <div id="resTable"></div>
      </section>
      <section class="card">
        <div class="card-title">累计积分榜</div>
        <div id="resStand"></div>
      </section>`;
  }

  function updateSettled(g) {
    const rows = g.ranking || [];
    const idx = rows.findIndex((r) => state.me && r.id === state.me.id);
    const mine = idx >= 0 ? rows[idx] : null;

    if (mine) {
      $('resRank').textContent = `第 ${mine.rank} 名 / ${rows.length} 人　·　积分 +${mine.points}`;
      const pnl = mine.pnl;
      const el = $('resPnl');
      el.textContent = (pnl >= 0 ? '+' : '') + yuan(pnl);
      el.classList.toggle('neg', pnl < 0);
    } else {
      $('resRank').textContent = '本局未参与';
      $('resPnl').textContent = '—';
    }

    const me = g.me || {};
    if (mine) {
      const holdPnl = mine.pnl - (me.realized || 0);
      $('resFormula').textContent = `已平仓 ${sym(me.realized || 0)} + 持仓结算 ${sym(holdPnl)} = ${sym(mine.pnl)} 盈亏`;
    }

    $('resNote').innerHTML = g.resolution
      ? `<b>结算答案</b>　${escapeHtml(g.resolution.note)}
         ${g.resolution.price != null ? `　<span class="num" style="color:var(--gold)">${yuan(g.resolution.price)}</span>` : ''}
         ${g.practice ? '<div style="margin-top:6px;color:var(--muted)">测试版不计分。</div>' : ''}`
      : '';

    $('resTable').innerHTML = `
      <table class="tbl">
        <thead><tr><th>名次</th><th>玩家</th><th style="text-align:right">最终盈亏</th><th style="text-align:right">本局积分</th></tr></thead>
        <tbody>${rows.map((r) => `
          <tr class="${state.me && r.id === state.me.id ? 'me' : ''}">
            <td class="n">${r.rank}</td>
            <td>${escapeHtml(r.name)}</td>
            <td class="n">${sym(r.pnl)}</td>
            <td class="n">+${r.points}</td>
          </tr>`).join('')}</tbody>
      </table>`;

    renderStandings($('resStand'));
  }

  function sym(v) {
    return (v > 0 ? '+' : '') + (v / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function renderStandings(container) {
    const st = state.standings;
    if (!st || !st.rows.length) { container.innerHTML = '<div class="list-empty">暂无计分题目</div>'; return; }
    container.innerHTML = `
      <table class="tbl">
        <thead><tr><th>名次</th><th>玩家</th><th>各题名次 / 积分</th><th style="text-align:right">总积分</th><th style="text-align:right">一/二</th></tr></thead>
        <tbody>${st.rows.map((r) => `
          <tr class="${r.rank === 1 ? 'top1' : ''} ${state.me && r.id === state.me.id ? 'me' : ''}">
            <td class="n">${r.rank}</td>
            <td>${escapeHtml(r.name)}</td>
            <td style="font-size:12px;color:var(--ink-2)">${r.results.map((x) => `第 ${x.number} 题 · ${x.rank ? '第' + x.rank + '名' : '—'} +${x.points}`).join('<br>') || '—'}</td>
            <td class="n">${r.points}</td>
            <td class="n">${r.wins} / ${r.seconds}</td>
          </tr>`).join('')}</tbody>
      </table>`;
  }

  /* ----------------------------- 底部面板 ----------------------------- */

  let openTab = null;

  function updateNav() {
    const badge = $('badgeOrders');
    const n = state && state.game && state.game.me ? (state.game.me.orders || []).length : 0;
    if (n > 0) { badge.hidden = false; badge.textContent = n; } else { badge.hidden = true; }
    document.querySelectorAll('#nav button').forEach((b) => b.classList.toggle('active', b.dataset.tab === openTab));
  }

  $('nav').addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    const tab = b.dataset.tab;
    if (openTab === tab) return closePanel();
    openTab = tab;
    renderPanel(tab);
    $('overlay').classList.add('show');
    $('panel').classList.add('show');
    updateNav();
  });

  $('overlay').onclick = closePanel;

  function closePanel() {
    openTab = null;
    $('panel').classList.remove('show');
    $('overlay').classList.remove('show');
    updateNav();
  }

  function renderPanel(tab) {
    const g = state.game;
    if (!g) { $('panel').innerHTML = '<div class="list-empty">暂无题目</div>'; return; }
    const me = g.me || {};
    const titles = { orders: '当前委托', trades: '我的成交', rank: '积分榜', review: '全员复盘', more: '更多' };

    let body = '';
    if (tab === 'orders') {
      const list = me.orders || [];
      body = list.length ? list.map((o) => `
        <div class="rt">
          <span class="side ${o.side}">${o.side === 'buy' ? '买' : '卖'}</span>
          <span class="p">${yuan(o.price)}</span>
          <span class="q">${o.remaining}/${o.qty}</span>
          <span class="cp">第 ${o.round} 轮</span>
          <span class="pnl"><button class="btn sm" data-cancel="${o.id}">撤单</button></span>
        </div>`).join('') : '<div class="list-empty">没有未成交委托。</div>';
      if (list.length) {
        body += `<div style="margin-top:12px"><button class="btn sm" id="cancelAll">全部撤单</button></div>`;
      }
    } else if (tab === 'trades') {
      const list = (me.trades || []).slice().reverse();
      body = list.length ? list.map((t) => `
        <div class="rt">
          <span class="side ${t.side}">${t.side === 'buy' ? '买' : '卖'}</span>
          <span class="p">${yuan(t.price)}</span>
          <span class="q">×${t.qty}</span>
          <span class="cp">第${t.round}轮 · 对手 ${escapeHtml(t.counterparty)}${t.program ? '（程序）' : ''}</span>
          <span class="pnl ${t.realizedPnl >= 0 ? 'up' : 'down'}">${t.realizedPnl === 0 ? '0.00' : sym(t.realizedPnl)}</span>
        </div>`).join('') : '<div class="list-empty">还没有成交。</div>';
    } else if (tab === 'rank') {
      body = '<div class="card-title">累计积分榜</div><div id="standBox"></div>';
      if (g.phase === 'settled') body += '<div class="card-title" style="margin-top:18px">本局排名</div><div id="gameRankBox"></div>';
    } else if (tab === 'review') {
      body = renderReview(g);
    } else if (tab === 'more') {
      body = `
        <div class="rt"><span class="cp">房间号</span><span class="p">${state.code}</span></div>
        <div class="rt"><span class="cp">我的昵称</span><span class="p" style="font-family:var(--font-cn)">${escapeHtml(state.me ? state.me.name : '—')}</span></div>
        <div class="rt"><span class="cp">轮次时长</span><span class="p">${g.roundSeconds} 秒 / 轮</span></div>
        <div class="rt"><span class="cp">本题轮次</span><span class="p">${g.round} / ${g.maxRound}</span></div>
        <div class="rt"><span class="cp">在线人数</span><span class="p">${state.playersOnline}</span></div>
        <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn sm" id="renameBtn">修改昵称</button>
          <button class="btn sm" id="seatBtn">换一个席位</button>
          <a class="btn sm" href="/" style="display:inline-block">离开房间</a>
        </div>
        <p class="est-note" style="margin-top:14px">提示：点击盘口任意一档即按该档价格与可成交量直接成交（点卖档为买入，点买档为卖出）；下方挂单可直接撤单。</p>`;
    }

    $('panel').innerHTML = `<div class="panel-head"><h3>${titles[tab]}</h3><button class="close" id="panelClose">×</button></div>${body}`;
    $('panelClose').onclick = closePanel;

    if (tab === 'rank') {
      renderStandings($('standBox'));
      if (g.phase === 'settled' && $('gameRankBox')) {
        const rows = g.ranking || [];
        $('gameRankBox').innerHTML = `<table class="tbl"><thead><tr><th>名次</th><th>玩家</th><th style="text-align:right">盈亏</th><th style="text-align:right">积分</th></tr></thead><tbody>
          ${rows.map((r) => `<tr class="${state.me && r.id === state.me.id ? 'me' : ''}"><td class="n">${r.rank}</td><td>${escapeHtml(r.name)}</td><td class="n">${sym(r.pnl)}</td><td class="n">+${r.points}</td></tr>`).join('')}
        </tbody></table>`;
      }
    }

    if (tab === 'orders') {
      $('panel').querySelectorAll('[data-cancel]').forEach((b) => {
        b.onclick = async () => {
          try { await act('cancel', { orderId: Number(b.dataset.cancel) }); toast('已撤单'); } catch (e) { toast(e.message); }
        };
      });
      const ca = $('cancelAll');
      if (ca) ca.onclick = async () => {
        try { await act('cancelAll'); toast('已全部撤单'); } catch (e) { toast(e.message); }
      };
    }

    if (tab === 'more') {
      const rb = $('renameBtn');
      if (rb) rb.onclick = async () => {
        const name = prompt('新的昵称', state.me ? state.me.name : '');
        if (!name) return;
        try { await act('rename', { name }); toast('昵称已更新'); } catch (e) { toast(e.message); }
      };
      const sb = $('seatBtn');
      if (sb) sb.onclick = () => {
        if (!confirm('放弃当前席位，重新以新昵称入场？持仓与成交会留在房间记录里。')) return;
        localStorage.removeItem(LS_T);
        location.reload();
      };
    }
  }

  function renderReview(g) {
    const sigs = (g.signals || []).map((s) => `
      <div class="rt"><span class="cp" style="flex:0 0 54px">第 ${s.round} 轮</span>
        <span style="flex:1;color:var(--ink)">${escapeHtml(s.text)}</span>
        <span class="pnl" style="width:auto;font-family:var(--font-cn);font-size:11.5px;color:var(--muted)">${escapeHtml(s.sourceName || '')}</span></div>`).join('');

    const players = (g.review ? g.review.players : []);
    const blocks = players.map((p) => {
      if (!p.trades.length) return '';
      return `
        <div class="rev-player">
          <div class="rev-head">
            <b>${escapeHtml(p.name)}</b>
            ${p.bot ? '<span class="bot">程序</span>' : ''}
            <span class="cnt">${p.trades.length} 笔成交</span>
          </div>
          ${p.trades.map((t) => `
            <div class="rt">
              <span class="side ${t.side}">${t.side === 'buy' ? '买' : '卖'}</span>
              <span class="p">${yuan(t.price)}</span>
              <span class="q">×${t.qty}</span>
              <span class="cp">第${t.round}轮 · 对手 ${escapeHtml(t.counterparty)}</span>
              <span class="pnl">${t.realizedPnl ? sym(t.realizedPnl) : '0.00'}</span>
            </div>`).join('')}
        </div>`;
    }).join('');

    return `
      <div class="card-title">线索记录</div>
      ${sigs || '<div class="list-empty">尚未释放线索</div>'}
      <div class="card-title" style="margin-top:18px">全员逐笔成交</div>
      <p class="est-note" style="margin-top:-4px">已结束轮次的成交对所有人公开；新题开始后仍可回看历史。</p>
      ${blocks || '<div class="list-empty">暂无公开成交</div>'}`;
  }

  /* ----------------------------- 时钟 ----------------------------- */

  function applyClock(d) {
    if (!state || !state.game) return;
    const g = state.game;
    if (g.phase !== 'trading') return;
    if (d.round !== g.round) return;
    g.roundRemain = d.remain;
    g.elapsed = d.elapsed;
    if (d.lastPrice != null && d.lastPrice !== g.lastPrice) {
      g.lastPrice = d.lastPrice;
      if ($('lastPrice')) $('lastPrice').textContent = yuan(d.lastPrice);
    }
    if ($('sigTimer')) {
      $('sigTimer').textContent = fmtClock(d.remain);
      $('sigTimer').style.color = d.remain <= 10 ? 'var(--red)' : '';
    }
    if ($('chartMeta')) {
      $('chartMeta').textContent = `开盘 ${g.openingPrice != null ? yuan(g.openingPrice) : '—'}　|　${d.elapsed}/${g.totalSeconds} 秒`;
    }
  }

  function fmtClock(sec) {
    const s = Math.max(0, Math.round(sec || 0));
    return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  }

  /* ----------------------------- 启动 ----------------------------- */

  if (!code) {
    location.href = '/';
  } else {
    if (token) connect();
    else showGate();
  }
})();
