#!/usr/bin/env python3
"""시세 수집: 네이버 증권(국내) + 야후 파이낸스(해외/원자재/환율). 표준 라이브러리만 사용."""
import json, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36",
      "Accept": "application/json,text/plain,*/*", "Referer": "https://m.stock.naver.com/"}
errors, items = [], {}


KR_EXT = {"069500", "395160", "005930", "000660"}
EXT_KEYS = KR_EXT | {"NVDA", "SKHY", "MU", "SNDK", "AVGO", "AMD", "SOXL"}


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
    if key in EXT_KEYS:
        e = ext_info(j, key in KR_EXT)
        if e:
            it["e"] = e
    items[key] = it



def ext_info(d, kr):
    """정규장 밖 세션(국내 NXT 프리/애프터, 미국 프리/애프터) 시세. 없으면 None."""
    o = d.get("overMarketPriceInfo") or {}
    sess = (o.get("tradingSessionType") or "").upper()
    price = num(o.get("overPrice"))
    if sess not in ("PRE_MARKET", "AFTER_MARKET") or price is None or not o.get("localTradedAt"):
        return None
    try:
        dt = datetime.fromisoformat(o["localTradedAt"]).astimezone(KST)
    except Exception:
        return None
    age = (datetime.now(KST) - dt).total_seconds()
    if age > 10 * 3600:
        return None
    ftype = ((o.get("compareToPreviousPrice") or {}).get("name") or "").upper()
    down, up = ftype in ("FALLING", "LOWER_LIMIT"), ftype in ("RISING", "UPPER_LIMIT")
    chg = num(o.get("compareToPreviousClosePrice"))
    ratio = num(o.get("fluctuationsRatio"))
    if chg is None or ratio is None:
        return None
    chg = -abs(chg) if down else abs(chg) if up else chg
    ratio = -abs(ratio) if down else abs(ratio) if up else ratio
    nd = 0 if kr else 2
    live = (o.get("overMarketStatus") or "").upper() == "OPEN"
    label = ("NXT " if kr else "") + ("프리마켓" if sess == "PRE_MARKET" else "애프터마켓")
    return {"l": label, "v": fmt(price, nd), "p": sgn(ratio), "d": sgn(chg, nd),
            "t": dt.strftime("%H:%M") + (" 현재" if live and age < 900 else " 마감" if not live else " 지연")}


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
    e = ext_info(d, True)
    if e:
        it["e"] = e
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
attempt("SPX", lambda: naver(f"{A}/index/.INX/basic", "SPX"), lambda: naver(f"{A}/index/.SPX/basic", "SPX"))
attempt("SOX", lambda: naver(f"{A}/index/.SOX/basic", "SOX"))
attempt("VIX", lambda: naver(f"{A}/index/.VIX/basic", "VIX"))
attempt("NDX", lambda: naver(f"{A}/index/.NDX/basic", "NDX"))
attempt("USDKRW", lambda: naver(f"{A}/marketindex/exchange/FX_USDKRW", "USDKRW"))
attempt("WTI", lambda: naver(f"{A}/marketindex/energy/CLcv1", "WTI"))
attempt("BRENT", lambda: naver(f"{A}/marketindex/energy/LCOcv1", "BRENT"))
attempt("DUBAI", lambda: naver(f"{A}/marketindex/energy/DCBc1", "DUBAI"))
attempt("GOLD", lambda: naver(f"{A}/marketindex/metals/GCcv1", "GOLD"))
attempt("US10Y", lambda: naver(f"{A}/marketindex/bond/US10YT=RR", "US10Y", 3))
attempt("US2Y", lambda: naver(f"{A}/marketindex/bond/US2YT=RR", "US2Y", 3))
attempt("NQF", lambda: naver(f"{A}/futures/NQcv1/basic", "NQF"))


def spread():
    a, b = items["US10Y"], items["US2Y"]
    sp = num(a["v"]) - num(b["v"])
    ch = num(a["d"]) - num(b["d"])
    items["SPRD"] = {"v": sgn(sp, 2) if sp < 0 else fmt(sp, 2), "p": sgn(ch, 3), "d": sgn(ch, 3), "t": a.get("t", "")}


attempt("SPRD", spread)


def invest_and_breadth():
    """네이버 지수 통합정보: 투자자별 순매수(코스피·선물) + 상승/하락 종목 수(코스피·코스닥)."""
    for code, fk, ik, pk, bk in [("KOSPI", "KFRGN", "KINST", "KPER", "KBRD"), ("FUT", "FFRGN", "FINST", "FPER", None), ("KOSDAQ", None, None, None, "QBRD")]:
        try:
            j = get(f"{M}/index/{code}/integration")
        except Exception as e:  # noqa
            errors.append(f"{code} integration: {e}"[:200])
            continue
        deal = j.get("dealTrendInfo") or {}
        bd = str(deal.get("bizdate") or "")
        tl = f"{bd[4:6]}/{bd[6:8]} 기준" if len(bd) == 8 else ""
        for key, fld in [(fk, "foreignValue"), (ik, "institutionalValue"), (pk, "personalValue")]:
            v = num(deal.get(fld))
            if key and v is not None:
                items[key] = {"v": sgn(v, 0), "p": sgn(v, 0), "d": "순매수" if v > 0 else "순매도" if v < 0 else "보합", "t": tl}
        ud = j.get("upDownStockInfo") or {}
        if bk and ud:
            rise = (num(ud.get("upperCount")) or 0) + (num(ud.get("riseCount")) or 0)
            fall = (num(ud.get("lowerCount")) or 0) + (num(ud.get("fallCount")) or 0)
            st = num(ud.get("steadyCount")) or 0
            if rise + fall > 0:
                items[bk] = {"v": f"{rise:,.0f} / {fall:,.0f}", "p": sgn(rise - fall, 0), "d": f"보합 {st:,.0f}", "t": "상승 / 하락"}


invest_and_breadth()
for key, codes in [("NVDA", ["NVDA.O"]), ("SKHY", ["SKHY.O", "SKHY.K", "SKHY"]), ("MU", ["MU.O"]),
                   ("SNDK", ["SNDK.O"]), ("AVGO", ["AVGO.O"]), ("AMD", ["AMD.O"]), ("SOXL", ["SOXL.K"])]:
    attempt(key, *[(lambda c=c, k=key: naver(f"{A}/stock/{c}/basic", k)) for c in codes])

def btc_yahoo():
    j = get("https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?range=1d&interval=5m")
    m = j["chart"]["result"][0]["meta"]
    px, pct = m["regularMarketPrice"], m.get("regularMarketChangePercent")
    if pct is None:
        raise ValueError("no pct")
    put("BTC", px, px / (1 + pct / 100), datetime.fromtimestamp(m["regularMarketTime"], KST), True, 0)


def btc_gecko():
    j = get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true")["bitcoin"]
    px = j["usd"]
    put("BTC", px, px / (1 + j["usd_24h_change"] / 100), datetime.now(KST), True, 0)


attempt("BTC", btc_yahoo, btc_gecko)

# 장중 흐름용 이력(코스피·코스닥, 당일만): 이전 게시본을 읽어 이어 붙임
def build_hist(now):
    day, hm = now.strftime("%Y-%m-%d"), now.strftime("%H:%M")
    h = {"d": day, "KOSPI": [], "KOSDAQ": []}
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            "https://raw.githubusercontent.com/cocok6666-ai/stock/data/quotes.json?_=%d" % int(time.time()), headers=UA), timeout=15)
        old = json.loads(r.read().decode("utf-8")).get("hist") or {}
        if old.get("d") == day:
            h = {"d": day, "KOSPI": old.get("KOSPI", []), "KOSDAQ": old.get("KOSDAQ", [])}
    except Exception:
        pass
    if now.weekday() < 5 and "09:00" <= hm <= "15:40":
        for k in ("KOSPI", "KOSDAQ"):
            it = items.get(k) or {}
            v = num(it.get("v")) if it.get("v") else None
            if v is not None and "현재" in str(it.get("t", "")):
                if not h[k] or h[k][-1][0] != hm:
                    h[k].append([hm, v])
            h[k] = h[k][-120:]
    return h

now_kst = datetime.now(KST)
out = {"updated": datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S+09:00"), "items": items, "errors": errors, "hist": build_hist(now_kst)}
with open(sys.argv[1] if len(sys.argv) > 1 else "quotes.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"ok={len(items)} errors={len(errors)}")
for e in errors:
    print(" -", e)
