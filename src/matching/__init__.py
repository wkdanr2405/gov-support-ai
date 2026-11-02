"""Track B: 공고 매칭 = 조건 필터 → 키워드 점수 + 임베딩 의미 점수 → 상위 N건."""
from datetime import date

import numpy as np

from .embed import Embedder, load_or_build_index
from .filters import check, d_day
from .keywords import keyword_score, profile_keyword_groups

__all__ = ["build_profile", "match", "Embedder"]

GENERIC_TOKENS = {"영상", "음향", "컴퓨터", "통신장비", "기타", "그", "외", "관련", "서비스"}   # 업종명에서 뜻이 너무 넓어 노이즈가 되는 단어
W_SEMANTIC, W_KEYWORD = 0.5, 0.5   # 의미 점수와 키워드 점수의 비중. 점수는 공고끼리 비교하는 상대 순위용이다.


def build_profile(industry_name: str, sido: str, founded: date, employees_prev: int, employees_curr: int,
                  youth_prev: int, youth_curr: int, rnd_curr: float, today: date | None = None) -> dict:
    today = today or date.today()
    age_years = max((today - founded).days // 365, 0)
    tokens = [t for t in "".join(c if c not in ",·" else " " for c in industry_name).replace("및", " ").split()
              if t not in ("제조업", "업", "서비스업") and len(t) >= 2]
    tokens = [t.replace("제조업", "").strip() for t in tokens]
    return {"industry_name": industry_name, "industry_tokens": [t for t in tokens if t and t not in GENERIC_TOKENS][:4],
            "is_manufacturing": "제조" in industry_name, "sido": sido, "age_years": age_years,
            "employees_added": max(employees_curr - employees_prev, 0), "youth_added": max(youth_curr - youth_prev, 0),
            "rnd_curr": rnd_curr}


def query_text(p: dict) -> str:
    parts = [f"{p['sido']} 소재 {p['industry_name']} 중소기업, 업력 {p['age_years']}년"]
    if p["youth_added"]:
        parts.append("청년을 신규 채용하려는 상황")
    elif p["employees_added"]:
        parts.append("직원을 늘리는 상황")
    if p["rnd_curr"]:
        parts.append("기술개발과 연구개발에 투자하는 기업")
    return ". ".join(parts)


def match(profile: dict, announcements: list[dict], embedder=None, top_n: int = 5, today: date | None = None,
          index_path=None) -> dict:
    """반환: {items:[MatchResult...], excluded:{사유:건수}, scored:int, semantic_used:bool}"""
    today = today or date.today()
    candidates, excluded = [], {}
    for a in announcements:
        ok, reason, flags = check(a, profile, today)
        if ok:
            candidates.append((a, flags))
        else:
            excluded[reason] = excluded.get(reason, 0) + 1
    groups = profile_keyword_groups(profile)
    kw = {a["id"]: keyword_score(a, groups) for a, _ in candidates}

    sem = {}
    if embedder is not None and candidates:
        vecs = load_or_build_index([a for a, _ in candidates], embedder, index_path)
        q = embedder.embed([query_text(profile)])[0]
        raw = {i: float(np.dot(v, q)) for i, v in vecs.items()}
        lo, hi = min(raw.values()), max(raw.values())
        sem = {i: (s - lo) / (hi - lo) if hi > lo else 0.5 for i, s in raw.items()}   # 후보 안에서 0~1로 맞춤

    items = []
    for a, flags in candidates:
        ks, matched = kw[a["id"]]
        ss = sem.get(a["id"])
        score = 100 * (W_SEMANTIC * ss + W_KEYWORD * ks) if ss is not None else 100 * ks
        items.append({"id": a["id"], "title": a["title"], "agency": a["agency"], "period_end": a["end"], "d_day": d_day(a, today),
                      "region": ", ".join(a["regions"]), "target": a["target"], "url": a["url"], "contact": a["contact"],
                      "score": round(score, 1), "semantic": None if ss is None else round(ss, 2), "keyword": round(ks, 2),
                      "matched_keywords": matched, "flags": flags, "is_sample": a.get("is_sample", False), "source": a["source"]})
    items.sort(key=lambda r: (-r["score"], r["d_day"] if r["d_day"] is not None else 10**6))
    return {"items": items[:top_n], "excluded": excluded, "scored": len(items), "semantic_used": bool(sem)}
