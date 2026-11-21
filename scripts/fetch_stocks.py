#!/usr/bin/env python3
"""전체 종목 목록(국내 코스피/코스닥/ETF, 미국 나스닥/뉴욕/아멕스)을 네이버에서 받아 stocks.json 으로 저장."""
import json, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
KST = timezone(timedelta(hours=9))
H = {"User-Agent": "Mozilla/5.0"}

def get(url, tries=3):
    for i in range(tries):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=25).read())
        except Exception as e:
            err = e
            time.sleep(1.5)
    raise err

def paged(base, size=100, maxpages=120):
    out = []
    for p in range(1, maxpages + 1):
        j = get(f"{base}?page={p}&pageSize={size}")
        st = j.get("stocks") or []
        out += st
        total = j.get("totalCount")
        if not st or len(st) < size or (total and len(out) >= total):
            break
    return out

def fn(x):
    try:
        return float(str(x).replace(",", "").replace("+", "").replace("%", "").replace("\u2212", "-"))
    except Exception:
        return None

def extra(s):
    """등락률(%)·거래대금(원/달러 환산)·거래량 — 정렬 메뉴용. 없으면 None."""
    chg = fn(s.get("fluctuationsRatio"))
    vol = fn(s.get("accumulatedTradingVolume"))
    px = fn(s.get("closePrice"))
    tv = fn(s.get("accumulatedTradingValue"))
    if tv is not None and "백만" in str(s.get("accumulatedTradingValue")):
        tv *= 1e6
    if tv is None and vol is not None and px is not None:
        tv = vol * px
    return [None if chg is None else round(chg, 2), None if tv is None else round(tv / 1e3)]  # 거래대금(정렬용 상대값)

PX = {}
kr, seen = [], set()
for mk, url in [("P", "https://m.stock.naver.com/api/stocks/marketValue/KOSPI"),
                ("D", "https://m.stock.naver.com/api/stocks/marketValue/KOSDAQ"),
                ("E", "https://m.stock.naver.com/api/stocks/etf")]:
    try:
        for s in paged(url):
            c, n = s.get("itemCode"), s.get("stockName")
            if c and n and c not in seen:
                PX[c] = fn(s.get("closePrice")); seen.add(c); kr.append([c, n, "E" if str(s.get("stockEndType", "")).lower() in ("etf", "etn") else mk] + extra(s))
    except Exception as e:
        print("KR 실패", mk, e)

us, seen = [], set()
for mk, ex in [("N", "NASDAQ"), ("Y", "NYSE"), ("A", "AMEX")]:
    try:
        for s in paged(f"https://api.stock.naver.com/stock/exchange/{ex}/marketValue"):
            rc, sy, n, e = s.get("reutersCode"), s.get("symbolCode"), s.get("stockName"), s.get("stockNameEng") or ""
            if rc and sy and n and rc not in seen:
                PX[rc] = fn(s.get("closePrice")); seen.add(rc); us.append([rc, sy, n, e, mk] + extra(s))
    except Exception as e:
        print("US 실패", ex, e)

# ---- 52주 고가 대비 위치(%) — 신고가 정렬용. 코스피·코스닥 전체, 미국은 거래소별 시총 상위만 조회 ----
def gap52(url, code):
    try:
        infos = get(url, tries=2)
        infos = infos.get("totalInfos") or infos.get("stockItemTotalInfos") or []
        hi = next((fn(i.get("value")) for i in infos if i.get("code") == "highPriceOf52Weeks"), None)
        px = PX.get(code)
        return round((px / hi - 1) * 100, 1) if hi and px and hi > 0 else None
    except Exception:
        return None

def add_gap(rows, ci, urlf, pick):
    ids = [i for i, r in enumerate(rows) if pick(r)]
    with ThreadPoolExecutor(max_workers=12) as ex:
        res = list(ex.map(lambda i: gap52(urlf(rows[i]), rows[i][ci]), ids))
    g = dict(zip(ids, res))
    for i, r in enumerate(rows):
        r.append(g.get(i))
    print("52주", len(ids), "조회 중", sum(1 for v in g.values() if v is not None), "건 성공")

t0 = time.time()
if len(kr) >= 500:
    add_gap(kr, 0, lambda r: "https://m.stock.naver.com/api/stock/%s/integration" % r[0], lambda r: r[2] in ("P", "D"))
if len(us) >= 500:
    cnt = {}
    def us_pick(r):
        cnt[r[4]] = cnt.get(r[4], 0) + 1
        return r[4] in ("N", "Y") and cnt[r[4]] <= 1000
    add_gap(us, 0, lambda r: "https://api.stock.naver.com/stock/%s/basic" % r[0], us_pick)
print("소요", round(time.time() - t0), "초")

if len(kr) < 500:
    print("목록이 너무 적어 저장하지 않음", len(kr)); sys.exit(1)
out = {"updated": datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S+09:00"), "kr": kr}
with open(sys.argv[1] if len(sys.argv) > 1 else "stocks.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print("kr", len(kr))
if len(us) >= 500:
    with open("stocks_us.json", "w", encoding="utf-8") as f:
        json.dump({"updated": out["updated"], "us": us}, f, ensure_ascii=False, separators=(",", ":"))
    print("us", len(us))
else:
    print("미국 목록이 너무 적어 저장하지 않음", len(us))
