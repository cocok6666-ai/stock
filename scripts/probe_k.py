import json,urllib.request
H={"User-Agent":"Mozilla/5.0"}
for u in ["https://m.stock.naver.com/api/stocks/marketValue/KOSPI?page=1&pageSize=2","https://m.stock.naver.com/api/stocks/etf?page=1&pageSize=1","https://api.stock.naver.com/stock/exchange/NASDAQ/marketValue?page=1&pageSize=2"]:
    j=json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=25).read())
    print("=====",u); print(json.dumps((j.get("stocks") or [])[:1],ensure_ascii=False)[:1800])
