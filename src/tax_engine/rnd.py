"""연구·인력개발비 세액공제 (조세특례제한법 제10조 제1항 제3호, 중소기업 일반 연구·인력개발비). 금액 단위: 만원."""
from decimal import ROUND_DOWN, Decimal

from .params import load_params


def _won(amount: Decimal) -> int:
    return int(amount.to_integral_value(rounding=ROUND_DOWN))  # 만원 미만 절사


def rnd_credit(rnd_curr: int, rnd_prev: int = 0, rnd_prev4_avg: int | None = None, params: dict | None = None) -> dict:
    """당기분(25%)과 증가분(50%) 중 유리한 방식을 고른다.

    증가분 방식은 직전 4년간 발생이 있고 직전 과세연도 발생액이 직전 4년 연평균 이상일 때만 가능하다.
    rnd_prev4_avg를 모르면(None) 증가분 방식을 검토할 수 없어 당기분만 계산한다.
    """
    for name, v in (("rnd_curr", rnd_curr), ("rnd_prev", rnd_prev)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
            raise ValueError(f"{name}은(는) 0 이상의 숫자여야 합니다: {v!r}")
    if rnd_prev4_avg is not None and (not isinstance(rnd_prev4_avg, (int, float)) or rnd_prev4_avg < 0):
        raise ValueError(f"rnd_prev4_avg는 0 이상의 숫자여야 합니다: {rnd_prev4_avg!r}")
    params = params or load_params()
    rate = params["rnd_credit"]["general_rnd"]["sme"]
    cur_rate, inc_rate = Decimal(str(rate["current_rate"])), Decimal(str(rate["increase_rate"]))

    if rnd_curr == 0:
        return {"amount": 0, "method": "none", "current": 0, "increase": None, "increase_note": "연구·인력개발비 지출이 없습니다"}

    current = _won(Decimal(str(rnd_curr)) * cur_rate)
    if rnd_prev4_avg is None:
        note = "직전 4년 연평균 발생액이 없어 증가분 방식은 검토하지 않았습니다"
        increase = None
    elif rnd_prev4_avg == 0 or rnd_prev == 0:
        note = "직전 4년간 또는 직전 과세연도에 발생액이 없어 당기분 방식만 적용됩니다"
        increase = None
    elif rnd_prev < rnd_prev4_avg:
        note = "직전 과세연도 발생액이 직전 4년 연평균보다 적어 당기분 방식만 적용됩니다"
        increase = None
    else:
        note = ""
        diff = max(Decimal(str(rnd_curr)) - Decimal(str(rnd_prev)), Decimal(0))
        increase = _won(diff * inc_rate)

    if increase is not None and increase > current:
        return {"amount": increase, "method": "increase", "current": current, "increase": increase, "increase_note": note}
    return {"amount": current, "method": "current", "current": current, "increase": increase, "increase_note": note}
