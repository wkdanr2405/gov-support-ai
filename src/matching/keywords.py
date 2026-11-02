"""키워드 점수: 기업 상황에서 뽑은 검색어가 공고 글에 얼마나 나오는지. 근거 키워드를 함께 돌려준다."""


def profile_keyword_groups(profile: dict) -> list[dict]:
    groups = []
    for tok in profile.get("industry_tokens", []):
        groups.append({"label": tok, "terms": [tok], "weight": 2.0})
    groups.append({"label": "제조", "terms": ["제조", "생산", "공장"], "weight": 1.0}) if profile.get("is_manufacturing") else None
    if profile["age_years"] <= 7:
        groups.append({"label": "창업·초기", "terms": ["창업", "초기"], "weight": 0.5})
    if profile.get("youth_added", 0) > 0:
        groups.append({"label": "청년 채용", "terms": ["청년", "신규채용", "채용", "일자리"], "weight": 2.0})
    elif profile.get("employees_added", 0) > 0:
        groups.append({"label": "고용 확대", "terms": ["고용", "채용", "일자리"], "weight": 1.5})
    if profile.get("rnd_curr", 0) > 0:
        groups.append({"label": "연구개발", "terms": ["기술개발", "R&D", "연구개발", "기술혁신", "시제품", "기술이전", "연구소"], "weight": 3.0})
    return [g for g in groups if g]


def keyword_score(a: dict, groups: list[dict]) -> tuple[float, list[str]]:
    text = " ".join([a["title"], a["summary"], a["target"], a["field"], " ".join(a["regions"])])
    total = sum(g["weight"] for g in groups) or 1.0
    got, matched = 0.0, []
    for g in groups:
        hit = [t for t in g["terms"] if t in text]
        if hit:
            got += g["weight"]
            matched += hit
    return got / total, list(dict.fromkeys(matched))
