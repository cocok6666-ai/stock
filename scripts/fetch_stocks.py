#!/usr/bin/env python3
"""전체 종목 목록(국내 코스피/코스닥/ETF)을 네이버에서 받아 stocks.json 으로 저장."""
import json, sys, time, urllib.request
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

kr, seen = [], set()
for mk, url in [("P", "https://m.stock.naver.com/api/stocks/marketValue/KOSPI"),
                ("D", "https://m.stock.naver.com/api/stocks/marketValue/KOSDAQ"),
                ("E", "https://m.stock.naver.com/api/stocks/etf")]:
    try:
        for s in paged(url):
            c, n = s.get("itemCode"), s.get("stockName")
            if c and n and c not in seen:
                seen.add(c); kr.append([c, n, "E" if str(s.get("stockEndType", "")).lower() in ("etf", "etn") else mk])
    except Exception as e:
        print("KR 실패", mk, e)

if len(kr) < 500:
    print("목록이 너무 적어 저장하지 않음", len(kr)); sys.exit(1)
out = {"updated": datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S+09:00"), "kr": kr}
with open(sys.argv[1] if len(sys.argv) > 1 else "stocks.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print("kr", len(kr))
