/* 종목 리서치 노트 — 3가지 관점(① 종가매수→시가매도 ② 수개월 스윙 ③ 수년 장기)
 * 입력: 네이버 금융 공개 데이터(일봉 이력, 투자지표, 재무, 컨센서스, 수급)
 * 모든 수치는 규칙으로 계산한 값이며, 표본 수(n)와 가정을 함께 표시한다. 투자자문이 아니다. */
(function (root) {
  'use strict';

  /* ---------- 기본 유틸 ---------- */
  function num(s) {
    if (s == null) return NaN;
    var t = String(s).replace(/[,\s%+배원달러]|USD/g, '').replace('−', '-');
    if (t === '' || t === '-' || t === 'N/A') return NaN;
    var n = parseFloat(t);
    return isFinite(n) ? n : NaN;
  }
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function fin(x) { return typeof x === 'number' && isFinite(x); }
  function F(n, d) { return fin(n) ? n.toLocaleString('ko-KR', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }) : '—'; }
  function S(n, d) { return fin(n) ? (n > 0 ? '+' : '') + n.toFixed(d == null ? 2 : d) : '—'; }
  function cls(n) { return !fin(n) || n === 0 ? '' : (n > 0 ? 'pu' : 'pd'); }          // 상승=빨강, 하락=파랑
  function PC(n, d) { return fin(n) ? '<b class="' + cls(n) + '">' + S(n, d == null ? 2 : d) + '%</b>' : '—'; }
  function mean(a) { if (!a.length) return NaN; var s = 0; for (var i = 0; i < a.length; i++) s += a[i]; return s / a.length; }
  function sd(a) { if (a.length < 2) return NaN; var m = mean(a), s = 0; for (var i = 0; i < a.length; i++) s += (a[i] - m) * (a[i] - m); return Math.sqrt(s / (a.length - 1)); }
  function pctile(a, p) {
    if (!a.length) return NaN;
    var b = a.slice().sort(function (x, y) { return x - y; }), k = (b.length - 1) * p, f = Math.floor(k), c = Math.ceil(k);
    return b[f] + (b[c] - b[f]) * (k - f);
  }
  function stats(a) {
    var n = a.length;
    if (!n) return { n: 0, mean: NaN, med: NaN, win: NaN, avgW: NaN, avgL: NaN, sd: NaN, min: NaN, max: NaN, p5: NaN, pf: NaN };
    var w = a.filter(function (x) { return x > 0; }), l = a.filter(function (x) { return x < 0; });
    var gw = w.reduce(function (s, x) { return s + x; }, 0), gl = -l.reduce(function (s, x) { return s + x; }, 0);
    return { n: n, mean: mean(a), med: pctile(a, 0.5), win: w.length / n * 100, avgW: mean(w), avgL: mean(l), sd: sd(a),
      min: Math.min.apply(null, a), max: Math.max.apply(null, a), p5: pctile(a, 0.05), pf: gl > 0 ? gw / gl : (gw > 0 ? Infinity : NaN) };
  }

  /* ---------- 일봉 이력 ---------- */
  function series(pages) {
    var seen = {}, a = [];
    (pages || []).forEach(function (pg) {
      (pg || []).forEach(function (x) {
        var d = String(x.localTradedAt || '').slice(0, 10);
        if (!d || seen[d]) return;
        var c = num(x.closePrice);
        if (!(c > 0)) return;
        seen[d] = 1;
        a.push({ d: d, o: num(x.openPrice), h: num(x.highPrice), l: num(x.lowPrice), c: c, v: num(x.accumulatedTradingVolume) });
      });
    });
    a.sort(function (p, q) { return p.d < q.d ? -1 : p.d > q.d ? 1 : 0; });
    return a;
  }
  function sma(a, n, off) { off = off || 0; if (a.length < n + off) return NaN; var s = 0; for (var i = a.length - off - n; i < a.length - off; i++) s += a[i].c; return s / n; }
  function emaArr(vals, n) { var k = 2 / (n + 1), e = [], p = vals[0]; for (var i = 0; i < vals.length; i++) { p = i === 0 ? vals[0] : vals[i] * k + p * (1 - k); e.push(p); } return e; }
  function rsi(a, n) {
    n = n || 14;
    if (a.length < n + 1) return NaN;
    var g = 0, l = 0, i;
    for (i = 1; i <= n; i++) { var d = a[i].c - a[i - 1].c; if (d > 0) g += d; else l -= d; }
    g /= n; l /= n;
    for (i = n + 1; i < a.length; i++) { var dd = a[i].c - a[i - 1].c; g = (g * (n - 1) + (dd > 0 ? dd : 0)) / n; l = (l * (n - 1) + (dd < 0 ? -dd : 0)) / n; }
    return l === 0 ? 100 : 100 - 100 / (1 + g / l);
  }
  function macd(a) {
    if (a.length < 35) return { m: NaN, s: NaN, h: NaN };
    var c = a.map(function (x) { return x.c; }), e12 = emaArr(c, 12), e26 = emaArr(c, 26), m = [];
    for (var i = 0; i < c.length; i++) m.push(e12[i] - e26[i]);
    var sg = emaArr(m, 9), L = c.length - 1;
    return { m: m[L], s: sg[L], h: m[L] - sg[L] };
  }
  function boll(a, n) {
    n = n || 20;
    if (a.length < n) return { up: NaN, lo: NaN, mid: NaN, pb: NaN };
    var w = a.slice(-n).map(function (x) { return x.c; }), m = mean(w), s = sd(w), c = a[a.length - 1].c;
    return { up: m + 2 * s, lo: m - 2 * s, mid: m, pb: s > 0 ? (c - (m - 2 * s)) / (4 * s) * 100 : NaN };
  }
  function atr(a, n) {
    n = n || 14;
    if (a.length < n + 1) return NaN;
    var t = [];
    for (var i = a.length - n; i < a.length; i++) {
      var h = fin(a[i].h) ? a[i].h : a[i].c, l = fin(a[i].l) ? a[i].l : a[i].c, pc = a[i - 1].c;
      t.push(Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc)));
    }
    return mean(t);
  }
  function ret(a, n) { return a.length > n ? (a[a.length - 1].c / a[a.length - 1 - n].c - 1) * 100 : NaN; }
  function hiN(a, n) { var m = -Infinity; for (var i = Math.max(0, a.length - n); i < a.length; i++) m = Math.max(m, fin(a[i].h) ? a[i].h : a[i].c); return m === -Infinity ? NaN : m; }
  function loN(a, n) { var m = Infinity; for (var i = Math.max(0, a.length - n); i < a.length; i++) m = Math.min(m, fin(a[i].l) ? a[i].l : a[i].c); return m === Infinity ? NaN : m; }

  /* ---------- 표시 보조 ---------- */
  var LV = [null, ['🚨', '위험'], ['⚠️', '주의'], ['⚖️', '중립'], ['📈', '우호'], ['🚀', '강력 우호']];
  function level(pass, total) {
    if (!total) return 3;
    var r = pass / total;
    return r >= 0.84 ? 5 : r >= 0.67 ? 4 : r >= 0.4 ? 3 : r >= 0.2 ? 2 : 1;
  }
  var _m = [];
  function head(title, sub, pass, total) {
    var lv = level(pass, total), L = LV[lv];
    _m.push(total >= 3 ? { lv: lv, p: pass, t: total } : null);
    return '<div class="rnh"><div><b>' + esc(title) + '</b><small>' + esc(sub) + '</small></div>' +
      '<div class="rnb l' + lv + '"><div style="display:flex;align-items:center;gap:6px"><span>' + L[0] + '</span><em>' + pass + '/' + total + '</em></div><span class="stars">' + '\u2605'.repeat(lv) + '<i>' + '\u2605'.repeat(5 - lv) + '</i></span></div></div>';
  }
  function kv(pairs) {
    return '<div class="rnk">' + pairs.map(function (p) { return '<div><span>' + p[0] + '</span><b>' + p[1] + '</b></div>'; }).join('') + '</div>';
  }
  function tbl(cols, rows, note) {
    var h = '<table class="rnt"><thead><tr>' + cols.map(function (c, i) { return '<th' + (i ? ' class="r"' : '') + '>' + c + '</th>'; }).join('') + '</tr></thead><tbody>';
    rows.forEach(function (r) { h += '<tr>' + r.map(function (c, i) { return '<td' + (i ? ' class="r"' : '') + '>' + c + '</td>'; }).join('') + '</tr>'; });
    return h + '</tbody></table>' + (note ? '<div class="rnn">' + note + '</div>' : '');
  }
  function chk(list) {
    return '<ul class="rnc">' + list.map(function (x) {
      var m = x.ok === true ? '<i class="ok">✔</i>' : x.ok === false ? '<i class="no">✖</i>' : '<i class="na">–</i>';
      return '<li>' + m + '<span>' + x.t + '</span></li>';
    }).join('') + '</ul>';
  }
  function sec(t, body) { return '<div class="rns"><h5>' + t + '</h5>' + body + '</div>'; }
  function cmt(t) { return '<div class="rnm">' + t + '</div>'; }
  function warn(list) { return list.length ? '<div class="rnw"><b>리스크 체크</b><ul>' + list.map(function (x) { return '<li>' + x + '</li>'; }).join('') + '</ul></div>' : ''; }
  var DISC = '<div class="rnd">공개 데이터(네이버 금융)를 정해진 규칙으로 계산한 참고 자료입니다. 과거 통계는 미래 수익을 보장하지 않으며, 표본 수(n)가 작으면 신뢰도가 낮습니다. 투자자문이 아니며 투자 책임은 본인에게 있습니다.</div>';

  /* ---------- 재무 프레임 ---------- */
  function frame(j) {
    var fi = j && (j.financeInfo || j);
    if (!fi || !fi.rowList || !fi.trTitleList) return null;
    var cols = fi.trTitleList.map(function (c) { return { key: c.key, title: c.title, est: c.isConsensus === 'Y' }; }), rows = {};
    fi.rowList.forEach(function (r) { rows[r.title] = r.columns || {}; });
    return {
      cols: cols,
      get: function (title, key) { var r = rows[title]; return r && r[key] ? num(r[key].value) : NaN; },
      has: function (title) { return !!rows[title]; }
    };
  }
  function actual(fr) { return fr ? fr.cols.filter(function (c) { return !c.est; }) : []; }
  function cagr(fr, title) {
    var ac = actual(fr);
    if (ac.length < 2) return { v: NaN, n: 0 };
    var a = fr.get(title, ac[0].key), b = fr.get(title, ac[ac.length - 1].key), yrs = ac.length - 1;
    if (!(a > 0) || !(b > 0)) return { v: NaN, n: yrs };
    return { v: (Math.pow(b / a, 1 / yrs) - 1) * 100, n: yrs };
  }
  function yoy(fr, title, ci) {
    if (!fr || ci < 1) return NaN;
    var a = fr.get(title, fr.cols[ci - 1].key), b = fr.get(title, fr.cols[ci].key);
    return a > 0 && fin(b) ? (b / a - 1) * 100 : NaN;
  }

  /* ---------- 메인 ---------- */
  function build(o) {
    _m = [];
    var us = !!o.us, ti = {};
    (o.totalInfos || []).forEach(function (x) { ti[x.code] = x.value; });
    var H = series(o.hist), N = H.length, last = N ? H[N - 1] : null;
    var P = fin(o.price) && o.price > 0 ? o.price : (last ? last.c : NaN);
    function PR(n, d) { return fin(n) ? (us ? '$' + F(n, d == null ? 2 : d) : F(n, 0) + '원') : '—'; }
    var cons = o.cons || {}, tp = num(cons.priceTargetMean), up = fin(tp) && P > 0 ? (tp / P - 1) * 100 : NaN, rec = num(cons.recommMean);
    var deal = (o.deal || []).slice(0, 5).map(function (x) { return { f: num(x.foreignerPureBuyQuant), i: num(x.organPureBuyQuant), p: num(x.individualPureBuyQuant), hr: num(x.foreignerHoldRatio) }; });
    var A = fin(N) && N > 14 ? atr(H, 14) : NaN, atrp = fin(A) && P > 0 ? A / P * 100 : NaN;
    var r14 = rsi(H, 14), bl = boll(H, 20), mc = macd(H);
    var m5 = sma(H, 5), m20 = sma(H, 20), m60 = sma(H, 60), m120 = sma(H, 120);
    var hi52 = num(ti.highPriceOf52Weeks), lo52 = num(ti.lowPriceOf52Weeks);
    var per = num(ti.per), pbr = num(ti.pbr), eps = num(ti.eps), bps = num(ti.bps), cnsEps = num(ti.cnsEps);
    var divy = num(ti.dividendYieldRatio), dps = num(ti.dividend);
    var out = ['', '', ''];
    var dataNote = N < 30 ? '<div class="rnw"><b>데이터 부족</b><ul><li>가격 이력 ' + N + '일 — 이력 기반 수치(갭 통계·이동평균 등)를 계산하지 못했습니다.</li></ul></div>' : '';

    /* ======== ① 종가매수 → 익일 시가매도 ======== */
    (function () {
      var rows = [], items = [], pass = 0, tot = 0, risks = [];
      function add(ok, t) { items.push({ ok: ok, t: t }); if (ok !== null) { tot++; if (ok) pass++; } }
      var strength = last && fin(last.h) && fin(last.l) && last.h > last.l ? (last.c - last.l) / (last.h - last.l) * 100 : NaN;
      var chg = N > 1 ? (H[N - 1].c / H[N - 2].c - 1) * 100 : NaN;
      var v20 = NaN, vx = NaN;
      if (N > 21 && fin(last.v)) {
        var vs = H.slice(-21, -1).map(function (x) { return x.v; }).filter(fin);
        v20 = vs.length >= 10 ? mean(vs) : NaN; vx = fin(v20) && v20 > 0 ? last.v / v20 : NaN;
      }
      var h20 = hiN(H, 20), fromH20 = fin(h20) ? (P / h20 - 1) * 100 : NaN;
      /* 오버나이트 갭 = 다음날 시가 / 오늘 종가 */
      var gaps = [], gStr = [], gUp = [];
      for (var i = Math.max(0, N - 61); i < N - 1; i++) {
        if (!fin(H[i + 1].o) || !(H[i + 1].o > 0)) continue;
        var g = (H[i + 1].o / H[i].c - 1) * 100;
        gaps.push(g);
        var s = fin(H[i].h) && fin(H[i].l) && H[i].h > H[i].l ? (H[i].c - H[i].l) / (H[i].h - H[i].l) * 100 : NaN;
        if (fin(s) && s >= 70) gStr.push(g);
        if (i > 0 && H[i].c > H[i - 1].c) gUp.push(g);
      }
      var sA = stats(gaps), sB = stats(gStr), sC = stats(gUp);
      add(fin(strength) ? strength >= 70 : null, '종가강도 ' + (fin(strength) ? strength.toFixed(0) + '%' : '—') + ' (당일 고저폭 중 종가 위치, 기준 ≥70%)');
      add(fin(vx) ? vx >= 1.2 : null, '거래량 ' + (fin(vx) ? vx.toFixed(2) + '배' : '—') + ' (20일 평균 대비, 기준 ≥1.2배)');
      add(fin(m5) ? P >= m5 : null, '종가 ' + PR(P) + ' vs 5일선 ' + PR(m5) + ' (기준: 상회)');
      add(fin(fromH20) ? fromH20 >= -3 : null, '20일 고점 대비 ' + (fin(fromH20) ? S(fromH20, 1) + '%' : '—') + ' (기준 -3% 이내)');
      if (!us && deal.length) { var fi = deal[0].f + deal[0].i; add(fin(fi) ? fi > 0 : null, '당일 외국인+기관 순매수 ' + (fin(fi) ? F(fi) + '주' : '—') + ' (기준: 순매수)'); }
      add(sA.n >= 20 ? sA.win >= 55 : null, '60일 오버나이트 승률 ' + (sA.n ? sA.win.toFixed(0) + '%' : '—') + ' (기준 ≥55%)');
      if (fin(r14) && r14 >= 78) risks.push('RSI(14) ' + r14.toFixed(0) + ' — 단기 과열 구간, 갭 반납 가능성');
      if (fin(chg) && chg >= 10) risks.push('당일 ' + S(chg, 1) + '% 급등 마감 — 익일 차익실현 매물 유의');
      if (fin(chg) && chg <= -7) risks.push('당일 ' + S(chg, 1) + '% 급락 — 추세 훼손 구간, 반등 갭은 약할 수 있음');
      if (fin(sA.sd) && sA.sd >= 2.5) risks.push('갭 변동성 σ ' + sA.sd.toFixed(2) + '% — 변동성이 커서 포지션 크기 축소 필요');
      if (fin(sA.min) && sA.min <= -5) risks.push('최근 60일 최악 갭 ' + S(sA.min, 2) + '% — 하방 꼬리 리스크 존재');
      if (!us && deal.length && deal[0].f < 0 && deal[0].i < 0) risks.push('외국인·기관 동반 순매도 — 수급 이탈');

      var sub = '1거래일 · 오버나이트 · 기준일 ' + (last ? last.d : '—') + (o.live ? ' (장중 값 포함)' : '');
      var h = head('단기 · 종가매수 → 익일 시가매도', sub, pass, tot);
      h += kv([
        ['종가', PR(P)], ['당일 등락', PC(chg, 2)], ['종가강도', fin(strength) ? strength.toFixed(0) + '%' : '—'],
        ['거래량 배수', fin(vx) ? vx.toFixed(2) + '배' : '—'], ['20일 고점 대비', PC(fromH20, 1)], ['ATR(14)', fin(A) ? PR(A) + ' (' + atrp.toFixed(2) + '%)' : '—']
      ]);
      h += sec('오버나이트 갭 통계 (최근 ' + sA.n + '거래일, 다음날 시가÷오늘 종가)',
        tbl(['조건', '표본', '승률', '평균', '손익비'], [
          ['전체', sA.n, sA.n ? sA.win.toFixed(0) + '%' : '—', PC(sA.mean, 2), fin(sA.pf) ? (isFinite(sA.pf) ? sA.pf.toFixed(2) : '∞') : '—'],
          ['종가강도 ≥70% 마감', sB.n, sB.n ? sB.win.toFixed(0) + '%' : '—', PC(sB.mean, 2), fin(sB.pf) ? (isFinite(sB.pf) ? sB.pf.toFixed(2) : '∞') : '—'],
          ['당일 상승 마감', sC.n, sC.n ? sC.win.toFixed(0) + '%' : '—', PC(sC.mean, 2), fin(sC.pf) ? (isFinite(sC.pf) ? sC.pf.toFixed(2) : '∞') : '—']
        ], '손익비 = 이익 갭 합 ÷ 손실 갭 합. 표본 20 미만 구간은 참고만 하세요.'));
      if (sA.n >= 10) {
        var base = P, bu = base * (1 + (sA.mean + sA.sd) / 100), bm = base * (1 + sA.mean / 100), bd = base * (1 + (sA.mean - sA.sd) / 100);
        h += sec('익일 시가 시나리오 (평균 ± 1σ, 약 68% 구간)', tbl(['시나리오', '예상 시가', '변동'], [
          ['강세 (+1σ)', PR(bu), PC(sA.mean + sA.sd, 2)], ['기준 (평균)', PR(bm), PC(sA.mean, 2)], ['약세 (−1σ)', PR(bd), PC(sA.mean - sA.sd, 2)]
        ], '하방 5% 분위 갭 ' + S(sA.p5, 2) + '% · 최악 ' + S(sA.min, 2) + '% · 최고 ' + S(sA.max, 2) + '%'));
      }
      h += sec('체크리스트', chk(items));
      var cm = sA.n >= 10 ? '최근 ' + sA.n + '거래일 오버나이트 갭 평균 <b>' + S(sA.mean, 2) + '%</b>, 승률 <b>' + sA.win.toFixed(0) + '%</b>, 갭 σ ' + sA.sd.toFixed(2) + '%.' +
        (sB.n >= 5 ? ' 종가강도 70% 이상으로 마감한 날(n=' + sB.n + ')에는 평균 ' + S(sB.mean, 2) + '%, 승률 ' + sB.win.toFixed(0) + '%.' : '') : '이력이 부족해 갭 통계를 산출하지 못했습니다.';
      h += cmt(cm);
      h += warn(risks);
      out[0] = h + dataNote + DISC;
    })();

    /* ======== ② 수개월 스윙 ======== */
    (function () {
      var items = [], pass = 0, tot = 0, risks = [];
      function add(ok, t) { items.push({ ok: ok, t: t }); if (ok !== null) { tot++; if (ok) pass++; } }
      var r1 = ret(H, 21), r3 = ret(H, 63), r6 = ret(H, 126);
      var d20 = fin(m20) ? (P / m20 - 1) * 100 : NaN, d60 = fin(m60) ? (P / m60 - 1) * 100 : NaN, d120 = fin(m120) ? (P / m120 - 1) * 100 : NaN;
      var pos52 = fin(hi52) && fin(lo52) && hi52 > lo52 ? (P - lo52) / (hi52 - lo52) * 100 : NaN;
      var aligned = fin(m20) && fin(m60) && fin(m120) ? (m20 > m60 && m60 > m120) : null;
      add(fin(m60) ? P > m60 : null, '현재가 ' + PR(P) + ' vs 60일선 ' + PR(m60) + ' (' + S(d60, 1) + '%)');
      add(fin(m20) && fin(m60) ? m20 > m60 : null, '20일선 ' + PR(m20) + ' vs 60일선 ' + PR(m60) + ' (중기 추세)');
      add(fin(r3) ? r3 > 0 : null, '3개월 수익률 ' + S(r3, 1) + '%');
      add(fin(r14) ? (r14 >= 45 && r14 <= 70) : null, 'RSI(14) ' + (fin(r14) ? r14.toFixed(0) : '—') + ' (건강 구간 45~70)');
      add(fin(mc.h) ? mc.h > 0 : null, 'MACD 히스토그램 ' + (fin(mc.h) ? S(mc.h, us ? 2 : 0) : '—') + ' (0 초과 = 상승 모멘텀)');
      if (!us && deal.length) { var f5 = deal.reduce(function (s, x) { return s + (fin(x.f) ? x.f : 0); }, 0), i5 = deal.reduce(function (s, x) { return s + (fin(x.i) ? x.i : 0); }, 0); add((f5 + i5) > 0, '최근 ' + deal.length + '일 외국인 ' + F(f5) + '주 · 기관 ' + F(i5) + '주 순매수'); }
      add(fin(up) ? up >= 10 : null, '컨센서스 목표가 ' + PR(tp) + ' (여력 ' + S(up, 1) + '%, 기준 ≥10%)');
      if (fin(r14) && r14 >= 75) risks.push('RSI ' + r14.toFixed(0) + ' 과열 — 신규 진입은 눌림 확인 후');
      if (fin(d20) && d20 >= 12) risks.push('20일선 이격 ' + S(d20, 1) + '% — 단기 과확장, 조정 시 20일선까지 되돌림 가능');
      if (fin(bl.pb) && bl.pb >= 100) risks.push('볼린저 상단 이탈(%B ' + bl.pb.toFixed(0) + ') — 변동성 확대 구간');
      if (aligned === false && fin(m120) && P < m120) risks.push('120일선 하회 — 중기 하락 추세');
      if (fin(r6) && r6 <= -25) risks.push('6개월 ' + S(r6, 1) + '% 하락 — 낙폭 과대, 반등 확인 전 분할 접근');
      var h60 = hiN(H, 60), l20 = loN(H, 20), l60 = loN(H, 60);
      var stop = fin(A) ? Math.max(P - 2.5 * A, fin(m60) ? m60 * 0.97 : -Infinity) : NaN;
      if (fin(stop) && stop >= P) stop = fin(A) ? P - 2.5 * A : NaN;
      var t1 = fin(h60) && h60 > P * 1.02 ? h60 : (fin(A) ? P + 3 * A : NaN);
      var t2 = fin(tp) && tp > t1 ? tp : (fin(hi52) && hi52 > t1 ? hi52 : (fin(t1) && fin(A) ? t1 + 3 * A : NaN));
      var rr1 = fin(stop) && fin(t1) && P > stop ? (t1 - P) / (P - stop) : NaN, rr2 = fin(stop) && fin(t2) && P > stop ? (t2 - P) / (P - stop) : NaN;
      var q = o.quarter && o.quarter.cols ? o.quarter : frame(o.quarter), qa = q ? actual(q) : [], ql = qa.length, qopT = us ? 'EBIT' : '영업이익';
      var qi = ql ? q.cols.indexOf(qa[ql - 1]) : -1;
      var opY = ql >= 5 ? (function () { var a = q.get(qopT, qa[ql - 5].key), b = q.get(qopT, qa[ql - 1].key); return a > 0 ? (b / a - 1) * 100 : NaN; })() : NaN;
      var opQ = ql >= 2 ? (function () { var a = q.get(qopT, qa[ql - 2].key), b = q.get(qopT, qa[ql - 1].key); return a > 0 ? (b / a - 1) * 100 : NaN; })() : NaN;
      var rvY = ql >= 5 ? (function () { var a = q.get('매출액', qa[ql - 5].key), b = q.get('매출액', qa[ql - 1].key); return a > 0 ? (b / a - 1) * 100 : NaN; })() : NaN;
      var rvQ = ql >= 2 ? (function () { var a = q.get('매출액', qa[ql - 2].key), b = q.get('매출액', qa[ql - 1].key); return a > 0 ? (b / a - 1) * 100 : NaN; })() : NaN;
      if (ql) { add(fin(opY) ? opY > 0 : null, '최근 분기(' + qa[ql - 1].title + ') ' + (us ? 'EBIT' : '영업이익') + ' YoY ' + S(opY, 1) + '% · QoQ ' + S(opQ, 1) + '%'); }

      var h = head('중기 · 스윙 (3~6개월)', '추세 · 모멘텀 · 실적 · 컨센서스 · 기준일 ' + (last ? last.d : '—'), pass, tot);
      h += kv([
        ['현재가', PR(P)], ['20일선', PR(m20) + ' <small>' + S(d20, 1) + '%</small>'], ['60일선', PR(m60) + ' <small>' + S(d60, 1) + '%</small>'],
        ['120일선', PR(m120) + ' <small>' + S(d120, 1) + '%</small>'], ['배열', aligned === true ? '정배열' : aligned === false ? '혼조/역배열' : '—'], ['52주 위치', fin(pos52) ? pos52.toFixed(0) + '% <small>(' + PR(lo52) + '~' + PR(hi52) + ')</small>' : '—'],
        ['RSI(14)', fin(r14) ? r14.toFixed(1) : '—'], ['MACD / 시그널', fin(mc.m) ? S(mc.m, us ? 2 : 0) + ' / ' + S(mc.s, us ? 2 : 0) : '—'], ['볼린저 %B', fin(bl.pb) ? bl.pb.toFixed(0) : '—']
      ]);
      h += sec('수익률 · 변동성', tbl(['구간', '1개월', '3개월', '6개월'], [
        ['주가 수익률', PC(r1, 1), PC(r3, 1), PC(r6, 1)],
        ['ATR(14) 일변동', fin(atrp) ? atrp.toFixed(2) + '%' : '—', '', '']
      ]));
      if (ql) h += sec('실적 모멘텀 (' + qa[ql - 1].title + ' 기준)', tbl(['항목', 'YoY', 'QoQ'], [['매출액', PC(rvY, 1), PC(rvQ, 1)], [us ? 'EBIT' : '영업이익', PC(opY, 1), PC(opQ, 1)]]));
      if (fin(stop) && fin(t1)) h += sec('트레이딩 플랜 (ATR·지지/저항 기반)', tbl(['구분', '가격', '현재가 대비', '손익비'], [
        ['진입(현재가)', PR(P), '—', '—'],
        ['손절', PR(stop), PC((stop / P - 1) * 100, 1), '—'],
        ['1차 목표 (60일 고점/3ATR)', PR(t1), PC((t1 / P - 1) * 100, 1), fin(rr1) ? rr1.toFixed(2) : '—'],
        ['2차 목표 (컨센서스/52주)', PR(t2), PC((t2 / P - 1) * 100, 1), fin(rr2) ? (rr2 > 10 ? '10+' : rr2.toFixed(2)) : '—']
      ], '손절 = max(현재가−2.5ATR, 60일선×0.97). 20일 저점 ' + PR(l20) + ' · 60일 저점 ' + PR(l60) + ' 이탈 시 추세 재점검.'));
      h += sec('체크리스트', chk(items));
      var cmS = '주가는 20/60/120일선 대비 ' + S(d20, 1) + '% / ' + S(d60, 1) + '% / ' + S(d120, 1) + '%에 위치하며 3개월 수익률은 ' + S(r3, 1) + '%입니다.';
      if (fin(up)) cmS += ' 컨센서스 평균 목표가 ' + PR(tp) + '(투자의견 평균 ' + (fin(rec) ? rec.toFixed(2) : '—') + ')로 여력은 ' + S(up, 1) + '%.';
      if (fin(per)) cmS += ' 현재 PER ' + per.toFixed(1) + '배, PBR ' + (fin(pbr) ? pbr.toFixed(2) : '—') + '배.';
      h += cmt(cmS);
      h += warn(risks);
      out[1] = h + dataNote + DISC;
    })();

    /* ======== ③ 수년 장기 ======== */
    (function () {
      var fa = o.annual && o.annual.cols ? o.annual : frame(o.annual), items = [], pass = 0, tot = 0, risks = [];
      function add(ok, t) { items.push({ ok: ok, t: t }); if (ok !== null) { tot++; if (ok) pass++; } }
      var opT = us ? 'EBIT' : '영업이익', niT = '당기순이익';
      var sub = '재무 · 밸류에이션 · 내재가치 · 3년 시나리오';
      if (!fa) {
        out[2] = head('장기 · 투자 (3년 이상)', sub, 0, 0) + '<div class="rnw"><b>재무 데이터 없음</b><ul><li>이 종목(ETF·신규상장 등)은 연간 재무 자료를 읽지 못했습니다. 컨센서스 목표가 ' + PR(tp) + ' (여력 ' + S(up, 1) + '%)</li></ul></div>' + DISC;
        return;
      }
      var ac = actual(fa), allc = fa.cols, lastA = ac[ac.length - 1], estC = allc.filter(function (c) { return c.est; })[0];
      var cr = cagr(fa, '매출액'), co = cagr(fa, opT), cn = cagr(fa, niT);
      var roeT = us ? 'ROA' : 'ROE';
      var roe = lastA ? fa.get(roeT, lastA.key) : NaN;
      var debt = lastA && !us ? fa.get('부채비율', lastA.key) : NaN;
      function opm(c) { var a = fa.get(opT, c.key), b = fa.get('매출액', c.key); return fin(a) && b > 0 ? a / b * 100 : NaN; }
      var opmLast = lastA ? opm(lastA) : NaN, opmPrev = ac.length > 1 ? opm(ac[ac.length - 2]) : NaN;
      var pers = ac.map(function (c) { return fa.get('PER', c.key); }).filter(function (x) { return fin(x) && x > 0; });
      var perAvg = mean(pers), perMin = pers.length ? Math.min.apply(null, pers) : NaN, perMax = pers.length ? Math.max.apply(null, pers) : NaN;
      var epsFwd = fin(cnsEps) && cnsEps > 0 ? cnsEps : eps, epsLabel = fin(cnsEps) && cnsEps > 0 ? '컨센서스 EPS' : '최근 EPS';
      var gEps = fin(cn.v) ? cn.v : cr.v;
      var peg = fin(per) && per > 0 && fin(gEps) && gEps > 0 ? per / gEps : NaN;
      var estG = estC && lastA ? (function () { var a = fa.get(opT, lastA.key), b = fa.get(opT, estC.key); return a > 0 && fin(b) ? (b / a - 1) * 100 : NaN; })() : NaN;

      add(fin(roe) ? roe >= (us ? 5 : 10) : null, roeT + ' ' + (fin(roe) ? roe.toFixed(1) + '%' : '—') + ' (기준 ≥' + (us ? 5 : 10) + '%)');
      add(fin(opmLast) && fin(opmPrev) ? opmLast >= opmPrev : null, (us ? 'EBIT' : '영업') + '이익률 ' + (fin(opmLast) ? opmLast.toFixed(1) + '%' : '—') + ' (전년 ' + (fin(opmPrev) ? opmPrev.toFixed(1) + '%' : '—') + ', 개선/유지 기준)');
      add(fin(cr.v) && fin(co.v) ? cr.v > 0 && co.v > 0 : (fin(cr.v) ? cr.v > 0 : null), '매출 CAGR ' + S(cr.v, 1) + '% · ' + (us ? 'EBIT' : '영업이익') + ' CAGR ' + S(co.v, 1) + '% (' + cr.n + '년)');
      if (!us) add(fin(debt) ? debt < 100 : null, '부채비율 ' + (fin(debt) ? debt.toFixed(0) + '%' : '—') + ' (기준 100% 미만)');
      add(fin(per) && fin(perAvg) ? per <= perAvg : null, '현재 PER ' + (fin(per) ? per.toFixed(1) : '—') + '배 vs 과거 평균 ' + (fin(perAvg) ? perAvg.toFixed(1) : '—') + '배');
      add(fin(peg) ? peg <= 1.5 : null, 'PEG ' + (fin(peg) ? peg.toFixed(2) : '—') + ' (PER÷이익성장률, 기준 ≤1.5)');
      add(fin(up) ? up >= 10 : null, '컨센서스 목표가 여력 ' + S(up, 1) + '% (기준 ≥10%)');
      add(fin(divy) ? divy > 0 : null, '배당수익률 ' + (fin(divy) ? divy.toFixed(2) + '%' : '—'));
      add(fin(estG) ? estG < 150 : null, '컨센서스 추정 신뢰성 — 영업이익 추정 증가율 ' + S(estG, 0) + '% (기준 150% 미만)');
      if (fin(estG) && estG >= 150) risks.push('컨센서스 ' + (us ? 'EBIT' : '영업이익') + ' 추정치가 전년 대비 ' + S(estG, 0) + '% — 사이클 정점·추정 오차 가능성, 실적 확인 전 보수적 해석');
      if (fin(per) && fin(perAvg) && per > perAvg * 1.5) risks.push('PER이 과거 평균의 ' + (per / perAvg).toFixed(1) + '배 — 밸류에이션 부담');
      if (fin(roe) && roe < 5 && !us) risks.push('ROE ' + roe.toFixed(1) + '% — 자본 효율 낮음');
      if (fin(debt) && debt >= 200) risks.push('부채비율 ' + debt.toFixed(0) + '% — 금리·경기 민감');

      function money(v) {
        if (!fin(v)) return '—';
        if (us) return Math.abs(v) >= 1000 ? '$' + F(v / 1000, 1) + 'B' : '$' + F(v, 0) + 'M';
        return Math.abs(v) >= 10000 ? F(v / 10000, 1) + '조' : F(v, 0) + '억';
      }
      var rowsF = [], showCols = allc.slice(-5);
      function rowF(label, fn) { rowsF.push([label].concat(showCols.map(fn))); }
      rowF('매출액', function (c) { return money(fa.get('매출액', c.key)); });
      rowF(us ? 'EBIT' : '영업이익', function (c) { return money(fa.get(opT, c.key)); });
      rowF('당기순이익', function (c) { return money(fa.get(niT, c.key)); });
      rowF((us ? 'EBIT' : '영업') + '이익률', function (c) { var v = opm(c); return fin(v) ? v.toFixed(1) + '%' : '—'; });
      rowF(roeT, function (c) { var v = fa.get(roeT, c.key); return fin(v) ? v.toFixed(1) + '%' : '—'; });
      if (!us) { rowF('부채비율', function (c) { var v = fa.get('부채비율', c.key); return fin(v) ? v.toFixed(0) + '%' : '—'; }); rowF('EPS', function (c) { var v = fa.get('EPS', c.key); return fin(v) ? F(v, 0) : '—'; }); rowF('주당배당금', function (c) { var v = fa.get('주당배당금', c.key); return fin(v) ? F(v, 0) : '—'; }); }
      else rowF('배당수익률', function (c) { var v = fa.get('배당수익률', c.key); return fin(v) ? v.toFixed(2) + '%' : '—'; });
      rowF('PER', function (c) { var v = fa.get('PER', c.key); return fin(v) ? v.toFixed(1) + '배' : '—'; });
      rowF('PBR', function (c) { var v = fa.get('PBR', c.key); return fin(v) ? v.toFixed(2) + '배' : '—'; });
      var colsF = ['항목'].concat(showCols.map(function (c) { return c.title.replace(/\.$/, '').slice(0, us ? 7 : 7) + (c.est ? '<i class="rne">E</i>' : ''); }));

      var h = head('장기 · 투자 (3년 이상)', sub, pass, tot);
      h += kv([
        ['시가총액', esc(ti.marketValue || '—')], ['PER / PBR', (fin(per) ? per.toFixed(1) : '—') + ' / ' + (fin(pbr) ? pbr.toFixed(2) : '—')], ['EPS / BPS', (fin(eps) ? F(eps, us ? 2 : 0) : '—') + ' / ' + (fin(bps) ? F(bps, us ? 2 : 0) : '—')],
        ['과거 평균 PER', fin(perAvg) ? perAvg.toFixed(1) + '배 <small>(' + perMin.toFixed(1) + '~' + perMax.toFixed(1) + ')</small>' : '—'], ['PEG', fin(peg) ? peg.toFixed(2) : '—'], ['배당수익률', fin(divy) ? divy.toFixed(2) + '%' : '—'],
        ['목표가(컨센서스)', PR(tp)], ['목표가 여력', PC(up, 1)], ['투자의견 평균', fin(rec) ? rec.toFixed(2) + ' / 5' : '—']
      ]);
      h += sec('연간 재무 추이 (' + (us ? 'USD' : '원화') + ')', tbl(colsF, rowsF, (estC ? 'E = 컨센서스 추정. ' : '') + (us ? '' : '금액 단위: 억원(1조=10,000억). ') + '성장률은 실적 연도 ' + cr.n + '년 구간 CAGR 기준.'));
      /* 내재가치 */
      var fvRows = [];
      if (fin(epsFwd) && epsFwd > 0 && pers.length) {
        fvRows.push(['PER 밴드 (' + epsLabel + ' ' + F(epsFwd, us ? 2 : 0) + ' × 과거 PER)', '저 ' + PR(epsFwd * perMin), '평균 ' + PR(epsFwd * perAvg), '고 ' + PR(epsFwd * perMax)]);
      }
      if (!us && fin(bps) && fin(roe) && roe > 0) {
        var fp = bps * Math.min(roe, 25) / 10;
        fvRows.push(['ROE-PBR (BPS×ROE÷10%, ROE≤25% 캡)', '—', PR(fp), '—']);
      }
      if (fvRows.length) {
        h += sec('적정주가 레인지 (현재가 ' + PR(P) + ')', tbl(['방법', '저', '기준', '고'], fvRows.map(function (r) { return r; }), '가정 기반 단순 모형입니다. 업황 사이클·일회성 이익이 크면 괴리가 큽니다.'));
      }
      /* 3년 시나리오 */
      if (fin(epsFwd) && epsFwd > 0 && fin(gEps) && P > 0) {
        var g0 = Math.max(-10, Math.min(30, gEps)), exitPer = pers.length ? Math.max(5, Math.min(40, perAvg)) : (fin(per) ? per : 12);
        var sc = g0 >= 0 ? [['보수', g0 * 0.5], ['기준', g0], ['낙관', g0 * 1.5]] : [['보수', g0 * 1.5], ['기준', g0], ['낙관', g0 * 0.5]];
        var dy = fin(divy) ? divy : 0;
        h += sec('3년 후 시나리오 (EPS 성장 × 종료 PER ' + exitPer.toFixed(1) + '배)', tbl(['시나리오', '연 EPS 성장', '3년 후 주가', '연환산 수익률(배당 포함)'], sc.map(function (s) {
          var p3 = epsFwd * Math.pow(1 + s[1] / 100, 3) * exitPer, ar = (Math.pow(p3 / P, 1 / 3) - 1) * 100 + dy;
          return [s[0], PC(s[1], 1), PR(p3), PC(ar, 1)];
        }), '기준 성장률 = ' + (fin(cn.v) ? '순이익' : '매출') + ' CAGR(±30% 캡). 종료 PER = 과거 평균(5~40배 캡). 가정이 바뀌면 결과도 크게 달라집니다.'));
      }
      h += sec('체크리스트', chk(items));
      var cmL = '실적 연도 기준 매출 CAGR <b>' + S(cr.v, 1) + '%</b>, ' + (us ? 'EBIT' : '영업이익') + ' CAGR <b>' + S(co.v, 1) + '%</b>, 순이익 CAGR ' + S(cn.v, 1) + '% (' + cr.n + '년). ';
      if (fin(per) && fin(perAvg)) cmL += '현재 PER ' + per.toFixed(1) + '배는 과거 평균 ' + perAvg.toFixed(1) + '배 대비 ' + S((per / perAvg - 1) * 100, 0) + '%. ';
      if (fin(estG)) cmL += '컨센서스 ' + (us ? 'EBIT' : '영업이익') + '은 전년 대비 ' + S(estG, 0) + '% 증가 전망. ';
      if (fin(up)) cmL += '평균 목표가 여력 ' + S(up, 1) + '%.';
      h += cmt(cmL);
      h += warn(risks);
      out[2] = h + DISC;
    })();
    out.meta = _m.slice(0, 3);
    return out;
  }

  var api = { build: build, LV: LV, level: level, _t: { num: num, series: series, stats: stats, rsi: rsi, macd: macd, atr: atr, cagr: cagr, frame: frame } };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.SaPro = api;
})(typeof window !== 'undefined' ? window : this);
