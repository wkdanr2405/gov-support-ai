from src.tax_engine import calculate

BASE = {"region": "capital", "employees_prev": 10, "employees_curr": 13, "youth_prev": 2, "youth_curr": 4, "rnd_curr": 20000}


def test_cards_cover_all_credits_in_order():
    cards = calculate(BASE)["credits"]
    assert [c["id"] for c in cards] == ["integrated_employment", "rnd_credit", "disaster_loss", "startup_sme_exemption", "sme_special_reduction"]


def test_card_amounts_match_legacy_totals():
    r = calculate(BASE)
    by_id = {c["id"]: c for c in r["credits"]}
    assert by_id["integrated_employment"]["amount_first_year"] == r["employment_by_year"][0]
    assert by_id["rnd_credit"]["amount_first_year"] == r["rnd_credit"]
    assert r["total_first_year"] == 6800


def test_not_applicable_when_inputs_are_zero():
    r = calculate({**BASE, "employees_curr": 10, "youth_curr": 2, "rnd_curr": 0})
    by_id = {c["id"]: c for c in r["credits"]}
    assert by_id["integrated_employment"]["status"] == "not_applicable"
    assert by_id["rnd_credit"]["status"] == "not_applicable"
    assert r["total_first_year"] == 0


def test_planned_card_has_no_amount_and_is_unverified():
    c = calculate(BASE)["credits"][3]
    assert c["status"] == "planned" and c["amount_first_year"] is None and c["verified"] is False
