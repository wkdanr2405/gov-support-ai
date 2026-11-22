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
    assert "부산 상담 가능" in busan[0]["reasons"] and "제조업 경험" in busan[0]["reasons"]
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


def test_auth_accounts_and_password_hash():
    from src.auth import DEMO_PASSWORD, accounts, hash_pw, login
    from src.experts.db import new_db, register_expert
    db = new_db()
    assert [a["id"] for a in accounts(db, "기업")] == ["corp-1", "corp-2"] and [a["id"] for a in accounts(db, "운영자")] == ["admin-1"]
    assert len(accounts(db, "공인회계사/세무사")) == 6
    assert login(db, "기업", "corp-1", DEMO_PASSWORD) == {"role": "기업", "id": "corp-1", "name": "가상전자(주) 대표"}
    assert login(db, "기업", "corp-1", "") is None and login(db, "기업", "corp-9", DEMO_PASSWORD) is None
    assert hash_pw(DEMO_PASSWORD) != DEMO_PASSWORD
    new_id = register_expert(db, "최가온 세무사", "다온", "세무사", 5, "소개", ["rnd_credit"], ["전국"], ["화상"])
    assert login(db, "공인회계사/세무사", new_id, DEMO_PASSWORD) is None          # 승인 전에는 로그인 불가


def test_requests_are_isolated_by_expert_and_by_client():
    from src.experts.db import add_request, list_requests, list_requests_by_client, new_db
    db = new_db()
    add_request(db, "DEMO-000001", "exp-1", "둘 다", "화상", "", "본문1", b"1", "corp-1", "가상전자(주) 대표")
    add_request(db, "DEMO-000002", "exp-2", "둘 다", "화상", "", "본문2", b"2", "corp-2", "새싹소프트(주) 대표")
    assert [r["receipt"] for r in list_requests(db, "exp-1")] == ["DEMO-000001"]
    assert [r["receipt"] for r in list_requests(db, "exp-3")] == []
    assert [r["receipt"] for r in list_requests_by_client(db, "corp-2")] == ["DEMO-000002"]
    assert list_requests_by_client(db, "corp-3") == []


def test_update_expert_changes_profile_but_keeps_requests_and_rejects_bad_input():
    import pytest
    from src.experts.db import add_request, list_requests, new_db, register_expert, update_expert
    db = new_db()
    add_request(db, "DEMO-000001", "exp-1", "주제", "화상", "", "요약", False, "corp-1", "가상전자(주) 대표")
    update_expert(db, "exp-1", "박서윤 세무사(수정)", "새 소속", "세무사", 12, "새 소개", ["disaster_loss"], ["영남권"], ["전화"], ["C"])
    me = next(e for e in load_experts(db) if e["id"] == "exp-1")
    assert me["name"] == "박서윤 세무사(수정)" and me["specialties"] == ["disaster_loss"] and me["regions"] == ["영남권"] and me["channels"] == ["전화"]
    assert len(list_requests(db, "exp-1")) == 1                                   # 받은 요청은 그대로
    assert load_experts(db)[0]["id"] == "exp-1" and len(load_experts(db)) == 6     # 순서·인원 그대로
    with pytest.raises(ValueError):
        update_expert(db, "exp-1", "박서윤", "소속", "세무사", 5, "소개", [], ["전국"], ["화상"])   # 전문 분야 비움
    assert next(e for e in load_experts(db) if e["id"] == "exp-1")["name"] == "박서윤 세무사(수정)"
    pid = register_expert(db, "대기자", "소속", "세무사", 3, "소개", ["rnd_credit"], ["전국"], ["화상"])
    with pytest.raises(ValueError):
        update_expert(db, pid, "대기자2", "소속", "세무사", 3, "소개", ["rnd_credit"], ["전국"], ["화상"])  # 미승인은 못 고침
    other = new_db()                                                               # 다른 접속(세션)에는 영향 없음
    assert next(e for e in load_experts(other) if e["id"] == "exp-1")["name"] == "박서윤 세무사"


def test_region_tree_two_step_with_merged_special_city_and_incheon_reform():
    from src.experts import ETC, join_etc, region_tree, region_values, show_etc, sido_options, split_etc, sub_kind, sub_options
    t = region_tree()
    assert sido_options()[0] == "전국" and "전남광주" in sido_options() and "광주" not in t and "전남" not in t     # 통합특별시 반영
    assert "대전" in t and "충남" in t and "대구" in t and "경북" in t                                            # 대전·충남, 대구·경북은 통합되지 않았다
    assert {"제물포구", "영종구", "서해구", "검단구", "강화군", "옹진군"} <= set(t["인천"]) and len(t["인천"]) == 11 and "서구" not in t["인천"]
    assert "광주 광산구" in t["전남광주"] and "신안군" in t["전남광주"] and len(t["전남광주"]) == 27
    assert {"강남구"} <= set(t["서울"]) and "해운대구" in t["부산"] and "달성군" in t["대구"] and "울주군" in t["울산"]          # 광역시: 구·군
    assert {"수원시", "가평군"} <= set(t["경기"]) and "춘천시" in t["강원"] and "서귀포시" in t["제주"] and not any("영통" in x for x in t["경기"])  # 도: 시·군
    assert sub_options("서울")[0] == "전체" and sub_kind("서울") == "구" and sub_kind("경기") == "시·군" and sub_kind("전남광주") == "구·시·군"
    assert sum(len(v) for v in t.values()) == 230
    assert region_values("서울", []) == ["서울 전체"] and region_values("서울", ["전체", "강남구"]) == ["서울 전체"] and region_values("서울", ["강남구", "송파구"]) == ["서울 강남구", "서울 송파구"]
    assert join_etc(["화상", ETC], "") == ["화상", "기타"] and join_etc(["화상"], " 우편 ") == ["화상", "기타: 우편"]
    assert split_etc(["화상", "기타: 우편"], ["화상", "전화"]) == (["화상"], "우편") and show_etc(["기타: 우편", "화상"]) == ["기타(우편)", "화상"]


def test_rank_treats_old_gwangju_jeonnam_names_as_merged_city():
    r = {e["id"]: e for e in rank_experts(load_experts(), ["rnd_credit"], want_gov_support=False, sido="전남")}
    assert "전남광주 상담 가능" in r["exp-6"]["reasons"]            # 기업이 이전 이름(전남)으로 적어도 통합특별시 전문가가 맞는다
    assert not any("상담 가능" in x and "전국" not in x for x in r["exp-4"]["reasons"])      # 영남권 전문가는 해당 없음


def test_rank_matches_expert_by_sido_even_when_only_a_district_is_chosen():
    from src.experts.db import new_db, update_expert
    db = new_db()
    update_expert(db, "exp-1", "박서윤 세무사", "소속", "세무사", 5, "소개", ["rnd_credit"], ["부산 해운대구"], ["화상"])
    r = {e["id"]: e for e in rank_experts(load_experts(db), ["rnd_credit"], want_gov_support=False, sido="부산")}
    assert "부산 상담 가능" in r["exp-1"]["reasons"]
    r2 = {e["id"]: e for e in rank_experts(load_experts(db), ["rnd_credit"], want_gov_support=False, sido="서울")}
    assert "서울 상담 가능" not in r2["exp-1"]["reasons"]
