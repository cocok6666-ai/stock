#!/usr/bin/env python3
"""국내 전 종목 현재 등락률(%) 일괄 수집 → rt.json {t, kr:{코드:등락률}}. 종목 선택 목록의 실시간 표시용."""
import json, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
KST = timezone(timedelta(hours=9))
H = {"User-Agent": "Mozilla/5.0"}
BASES = ["https://m.stock.naver.com/api/stocks/marketValue/KOSPI",
         "https://m.stock.naver.com/api/stocks/marketValue/KOSDAQ",
         "https://m.stock.naver.com/api/stocks/etf"]

def get(url):
    for _ in range(2):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=12).read())
        except Exception:
            time.sleep(0.5)
    return None

def fn(x):
    try:
        return float(str(x).replace(",", "").replace("+", "").replace("%", "").replace("−", "-"))
    except Exception:
        return None

def page(a):
    base, p = a
    j = get(f"{base}?page={p}&pageSize=100")
    return (j or {}).get("stocks") or [], (j or {}).get("totalCount")

def collect(bases, key):
    res = {}
    for base in bases:
        first, total = page((base, 1))
        n = max(1, -(-(total or len(first)) // 100))
        with ThreadPoolExecutor(max_workers=8) as ex:
            rest = list(ex.map(page, [(base, p) for p in range(2, n + 1)]))
        for st in [first] + [r[0] for r in rest]:
            for s in st:
                c, g = s.get(key), fn(s.get("fluctuationsRatio"))
                if c and g is not None:
                    res[c] = round(g, 2)
    return res

out = collect(BASES, "itemCode")
us = collect(["https://api.stock.naver.com/stock/exchange/%s/marketValue" % e for e in ("NASDAQ", "NYSE", "AMEX")], "reutersCode")
if len(out) < 500:
    print("수집 부족", len(out)); sys.exit(1)
with open(sys.argv[1] if len(sys.argv) > 1 else "rt.json", "w", encoding="utf-8") as f:
    json.dump({"t": datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S+09:00"), "kr": out, "us": us if len(us) >= 500 else {}}, f, ensure_ascii=False, separators=(",", ":"))
print("rt", len(out), len(us))
