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



## 승인 코드 (제작자가 허락한 사람만 사용)
- 사용자는 제작자에게 받은 8자리 코드(예: `ABCD-2345`)를 입력해야 앱을 쓸 수 있습니다. 코드 1개당 기기 2대까지.
- 서버: `worker/naver-proxy.js` (Cloudflare Worker `kkaebi-naver`). KV 네임스페이스를 변수명 `GATE` 로 연결하고, 비밀 변수 `ADMIN_INIT`(관리자 처음 암호, 11자 이상)을 설정합니다.
- 관리자 화면: `admin.html` (앱 어디에도 링크 없음). 코드 생성/붙여넣기 등록, 받은 사람 이름, 차단·해제, 기기 삭제, 승인 모드 켜기/끄기, 관리자 암호 변경(11자 이상·영문+숫자+특수문자).
- `index.html`·`admin.html` 의 `GATE_URL` 에 Worker 주소를 넣으면 승인 기능이 켜집니다(비어 있으면 기존과 동일).
- 승인 모드는 기본 꺼짐(안내 문구만 표시). 모두에게 코드를 나눠준 뒤 관리자 화면에서 켭니다.
- 관리자 암호를 잊으면: Cloudflare → KV `GATE` 에서 키 `cfg:pw` 삭제 → `ADMIN_INIT` 값으로 다시 들어가 새 암호 설정.
- 한계: 앱 화면과 데이터 파일이 담긴 저장소가 공개라서, 승인 모드를 켜도 옛 주소로 직접 받는 공개 데이터 파일은 막히지 않습니다(분석 서버·Worker 경유 데이터는 막힘).
