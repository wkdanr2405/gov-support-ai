"""세액공제 항목 모듈 목록. 항목마다 evaluate 함수 하나로 '카드'(dict)를 돌려준다.

새 공제를 추가하려면: (1) data/tax_params/연도.yaml에 수치 (2) 이 파일에 evaluate 함수 (3) evaluate_all의 카드 목록에 한 줄. 중복 배제는 _resolve_overlaps에서 정한다.
카드 status: 'computed' 금액 계산됨 / 'not_applicable' 입력상 해당 없음 / 'planned' 아직 구현 전.
"""
from .disaster import disaster_credit
from .employment import employment_credit, headcount_increases
from .reductions import sme_special, startup_exemption
from .rnd import rnd_credit


def _employment(inp: dict, params: dict) -> dict:
    inc = headcount_increases(inp["employees_prev"], inp["employees_curr"], inp["youth_prev"], inp["youth_curr"])
    by_year = employment_credit(inp["region"], inc, params)
    ie = params["integrated_employment"]
    base = {"id": "integrated_employment", "name": "통합고용세액공제", "law_ref": ie["law_ref"], "verified": ie["verified"], "checked_at": ie.get("checked_at", ""), "evidence": ie.get("evidence", ""),
            "formula": "증가 인원 × 연차별 1인당 금액", "raw": {"increases": inc, "by_year": by_year}}
    if sum(by_year) == 0:
        return {**base, "status": "not_applicable", "basis": "상시근로자(청년 포함)가 늘지 않았습니다",
                "amount_by_year": by_year, "amount_first_year": 0}
    return {**base, "status": "computed", "basis": f"청년등 {inc['youth']}명, 청년 외 {inc['other']}명 증가",
            "amount_by_year": by_year, "amount_first_year": by_year[0]}


def _rnd(inp: dict, params: dict) -> dict:
    r = rnd_credit(inp.get("rnd_curr", 0), inp.get("rnd_prev", 0), inp.get("rnd_prev4_avg"), params)
    rc = params["rnd_credit"]
    base = {"id": "rnd_credit", "name": "연구·인력개발비 세액공제", "law_ref": rc["law_ref"], "verified": rc["verified"], "checked_at": rc.get("checked_at", ""), "evidence": rc.get("evidence", ""),
            "formula": "당기분 25% 또는 증가분 50% 중 유리한 쪽", "raw": r}
    if r["method"] == "none":
        return {**base, "status": "not_applicable", "basis": r["increase_note"], "amount_first_year": 0}
    return {**base, "status": "computed", "basis": {"current": "당기분 방식 (당기 지출의 25%)", "increase": "증가분 방식 (증가액의 50%)"}[r["method"]], "amount_first_year": r["amount"]}


def _disaster(inp: dict, params: dict) -> dict:
    r = disaster_credit(inp.get("disaster_lost_assets", 0), inp.get("disaster_total_assets", 0), inp.get("disaster_unpaid_tax", 0),
                        inp.get("disaster_current_tax", 0), inp.get("disaster_other_reductions", 0), params)
    d = params["disaster_loss"]
    base = {"id": "disaster_loss", "name": "재해손실세액공제", "law_ref": d["law_ref"], "verified": d["verified"], "checked_at": d.get("checked_at", ""), "evidence": d.get("evidence", ""),
            "formula": "(미납 법인세 + 해당연도 법인세) × 상실비율, 상실 자산가액 한도", "raw": r}
    if r["amount"] > 0:
        basis = f"재해상실비율 {r['ratio_pct']}%" + (" · 상실 자산가액 한도 적용" if r["cap_applied"] else "")
        return {**base, "status": "computed", "basis": basis, "amount_first_year": r["amount"]}
    return {**base, "status": "not_applicable", "basis": r["note"], "amount_first_year": 0}


def _reduction_card(cid: str, name: str, key: str, r: dict, params: dict, formula: str) -> dict:
    d = params[key]
    base = {"id": cid, "name": name, "law_ref": d["law_ref"], "verified": d["verified"], "checked_at": d.get("checked_at", ""), "evidence": d.get("evidence", ""), "formula": formula, "raw": r}
    if r["amount"] > 0:
        size = f"{r['size']} · " if r.get("size") else ""
        basis = f"{size}감면율 {r['rate_pct']}%" + (" · 한도 적용" if r["cap_applied"] else "")
        return {**base, "status": "computed", "basis": basis, "amount_first_year": r["amount"]}
    return {**base, "status": "not_applicable", "basis": r["note"], "amount_first_year": 0}


def _startup(inp: dict, params: dict, tax_year: int = 2026) -> dict:
    return _reduction_card("startup_sme_exemption", "창업중소기업 세액감면", "startup_exemption",
                           startup_exemption(inp, params, tax_year), params, "산출세액 × 감면소득 비율 × 감면율, 연 5억 원 한도")


def _sme_special(inp: dict, params: dict, tax_year: int = 2026) -> dict:
    return _reduction_card("sme_special_reduction", "중소기업 특별세액감면", "sme_special",
                           sme_special(inp, params), params, "산출세액 × 감면소득 비율 × 감면율, 연 1억 원 한도(감소 인원 차감)")


def _resolve_overlaps(cards: list[dict]) -> str:
    """중복 적용 배제(제127조). 합계에 넣을 카드를 정한다. 반환: 선택 결과 설명(없으면 빈 문자열)."""
    by = {c["id"]: c for c in cards}
    for c in cards:
        c["in_total"], c["excluded_reason"] = c["status"] == "computed", ""
    emp, sp, su = by["integrated_employment"], by["sme_special_reduction"], by["startup_sme_exemption"]
    # 선택지 A: 통합고용 + 특별감면 / 선택지 B: 창업감면(통합고용·특별감면 제외). 같은 연도 첫해 금액이 큰 쪽.
    a = emp["amount_first_year"] + sp["amount_first_year"]
    b = su["amount_first_year"]
    if su["status"] != "computed":
        return ""      # 창업감면이 없으면 통합고용·특별감면은 함께 받을 수 있다
    if b > a:
        for c, why in ((emp, "창업중소기업 세액감면을 선택해 통합고용세액공제는 함께 받을 수 없습니다 (제127조)"),
                       (sp, "창업감면과 특별감면은 하나만 선택합니다 (제127조)")):
            if c["status"] == "computed":
                c["in_total"], c["excluded_reason"] = False, why
        return f"중복 적용 배제: 창업감면({b*10000:,}원)이 통합고용+특별감면({a*10000:,}원)보다 커서 창업감면을 선택한 것으로 계산했습니다."
    su["in_total"], su["excluded_reason"] = False, "특별감면과 통합고용 조합이 더 유리해 이쪽은 선택하지 않은 것으로 계산했습니다 (제127조)"
    return f"중복 적용 배제: 통합고용+특별감면({a*10000:,}원)이 창업감면({b*10000:,}원) 이상이라 이 조합을 선택한 것으로 계산했습니다."


def evaluate_all(inp: dict, params: dict, tax_year: int = 2026) -> tuple[list[dict], str]:
    cards = [_employment(inp, params), _rnd(inp, params), _disaster(inp, params), _startup(inp, params, tax_year), _sme_special(inp, params, tax_year)]
    return cards, _resolve_overlaps(cards)
