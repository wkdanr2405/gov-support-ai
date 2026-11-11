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


def test_consumer_service_and_large_group_exclude_sme_with_confirmed_basis():
    """조특령 제2조 제1항 제3·4호 원문 확인(11/11): 두 사유 모두 확정 근거로 중소기업 제외."""
    for flag, name in (("consumer_service", "소비성"), ("in_large_group", "공시대상기업집단")):
        r = judge_sme(prof(**{flag: True}))
        assert r["is_sme"] is False
        assert any(name in c["name"] and c["verified"] is True and not c["passed"] for c in r["checks"])
    assert judge_sme(prof())["is_sme"] is True


def test_remaining_unverified_items_are_reported():
    r = judge_sme(prof())
    assert r["unverified"]
    assert any("관계기업" in u for u in r["unverified"])


def test_unknown_code_and_bad_numbers():
    with pytest.raises(ValueError):
        judge_sme(prof(ksic="ZZZ"))
    with pytest.raises(ValueError):
        judge_sme(prof(avg_revenue_eok=-1))


def test_industry_list_has_all_manufacturing_codes():
    codes = {i["code"] for i in industry_list()}
    assert {f"C{n}" for n in range(10, 35)} <= codes
