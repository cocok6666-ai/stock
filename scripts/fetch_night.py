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

best = None
for dt, t in sorted(set(items), reverse=True):
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
