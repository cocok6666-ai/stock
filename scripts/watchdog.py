#!/usr/bin/env python3
"""자동 갱신 감시: 갱신 시각이 지났는데 데이터가 오래됐으면 해당 워크플로를 다시 실행한다.
- 국내 종목분석: 평일 15:00 목록 / 15:10 통계 (마감 20분·10분 전 기준 아님, 사용자가 정한 시각)
- 미국 종목분석: 미국장 마감 20분 전 목록 / 10분 전 통계 (서머타임 자동 반영)
- 시세(quotes): 장 시간대에 15분 넘게 갱신 없으면 재실행
이미 실행 중이거나 최근 12분 안에 실행된 워크플로는 건드리지 않는다. 호출: quotes.yml 끝, watchdog.yml(10분 주기·push)."""
import json, subprocess, sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

KST, ET = ZoneInfo("Asia/Seoul"), ZoneInfo("America/New_York")
now = datetime.now(KST)

def sh(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout

def parse(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

def load(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}

def recently_active(wf):
    try:
        runs = json.loads(sh("gh", "run", "list", "--workflow", wf, "--limit", "6", "--json", "status,createdAt"))
    except Exception:
        return False
    for r in runs:
        if r.get("status") in ("queued", "in_progress", "waiting", "requested", "pending"):
            return True
        t = parse((r.get("createdAt") or "").replace("Z", "+00:00"))
        if t and now - t.astimezone(KST) < timedelta(minutes=12):
            return True
    return False

def dispatch(wf, why, mode=None):
    if recently_active(wf):
        print("건너뜀(실행 중/최근 실행):", wf, why); return
    cmd = ["gh", "workflow", "run", wf, "--ref", "main"] + (["-f", f"mode={mode}"] if mode else [])
    print("재실행:", wf, mode or "", "-", why, "→", subprocess.run(cmd, capture_output=True, text=True).returncode)

stats, stocks, stocks_us = load("stats.json"), load("stocks.json"), load("stocks_us.json")
wd = now.weekday() < 5

# ---- 국내: 15:10 통계, 15:00 목록 ----
if wd:
    d = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if now >= d.replace(hour=15, minute=20):
        at = parse(((stats.get("meta") or {}).get("kr") or {}).get("at", ""))
        if not at or at < d.replace(hour=15, minute=5):
            dispatch("screen.yml", "국내 분석통계 15:10 미갱신", "kr")
    if now >= d.replace(hour=15, minute=15):
        up = parse(stocks.get("updated", ""))
        if not up or up < d.replace(hour=14, minute=55):
            dispatch("stocks.yml", "종목 목록 15:00 미갱신")

# ---- 미국: 마감 20분 전 목록 / 10분 전 통계 ----
e = now.astimezone(ET)
for back in range(0, 4):
    day = (e - timedelta(days=back)).date()
    if day.weekday() >= 5:
        continue
    close = datetime(day.year, day.month, day.day, 16, 0, tzinfo=ET).astimezone(KST)
    if close <= now:
        if now - close < timedelta(hours=20):
            at = parse(((stats.get("meta") or {}).get("us") or {}).get("at", ""))
            if not at or at < close - timedelta(minutes=15):
                dispatch("screen.yml", f"미국 분석통계 미갱신(마감 {close:%m/%d %H:%M} KST)", "us")
            up = parse(stocks_us.get("updated", ""))
            if not up or up < close - timedelta(minutes=30):
                dispatch("stocks.yml", f"미국 종목 목록 미갱신(마감 {close:%m/%d %H:%M} KST)")
        break

# ---- 시세(quotes): 장 시간대 15분 이상 정체 ----
def in_window(n):
    d, hm = n.isoweekday(), n.hour * 100 + n.minute
    return (d <= 5 and hm >= 650) or (2 <= d <= 6 and hm < 650)

if in_window(now):
    import base64, os
    repo = os.environ.get("GITHUB_REPOSITORY", "cocok6666-ai/stock")
    try:
        c = json.loads(sh("gh", "api", f"repos/{repo}/contents/quotes.json?ref=data"))
        q = json.loads(base64.b64decode(c["content"]))
        qa = parse(q.get("updated", ""))
    except Exception:
        qa = None
    if not qa or now - qa > timedelta(minutes=15):
        dispatch("quotes.yml", "시세 15분 이상 정체")
print("감시 완료", now.strftime("%m/%d %H:%M KST"))
