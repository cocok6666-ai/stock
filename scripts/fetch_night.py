#!/usr/bin/env python3
"""코스피200 야간선물 마감 등락률을 뉴스 제목에서 찾아 night.json 에 저장.
세션은 화~토 06:00(KST)에 끝난다. 월요일/일요일 아침이면 직전 토요일 마감이 대상이다."""
import json, re, sys, os, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
KST = timezone(timedelta(hours=9))
now = datetime.now(KST)

def expected_closed(n):
    d = n.date()
    if n.strftime("%H:%M") < "06:00":
        d -= timedelta(days=1)
    while d.weekday() not in (1, 2, 3, 4, 5):  # 화~토
        d -= timedelta(days=1)
    return d

closed = expected_closed(now)
NF = "night.json"
cur = {}
try:
    cur = json.load(open(NF, encoding="utf-8"))
except Exception:
    pass
if cur.get("closed") == closed.isoformat() and (cur.get("pct") or cur.get("close")):
    print("이미 기록됨", cur); sys.exit(0)



# ---- 1순위: 시세 전문 페이지(서버 렌더링 HTML) — PreKOSPI / 차트로그 (모두 KIS·KRX 야간선물 1분봉 기반) ----
import html as _html
HDR = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36",
       "Accept-Language": "ko-KR,ko;q=0.9"}

def page_text(u):
    b = urllib.request.urlopen(urllib.request.Request(u, headers=HDR), timeout=25).read().decode("utf-8", "ignore")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", b, flags=re.S)
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", t)))

def fnum(x):
    return float(x.replace(",", "").replace("\u2212", "-").replace("+", ""))

def from_prekospi():
    try:
        t = page_text("https://www.prekospi.com/kospi200-night")
        m = re.search(r"마지막 야간 기록\s*([\d,]+\.\d+)\s*([+\-\u2212]?[\d.,]+)\s*\(([+\-\u2212]?[\d.]+)%\)", t)
        d = re.search(r"(\d{4})-(\d{2})-(\d{2}) 18:00 ~ 익일 06:00", t)
        if not m or not d:
            print("PreKOSPI: 마감 기록 형식 불일치(세션 진행 중이거나 구조 변경)"); return None
        sess = datetime(int(d.group(1)), int(d.group(2)), int(d.group(3))).date() + timedelta(days=1)
        print("PreKOSPI:", m.group(1), m.group(2), m.group(3), "세션종료일", sess)
        if sess != closed:
            print("PreKOSPI 세션일 불일치(기대 %s)" % closed); return None
        close, chg = fnum(m.group(1)), fnum(m.group(2))
        base = re.search(r"야간 기준가\s*([\d,]+\.\d+)", t)
        pct = chg / fnum(base.group(1)) * 100 if base else fnum(m.group(3))
        return {"closed": closed.isoformat(), "close": "%.2f" % close, "pct": "%+.2f" % pct,
                "src": "PreKOSPI(야간선물 1분봉) 자동수집", "at": now.strftime("%H:%M")}
    except Exception as e:
        print("PreKOSPI 실패", e); return None

def from_chartlog():
    try:
        t = page_text("https://chartlog.net/stats/market-index/kospi-night-futures/")
        if "휴장" not in t and "마감" not in t:
            print("차트로그: 장 진행 중"); return None
        m = re.search(r"최종 마감가\s*([\d,]+\.\d+)\s*pt\s*([+\-\u2212]?[\d.,]+)\s*pt\s*\(\s*([+\-\u2212]?[\d.]+)%", t)
        if not m:
            print("차트로그: 형식 불일치"); return None
        print("차트로그:", m.groups())
        return {"closed": closed.isoformat(), "close": "%.2f" % fnum(m.group(1)), "pct": "%+.2f" % fnum(m.group(3)),
                "src": "차트로그(KIS 야간선물) 자동수집", "at": now.strftime("%H:%M")}
    except Exception as e:
        print("차트로그 실패", e); return None

# ---- 3순위: TradingView 스캐너(KOSPI200 선물 연속월물) — 야간 세션 마감 시각이 맞을 때만 사용 ----
def from_tradingview():
    try:
        body = {"symbols": {"tickers": ["KRX:K2I1!"]}, "columns": ["close", "change", "change_abs", "time", "update_mode"]}
        req = urllib.request.Request("https://scanner.tradingview.com/futures/scan", data=json.dumps(body).encode(),
              headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json",
                       "Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/"})
        d = json.loads(urllib.request.urlopen(req, timeout=25).read())["data"][0]["d"]
        close, chg, tm = d[0], d[1], d[3]
        t = datetime.fromtimestamp(tm, KST)
        print("TV:", close, chg, t.strftime("%m/%d %H:%M"), d[4])
        # 마감 세션 종료(해당일 06:00) 직전~이후에 갱신된 값만 인정
        end = datetime(closed.year, closed.month, closed.day, 6, 0, tzinfo=KST)
        if t < end - timedelta(minutes=30):
            print("TV 값이 마감 전 시각이라 사용하지 않음"); return None
        return {"closed": closed.isoformat(), "close": ("%.2f" % close), "pct": ("%+.2f" % chg),
                "src": "TradingView 지연시세 자동수집", "at": now.strftime("%H:%M")}
    except Exception as e:
        print("TV 실패", e); return None

QUERIES = ["코스피200 야간선물 마감 when:4d", "코스피 야간선물 마감 when:4d", "야간선물 코스피200 when:4d"]
DOWN = re.compile(r"하락|급락|폭락|내림|약세|후퇴|털썩|밀려|하회|떨어|추락|마이너스")
UP = re.compile(r"상승|급등|폭등|강세|반등|올라|오름|뛰|돌파|안착|회복|플러스")
items = []
for q in QUERIES:
    try:
        url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q) + "&hl=ko&gl=KR&ceid=KR:ko"
        xml = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=25).read()
        for it in ET.fromstring(xml).iter("item"):
            t = it.findtext("title") or ""
            pd = it.findtext("pubDate") or ""
            try:
                dt = parsedate_to_datetime(pd).astimezone(KST)
            except Exception:
                continue
            items.append((dt, t))
    except Exception as e:
        print("검색 실패", q, e)

best = from_prekospi() or from_chartlog() or from_tradingview()
for dt, t in ([] if best else sorted(set(items), reverse=True)):
    if dt.date() != closed or "야간" not in t or "장중" in t:
        continue
    m = re.search(r"(\d{1,2}(?:\.\d{1,2})?)\s*%", t)
    if not m:
        continue
    up, dn = bool(UP.search(t)), bool(DOWN.search(t))
    if up == dn:
        continue
    pct = float(m.group(1)) * (1 if up else -1)
    lv = re.search(r"(\d{3,4}\.\d{2})", t)
    src = t.rsplit(" - ", 1)[-1] if " - " in t else "뉴스"
    best = {"closed": closed.isoformat(), "close": lv.group(1) if lv else "", "pct": ("%+.2f" % pct),
            "src": "뉴스 제목 자동수집 · " + src, "at": now.strftime("%H:%M")}
    print("채택:", t, best)
    break

if not best:
    print("해당일(%s) 마감 기사 없음 — 후보 %d건" % (closed, len(items)))
    for dt, t in sorted(set(items), reverse=True)[:8]:
        print("  ", dt.strftime("%m/%d %H:%M"), t)
    sys.exit(0)
json.dump(best, open(NF, "w", encoding="utf-8"), ensure_ascii=False)
