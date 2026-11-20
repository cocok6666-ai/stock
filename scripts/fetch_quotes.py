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
    age = (datetime.now(KST) - dt).total_seconds()
    if live is None:
        live = age < 1800
    if live and age < 3600:
        return dt.strftime("%H:%M") + " 현재"
    return dt.strftime("%m/%d %H:%M") + " 종가"


def put(key, price, prev, dt, live, nd=2, vol=None, chg_nd=None):
    if price is None or prev in (None, 0):
        raise ValueError("price/prev missing")
    d = price - prev
    p = d / prev * 100
    it = {"v": fmt(price, nd), "p": sgn(p), "d": sgn(d, chg_nd if chg_nd is not None else nd), "t": tlabel(dt, live)}
    if vol:
        it["x"] = fmt(vol, 0)
    items[key] = it


# ---------- 네이버 (국내/해외/환율/원자재/채권 모두 동일 계열 API) ----------
def naver(url, key, nd=2, vol=False):
    j = get(url)
    d = j.get("exchangeInfo") or j
    price = num(d.get("closePrice"))
    ftype = ((d.get("compareToPreviousPrice") or d.get("fluctuationsType") or {}).get("name") or "").upper()
    chg = num(d.get("compareToPreviousClosePrice"))
    if chg is None:
        chg = num(d.get("fluctuations"))
    ratio = num(d.get("fluctuationsRatio"))
    if price is None or chg is None:
        raise ValueError("price/change missing")
    down = ftype in ("FALLING", "LOWER_LIMIT")
    up = ftype in ("RISING", "UPPER_LIMIT")
    chg = -abs(chg) if down else abs(chg) if up else chg
    if ratio is None:
        ratio = chg / (price - chg) * 100 if price != chg else 0.0
    else:
        ratio = -abs(ratio) if down else abs(ratio) if up else ratio
    dt = datetime.fromisoformat(d["localTradedAt"]).astimezone(KST) if d.get("localTradedAt") else datetime.now(KST)
    st = (d.get("marketStatus") or "").upper()
    live = True if st == "OPEN" else False if st == "CLOSE" else None
    it = {"v": fmt(price, nd), "p": sgn(ratio), "d": sgn(chg, nd), "t": tlabel(dt, live)}
    if vol:
        v = num(d.get("accumulatedTradingVolume"))
        if v:
            it["x"] = fmt(v, 0)
    items[key] = it


def polling_stock(code):
    j = get(f"https://polling.finance.naver.com/api/realtime/domestic/stock/{code}")
    d = (j.get("datas") or [None])[0]
    if not d:
        raise ValueError("no data")
    price = num(d.get("closePrice"))
    chg = num(d.get("compareToPreviousClosePrice"))
    ftype = ((d.get("compareToPreviousPrice") or {}).get("name") or "").upper()
    down = ftype in ("FALLING", "LOWER_LIMIT")
    chg = -abs(chg) if down else abs(chg)
    ratio = num(d.get("fluctuationsRatio"))
    ratio = -abs(ratio) if down else abs(ratio)
    dt = datetime.fromisoformat(d["localTradedAt"]).astimezone(KST)
    st = (d.get("marketStatus") or "").upper()
    it = {"v": fmt(price, 0), "p": sgn(ratio), "d": sgn(chg, 0), "t": tlabel(dt, True if st == "OPEN" else False if st == "CLOSE" else None)}
    v = num(d.get("accumulatedTradingVolume"))
    if v:
        it["x"] = fmt(v, 0)
    items[code] = it


def attempt(label, *fns):
    for fn in fns:
        try:
            fn()
            return True
        except Exception as e:  # noqa
            errors.append(f"{label}: {type(e).__name__}: {e}"[:200])
    return False


M = "https://m.stock.naver.com/api"
A = "https://api.stock.naver.com"
attempt("KOSPI", lambda: naver(f"{M}/index/KOSPI/basic", "KOSPI"))
attempt("KOSDAQ", lambda: naver(f"{M}/index/KOSDAQ/basic", "KOSDAQ"))
attempt("K200F", lambda: naver(f"{M}/index/FUT/basic", "K200F"))
for code in ["069500", "395160", "005930", "000660"]:
    attempt(code, lambda c=code: polling_stock(c), lambda c=code: naver(f"{M}/stock/{c}/basic", c, 0, True))
attempt("DJI", lambda: naver(f"{A}/index/.DJI/basic", "DJI"))
attempt("IXIC", lambda: naver(f"{A}/index/.IXIC/basic", "IXIC"))
attempt("USDKRW", lambda: naver(f"{A}/marketindex/exchange/FX_USDKRW", "USDKRW"))
attempt("WTI", lambda: naver(f"{A}/marketindex/energy/CLcv1", "WTI"))
attempt("BRENT", lambda: naver(f"{A}/marketindex/energy/LCOcv1", "BRENT"))
attempt("US10Y", lambda: naver(f"{A}/marketindex/bond/US10YT=RR", "US10Y", 3))
for key, codes in [("NVDA", ["NVDA.O"]), ("SKHY", ["SKHY.O", "SKHY.K", "SKHY"]), ("MU", ["MU.O"]),
                   ("SNDK", ["SNDK.O"]), ("AVGO", ["AVGO.O"]), ("AMD", ["AMD.O"]), ("SOXL", ["SOXL.K"])]:
    attempt(key, *[(lambda c=c, k=key: naver(f"{A}/stock/{c}/basic", k)) for c in codes])

out = {"updated": datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S+09:00"), "items": items, "errors": errors}
with open(sys.argv[1] if len(sys.argv) > 1 else "quotes.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"ok={len(items)} errors={len(errors)}")
for e in errors:
    print(" -", e)
