import urllib.request, re, html
H={"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1","Accept-Language":"ko-KR,ko;q=0.9"}
def get(u):
    try: return urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=20).read().decode("utf-8","ignore")
    except Exception as e: return "ERR "+str(e)
for n,u in [("NAVER-PC","https://search.naver.com/search.naver?query=%EC%BD%94%EC%8A%A4%ED%94%BC200+%EC%95%BC%EA%B0%84%EC%84%A0%EB%AC%BC"),
            ("NAVER-M","https://m.search.naver.com/search.naver?query=%EC%BD%94%EC%8A%A4%ED%94%BC200+%EC%95%BC%EA%B0%84%EC%84%A0%EB%AC%BC"),
            ("NAVER-M2","https://m.search.naver.com/search.naver?query=%EC%95%BC%EA%B0%84%EC%84%A0%EB%AC%BC"),
            ("GOOGLE","https://www.google.com/search?q=%EC%BD%94%EC%8A%A4%ED%94%BC200+%EC%95%BC%EA%B0%84%EC%84%A0%EB%AC%BC&hl=ko&gl=kr")]:
    b=get(n and u); print("=====",n,len(b))
    t=re.sub(r"<script.*?</script>|<style.*?</style>","",b,flags=re.S)
    t=html.unescape(re.sub(r"<[^>]+>"," ",t)); t=re.sub(r"\s+"," ",t)
    for m in list(re.finditer(r"야간",t))[:6]:
        print("  ..",t[max(0,m.start()-120):m.start()+260])
    for m in list(re.finditer(r"야간선물[^\n]{0,40}\d{3}\.\d{2}",b))[:3]: print("  RAW",m.group(0)[:200])
