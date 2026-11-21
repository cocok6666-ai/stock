import sys,json,urllib.request
H={"User-Agent":"Mozilla/5.0"}
for u in ["https://m.stock.naver.com/api/stock/005930/basic","https://m.stock.naver.com/api/stock/005930/integration","https://m.stock.naver.com/api/stock/AAPL.O/basic","https://m.stock.naver.com/api/stock/247540/integration"]:
    print("===",u)
    try: d=json.load(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=20))
    except Exception as e: print("ERR",e); continue
    out=[]
    def w(o,p="",dep=0):
        if isinstance(o,dict):
            for k,v in o.items():
                if isinstance(v,(dict,list)):
                    if dep<3: w(v,p+k+".",dep+1)
                else: out.append(p+k+"="+str(v)[:60])
        elif isinstance(o,list) and o: w(o[0],p+"[0].",dep+1)
    w(d)
    for l in out:
        if any(s in l.lower() for s in ["indust","sector","upjong","categor","theme","group","stockendtype","kor"]): print(l)
