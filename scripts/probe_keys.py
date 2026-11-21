import json,urllib.request
H={"User-Agent":"Mozilla/5.0"}
def get(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=20))
    except Exception as e: print("ERR",u,e); return None
for c in ["005930","247540","068270"]:
    d=get("https://m.stock.naver.com/api/stock/%s/integration"%c)
    if d: print(c,d.get("industryCode"),"|",str(d.get("description"))[:300])
for c in ["AAPL.O","NVDA.O","JPM"]:
    d=get("https://api.stock.naver.com/stock/%s/basic"%c)
    if d:
        print(c,d.get("industryCodeType"),"|",str(d.get("description"))[:200],"|",[k for k in d.keys()])
x=get("https://m.stock.naver.com/api/stocks/industry?page=1&pageSize=100")
if x: print(len(x["groups"]),[(g["no"],g["name"]) for g in x["groups"]])
