"""Track A 규칙 엔진. 세액·금액은 이 모듈(코드)만 계산하고 LLM은 숫자를 만들거나 바꾸지 않는다."""
from .employment import employment_credit, headcount_increases
from .params import load_params
from .rnd import rnd_credit
from .sme import industry_list, judge_sme

__all__ = ["calculate", "scenario", "judge_sme", "industry_list", "load_params"]

DISCLAIMER = "참고용 예상치이며 최종 판단은 세무 전문가가 합니다."


def calculate(inp: dict, year: int = 2026) -> dict:
    """입력 dict → 계산 결과 dict. 금액 단위 만원.

    inp: region('capital'|'non_capital'), employees_prev/curr, youth_prev/curr,
         rnd_curr, rnd_prev(선택), rnd_prev4_avg(선택)
    """
    params = load_params(year)
    inc = headcount_increases(inp["employees_prev"], inp["employees_curr"], inp["youth_prev"], inp["youth_curr"])
    by_year = employment_credit(inp["region"], inc, params)
    rnd = rnd_credit(inp.get("rnd_curr", 0), inp.get("rnd_prev", 0), inp.get("rnd_prev4_avg"), params)
    ie, rc = params["integrated_employment"], params["rnd_credit"]
    items = [
        {"name": "통합고용세액공제", "basis": f"청년등 {inc['youth']}명, 청년 외 {inc['other']}명 증가",
         "formula": "증가 인원 × 연차별 1인당 금액", "amount_by_year": by_year,
         "law_ref": ie["law_ref"], "verified": ie["verified"]},
        {"name": "연구·인력개발비 세액공제", "basis": f"{rnd['method']} 방식", "formula": "당기분 25% 또는 증가분 50% 중 유리한 쪽",
         "amount": rnd["amount"], "law_ref": rc["law_ref"], "verified": rc["verified"]},
    ]
    notes = [
        "증가한 상시근로자가 3년간 유지된다고 가정합니다.",
        "최저한세와 다른 공제와의 중복 적용 배제는 반영하지 않았습니다.",
        "만원 미만은 절사했습니다.",
        DISCLAIMER,
    ]
    if rnd["increase_note"]:
        notes.append(rnd["increase_note"])
    return {
        "increases": inc,
        "employment_by_year": by_year,
        "rnd_credit": rnd["amount"],
        "rnd_method": rnd["method"],
        "rnd_options": {"current": rnd["current"], "increase": rnd["increase"]},
        "total_first_year": by_year[0] + rnd["amount"],
        "total_employment_3y": sum(by_year),
        "items": items,
        "notes": notes,
        "tax_year": year,
    }


def scenario(inp: dict, extra_youth_range=range(0, 4), year: int = 2026) -> list[dict]:
    """청년을 더 채용했을 때(전체·청년 근로자가 함께 늘어남) 통합고용 공제액 변화."""
    out = []
    for k in extra_youth_range:
        s = dict(inp, employees_curr=inp["employees_curr"] + k, youth_curr=inp["youth_curr"] + k)
        r = calculate(s, year)
        out.append({"extra_youth": k, "employment_by_year": r["employment_by_year"],
                    "first_year": r["employment_by_year"][0], "total_3y": r["total_employment_3y"]})
    return out
