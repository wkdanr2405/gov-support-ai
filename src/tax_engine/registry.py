"""세액공제 항목 모듈 목록. 항목마다 evaluate 함수 하나로 '카드'(dict)를 돌려준다.

새 공제를 추가하려면: (1) data/tax_params/연도.yaml에 수치 (2) 이 파일에 evaluate 함수 (3) CREDITS에 한 줄.
카드 status: 'computed' 금액 계산됨 / 'not_applicable' 입력상 해당 없음 / 'planned' 아직 구현 전.
"""
from .disaster import disaster_credit
from .employment import employment_credit, headcount_increases
from .rnd import rnd_credit


def _employment(inp: dict, params: dict) -> dict:
    inc = headcount_increases(inp["employees_prev"], inp["employees_curr"], inp["youth_prev"], inp["youth_curr"])
    by_year = employment_credit(inp["region"], inc, params)
    ie = params["integrated_employment"]
    base = {"id": "integrated_employment", "name": "통합고용세액공제", "law_ref": ie["law_ref"], "verified": ie["verified"],
            "formula": "증가 인원 × 연차별 1인당 금액", "raw": {"increases": inc, "by_year": by_year}}
    if sum(by_year) == 0:
        return {**base, "status": "not_applicable", "basis": "상시근로자(청년 포함)가 늘지 않았습니다",
                "amount_by_year": by_year, "amount_first_year": 0}
    return {**base, "status": "computed", "basis": f"청년등 {inc['youth']}명, 청년 외 {inc['other']}명 증가",
            "amount_by_year": by_year, "amount_first_year": by_year[0]}


def _rnd(inp: dict, params: dict) -> dict:
    r = rnd_credit(inp.get("rnd_curr", 0), inp.get("rnd_prev", 0), inp.get("rnd_prev4_avg"), params)
    rc = params["rnd_credit"]
    base = {"id": "rnd_credit", "name": "연구·인력개발비 세액공제", "law_ref": rc["law_ref"], "verified": rc["verified"],
            "formula": "당기분 25% 또는 증가분 50% 중 유리한 쪽", "raw": r}
    if r["method"] == "none":
        return {**base, "status": "not_applicable", "basis": r["increase_note"], "amount_first_year": 0}
    return {**base, "status": "computed", "basis": {"current": "당기분 방식 (당기 지출의 25%)", "increase": "증가분 방식 (증가액의 50%)"}[r["method"]], "amount_first_year": r["amount"]}


def _disaster(inp: dict, params: dict) -> dict:
    r = disaster_credit(inp.get("disaster_lost_assets", 0), inp.get("disaster_total_assets", 0), inp.get("disaster_unpaid_tax", 0),
                        inp.get("disaster_current_tax", 0), inp.get("disaster_other_reductions", 0), params)
    d = params["disaster_loss"]
    base = {"id": "disaster_loss", "name": "재해손실세액공제", "law_ref": d["law_ref"], "verified": d["verified"],
            "formula": "(미납 법인세 + 해당연도 법인세) × 상실비율, 상실 자산가액 한도", "raw": r}
    if r["amount"] > 0:
        basis = f"재해상실비율 {r['ratio_pct']}%" + (" · 상실 자산가액 한도 적용" if r["cap_applied"] else "")
        return {**base, "status": "computed", "basis": basis, "amount_first_year": r["amount"]}
    return {**base, "status": "not_applicable", "basis": r["note"], "amount_first_year": 0}


def _planned(credit_id: str):
    def evaluate(inp: dict, params: dict) -> dict:
        p = params["planned_credits"][credit_id]
        return {"id": credit_id, "name": p["name"], "status": "planned", "basis": p["note"], "formula": "",
                "law_ref": p["law_ref"], "verified": False, "amount_first_year": None}
    return evaluate


CREDITS = [_employment, _rnd, _disaster, _planned("startup_sme_exemption"), _planned("sme_special_reduction")]


def evaluate_all(inp: dict, params: dict) -> list[dict]:
    return [f(inp, params) for f in CREDITS]
