# 02. 구조

```
[Streamlit 화면 app.py]
   │ 입력 dict
   ├─► src/tax_engine      → 계산 결과 dict (금액은 여기서만 만든다)
   ├─► src/matching        ← src/data_sources (K-Startup, 기업마당) / data/snapshots (저장본)
   │                         → 후보 공고 리스트 → LLM이 상위 N건 선별·설명
   └─► src/report          → 계산 결과 + 매칭 결과 → LLM 해설 → 화면/PDF
```

## 모듈 간 데이터 형식 (초안, 구현하면서 확정)

입력(`CompanyProfile`)
```
industry, founded_date, region(수도권/비수도권 + 시·도), revenue,
employees_prev, employees_curr, youth_prev, youth_curr, rnd_expense
```

계산 결과(`TaxResult`)
```
items: [{name, basis, formula, amount, law_ref, verified}]
total_annual, notes(사후관리 등), scenario: [{extra_youth, annual_saving}]
```

매칭 결과(`MatchResult`)
```
items: [{title, agency, period, region, target, url, score, matched_keywords, d_day, contact}]
```

## 설계 결정과 이유
- **금액은 코드만 계산**: LLM이 숫자를 틀리거나 지어내면 안 되므로, LLM에는 계산 결과(JSON)만 주고 설명을 맡긴다.
- **법령 수치를 YAML로 분리**: 세법이 바뀌어도 코드 수정 없이 수치만 교체하고, 값마다 출처와 확인일을 남긴다.
- **Streamlit 단일 앱**: 비전문가 1인이 6주 안에 끝내기 위해 언어·서버를 하나로 줄인다.
- **저장본(스냅샷) 우선**: 시연 중 외부 API 장애가 발표를 망치지 않게 한다.
- **임베딩 보류**: 조건 필터 + 키워드 점수 + LLM 선별로 먼저 완성하고, 시간이 남으면 임베딩 검색을 추가한다. (덱 9번 슬라이드의 "임베딩해 DB 구축" 문구와 차이 → `08-deck-sync.md`)
