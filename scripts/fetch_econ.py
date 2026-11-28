#!/usr/bin/env python3
"""직전 발표 수치: 미국 CPI(전년비·전월비), 고용(비농업 일자리 증감·실업률) — BLS 공개 API(v1), 기준금리 — FRED."""
import json, urllib.request
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
out = {"updated": datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S+09:00")}


def series(sid):
    req = urllib.request.Request("https://api.bls.gov/publicAPI/v1/timeseries/data/" + sid, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.loads(r.read().decode("utf-8"))
    if j.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(str(j.get("message"))[:200])
    d = {}
    for x in j["Results"]["series"][0]["data"]:
        if x["period"].startswith("M") and x["period"] != "M13" and x["value"] not in ("-", ""):
            d[(int(x["year"]), int(x["period"][1:]))] = float(x["value"])
    return d


def prev(k):
    y, m = k
    return (y, m - 1) if m > 1 else (y - 1, 12)


try:
    nsa, sa = series("CUUR0000SA0"), series("CUSR0000SA0")
    y, m = max(nsa)
    c = {"year": y, "month": m, "yoy": round((nsa[(y, m)] / nsa[(y - 1, m)] - 1) * 100, 1)}
    if (y, m) in sa and prev((y, m)) in sa:
        c["mom"] = round((sa[(y, m)] / sa[prev((y, m))] - 1) * 100, 1)
    out["cpi"] = c
except Exception as e:  # noqa
    print("CPI 실패:", e)

try:
    pay, ur = series("CES0000000001"), series("LNS14000000")
    y, m = max(pay)
    j = {"year": y, "month": m, "chg": round(pay[(y, m)] - pay[prev((y, m))])}
    if (y, m) in ur:
        j["ur"] = ur[(y, m)]
    out["jobs"] = j
except Exception as e:  # noqa
    print("고용 실패:", e)

try:
    def fred(sid):
        req = urllib.request.Request("https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + sid, headers={"User-Agent": "Mozilla/5.0"})
        rows = [l.split(",") for l in urllib.request.urlopen(req, timeout=30).read().decode().strip().splitlines()[1:]]
        rows = [r for r in rows if len(r) == 2 and r[1] not in (".", "")]
        return float(rows[-1][1]), rows[-1][0]
    hi, d1 = fred("DFEDTARU")
    lo, _ = fred("DFEDTARL")
    out["fed"] = {"lo": lo, "hi": hi, "date": d1}
except Exception as e:  # noqa
    print("기준금리 실패:", e)

if len(out) == 1:
    raise SystemExit("수집 실패")
json.dump(out, open("econ.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(out)
