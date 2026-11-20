import urllib.request, re, html
H={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36","Accept-Language":"ko-KR,ko;q=0.9"}
for n,u in [("prekospi","https://www.prekospi.com/kospi200-night"),("chartlog","https://chartlog.net/stats/market-index/kospi-night-futures/")]:
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=25); b=r.read().decode("utf-8","ignore"); print("=====",n,r.status,len(b))
    except Exception as e:
        print("=====",n,"ERR",e); continue
    t=re.sub(r"<script.*?</script>|<style.*?</style>","",b,flags=re.S); t=html.unescape(re.sub(r"<[^>]+>"," ",t)); t=re.sub(r"\s+"," ",t)
    print(t[:1800])
    for m in list(re.finditer(r"__NEXT_DATA__|application/json|\"close\"|마감",b))[:5]:
        print("  RAW:",re.sub(r"\s+"," ",b[max(0,m.start()-100):m.start()+400]))
