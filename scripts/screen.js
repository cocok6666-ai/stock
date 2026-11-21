#!/usr/bin/env node
/* 종목 스크리닝: research.js(종목분석과 동일한 계산)로 종목별 3관점 단계를 계산해 stats.json 에 저장.
 * 사용: node scripts/screen.js [kr|us|all]   (환경변수 LIMIT=n 이면 시장별 n개만) */
const fs = require('fs');
const SaPro = require('../research.js');
const MODE = process.argv[2] || 'all';
const LIMIT = +process.env.LIMIT || 0;
const H = { 'User-Agent': 'Mozilla/5.0' };
async function get(url, tries = 3) {
  let err;
  for (let i = 0; i < tries; i++) {
    try {
      const r = await fetch(url, { headers: H, signal: AbortSignal.timeout(25000) });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return await r.json();
    } catch (e) { err = e; await new Promise(r => setTimeout(r, 700 * (i + 1))); }
  }
  throw err;
}
const soft = u => get(u, 2).catch(() => null);
const N = s => { if (s == null) return NaN; const m = String(s).replace(/[,\s%+]/g, '').replace('−', '-').match(/-?\d+(?:\.\d+)?/); return m ? parseFloat(m[0]) : NaN; };

async function one(us, id) {
  const B = us ? 'https://api.stock.naver.com/stock/' + encodeURIComponent(id) : 'https://m.stock.naver.com/api/stock/' + encodeURIComponent(id);
  const [bs, it, p1, p2, p3, fa, fq] = await Promise.all([
    soft(B + '/basic'), soft(B + '/integration'),
    soft(B + '/price?pageSize=60&page=1'), soft(B + '/price?pageSize=60&page=2'), soft(B + '/price?pageSize=60&page=3'),
    soft(B + '/finance/annual'), soft(B + '/finance/quarter')]);
  const pages = [p1, p2, p3].filter(Array.isArray);
  if (!bs || pages.length < 2) return null;
  const ig = us ? { totalInfos: bs.stockItemTotalInfos || [], consensusInfo: (it && it.consensusInfo) || {} } : (it || {});
  const out = SaPro.build({ us, price: N(bs.closePrice), totalInfos: ig.totalInfos || [], hist: pages, cons: ig.consensusInfo || {},
    deal: us ? [] : (ig.dealTrendInfos || []), annual: fa, quarter: fq });
  const last = pages[0][0] && String(pages[0][0].localTradedAt || '').slice(0, 10);
  return { meta: out.meta, last };
}
async function pool(items, fn, n = 12) {
  const res = new Array(items.length); let i = 0, done = 0;
  await Promise.all(Array.from({ length: n }, async () => {
    while (i < items.length) {
      const k = i++;
      try { res[k] = await fn(items[k]); } catch (e) { res[k] = null; }
      if (++done % 100 === 0) console.log(done + '/' + items.length);
    }
  }));
  return res;
}
const flat = m => m ? [m.lv, m.p, m.t] : [null, null, null];

(async () => {
  const t0 = Date.now();
  let cur = {};
  try { cur = JSON.parse(fs.readFileSync('stats.json', 'utf8')); } catch (e) {}
  const out = { updated: new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 19) + '+09:00', kr: cur.kr || [], us: cur.us || [], meta: cur.meta || {} };
  const dates = {};
  if (MODE === 'kr' || MODE === 'all') {
    let u = JSON.parse(fs.readFileSync('stocks.json', 'utf8')).kr.filter(x => (x[2] === 'P' || x[2] === 'D') && x[4] >= 5);
    if (LIMIT) u = u.slice(0, LIMIT);
    console.log('KR 대상', u.length);
    const r = await pool(u, x => one(false, x[0]));
    out.kr = []; let ok = 0;
    u.forEach((x, i) => { const v = r[i]; if (!v) return; ok++; dates[v.last] = (dates[v.last] || 0) + 1;
      out.kr.push([x[0], x[1], x[3]].concat(flat(v.meta[0]), flat(v.meta[1]), flat(v.meta[2]))); });
    out.meta.kr = { universe: u.length, ok, at: out.updated, asof: Object.keys(dates).sort().pop() || '' };
    console.log('KR 완료', ok, '/', u.length);
  }
  if (MODE === 'us' || MODE === 'all') {
    let u = JSON.parse(fs.readFileSync('stocks_us.json', 'utf8')).us.filter(x => (x[4] === 'N' || x[4] === 'Y') && x[6] >= 5000);
    u.sort((a, b) => b[6] - a[6]); u = u.slice(0, LIMIT || 500);
    console.log('US 대상', u.length);
    const r = await pool(u, x => one(true, x[0]));
    out.us = []; let ok = 0; const d2 = {};
    u.forEach((x, i) => { const v = r[i]; if (!v) return; ok++; d2[v.last] = (d2[v.last] || 0) + 1;
      out.us.push([x[0], x[2], x[1], x[5]].concat(flat(v.meta[0]), flat(v.meta[1]), flat(v.meta[2]))); });
    out.meta.us = { universe: u.length, ok, at: out.updated, asof: Object.keys(d2).sort().pop() || '' };
    console.log('US 완료', ok, '/', u.length);
  }
  fs.writeFileSync('stats.json', JSON.stringify(out));
  console.log('저장', Math.round((Date.now() - t0) / 1000) + '초', 'kr', out.kr.length, 'us', out.us.length);
})();
