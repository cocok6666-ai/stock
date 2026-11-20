#!/usr/bin/env python3
"""시세 수집: 네이버 증권(국내) + 야후 파이낸스(해외/원자재/환율). 표준 라이브러리만 사용."""
import json, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36",
      "Accept": "application/json,text/plain,*/*", "Referer": "https://m.stock.naver.com/"}
errors, items = [], {}


def get(url, tries=2):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:  # noqa
            last = e
            time.sleep(1)
    raise last


def num(s):
    if s is None:
        return None
    s = str(s).replace(",", "").replace("+", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def fmt(x, nd=2):
    return f"{x:,.{nd}f}"


def sgn(x, nd=2):
    return ("+" if x > 0 else "-" if x < 0 else "") + f"{abs(x):,.{nd}f}"


def tlabel(dt, live):
    now = datetime.now(KST)
    if live and (now - dt).total_seconds() < 1800:
        return dt.strftime("%H:%M") + " 현재"
    return dt.strftime("%m/%d %H:%M")


def put(key, price, prev, dt, live, nd=2, vol=None, chg_nd=None):
    if price is None or prev in (None, 0):
        raise ValueError("price/prev missing")
    d = price - prev
    p = d / prev * 100
    it = {"v": fmt(price, nd), "p": sgn(p), "d": sgn(d, chg_nd if chg_nd is not None else nd), "t": tlabel(dt, live)}
    if vol:
        it["x"] = fmt(vol, 0)
    items[key] = it


# ---------- 네이버 ----------
def naver_basic(kind, code, key, nd=2, vol=False):
    j = get(f"https://m.stock.naver.com/api/{kind}/{code}/basic")
    price = num(j.get("closePrice"))
    cmp_ = num(j.get("compareToPreviousClosePrice"))
    ratio = num(j.get("fluctuationsRatio"))
    name = ((j.get("compareToPreviousPrice") or {}).get("name") or "").upper()
    if cmp_ is not None and name in ("FALLING", "LOWER_LIMIT"):
        cmp_ = -abs(cmp_)
    elif cmp_ is not None:
        cmp_ = abs(cmp_) if name in ("RISING", "UPPER_LIMIT") else cmp_
    prev = price - cmp_ if (price is not None and cmp_ is not None) else None
    dt = datetime.fromisoformat(j["localTradedAt"]).astimezone(KST) if j.get("localTradedAt") else datetime.now(KST)
    live = (j.get("marketStatus") or "").upper() == "OPEN"
    v = num(j.get("accumulatedTradingVolume")) if vol else None
    put(key, price, prev, dt, live, nd, v, nd)


def naver_polling_stock(code, key):
    j = get(f"https://polling.finance.naver.com/api/realtime/domestic/stock/{code}")
    d = (j.get("datas") or [None])[0]
    if not d:
        raise ValueError("no data")
    price = num(d.get("closePrice"))
    cmp_ = num(d.get("compareToPreviousClosePrice"))
    name = ((d.get("compareToPreviousPrice") or {}).get("name") or "").upper()
    if cmp_ is not None and name in ("FALLING", "LOWER_LIMIT"):
        cmp_ = -abs(cmp_)
    prev = price - cmp_ if cmp_ is not None else None
    dt = datetime.fromisoformat(d["localTradedAt"]).astimezone(KST)
    live = (d.get("marketStatus") or "").upper() == "OPEN"
    put(key, price, prev, dt, live, 0, num(d.get("accumulatedTradingVolume")), 0)


# ---------- 야후 ----------
def yahoo(sym, key, nd=2, chg_nd=None):
    u = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(sym) + "?interval=1m&range=1d"
    j = get(u)
    r = j["chart"]["result"][0]
    m = r["meta"]
    price = num(m.get("regularMarketPrice"))
    prev = num(m.get("chartPreviousClose")) or num(m.get("previousClose"))
    dt = datetime.fromtimestamp(m["regularMarketTime"], KST)
    put(key, price, prev, dt, True, nd, None, chg_nd)


def attempt(label, *fns):
    for fn in fns:
        try:
            fn()
            return True
        except Exception as e:  # noqa
            errors.append(f"{label}: {type(e).__name__}: {e}"[:200])
    return False


# 국내 지수/종목
attempt("KOSPI", lambda: naver_basic("index", "KOSPI", "KOSPI"), lambda: yahoo("^KS11", "KOSPI"))
attempt("KOSDAQ", lambda: naver_basic("index", "KOSDAQ", "KOSDAQ"), lambda: yahoo("^KQ11", "KOSDAQ"))
for code in ["069500", "395160", "005930", "000660"]:
    attempt(code, lambda c=code: naver_polling_stock(c, c), lambda c=code: naver_basic("stock", c, c, 0, True),
            lambda c=code: yahoo(c + ".KS", c, 0))
# 코스피200 선물 (네이버 지수 코드 FUT 시도)
attempt("K200F", lambda: naver_basic("index", "FUT", "K200F"))
# 해외/원자재/환율/금리
for sym, key, nd in [("^DJI", "DJI", 2), ("^IXIC", "IXIC", 2), ("CL=F", "WTI", 2), ("BZ=F", "BRENT", 2),
                     ("KRW=X", "USDKRW", 2), ("^TNX", "US10Y", 3), ("NQ=F", "NQF", 2),
                     ("NVDA", "NVDA", 2), ("SKHY", "SKHY", 2), ("MU", "MU", 2), ("SNDK", "SNDK", 2),
                     ("AVGO", "AVGO", 2), ("AMD", "AMD", 2), ("SOXL", "SOXL", 2)]:
    attempt(key, lambda s=sym, k=key, n=nd: yahoo(s, k, n))

out = {"updated": datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S+09:00"), "items": items, "errors": errors}
with open(sys.argv[1] if len(sys.argv) > 1 else "quotes.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"ok={len(items)} errors={len(errors)}")
for e in errors:
    print(" -", e)
