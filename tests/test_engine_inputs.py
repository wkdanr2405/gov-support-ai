import pytest

from src.tax_engine import calculate, headcount_increases, scenario
from src.tax_engine.rnd import rnd_credit

DECK = dict(region="capital", employees_prev=10, employees_curr=13, youth_prev=0, youth_curr=2,
            rnd_curr=20000, rnd_prev=15000, rnd_prev4_avg=14000)


def test_bad_inputs_raise():
    with pytest.raises(ValueError):
        calculate(dict(DECK, region="seoul"))
    with pytest.raises(ValueError):
        calculate(dict(DECK, youth_curr=14))          # 청년이 전체보다 많음
    with pytest.raises(ValueError):
        calculate(dict(DECK, employees_prev=-1))
    with pytest.raises(ValueError):
        calculate(dict(DECK, employees_curr=13.5))


def test_headcount_cap():
    assert headcount_increases(10, 11, 0, 3) == {"total": 1, "youth": 1, "other": 0}


def test_scenario_is_monotonic_and_matches_calculate():
    rows = scenario(DECK)
    assert [r["extra_youth"] for r in rows] == [0, 1, 2, 3]
    firsts = [r["first_year"] for r in rows]
    assert firsts == sorted(firsts) and firsts[0] == calculate(DECK)["employment_by_year"][0]
    assert rows[1]["first_year"] - rows[0]["first_year"] == 700   # 청년 1명당 1차연도 단가


def test_result_has_disclaimer_and_verified_flags():
    r = calculate(DECK)
    assert any("최종 판단은 세무 전문가" in n for n in r["notes"])
    assert all(isinstance(i["verified"], bool) for i in r["items"])
    assert r["total_first_year"] == r["employment_by_year"][0] + r["rnd_credit"]


def test_rnd_rounds_down_to_manwon():
    assert rnd_credit(10001, 0, 0)["amount"] == 2500   # 2500.25 → 절사
