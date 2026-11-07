"""법인세 감면: 창업중소기업 세액감면(조세특례제한법 제6조), 중소기업 특별세액감면(제7조). 금액 단위: 만원.

감면세액 = 법인세 산출세액 × 감면대상 소득 비율 × 감면율, 한도 적용, 만원 미만 절사.
입력(inp): corp_tax(산출세액), eligible_income_pct(감면대상 소득 비율 %, 기본 100), is_sme, ksic, avg_revenue_eok, region('capital'|'non_capital'),
          founded(ISO 날짜), first_income_year, startup_area('overcrowded'|'capital_other'|'pop_decline'|'non_capital'), youth_ceo,
          employees_prev/employees_curr(상시근로자 감소 인원 계산)
"""
from datetime import date
from decimal import ROUND_DOWN, Decimal


def _result(amount=0, applicable=False, rate_pct=None, cap_applied=False, note=""):
    return {"amount": amount, "applicable": applicable, "rate_pct": rate_pct, "cap_applied": cap_applied, "note": note}


def _reduce(corp_tax, pct, rate_pct, cap) -> tuple[int, bool]:
    raw = Decimal(str(corp_tax)) * Decimal(str(pct)) / 100 * Decimal(str(rate_pct)) / 100
    capped = raw > cap
    return int(min(raw, Decimal(str(cap))).to_integral_value(rounding=ROUND_DOWN)), capped


def _common_block(inp: dict, ksic_ok: bool):
    """공통으로 걸러지는 경우. 해당하면 (_result)를, 아니면 None."""
    if not inp.get("is_sme", False):
        return _result(note="중소기업에 해당하지 않아 적용하지 않습니다")
    if not ksic_ok:
        return _result(note="감면 대상 업종이 아니거나 업종 요건을 확인하지 못했습니다")
    corp_tax = inp.get("corp_tax", 0)
    if isinstance(corp_tax, bool) or not isinstance(corp_tax, (int, float)) or corp_tax < 0:
        raise ValueError(f"corp_tax는 0 이상의 숫자여야 합니다: {corp_tax!r}")
    if corp_tax == 0:
        return _result(note="법인세 산출세액이 입력되지 않았습니다")
    pct = inp.get("eligible_income_pct", 100)
    if isinstance(pct, bool) or not isinstance(pct, (int, float)) or not 0 <= pct <= 100:
        raise ValueError(f"eligible_income_pct는 0~100 사이여야 합니다: {pct!r}")
    return None


def startup_exemption(inp: dict, params: dict, tax_year: int = 2026) -> dict:
    p = params["startup_exemption"]
    blocked = _common_block(inp, inp.get("ksic") in p["eligible_ksic"])
    if blocked:
        return blocked
    founded = inp.get("founded")
    if not founded:
        return _result(note="설립일이 입력되지 않았습니다")
    founded_d = date.fromisoformat(founded) if isinstance(founded, str) else founded
    if founded_d > date.fromisoformat(p["founded_until"]):
        return _result(note="2027-12-31 이전에 창업한 기업만 대상입니다")
    first = inp.get("first_income_year")
    if first is None:
        return _result(note="최초 소득 발생 연도가 입력되지 않았습니다")
    if not first <= tax_year <= first + p["period_years"] - 1:
        return _result(note=f"감면 기간({first}~{first + p['period_years'] - 1}년)이 아닙니다")
    table = p["rates_pct"]["until_2025_12_31" if founded_d < date(2026, 1, 1) else "from_2026_01_01"]
    rate = table["youth" if inp.get("youth_ceo") else "general"][inp.get("startup_area", "overcrowded")]
    if rate == 0:
        return _result(note="이 지역·유형의 창업 기업은 감면율이 없습니다 (과밀억제권역 일반 창업)")
    amount, capped = _reduce(inp["corp_tax"], inp.get("eligible_income_pct", 100), rate, p["cap_man_won"])
    return _result(amount, amount > 0, rate, capped, "" if amount > 0 else "감면 대상 세액이 없습니다")


def sme_special(inp: dict, params: dict) -> dict:
    p = params["sme_special"]
    blocked = _common_block(inp, inp.get("ksic") in p["eligible_ksic"])
    if blocked:
        return blocked
    code, rev = inp["ksic"], inp.get("avg_revenue_eok", 0)
    limit = p["small_enterprise_limit_eok"].get(code)
    if limit is None:
        return _result(note="이 업종의 소기업 매출액 기준표를 확인하지 못해 소기업·중기업을 나누지 못했습니다 (계산하지 않음)")
    size = "small" if rev <= limit else "medium"
    kind = "wholesale_retail" if code in p["wholesale_retail_ksic"] else "other"
    area = "capital" if inp.get("region") == "capital" else "non_capital"
    rate = p["rates_pct"][size][kind][area]
    if rate == 0:
        return _result(note="수도권 안의 중기업은 감면 대상이 아닙니다")
    decrease = max(inp.get("employees_prev", 0) - inp.get("employees_curr", 0), 0)
    cap = max(p["cap_man_won"] - decrease * p["cap_deduct_per_decrease"], 0)
    amount, capped = _reduce(inp["corp_tax"], inp.get("eligible_income_pct", 100), rate, cap)
    note = "" if amount > 0 else "한도(상시근로자 감소 차감 후)가 0이거나 감면 대상 세액이 없습니다"
    r = _result(amount, amount > 0, rate, capped, note)
    r["size"] = "소기업" if size == "small" else "중기업"
    return r
