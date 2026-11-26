/* 临渊量化 · 交易实验室 —— 主持台 */
(() => {
  const $ = (id) => document.getElementById(id);
  const code = new URLSearchParams(location.search).get('code') || '';
  const LS = 'lq:host:' + code;

  let key = localStorage.getItem(LS) || '';
  let state = null;
  let es = null;

  const yuan = (c) => (c == null ? '—' : (c / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));

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
      body: JSON.stringify({ code, token: key, action, ...payload })
    });
    const d = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(d.error || '操作失败');
    return d;
  }

  /* ---------------------------- 验证与连接 ---------------------------- */

  function showGate(err) {
    $('gate').hidden = false;
    $('gateCode').textContent = code;
    $('gateKey').value = key || '';
    $('gateErr').textContent = err || '';
  }

  async function verify() {
    const k = $('gateKey').value.trim();
    if (!k) { $('gateErr').textContent = '请输入密钥'; return; }
    try {
      const res = await fetch(`/api/host?code=${encodeURIComponent(code)}&key=${encodeURIComponent(k)}`);
      const d = await res.json();
      if (!res.ok) throw new Error(d.error || '验证失败');
      key = k;
      localStorage.setItem(LS, k);
      $('gate').hidden = true;
      connect();
    } catch (e) {
      $('gateErr').textContent = e.message;
    }
  }

  $('gateBtn').onclick = verify;
  $('gateKey').addEventListener('keydown', (e) => { if (e.key === 'Enter') verify(); });

  function connect() {
    if (es) es.close();
    es = new EventSource(`/api/stream?code=${encodeURIComponent(code)}&token=${encodeURIComponent(key)}`);
    es.onopen = () => { $('dot').classList.remove('off'); $('connText').textContent = '已连接'; };
    es.onerror = () => { $('dot').classList.add('off'); $('connText').textContent = '重连中…'; };
    es.onmessage = (ev) => {
      let d;
      try { d = JSON.parse(ev.data); } catch (e) { return; }
      if (d.t === 'state') { state = d; render(); }
      else if (d.t === 'clock') updateClock(d);
    };
  }

  /* ---------------------------- 渲染 ---------------------------- */

  function render() {
    if (!state) return;
    $('roomCode').textContent = state.code;
    $('roleChip').textContent = state.role === 'host' ? '主持人' : '只读';

    const g = state.game;
    renderTop(g);

    // 播放地址
    const origin = location.origin;
    $('playUrl').textContent = `${origin}/play.html?code=${state.code}`;
    $('btnExport').href = `/api/export?code=${encodeURIComponent(state.code)}&key=${encodeURIComponent(key)}`;

    renderBank(g);
    renderBots();
    renderPlayers(g);

    if (document.activeElement !== $('secInput')) $('secInput').value = state.roundSeconds;
  }

  function renderTop(g) {
    $('qTitle').textContent = g ? g.question.q : '尚未选题';
    $('qSub').innerHTML = g
      ? `${state.allGames.find((x) => x.index === state.currentIndex) ? `第 ${state.allGames.find((x) => x.index === state.currentIndex).number} 题 · ` : ''}单位：${g.question.unit}　·　第 ${g.round}/${g.maxRound} 轮${g.practice ? '　<span class="tag">测试版</span>' : ''}`
      : '从下方题库挑一道题开始';

    const chips = [];
    if (g) {
      const phaseText = { estimate: '估值中', trading: '交易中', closed: '已停牌', settled: '已结算' }[g.phase];
      chips.push(`<span class="tag ${g.phase === 'trading' ? 'green' : ''}">${phaseText}</span>`);
      if (g.openingPrice != null) chips.push(`<span class="chip">开盘 <b class="num">${yuan(g.openingPrice)}</b></span>`);
      if (g.lastPrice != null) chips.push(`<span class="chip">最新 <b class="num">${yuan(g.lastPrice)}</b></span>`);
      chips.push(`<span class="chip">报价 <b class="num">${g.submitted}</b></span>`);
      chips.push(`<span class="chip">成交 <b class="num" id="tradeCount">${g.tradeCount || 0}</b> 笔</span>`);
      if (g.phase === 'trading') chips.push(`<span class="chip">剩余 <b class="num" id="remainChip">${g.roundRemain}</b> 秒</span>`);
      if (g.resolution) chips.push(`<span class="chip">答案 <b class="num">${g.resolution.price != null ? yuan(g.resolution.price) : g.resolution.note}</b></span>`);
    }
    $('stateLine').innerHTML = chips.join('');

    $('btnOpen').disabled = !g || g.phase !== 'estimate';
    $('btnNext').disabled = !g || g.phase !== 'trading' || g.round >= g.maxRound;
    $('btnClose').disabled = !g || g.phase !== 'trading';
    $('btnSettle').disabled = !g || !(g.phase === 'trading' || g.phase === 'closed');

    let hint = '';
    if (!g) hint = '先选题。';
    else if (g.phase === 'estimate') hint = '等玩家报完估价后点“开盘”。开盘价取所有已提交估价的中位数。';
    else if (g.phase === 'trading') hint = `第 ${g.round} 轮进行中。可“下一轮”继续放线索，或“停牌”结束交易后结算。`;
    else if (g.phase === 'closed') hint = '交易已停牌，盘口已清空。点“结算”公布答案并计算名次。';
    else hint = '本题已结算。可继续选下一题，或导出复盘。';
    $('hint').textContent = hint;
  }

  function renderBank(g) {
    const bank = state.bank || [];
    $('bankCount').textContent = `${bank.length} 题`;
    const curQ = g ? g.question.q : '';
    $('bank').innerHTML = bank.map((q) => `
      <div class="qbank-item ${q.q === curQ ? 'selected' : ''}" data-index="${q.index}">
        <div class="qi-main">
          <div class="qi-q">${escapeHtml(q.q)}</div>
          <div class="qi-meta">${escapeHtml(q.unit)}　·　${q.rounds} 轮线索　·　${q.practice ? '测试版' : '正式题'}</div>
        </div>
        <div class="qi-ans">${escapeHtml(q.answer)}</div>
      </div>`).join('');

    $('bank').querySelectorAll('[data-index]').forEach((row) => {
      row.onclick = async () => {
        const idx = Number(row.dataset.index);
        if (g && (g.phase === 'trading' || g.phase === 'estimate')) {
          if (!confirm('当前题目尚未结算，确定切换到新题？')) return;
        }
        try { await act('addQuestion', { index: idx }); toast('题目已载入'); } catch (e) { toast(e.message); }
      };
    });
  }

  function renderBots() {
    const bots = state.bots || [];
    $('bots').innerHTML = bots.map((b) => `
      <div class="bot-row">
        <div class="bt-main">
          <div class="bt-name">${escapeHtml(b.name)} <span class="qi-meta">${escapeHtml(b.kind)}</span></div>
          <div class="bt-desc">${escapeHtml(b.desc)}</div>
        </div>
        <button class="switch ${b.enabled ? 'on' : ''}" data-bot="${b.id}" aria-label="${escapeHtml(b.name)}"></button>
      </div>`).join('');

    $('bots').querySelectorAll('[data-bot]').forEach((sw) => {
      sw.onclick = async () => {
        const enabled = !sw.classList.contains('on');
        try { await act('toggleBot', { botId: sw.dataset.bot, enabled }); } catch (e) { toast(e.message); }
      };
    });
  }

  function renderPlayers(g) {
    const players = state.players || [];
    $('plyCount').textContent = `${players.length} 人 · ${state.playersOnline} 在线`;
    $('players').innerHTML = players.length ? players.map((p) => `
      <div class="ply-row">
        <span class="dot ${p.online ? 'on' : ''}"></span>
        <span class="nm">${escapeHtml(p.name)}</span>
        <button class="btn sm" data-kick="${p.id}">移除</button>
      </div>`).join('') : '<div class="list-empty">还没有玩家入场</div>';

    $('players').querySelectorAll('[data-kick]').forEach((b) => {
      b.onclick = async () => {
        if (!confirm('把该玩家移出房间？其持仓记录会随之删除。')) return;
        try { await act('kick', { playerId: b.dataset.kick }); toast('已移除'); } catch (e) { toast(e.message); }
      };
    });
  }

  function updateClock(d) {
    if (!state || !state.game) return;
    if (d.round !== state.game.round) return;
    if ($('remainChip')) $('remainChip').textContent = d.remain;
    if ($('tradeCount') && state.game.tradeCount != null) $('tradeCount').textContent = state.game.tradeCount;
  }

  /* ---------------------------- 按钮 ---------------------------- */

  const bind = (id, fn) => {
    $(id).onclick = async () => {
      try { await fn(); } catch (e) { toast(e.message); }
    };
  };

  bind('btnOpen', async () => {
    const d = await act('open');
    toast(`已开盘，参考价 ${yuan(d.openingPrice)}`);
  });

  bind('btnNext', async () => { await act('nextRound'); toast('已进入下一轮'); });

  bind('btnClose', async () => {
    if (!confirm('停牌后不可再下单，盘口将被清空。继续？')) return;
    await act('closeTrading');
    toast('已停牌');
  });

  bind('btnSettle', async () => {
    if (!confirm('按题库答案结算本题？')) return;
    await act('settle');
    toast('已结算');
  });

  bind('btnSec', async () => {
    const s = Number($('secInput').value);
    const d = await act('setRoundSeconds', { seconds: s });
    toast(`轮次时长已设为 ${d.roundSeconds} 秒`);
  });

  bind('btnResetScores', async () => {
    if (!confirm('清空所有已结算题目的积分记录？')) return;
    await act('resetScores');
    toast('积分已清空');
  });

  bind('btnResetRoom', async () => {
    if (!confirm('清空本房间所有题目与成绩？玩家保持在场。')) return;
    await act('resetRoom');
    toast('房间已重置');
  });

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  }

  /* ---------------------------- 启动 ---------------------------- */

  if (!code) {
    location.href = '/';
  } else if (key) {
    fetch(`/api/host?code=${encodeURIComponent(code)}&key=${encodeURIComponent(key)}`)
      .then((r) => { if (!r.ok) throw new Error(); connect(); })
      .catch(() => showGate());
  } else {
    showGate();
  }
})();
