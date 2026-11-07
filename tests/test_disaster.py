"""재해손실세액공제(법인세법 제58조) 정답 사례. 금액 단위 만원. 손계산 값이며 엔진 코드와 독립적이다.

산식: 재해상실비율 = 상실 자산가액 ÷ 상실 전 총자산가액(토지 제외). 20% 이상일 때만 적용.
      공제액 = min( (재해일 현재 미부과·미납 법인세 + max(해당 사업연도 법인세 - 다른 법률 공제·감면, 0)) × 상실비율, 상실 자산가액 )
      만원 미만 절사.
사례 A는 국세청 보도참고자료(2025-03-31)의 계산 사례: 21억/35억=60%, (3억+2억 + (1억-0.5억)) × 60% = 3.3억.
"""
import pytest

from src.tax_engine import calculate
from src.tax_engine.disaster import disaster_credit
from src.tax_engine.params import load_params

P = load_params(2026)


def dc(lost, total, unpaid=0, current=0, red=0):
    return disaster_credit(lost, total, unpaid, current, red, P)


def test_case_a_nts_example():
    r = dc(210000, 350000, unpaid=50000, current=10000, red=5000)
    assert r["amount"] == 33000 and r["qualifies"] is True and r["ratio_pct"] == 60.0 and r["cap_applied"] is False


def test_case_b_exactly_20_percent_qualifies():
    assert dc(20000, 100000, unpaid=10000)["amount"] == 2000


def test_case_c_just_under_20_percent_not_applicable():
    r = dc(19900, 100000, unpaid=10000)
    assert r["qualifies"] is False and r["amount"] == 0


def test_case_d_capped_by_lost_assets():
    r = dc(1000, 2000, unpaid=5000, current=5000)
    assert r["amount"] == 1000 and r["cap_applied"] is True


def test_case_e_reductions_exceed_current_tax():
    r = dc(50000, 100000, unpaid=0, current=3000, red=5000)
    assert r["amount"] == 0


def test_case_f_floor_to_man_won():
    assert dc(1000, 3000, unpaid=1000)["amount"] == 333


def test_case_g_no_disaster():
    r = dc(0, 0)
    assert r["qualifies"] is False and r["amount"] == 0


@pytest.mark.parametrize("args", [(200, 100), (-1, 100), (10, 0), (10, 100, -5)])
def test_invalid_inputs_raise(args):
    with pytest.raises(ValueError):
        dc(*args)


BASE = {"region": "capital", "employees_prev": 10, "employees_curr": 13, "youth_prev": 2, "youth_curr": 4, "rnd_curr": 20000}


def test_calculate_without_disaster_inputs_keeps_totals():
    r = calculate(BASE)
    card = {c["id"]: c for c in r["credits"]}["disaster_loss"]
    assert card["status"] == "not_applicable" and r["total_first_year"] == 6800


def test_calculate_with_disaster_adds_to_first_year_total():
    r = calculate({**BASE, "disaster_lost_assets": 210000, "disaster_total_assets": 350000,
                   "disaster_unpaid_tax": 50000, "disaster_current_tax": 10000, "disaster_other_reductions": 5000})
    card = {c["id"]: c for c in r["credits"]}["disaster_loss"]
    assert card["status"] == "computed" and card["amount_first_year"] == 33000
    assert r["total_first_year"] == 6800 + 33000
    assert r["disaster_credit"] == 33000
