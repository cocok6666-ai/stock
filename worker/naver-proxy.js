// 깨비주식 종목분석용 네이버 조회 프록시 (Cloudflare Worker)
// - 앱(https://cocok6666-ai.github.io)에서만 호출 가능, 네이버 주식 관련 호스트만 중계합니다.
// - 사용: GET https://<내-worker>.workers.dev/?u=<인코딩된 네이버 API 주소>
// - 주소 없이 열면 "naver-proxy ok" 가 보여야 정상 배포입니다.

const ALLOW_ORIGINS = ['https://cocok6666-ai.github.io'];
const ALLOW_HOSTS = [
  'm.stock.naver.com',
  'api.stock.naver.com',
  'polling.finance.naver.com',
  'ac.stock.naver.com',
];
const MAX_BYTES = 2 * 1024 * 1024;

function corsHeaders(origin) {
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': '*',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin',
  };
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const origin = request.headers.get('Origin') || '';
    const okOrigin = ALLOW_ORIGINS.includes(origin);
    const cors = okOrigin ? corsHeaders(origin) : { Vary: 'Origin' };

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: okOrigin ? 204 : 403, headers: cors });
    }
    if (request.method !== 'GET') {
      return new Response('method not allowed', { status: 405, headers: cors });
    }

    const u = url.searchParams.get('u');
    if (!u) {
      return new Response('naver-proxy ok', {
        status: 200,
        headers: { ...cors, 'Content-Type': 'text/plain; charset=utf-8' },
      });
    }
    if (!okOrigin) {
      return new Response('forbidden origin', { status: 403, headers: cors });
    }

    let target;
    try {
      target = new URL(u);
    } catch (e) {
      return new Response('bad url', { status: 400, headers: cors });
    }
    if (
      target.protocol !== 'https:' ||
      target.username ||
      target.password ||
      !ALLOW_HOSTS.includes(target.hostname)
    ) {
      return new Response('host not allowed', { status: 400, headers: cors });
    }

    try {
      const r = await fetch(target.toString(), {
        redirect: 'manual',
        headers: {
          'User-Agent':
            'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36',
          Accept: 'application/json, text/plain, */*',
          'Accept-Language': 'ko-KR,ko;q=0.9',
          Referer: 'https://m.stock.naver.com/',
        },
        cf: { cacheTtl: 30, cacheEverything: true },
      });
      if (r.status >= 300 && r.status < 400) {
        return new Response('redirect blocked', { status: 502, headers: cors });
      }
      const buf = await r.arrayBuffer();
      if (buf.byteLength > MAX_BYTES) {
        return new Response('response too large', { status: 502, headers: cors });
      }
      return new Response(buf, {
        status: r.status,
        headers: {
          ...cors,
          'Content-Type': r.headers.get('Content-Type') || 'application/json; charset=utf-8',
          'Cache-Control': 'public, max-age=30',
        },
      });
    } catch (e) {
      return new Response('upstream error', { status: 502, headers: cors });
    }
  },
};
