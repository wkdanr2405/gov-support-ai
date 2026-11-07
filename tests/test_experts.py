from src.experts import DISCLAIMER, build_brief, load_experts, rank_experts, receipt_no
from src.report.explain import FORBIDDEN

RES = {"total_first_year": 6800, "overlap_note": "",
       "credits": [{"id": "integrated_employment", "name": "통합고용세액공제", "status": "computed", "in_total": True, "amount_first_year": 1800},
                   {"id": "rnd_credit", "name": "연구·인력개발비 세액공제", "status": "computed", "in_total": True, "amount_first_year": 5000},
                   {"id": "disaster_loss", "name": "재해손실세액공제", "status": "not_applicable", "in_total": True, "amount_first_year": 0}]}
CO = dict(industry="전자부품 제조업", sido="서울", founded="2023-03-15", is_sme=True, ep=10, ec=13, yp=0, yc=2)


def test_experts_are_marked_virtual_and_have_fields():
    ex = load_experts()
    assert len(ex) == 3
    for e in ex:
        assert e["name"].startswith("가상") and e["firm"].startswith("가상") and e["specialties"] and e["channels"]


def test_rank_puts_overlapping_specialty_first():
    r = rank_experts(load_experts(), ["rnd_credit", "integrated_employment"])
    assert r[0]["id"] == "demo-a" and r[0]["score"] == 2 and "연구·인력개발비 공제" in r[0]["reasons"]
    r2 = rank_experts(load_experts(), ["startup_sme_exemption", "disaster_loss"], want_gov_support=False)
    assert r2[0]["id"] == "demo-b"


def test_brief_uses_engine_amounts_in_won_and_disclaimer():
    b = build_brief("가상 기업 기준 예시", CO, RES, [], [{"title": "기술개발 지원사업"}], topic="둘 다", memo="일정 문의")
    assert "68,000,000원" in b and "18,000,000원" in b and "50,000,000원" in b
    assert "재해손실" not in b                      # 합계에 들어갔어도 금액이 계산되지 않은 항목은 제외
    assert DISCLAIMER in b and "기술개발 지원사업" in b and "일정 문의" in b
    assert not [w for w in FORBIDDEN if w in b]


def test_receipt_no_is_stable_and_demo_labeled():
    assert receipt_no("a") == receipt_no("a") != receipt_no("b") and receipt_no("a").startswith("DEMO-")
