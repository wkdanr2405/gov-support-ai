"""통합고용세액공제 (조세특례제한법 제29조의8). 금액 단위: 만원."""
from .params import load_params

REGIONS = {"capital": "capital_area", "non_capital": "non_capital_area"}


def _check_int(name: str, value) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name}은(는) 0 이상의 정수여야 합니다: {value!r}")
    return value


def headcount_increases(employees_prev: int, employees_curr: int, youth_prev: int, youth_curr: int) -> dict:
    """증가 인원 계산. 청년등·청년등외 증가 인원은 각각 전체 증가 인원을 한도로 한다 (법 제29조의8 제1항 1·2호)."""
    ep, ec = _check_int("employees_prev", employees_prev), _check_int("employees_curr", employees_curr)
    yp, yc = _check_int("youth_prev", youth_prev), _check_int("youth_curr", youth_curr)
    if yp > ep or yc > ec:
        raise ValueError("청년 근로자 수가 전체 상시근로자 수보다 많을 수 없습니다")
    total = max(ec - ep, 0)
    youth = min(max(yc - yp, 0), total)
    other = min(max((ec - yc) - (ep - yp), 0), total)
    return {"total": total, "youth": youth, "other": other}


def employment_credit(region: str, increases: dict, params: dict | None = None) -> list[int]:
    """연차별(1·2·3차) 통합고용세액공제액 [만원]. 증가 인원이 3년간 유지된다고 가정."""
    if region not in REGIONS:
        raise ValueError(f"region은 'capital' 또는 'non_capital'이어야 합니다: {region!r}")
    params = params or load_params()
    table = params["integrated_employment"]["sme"][REGIONS[region]]
    return [
        increases["youth"] * table["youth_etc"][i] + increases["other"] * table["other"][i]
        for i in range(params["integrated_employment"]["years"])
    ]
