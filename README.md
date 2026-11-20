# 깨비주식 아침브리핑
- `index.html` 앱 화면 (GitHub Pages)
- `brief.json` 아침 7시 브리핑 문구
- `scripts/fetch_quotes.py` + `.github/workflows/quotes.yml` 5분마다 시세 수집 → `data` 브랜치의 `quotes.json`
- `night.json` 코스피200 야간선물 마감값 (06:20 예약 작업이 기록). 형식: `{"closed":"YYYY-MM-DD","close":"1,146.50","pct":"+1.23","src":"출처","at":"06:25"}` — `closed`는 야간 세션이 끝난 날짜(KST, 화~토 06:00). 값이 없거나 날짜가 다르면 앱이 등락률(%) 입력 팝업을 띄웁니다(수동입력은 해당 기기에만 저장, `무시하고 시작하기` 가능).
