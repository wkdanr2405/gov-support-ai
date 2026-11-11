"""창업중소기업 세액감면(조특법 제6조)·중소기업 특별세액감면(제7조)·중복 배제 정답 사례. 금액 단위 만원.
손계산 값이며 엔진 코드와 독립적이다.

감면세액 = 법인세 산출세액 × 감면대상 소득 비율 × 감면율, 한도 적용, 만원 미만 절사.
제6조 감면율(창업일 2025-12-31 이전): 과밀억제권역 밖 청년 100% / 일반 50%, 과밀억제권역 안 청년 50% / 일반 없음.
제6조 감면율(2026-01-01 이후): 비수도권·인구감소지역 청년 100%·일반 50%, 수도권(과밀억제 제외) 청년 75%·일반 25%, 과밀억제권역 청년 50%·일반 없음.
제6조 한도 5억원, 감면기간 = 최초 소득 발생 연도부터 5개 과세연도.
제7조 감면율: 소기업 도소매·의료 10%, 그 밖 수도권 20% / 수도권 밖 30%, 중기업 수도권 밖 도소매 5% / 그 밖 15%, 수도권 중기업 없음.
제7조 한도 1억원 - 상시근로자 감소 1명당 500만원(0 미만이면 0).
중복: 제6조와 제7조는 택일, 제6조를 받으면 통합고용공제 불가(제127조), 연구·인력개발비·재해손실은 모두와 함께 가능.
"""
import pytest

from src.tax_engine import calculate

BASE = {"region": "non_capital", "employees_prev": 10, "employees_curr": 13, "youth_prev": 2, "youth_curr": 4, "rnd_curr": 20000,
        "ksic": "C26", "avg_revenue_eok": 30, "is_sme": True, "corp_tax": 4000, "eligible_income_pct": 100,
        "founded": "2023-03-15", "first_income_year": 2023, "startup_area": "non_capital", "youth_ceo": True}


def card(cid, **over):
    r = calculate({**BASE, **over})
    return {c["id"]: c for c in r["credits"]}[cid]


def su(**o):
    return card("startup_sme_exemption", **o)


def sp(**o):
    return card("sme_special_reduction", **o)


# ---- 제6조 창업중소기업 세액감면 ----
@pytest.mark.parametrize("over,amount", [
    (dict(startup_area="overcrowded", youth_ceo=True), 2000),                                   # 2023 창업, 과밀억제권역 청년 50% × 4000
    (dict(founded="2024-05-01", youth_ceo=False, corp_tax=10000, first_income_year=2024), 5000),  # 2025 이전, 비수도권 일반 50%
    (dict(founded="2024-05-01", startup_area="capital_other", youth_ceo=False, corp_tax=10000, first_income_year=2024), 5000),  # 과밀억제 밖 일반 50%
    (dict(founded="2026-03-01", startup_area="capital_other", youth_ceo=True, corp_tax=8000, first_income_year=2026), 6000),    # 2026 이후 수도권 청년 75%
    (dict(founded="2026-03-01", startup_area="capital_other", youth_ceo=False, corp_tax=8000, first_income_year=2026), 2000),   # 2026 이후 수도권 일반 25%
    (dict(founded="2026-03-01", startup_area="pop_decline", youth_ceo=False, corp_tax=1000, first_income_year=2026), 500),      # 인구감소지역 일반 50%
    (dict(founded="2026-03-01", startup_area="non_capital", youth_ceo=True, corp_tax=3000, first_income_year=2026), 3000),      # 비수도권 청년 100%
    (dict(corp_tax=5000, eligible_income_pct=60), 3000),                                         # 2023 창업 비수도권 청년 100% × 소득비율 60%
])
def test_startup_amounts(over, amount):
    c = su(**over)
    assert c["status"] == "computed" and c["amount_first_year"] == amount


def test_startup_capped_at_5eok():
    c = su(founded="2026-03-01", startup_area="non_capital", youth_ceo=True, corp_tax=70000, first_income_year=2026)
    assert c["amount_first_year"] == 50000 and c["raw"]["cap_applied"] is True


@pytest.mark.parametrize("over", [
    dict(founded="2026-03-01", startup_area="overcrowded", youth_ceo=False, first_income_year=2026),   # 과밀억제권역 일반 창업 없음
    dict(founded="2024-05-01", startup_area="overcrowded", youth_ceo=False, first_income_year=2024),
    dict(first_income_year=2020),                 # 감면기간(2020~2024) 지남
    dict(first_income_year=2021),                 # 2021~2025 지남
    dict(founded="2028-01-01", first_income_year=2028),   # 2027-12-31 이후 창업
    dict(ksic="K"),                                # 대상 업종 아님
    dict(is_sme=False),
    dict(corp_tax=0),
])
def test_startup_not_applicable(over):
    c = su(**over)
    assert c["status"] == "not_applicable" and c["amount_first_year"] == 0


def test_startup_last_year_of_period():
    assert su(first_income_year=2022)["status"] == "computed"      # 2022~2026 → 2026 마지막 해


# ---- 제7조 중소기업 특별세액감면 ----
@pytest.mark.parametrize("over,amount", [
    (dict(), 1200),                                                      # 소기업 수도권 밖 제조 30% × 4000
    (dict(region="capital"), 800),                                       # 소기업 수도권 제조 20%
    (dict(region="capital", ksic="G", avg_revenue_eok=20, corp_tax=5000), 500),   # 소기업 도소매 10%
    (dict(ksic="C26", avg_revenue_eok=300, corp_tax=20000), 3000),       # 중기업 수도권 밖 15%
    (dict(ksic="G", avg_revenue_eok=100, corp_tax=20000), 1000),         # 중기업 수도권 밖 도소매 5%
    (dict(corp_tax=50000), 10000),                                       # 15,000 → 한도 1억
    (dict(corp_tax=50000, employees_prev=16, employees_curr=13, youth_prev=2, youth_curr=2), 8500),  # 3명 감소 → 한도 8,500
])
def test_sme_special_amounts(over, amount):
    c = sp(**over)
    assert c["status"] == "computed" and c["amount_first_year"] == amount


def test_sme_special_cap_flag_and_decrease_to_zero():
    assert sp(corp_tax=50000)["raw"]["cap_applied"] is True
    c = sp(corp_tax=50000, employees_prev=40, employees_curr=20, youth_prev=2, youth_curr=2)   # 20명 감소 → 한도 0
    assert c["status"] == "not_applicable" and c["amount_first_year"] == 0


@pytest.mark.parametrize("over", [
    dict(region="capital", avg_revenue_eok=300),    # 수도권 중기업 제외
    dict(is_sme=False),
    dict(ksic="K"),                                  # 대상 업종 아님
    dict(ksic="C29"),                                # 소기업 기준표 미확인 업종 → 계산하지 않음
    dict(corp_tax=0),
])
def test_sme_special_not_applicable(over):
    c = sp(**over)
    assert c["status"] == "not_applicable" and c["amount_first_year"] == 0


# ---- 중복 배제와 합계 ----
def totals(**o):
    r = calculate({**BASE, **o})
    return r["total_first_year"], {c["id"]: c for c in r["credits"]}


def test_overlap_employment_plus_special_beats_startup():
    # 통합고용 1,800 + 특별감면 800 = 2,600 > 창업감면 2,000. R&D 5,000은 항상 포함.
    total, cs = totals(region="capital", startup_area="overcrowded", youth_ceo=True)
    assert total == 5000 + 2600
    assert cs["startup_sme_exemption"]["in_total"] is False and cs["startup_sme_exemption"]["excluded_reason"]
    assert cs["integrated_employment"]["in_total"] and cs["sme_special_reduction"]["in_total"] and cs["rnd_credit"]["in_total"]


def test_overlap_startup_beats_employment_plus_special():
    # 비수도권: 통합고용 2,700 + 특별감면 1,200 = 3,900 < 창업감면 4,000(청년 100%). 창업감면 선택 시 통합고용·특별감면 제외.
    total, cs = totals()
    assert total == 5000 + 4000
    assert cs["startup_sme_exemption"]["in_total"] is True
    assert cs["integrated_employment"]["in_total"] is False and cs["sme_special_reduction"]["in_total"] is False


def test_disaster_and_rnd_always_included():
    total, cs = totals(disaster_lost_assets=210000, disaster_total_assets=350000, disaster_unpaid_tax=50000,
                       disaster_current_tax=10000, disaster_other_reductions=5000)
    assert total == 5000 + 4000 + 33000 and cs["disaster_loss"]["in_total"] is True


def test_no_reduction_inputs_keeps_old_total():
    r = calculate({"region": "capital", "employees_prev": 10, "employees_curr": 13, "youth_prev": 2, "youth_curr": 4, "rnd_curr": 20000})
    assert r["total_first_year"] == 6800


# ---- 2026-11-11 법 원문 대조로 정정 ----
def test_water_supply_is_startup_eligible_but_not_sme_special():
    """수도업(E36): 제6조 제3항 제3호에는 있으나 제7조 제1항 감면 업종에는 없다."""
    assert su(ksic="E36")["status"] == "computed" and su(ksic="E36")["amount_first_year"] == 4000
    assert sp(ksic="E36")["status"] == "not_applicable" and sp(ksic="E36")["amount_first_year"] == 0


def test_integrated_employment_amounts_match_statute_formula():
    """제29조의8 제1항 A+B+C 원문 계산식(손계산). 수도권 밖: 청년등 1,000/1,900/2,000만 원, 청년등 외 700/1,200/1,300만 원.
    청년등 2명·청년등 외 1명 증가가 3년 유지되면 1차 2,700 / 2차 5,000 / 3차 5,300만 원."""
    assert calculate(BASE)["employment_by_year"] == [2 * 1000 + 700, 2 * 1900 + 1200, 2 * 2000 + 1300]
