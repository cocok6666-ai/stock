#!/usr/bin/env python3
"""미국 PPI(최종수요) — BLS 공개 API(v1, 키 불필요). YoY(원계열) + MoM(계절조정)."""
import json, sys, urllib.request
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))


def series(sid):
    req = urllib.request.Request("https://api.bls.gov/publicAPI/v1/timeseries/data/" + sid,
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.loads(r.read().decode("utf-8"))
    if j.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(str(j.get("message"))[:200])
    d = {}
    for x in j["Results"]["series"][0]["data"]:
        if x["period"].startswith("M") and x["period"] != "M13":
            d[(int(x["year"]), int(x["period"][1:]))] = float(x["value"])
    return d


nsa = series("WPSFD4")
try:
    sa = series("WPSFD49104")
except Exception as e:  # noqa
    print("SA 실패:", e)
    sa = {}
y, m = max(nsa)
yoy = (nsa[(y, m)] / nsa[(y - 1, m)] - 1) * 100 if (y - 1, m) in nsa else None
mom = None
if sa:
    sy, sm = max(sa)
    py, pm = (sy, sm - 1) if sm > 1 else (sy - 1, 12)
    if (py, pm) in sa:
        mom = (sa[(sy, sm)] / sa[(py, pm)] - 1) * 100
if mom is None:
    py, pm = (y, m - 1) if m > 1 else (y - 1, 12)
    if (py, pm) in nsa:
        mom = (nsa[(y, m)] / nsa[(py, pm)] - 1) * 100
if yoy is None and mom is None:
    sys.exit("계산 불가")
out = {"updated": datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S+09:00"), "year": y, "month": m,
       "yoy": None if yoy is None else round(yoy, 1), "mom": None if mom is None else round(mom, 1),
       "index": nsa[(y, m)]}
json.dump(out, open("ppi.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(out)
