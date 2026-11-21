import json,urllib.request
H={"User-Agent":"Mozilla/5.0"}
def get(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=20))
    except Exception as e: print("ERR",u,e); return None
d=get("https://m.stock.naver.com/api/stock/005930/integration")
if d:
    print("KEYS",list(d.keys()))
    for k,v in d.items():
        if isinstance(v,str): print(k,"=",v[:120])
for u in ["https://m.stock.naver.com/api/stocks/industry?page=1&pageSize=5","https://m.stock.naver.com/api/stocks/industry/283","https://m.stock.naver.com/api/stock/005930/basic","https://api.stock.naver.com/stock/AAPL.O/basic","https://m.stock.naver.com/api/stocks/industry/278?page=1&pageSize=3"]:
    x=get(u); print("===",u)
    if x is not None: print(json.dumps(x,ensure_ascii=False)[:700])
