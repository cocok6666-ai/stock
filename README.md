# 깨비주식 아침브리핑
- `index.html` 앱 화면 (GitHub Pages)
- `brief.json` 아침 7시 브리핑 문구
- `scripts/fetch_quotes.py` + `.github/workflows/quotes.yml` 5분마다 시세 수집 → `data` 브랜치의 `quotes.json`
- `night.json` 코스피200 야간선물 마감값 (06:20 예약 작업이 기록). 형식: `{"closed":"YYYY-MM-DD","close":"1,146.50","pct":"+1.23","src":"출처","at":"06:25"}` — `closed`는 야간 세션이 끝난 날짜(KST, 화~토 06:00). 값이 없거나 날짜가 다르면 앱이 등락률(%) 입력 팝업을 띄웁니다(수동입력은 해당 기기에만 저장, `무시하고 시작하기` 가능).

## 종목분석 서버 (Cloudflare Worker, 처음 한 번만)
앱의 `📊 종목분석` 버튼은 네이버 주식 정보를 브라우저에서 직접 읽을 수 없어서, 작은 중계 서버(Worker)를 거칩니다. 무료입니다.
1. https://dash.cloudflare.com 로그인 → **Workers & Pages** → **Create** → **Create Worker** → 이름 입력(예: `kkaebi-naver`) → **Deploy**
2. **Edit code** 를 눌러 기본 코드를 모두 지우고 `worker/naver-proxy.js` 내용을 붙여넣은 뒤 **Deploy**
3. 주소(`https://kkaebi-naver.<계정>.workers.dev`)를 복사 → 주소창에 열었을 때 `naver-proxy ok` 가 보이면 정상
4. 앱에서 `📊 종목분석` → 위쪽 입력칸에 그 주소를 붙여넣고 **저장** (기기마다 한 번)

- Worker 는 `https://cocok6666-ai.github.io` 에서 온 요청만, 네이버 주식 도메인(`m.stock.naver.com` 등)만 중계합니다.
- 분석은 시세·수급·지표와 오늘 브리핑(갭 방향, 반도체 등)을 규칙으로 조합한 참고용 체크이며, AI 가 쓰는 글이 아닙니다.

