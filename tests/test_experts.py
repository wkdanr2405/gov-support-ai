from src.experts import DISCLAIMER, build_brief, load_experts, rank_experts, receipt_no
from src.report.explain import FORBIDDEN

RES = {"total_first_year": 6800, "overlap_note": "",
       "credits": [{"id": "integrated_employment", "name": "통합고용세액공제", "status": "computed", "in_total": True, "amount_first_year": 1800},
                   {"id": "rnd_credit", "name": "연구·인력개발비 세액공제", "status": "computed", "in_total": True, "amount_first_year": 5000},
                   {"id": "disaster_loss", "name": "재해손실세액공제", "status": "not_applicable", "in_total": True, "amount_first_year": 0}]}
CO = dict(industry="전자부품 제조업", sido="서울", founded="2023-03-15", is_sme=True, ep=10, ec=13, yp=0, yc=2)


def test_experts_have_required_fields():
    ex = load_experts()
    assert len(ex) == 6 and len({e["id"] for e in ex}) == 6
    for e in ex:
        assert e["name"] and e["firm"] and e["license"] in ("세무사", "공인회계사") and e["specialties"] and e["channels"] and e["regions"] and e["intro"]


def test_rank_puts_overlapping_specialty_first():
    r = rank_experts(load_experts(), ["rnd_credit", "integrated_employment"])
    assert r[0]["id"] == "exp-1" and r[0]["score"] == 20 and "연구·인력개발비 공제" in r[0]["reasons"]
    r2 = rank_experts(load_experts(), ["startup_sme_exemption", "disaster_loss"], want_gov_support=False)
    assert r2[0]["id"] == "exp-2"


def test_brief_uses_engine_amounts_in_won_and_disclaimer():
    b = build_brief("가상 기업 기준 예시", CO, RES, [], [{"title": "기술개발 지원사업"}], topic="둘 다", memo="일정 문의")
    assert "68,000,000원" in b and "18,000,000원" in b and "50,000,000원" in b
    assert "재해손실" not in b                      # 합계에 들어갔어도 금액이 계산되지 않은 항목은 제외
    assert DISCLAIMER in b and "기술개발 지원사업" in b and "일정 문의" in b
    assert not [w for w in FORBIDDEN if w in b]


def test_receipt_no_is_stable_and_demo_labeled():
    assert receipt_no("a") == receipt_no("a") != receipt_no("b") and receipt_no("a").startswith("DEMO-")


def test_rank_uses_region_and_industry_as_tiebreakers():
    base = ["rnd_credit"]
    busan = rank_experts(load_experts(), base, want_gov_support=False, sido="부산", ksic="C26")
    assert busan[0]["id"] == "exp-4"                                  # 영남권·제조업 경험이 있는 김민재 세무사가 같은 분야 중 맨 앞
    assert "영남권 상담 가능" in busan[0]["reasons"] and "제조업 경험" in busan[0]["reasons"]
    seoul = rank_experts(load_experts(), base, want_gov_support=False, sido="서울", ksic="J62")
    assert seoul[0]["id"] in ("exp-1", "exp-5") and seoul[0]["score"] == 10 + 2 + 2
    none = rank_experts(load_experts(), [], want_gov_support=False)
    assert all(e["score"] == 0 and e["reason_line"] == "" for e in none)


def test_db_register_approve_and_requests_are_session_local():
    from src.experts.db import add_request, approve_expert, list_experts, list_requests, new_db, register_expert
    import pytest
    a, b = new_db(), new_db()
    assert len(list_experts(a)) == 6
    new_id = register_expert(a, "최가온 세무사", "세무회계 다온 · 대구", "세무사", 5, "소개", ["rnd_credit"], ["영남권"], ["화상"])
    assert len(list_experts(a)) == 6 and len(list_experts(a, "pending")) == 1       # 승인 전에는 추천 명단에 없음
    approve_expert(a, new_id)
    assert len(list_experts(a)) == 7 and len(list_experts(b)) == 6                  # 다른 접속(b)에는 영향 없음
    with pytest.raises(ValueError):
        approve_expert(a, new_id)                                                   # 이미 승인됨
    with pytest.raises(ValueError):
        register_expert(a, "", "x", "세무사", 5, "소개", ["rnd_credit"], ["전국"], ["화상"])
    with pytest.raises(ValueError):
        register_expert(a, "가", "나", "세무사", 5, "소개", [], ["전국"], ["화상"])
    add_request(a, "DEMO-AAAAAA", new_id, "둘 다", "화상", "메모", "본문", b"%PDF")
    assert list_requests(a, new_id)[0]["receipt"] == "DEMO-AAAAAA" and list_requests(b, new_id) == []
