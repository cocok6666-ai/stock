import json,sys,time,urllib.request
UA={"User-Agent":"Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36","Referer":"https://m.stock.naver.com/","Accept":"application/json,*/*"}
C=["https://api.stock.naver.com/index/.DJI/basic","https://api.stock.naver.com/stock/NVDA.O/basic","https://api.stock.naver.com/stock/SKHY/basic","https://api.stock.naver.com/stock/SOXL.K/basic",
"https://api.stock.naver.com/marketindex/exchange/FX_USDKRW","https://api.stock.naver.com/marketindex/energy/CLcv1","https://api.stock.naver.com/marketindex/bond/US10YT=RR"]
out={}
def flat(o,p=""):
    r={}
    if isinstance(o,dict):
        for k,v in o.items():
            if isinstance(v,(dict,list)) and k not in("stockExchangeType",): r.update(flat(v if isinstance(v,dict) else {},p+k+"."))
            elif not isinstance(v,(dict,list)): r[p+k]=v
    return r
for u in C:
    try:
        j=json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=15).read().decode())
        f=flat(j); out[u]={k:v for k,v in f.items() if not str(k).endswith(("Url","Name","NameEng","fullName"))}
    except Exception as e: out[u]="ERR %s"%e
    time.sleep(1)
json.dump(out,open(sys.argv[1],"w"),ensure_ascii=False,indent=1)
