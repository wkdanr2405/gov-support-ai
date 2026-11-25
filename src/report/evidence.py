"""계산·추천 근거 정리. PDF 부록과 화면 미리보기가 같은 내용을 쓰도록 한 곳에서 만든다.
금액은 규칙 엔진 결과(만원)를 원으로만 바꿔 옮기고, 새 숫자를 만들지 않는다."""
from src.data_sources.status import source_label
from src.money import man_to_won


def _status(verified: bool, checked_at: str) -> str:
    d = f" ({checked_at})" if checked_at else ""
    return ("조문 확인" if verified else "일부 미확인") + d


def tax_rows(res: dict, sme: dict | None, params: dict) -> list[dict]:
    rows = []
    if sme is not None:
        t = params["sme_test"]
        checks = " / ".join(f"{c['name']} {'충족' if c['passed'] else '불충족'}" for c in sme["checks"])
        rows.append({"name": "중소기업 해당 여부", "law_ref": t["law_ref"], "formula": "업종별 평균매출액 기준·자산총액·독립성",
                     "result": ("해당" if sme["is_sme"] else "해당하지 않음") + f" · {checks}", "status": _status(t["verified"], t.get("checked_at", ""))})
    for c in res.get("credits", []):
        if c["status"] == "computed":
            result = f"{man_to_won(c['amount_first_year']):,}원 (첫해) · {c['basis']}"
            if not c.get("in_total", True):
                result += f" · 합계 제외: {c['excluded_reason']}"
        else:
            result = f"해당 없음 · {c['basis']}"
        rows.append({"name": c["name"], "law_ref": c["law_ref"], "formula": c["formula"], "result": result,
                     "status": _status(c["verified"], c.get("checked_at", ""))})
    if res.get("overlap_note"):
        o = params["overlap"]
        rows.append({"name": "중복 적용 배제", "law_ref": o["law_ref"], "formula": "창업감면 vs (통합고용+특별감면) 중 첫해 금액이 큰 쪽",
                     "result": res["overlap_note"], "status": _status(o["verified"], o.get("checked_at", ""))})
    return rows


def match_rows(matches: list[dict], limit: int = 3) -> list[dict]:
    rows = []
    for m in matches[:limit]:
        parts = [f"키워드 {m.get('keyword', '-')}"]
        parts.append(f"의미 {m['semantic']}" if m.get("semantic") is not None else "의미 점수 미사용")
        kws = ", ".join(m.get("matched_keywords", [])[:4]) or "없음"
        why = f"일치 키워드: {kws} · 점수 {' / '.join(parts)} → 종합 {m.get('score', '-')}점(상대값)"
        rows.append({"title": m["title"], "agency": m.get("agency", ""), "id": m.get("id", ""),
                     "source_label": source_label(m.get("source", "")),
                     "deadline": "상시/확인 필요" if m.get("d_day") is None else f"D-{m['d_day']} ({m.get('period_end')})",
                     "url": m.get("url", ""), "why": why, "flags": list(m.get("flags", []))})
    return rows


def build_evidence(res: dict, sme: dict | None, params: dict, matches: list[dict], data_status: list[dict],
                   excluded: dict, scored: int, input_rows: list[list[str]]) -> dict:
    return {"tax_rows": tax_rows(res, sme, params), "match_rows": match_rows(matches), "data_status": data_status,
            "excluded": excluded, "scored": scored, "input_rows": input_rows}
