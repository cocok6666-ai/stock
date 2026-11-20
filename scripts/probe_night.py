import urllib.request, re, html, json
H={"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1","Accept-Language":"ko-KR,ko;q=0.9"}
b=urllib.request.urlopen(urllib.request.Request("https://m.search.naver.com/search.naver?query=%EC%BD%94%EC%8A%A4%ED%94%BC200+%EC%95%BC%EA%B0%84%EC%84%A0%EB%AC%BC",headers=H),timeout=20).read().decode("utf-8","ignore")
for key in ["야간 시세","KIS 코스피 200 야간선물"]:
    for m in list(re.finditer(re.escape(key),b))[:2]:
        s=b[max(0,m.start()-1500):m.start()+1800]
        s=re.sub(r"\s+"," ",s)
        print("##### ",key,m.start()); print(s)
