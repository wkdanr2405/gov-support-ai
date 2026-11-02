# 04. 외부 API 조사 (2026-11-01 기준)

각 항목에 확인한 것과 확인하지 못한 것을 구분해 둔다. 키 발급 후 실제 응답으로 다시 확정한다.

## K-Startup 조회서비스 (창업진흥원) ← 1순위
- 공공데이터포털 15125364: https://www.data.go.kr/data/15125364/openapi.do
- 확인함: 개발·운영 자동승인, 무료, JSON/XML, 이용허락 제한 없음, 개발계정 10,000건(운영계정은 활용사례 등록 시 증설 가능), 갱신 주기 "실시간"
- 제3자 문서(미검증): 서비스 URL `https://apis.data.go.kr/B552735/kisedKstartupService01`, 공고 조회 `getAnnouncementInformation01`, 파라미터 `supt_regin`·`rcrt_prgs_yn`·`per_page`, 응답에 공고명·접수기간·지역·신청대상·모집진행여부·`detl_pg_url` 포함
  (출처: https://raw.githubusercontent.com/NomaDamas/k-skill/main/docs/features/kstartup-search.md)
- 주의: 지역 필터(`supt_regin`)가 서버에서 적용되지 않는 사례가 있다고 함 → 받은 뒤 코드에서 다시 거른다. 갱신 주기 표기가 문서마다 다르므로 마감 여부는 상세 링크에서 확인하도록 안내한다.

## 기업마당 지원사업정보 API (중소벤처기업부)
- https://www.bizinfo.go.kr/web/lay1/program/S1T175C174/apiList.do
- 확인함: 별도 인증키가 필요하다는 점
- 확인하지 못함: 발급 절차, 응답 항목, 호출 한도 (공식 페이지가 자동 접근을 막음) → **사용자가 직접 확인 필요**

## 중소벤처기업부 사업공고 (공공데이터포털 15113297) ← 보조
- https://www.data.go.kr/data/15113297/openapi.do
- 확인함: 무료, XML, 요청 변수 `serviceKey`·`pageNo`·`numOfRows`·`startDate`·`endDate`(등록일 기준), 응답은 제목·작성자·첨부파일 위주
- 신청기간·지원대상 항목이 보이지 않아 매칭용으로는 부적합. 활용신청 승인 방식은 확인하지 못함.

## LLM API
- Claude API 가격표(2026-11-01 확인): https://platform.claude.com/docs/en/about-claude/pricing
  Haiku 5.5 입력 $0.10 / 출력 $0.50, Sonnet 5.5 입력 $2 / 출력 $10 (100만 토큰당, 입력 10만 토큰 이하 기준)
- 리포트 1건(입력 약 8천, 출력 약 1천 토큰 가정) ≈ Sonnet 5.5로 0.03달러 안팎 (추정)
- 키 발급에 결제수단이 필요할 수 있음 (최소 충전액 미확인)
- 시연에는 가상 기업 데이터만 사용한다.

## 개발 환경 제한
클라우드 개발 환경에서는 외부 사이트 호출이 막혀 있어 API 실호출 테스트가 어렵다. 샘플 데이터로 먼저 개발하고, 사용자 PC에서 키를 넣어 한 번 실행해 받은 응답을 `data/snapshots/`에 저장한다.

## 11/2 추가 확인
- K-Startup 서버(apis.data.go.kr)는 클라우드 개발 환경에서 접속되며 키 없이 호출하면 401이 온다. 키를 넣은 실제 응답은 아직 보지 못했다 → 응답 항목명·경로는 `src/data_sources/kstartup.py`의 `normalize()`에서 첫 실호출 후 확정.
- 기업마당(bizinfo.go.kr)은 클라우드 환경에서 연결이 끊긴다 → 사용자 PC나 배포 서버에서 받아 저장본으로 넘긴다.
- 크롤링 대신 공식 API를 쓴다 (robots.txt, 화면 구조 변경에 취약).
- **K-Startup 실호출 확인 (11/2):** 경로 `getAnnouncementInformation01` 정상. 응답은 `{currentCount, matchCount, page, perPage, totalCount, data[]}`, `cond[rcrt_prgs_yn::EQ]=Y`로 모집 중 196건 (전체 30,483건). 건수는 `matchCount`로 판단. 프록시 연결이 간헐적으로 끊겨 재시도 추가. 지역 120건 전국, 서울 24건. 대부분 창업·입주·교육 성격이라 제조 R&D·인건비 지원은 기업마당이 보완해야 함.
- **기업마당 실호출 확인 (11/2, 사용자 PC에서 실행):** 응답 `{"jsonArray":[...]}` 300건. 항목: pblancId, pblancNm, bsnsSumryCn(HTML 포함), jrsdInsttNm(관할기관), excInsttNm, trgetNm, pldirSportRealmLclasCodeNm(경영·기술·수출·창업·인력·금융·내수), reqstBeginEndDe, pblancUrl, hashtags 등. 접수기간 221건은 `YYYY-MM-DD ~ YYYY-MM-DD`, 79건은 '예산 소진시까지' 등 문구(종료일 없음). 지역은 관할기관으로 정하고 중앙부처 소관이라도 제목이 `[대구]`로 시작하면 그 지역. 클라우드 환경에서는 접속 불가라 PC에서 받는다.
