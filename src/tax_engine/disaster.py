"""재해손실세액공제 (법인세법 제58조, 시행령 제95조). 금액 단위: 만원.

재해로 사업용 자산의 20% 이상을 잃은 법인에게, 아직 내지 않은 법인세와 재해가 난 사업연도 법인세 중
상실비율만큼을 공제한다. 공제액은 상실 자산가액을 넘지 못한다.
'납세가 곤란하다고 인정'되는지는 세무서장 판단이므로 코드가 판정하지 않고 화면에서 안내만 한다.
"""
from decimal import ROUND_DOWN, Decimal

from .params import load_params


def _num(name: str, v) -> Decimal:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
        raise ValueError(f"{name}은(는) 0 이상의 숫자여야 합니다: {v!r}")
    return Decimal(str(v))


def disaster_credit(lost_assets, total_assets, unpaid_tax=0, current_tax=0, other_reductions=0, params: dict | None = None) -> dict:
    """lost_assets 상실 자산가액, total_assets 상실 전 총자산가액(토지 제외),
    unpaid_tax 재해일 현재 미부과·미납 법인세(가산세 포함), current_tax 재해일이 속한 사업연도 법인세(산출세액+가산세),
    other_reductions 그 법인세에서 다른 법률로 받는 공제·감면세액."""
    lost, total = _num("lost_assets", lost_assets), _num("total_assets", total_assets)
    unpaid, cur, red = _num("unpaid_tax", unpaid_tax), _num("current_tax", current_tax), _num("other_reductions", other_reductions)
    if lost > total:
        raise ValueError("상실 자산가액이 상실 전 총자산가액보다 클 수 없습니다")
    if lost > 0 and total == 0:
        raise ValueError("상실 전 총자산가액이 0이면 상실비율을 계산할 수 없습니다")
    base = {"amount": 0, "qualifies": False, "ratio_pct": 0.0, "cap_applied": False, "note": ""}
    if lost == 0:
        return {**base, "note": "재해로 인한 자산 상실이 입력되지 않았습니다"}
    params = params or load_params()
    min_ratio = Decimal(str(params["disaster_loss"]["min_loss_ratio"]["value"]))
    ratio = lost / total
    pct = float((ratio * 100).quantize(Decimal("0.1"), rounding=ROUND_DOWN))
    if ratio < min_ratio:
        return {**base, "ratio_pct": pct, "note": f"상실비율 {pct}%로 20% 미만이라 요건에 해당하지 않습니다"}
    taxable = unpaid + max(cur - red, Decimal(0))
    raw = taxable * ratio
    capped = raw > lost
    amount = int(min(raw, lost).to_integral_value(rounding=ROUND_DOWN))
    note = "" if amount > 0 else "공제 대상이 되는 법인세가 없습니다"
    return {"amount": amount, "qualifies": True, "ratio_pct": pct, "cap_applied": capped, "note": note}
