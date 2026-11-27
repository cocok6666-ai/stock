// 깨비주식 Worker: ① 네이버 조회 프록시 ② 승인 코드 확인 ③ 데이터 중계 ④ 관리자 API
// 바인딩: KV 네임스페이스 변수명 GATE (필수) / 비밀 변수 ADMIN_INIT (관리자 처음 암호, 11자 이상)
// 주소 없이 열면 "naver-proxy ok" 가 보여야 정상입니다.

const ALLOW_ORIGINS = ['https://cocok6666-ai.github.io'];
const ALLOW_HOSTS = ['m.stock.naver.com', 'api.stock.naver.com', 'polling.finance.naver.com', 'ac.stock.naver.com'];
const MAX_BYTES = 2 * 1024 * 1024;
const RAW = 'https://raw.githubusercontent.com/cocok6666-ai/stock/';
const MAIN_FILES = ['stocks.json', 'stocks_us.json', 'stats.json', 'brief.json', 'brief_status.json', 'night.json', 'ppi.json', 'close.json', 'live.json'];
const DATA_FILES = /^(quotes|rt|q\d{1,3})\.json$/;
const MAX_DEV = 2;
const ALPHA = '23456789ABCDEFGHJKMNPQRSTUVWXYZ';
const enc = new TextEncoder();

function cors(origin) {
  const ok = ALLOW_ORIGINS.includes(origin);
  return ok
    ? { 'Access-Control-Allow-Origin': origin, 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': '*', 'Access-Control-Max-Age': '86400', Vary: 'Origin' }
    : { Vary: 'Origin' };
}
function J(obj, status, c) {
  return new Response(JSON.stringify(obj), { status: status || 200, headers: { ...c, 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' } });
}
const hex = (b) => [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, '0')).join('');
async function hmac(key, msg) {
  const k = await crypto.subtle.importKey('raw', enc.encode(key), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return hex(await crypto.subtle.sign('HMAC', k, enc.encode(msg)));
}
function same(a, b) {
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}
function kstDay() {
  return new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
}
function normCode(s) {
  s = String(s || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
  return s.length === 8 && [...s].every((ch) => ALPHA.includes(ch)) ? s : '';
}
function newCode() {
  const r = crypto.getRandomValues(new Uint8Array(8));
  let s = '';
  for (let i = 0; i < 8; i++) s += ALPHA[r[i] % ALPHA.length];
  return s;
}
const fmt = (s) => s.slice(0, 4) + '-' + s.slice(4);
function pwOk(p) {
  return typeof p === 'string' && p.length >= 11 && p.length <= 100 && /[A-Za-z]/.test(p) && /\d/.test(p) && /[^A-Za-z0-9]/.test(p);
}

// 실패 횟수 제한 (Cache API · KV 쓰기 한도를 쓰지 않음)
async function fails(ip, b) {
  const r = await caches.default.match(new Request('https://rl.local/' + b + '/' + ip));
  return r ? parseInt(await r.text(), 10) || 0 : 0;
}
async function addFail(ip, b) {
  const n = (await fails(ip, b)) + 1;
  await caches.default.put(new Request('https://rl.local/' + b + '/' + ip), new Response(String(n), { headers: { 'Cache-Control': 'max-age=600' } }));
}

// 코드 기록 저장 (목록 화면용 요약은 KV 메타데이터에 같이 저장: 무료 요금제는 요청당 KV 호출 50회 제한)
function putRec(env, key, rec) {
  const meta = { n: rec.n, label: rec.label || '', off: !!rec.off, used: rec.used || '', created: rec.created || '', devs: rec.devs.map((d) => ({ s: d.id.slice(0, 6), name: d.name, at: d.at })) };
  return env.GATE.put(key, JSON.stringify(rec), { metadata: meta });
}

async function pepper(env, create) {
  let p = await env.GATE.get('cfg:pepper', { cacheTtl: 3600 });
  if (!p && create) {
    p = hex(crypto.getRandomValues(new Uint8Array(24)));
    await env.GATE.put('cfg:pepper', p);
  }
  return p;
}
async function enforced(env) {
  return (await env.GATE.get('cfg:enforce', { cacheTtl: 60 })) === '1';
}
async function codeKey(env, code, create) {
  const p = await pepper(env, create);
  return p ? 'c:' + (await hmac(p, 'code|' + code)) : null;
}

// 코드+기기 확인 (요청 헤더 X-Code, X-Dev)
async function authOK(request, env, ctx) {
  const code = normCode(request.headers.get('X-Code'));
  const dev = String(request.headers.get('X-Dev') || '');
  if (!code || !/^[0-9a-f]{16,64}$/.test(dev)) return false;
  const key = await codeKey(env, code, false);
  if (!key) return false;
  const rec = await env.GATE.get(key, { type: 'json', cacheTtl: 30 });
  if (!rec || rec.off || !rec.devs.some((d) => d.id === dev)) return false;
  const today = kstDay();
  if (rec.used !== today) {
    // 캐시된 옛 기록을 덮어쓰면 관리자가 방금 바꾼 이름·차단이 사라지므로, 최신 기록을 다시 읽어 날짜만 바꾼다
    ctx.waitUntil(
      (async () => {
        const fresh = await env.GATE.get(key, { type: 'json' });
        if (fresh && fresh.used !== today) {
          fresh.used = today;
          await putRec(env, key, fresh);
        }
      })()
    );
  }
  return true;
}

async function adminOK(request, env) {
  const pw = String(request.headers.get('X-Admin') || '');
  if (!pw) return false;
  const p = await pepper(env, false);
  const stored = await env.GATE.get('cfg:pw');
  if (stored && p) return same(stored, await hmac(p, 'admin|' + pw));
  const init = String(env.ADMIN_INIT || '');
  return init.length >= 11 && same(init, pw);
}

async function body(request) {
  try {
    return await request.json();
  } catch (e) {
    return {};
  }
}

async function listCodes(env) {
  const out = [];
  let cursor;
  do {
    const r = await env.GATE.list({ prefix: 'c:', cursor });
    for (const k of r.keys) out.push({ h: k.name.slice(2), ...(k.metadata || { n: 0, devs: [] }) });
    cursor = r.list_complete ? null : r.cursor;
  } while (cursor);
  return out.sort((x, y) => (x.n || 0) - (y.n || 0));
}

async function admin(request, env, c, path, ip) {
  if ((await fails(ip, 'adm')) >= 8) return J({ e: 'locked' }, 429, c);
  if (!(await adminOK(request, env))) {
    await addFail(ip, 'adm');
    return J({ e: 'auth' }, 401, c);
  }
  const b = await body(request);
  const act = path.slice(3);
  await pepper(env, true);
  if (act === 'list') {
    const items = await listCodes(env);
    return J({ enforce: await enforced(env), max: MAX_DEV, items }, 200, c);
  }
  async function add(codes) {
    const have = new Set((await listCodes(env)).map((x) => x.h));
    const p = await pepper(env, true);
    let n = parseInt((await env.GATE.get('cfg:n')) || '0', 10);
    let added = 0;
    for (const code of codes) {
      const h = await hmac(p, 'code|' + code);
      if (have.has(h)) continue;
      n++;
      await putRec(env, 'c:' + h, { n, label: '', off: false, created: kstDay(), used: '', devs: [] });
      added++;
    }
    await env.GATE.put('cfg:n', String(n));
    return added;
  }
  if (act === 'gen') {
    const cnt = Math.max(1, Math.min(30, parseInt(b.count, 10) || 1));
    const codes = [];
    while (codes.length < cnt) {
      const x = newCode();
      if (!codes.includes(x)) codes.push(x);
    }
    const added = await add(codes);
    return J({ added, codes: codes.map(fmt) }, 200, c);
  }
  if (act === 'import') {
    const codes = [...new Set((Array.isArray(b.codes) ? b.codes : []).map(normCode).filter(Boolean))].slice(0, 30);
    return J({ added: await add(codes), total: codes.length }, 200, c);
  }
  if (act === 'set' || act === 'deldev') {
    const h = String(b.h || '');
    if (!/^[0-9a-f]{64}$/.test(h)) return J({ e: 'bad' }, 400, c);
    const rec = await env.GATE.get('c:' + h, { type: 'json' });
    if (!rec) return J({ e: 'none' }, 404, c);
    if (act === 'set') {
      if (typeof b.label === 'string') rec.label = b.label.slice(0, 30);
      if (typeof b.off === 'boolean') rec.off = b.off;
    } else if (b.all) rec.devs = [];
    else rec.devs = rec.devs.filter((d) => d.id.slice(0, 6) !== String(b.s || ''));
    await putRec(env, 'c:' + h, rec);
    return J({ ok: 1 }, 200, c);
  }
  if (act === 'enforce') {
    await env.GATE.put('cfg:enforce', b.on ? '1' : '0');
    return J({ ok: 1, enforce: !!b.on }, 200, c);
  }
  if (act === 'pw') {
    const np = String(b.new || '');
    if (!pwOk(np)) return J({ e: 'policy' }, 400, c);
    if (np === String(request.headers.get('X-Admin') || '')) return J({ e: 'same' }, 400, c);
    await env.GATE.put('cfg:pw', await hmac(await pepper(env, true), 'admin|' + np));
    return J({ ok: 1 }, 200, c);
  }
  if (act === 'find') {
    const code = normCode(b.code);
    if (!code) return J({ e: 'bad' }, 400, c);
    const key = await codeKey(env, code, false);
    const rec = key ? await env.GATE.get(key, { type: 'json' }) : null;
    return rec ? J({ ok: 1, h: key.slice(2), n: rec.n }, 200, c) : J({ e: 'none' }, 404, c);
  }
  if (act === 'ping') return J({ ok: 1 }, 200, c);
  return J({ e: 'unknown' }, 404, c);
}

async function gate(request, env, ctx, c, path, ip) {
  if (path === '/g/status') return J({ enforce: await enforced(env) }, 200, c);
  if (request.method !== 'POST') return J({ e: 'method' }, 405, c);
  if ((await fails(ip, 'lg')) >= 10) return J({ e: 'locked' }, 429, c);
  const b = await body(request);
  const code = normCode(b.code);
  const dev = String(b.dev || '');
  if (!code || !/^[0-9a-f]{16,64}$/.test(dev)) {
    await addFail(ip, 'lg');
    return J({ e: 'invalid' }, 401, c);
  }
  const key = await codeKey(env, code, false);
  const rec = key ? await env.GATE.get(key, { type: 'json' }) : null;
  if (!rec || rec.off) {
    await addFail(ip, 'lg');
    return J({ e: rec ? 'off' : 'invalid' }, 401, c);
  }
  if (path === '/g/rm') {
    rec.devs = rec.devs.filter((d) => d.id.slice(0, 6) !== String(b.s || ''));
    await putRec(env, key, rec);
    return J({ ok: 1 }, 200, c);
  }
  if (path === '/g/login' || path === '/g/check') {
    const has = rec.devs.some((d) => d.id === dev);
    if (!has) {
      if (path === '/g/check') return J({ e: 'nodev' }, 401, c);
      if (rec.devs.length >= MAX_DEV) return J({ e: 'full', devs: rec.devs.map((d) => ({ s: d.id.slice(0, 6), name: d.name, at: d.at })) }, 409, c);
      rec.devs.push({ id: dev, name: String(b.name || '').slice(0, 30), at: kstDay() });
      rec.used = kstDay();
      await putRec(env, key, rec);
    }
    return J({ ok: 1 }, 200, c);
  }
  return J({ e: 'unknown' }, 404, c);
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const origin = request.headers.get('Origin') || '';
    const c = cors(origin);
    const okOrigin = ALLOW_ORIGINS.includes(origin);
    const ip = request.headers.get('CF-Connecting-IP') || 'x';
    if (request.method === 'OPTIONS') return new Response(null, { status: okOrigin ? 204 : 403, headers: c });
    const path = url.pathname;

    if (path.startsWith('/a/') || path.startsWith('/g/')) {
      if (!okOrigin) return new Response('forbidden origin', { status: 403, headers: c });
      if (!env.GATE) return J({ e: 'nokv' }, 500, c);
      return path.startsWith('/a/') ? admin(request, env, c, path, ip) : gate(request, env, ctx, c, path, ip);
    }

    if (request.method !== 'GET') return new Response('method not allowed', { status: 405, headers: c });

    if (path.startsWith('/d/')) {
      if (!okOrigin) return new Response('forbidden origin', { status: 403, headers: c });
      if (env.GATE && (await enforced(env)) && !(await authOK(request, env, ctx))) return J({ e: 'auth' }, 401, c);
      const m = path.match(/^\/d\/(data|main)\/([A-Za-z0-9_]+\.json)$/);
      if (!m || (m[1] === 'data' ? !DATA_FILES.test(m[2]) : !MAIN_FILES.includes(m[2]))) return J({ e: 'file' }, 404, c);
      const r = await fetch(RAW + m[1] + '/' + m[2], { cf: { cacheTtl: 20, cacheEverything: true } });
      if (!r.ok) return J({ e: 'upstream' }, r.status === 404 ? 404 : 502, c);
      return new Response(await r.arrayBuffer(), { status: 200, headers: { ...c, 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' } });
    }

    const u = url.searchParams.get('u');
    if (!u) return new Response('naver-proxy ok', { status: 200, headers: { ...c, 'Content-Type': 'text/plain; charset=utf-8' } });
    if (!okOrigin) return new Response('forbidden origin', { status: 403, headers: c });
    if (env.GATE && (await enforced(env)) && !(await authOK(request, env, ctx))) return J({ e: 'auth' }, 401, c);

    let target;
    try {
      target = new URL(u);
    } catch (e) {
      return new Response('bad url', { status: 400, headers: c });
    }
    if (target.protocol !== 'https:' || target.username || target.password || !ALLOW_HOSTS.includes(target.hostname)) {
      return new Response('host not allowed', { status: 400, headers: c });
    }
    try {
      const r = await fetch(target.toString(), {
        redirect: 'manual',
        headers: {
          'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36',
          Accept: 'application/json, text/plain, */*',
          'Accept-Language': 'ko-KR,ko;q=0.9',
          Referer: 'https://m.stock.naver.com/',
        },
        cf: { cacheTtl: 30, cacheEverything: true },
      });
      if (r.status >= 300 && r.status < 400) return new Response('redirect blocked', { status: 502, headers: c });
      const buf = await r.arrayBuffer();
      if (buf.byteLength > MAX_BYTES) return new Response('response too large', { status: 502, headers: c });
      return new Response(buf, { status: r.status, headers: { ...c, 'Content-Type': r.headers.get('Content-Type') || 'application/json; charset=utf-8', 'Cache-Control': 'public, max-age=30' } });
    } catch (e) {
      return new Response('upstream error', { status: 502, headers: c });
    }
  },
};
