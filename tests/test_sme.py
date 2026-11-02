import pytest

from src.tax_engine import industry_list, judge_sme


def prof(**kw):
    base = dict(ksic="C26", avg_revenue_eok=900, assets_eok=300)
    base.update(kw)
    return base


def test_electronics_within_limit():
    r = judge_sme(prof())
    assert r["is_sme"] is True and r["limit_eok"] == 1000


def test_revenue_boundary_is_inclusive():
    assert judge_sme(prof(avg_revenue_eok=1000))["is_sme"] is True
    assert judge_sme(prof(avg_revenue_eok=1001))["is_sme"] is False


def test_assets_boundary_is_exclusive():
    assert judge_sme(prof(assets_eok=4999))["is_sme"] is True
    assert judge_sme(prof(assets_eok=5000))["is_sme"] is False


def test_owned_by_large_corp_fails_independence():
    r = judge_sme(prof(owned_by_large_corp=True))
    assert r["is_sme"] is False
    assert any(c["name"].startswith("독립성") and not c["passed"] for c in r["checks"])


def test_finance_limit_is_400():
    assert judge_sme(dict(ksic="K", avg_revenue_eok=400, assets_eok=100))["is_sme"] is True
    assert judge_sme(dict(ksic="K", avg_revenue_eok=401, assets_eok=100))["is_sme"] is False


def test_unverified_flags_are_reported():
    r = judge_sme(prof(consumer_service=True))
    assert r["is_sme"] is False
    assert any(c["verified"] is False for c in r["checks"])
    assert r["unverified"]


def test_unknown_code_and_bad_numbers():
    with pytest.raises(ValueError):
        judge_sme(prof(ksic="ZZZ"))
    with pytest.raises(ValueError):
        judge_sme(prof(avg_revenue_eok=-1))


def test_industry_list_has_all_manufacturing_codes():
    codes = {i["code"] for i in industry_list()}
    assert {f"C{n}" for n in range(10, 35)} <= codes
