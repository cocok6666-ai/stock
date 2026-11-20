import urllib.request, json, re
H={"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)","Accept":"*/*"}
def get(u, extra=None, data=None):
    h=dict(H); h.update(extra or {})
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=h,data=data),timeout=20)
        b=r.read(); return r.status,b.decode("utf-8","ignore")
    except Exception as e:
        return "ERR",str(e)[:120]
T=[
 ("naver FUT basic","https://m.stock.naver.com/api/index/FUT/basic"),
 ("naver FUT integ","https://m.stock.naver.com/api/index/FUT/integration"),
 ("naver NIGHT?","https://m.stock.naver.com/api/index/NIGHT/basic"),
 ("naver polling FUT","https://polling.finance.naver.com/api/realtime/domestic/index/FUT"),
 ("naver sise fut","https://finance.naver.com/sise/sise_index.naver?code=FUT"),
 ("naver nightfut page","https://finance.naver.com/sise/nightFutures.naver"),
 ("daum fut","https://finance.daum.net/api/domestic/futures"),
 ("investing k200 fut","https://api.investing.com/api/financialdata/historical/101797?start-date=2026-11-10&end-date=2026-11-21&time-frame=Daily&add-missing-rows=false"),
 ("yahoo ks200","https://query1.finance.yahoo.com/v8/finance/chart/%5EKS200?interval=1d&range=5d"),
 ("yahoo kospi fut","https://query1.finance.yahoo.com/v8/finance/chart/KS200.KS?interval=1d&range=5d"),
 ("krx night market","https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"),
 ("tv scan night","https://scanner.tradingview.com/futures/scan"),
 ("kofia/ebest","https://www.ebestsec.co.kr/"),
 ("naver search night","https://search.naver.com/search.naver?query=%EC%BD%94%EC%8A%A4%ED%94%BC200+%EC%95%BC%EA%B0%84%EC%84%A0%EB%AC%BC"),
 ("google search night","https://www.google.com/search?q=%EC%BD%94%EC%8A%A4%ED%94%BC200+%EC%95%BC%EA%B0%84%EC%84%A0%EB%AC%BC&hl=ko"),
]
for n,u in T:
    if n=="tv scan night":
        body={"symbols":{"tickers":["KRX:K2I1!","KRX:K2I2!","KRX:KS200"]},"columns":["name","description","close","change","time","update_mode","exchange"]}
        s,b=get(u,{"Content-Type":"application/json","Origin":"https://www.tradingview.com"},json.dumps(body).encode())
    elif n.startswith("krx"):
        s,b=get(u,{"Referer":"https://data.krx.co.kr/","Content-Type":"application/x-www-form-urlencoded"},b"bld=dbms/MDC/STAT/standard/MDCSTAT12501&locale=ko_KR&trdDd=20261120")
    else:
        s,b=get(u)
    print("=====",n,s,len(b)); print(re.sub(r"\s+"," ",b)[:700])
