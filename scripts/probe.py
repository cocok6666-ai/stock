import json,sys,time,urllib.request
UA={"User-Agent":"Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36","Referer":"https://m.stock.naver.com/","Accept":"application/json,*/*"}
C=["https://api.stock.naver.com/index/.DJI/basic","https://api.stock.naver.com/index/.IXIC/basic",
"https://api.stock.naver.com/stock/NVDA.O/basic","https://api.stock.naver.com/stock/MU.O/basic",
"https://m.stock.naver.com/api/index/.DJI/basic",
"https://m.stock.naver.com/front-api/marketIndex/productDetail?category=exchange&reutersCode=FX_USDKRW",
"https://m.stock.naver.com/front-api/marketIndex/productDetail?category=energy&reutersCode=CLcv1",
"https://m.stock.naver.com/front-api/marketIndex/productDetail?category=energy&reutersCode=LCOcv1",
"https://m.stock.naver.com/front-api/marketIndex/productDetail?category=bond&reutersCode=US10YT=RR",
"https://api.stock.naver.com/marketindex/exchange/FX_USDKRW",
"https://api.stock.naver.com/marketindex/energy/CLcv1",
"https://api.stock.naver.com/marketindex/bond/US10YT=RR",
"https://api.stock.naver.com/futures/NQ", 
"https://query2.finance.yahoo.com/v8/finance/chart/NQ%3DF?interval=1m&range=1d",
"https://m.stock.naver.com/api/index/KPI200/basic","https://m.stock.naver.com/api/index/FUT/basic"]
out={}
for u in C:
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=15)
        out[u]=r.read().decode("utf-8","replace")[:700]
    except Exception as e: out[u]="ERR %s"%e
    time.sleep(2)
json.dump(out,open(sys.argv[1],"w"),ensure_ascii=False,indent=1)
