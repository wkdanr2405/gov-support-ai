from datetime import date

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
        assert e["name"].endswith(("회계법인", "세무법인")) and e["kind"] in ("회계법인", "세무법인") and e["name"].endswith(e["kind"])
        assert e["specialties"] and e["channels"] and e["intro"] and e["staff"] >= 1 and e["founded"] >= 1950 and e["years"] == date.today().year - e["founded"]
        assert "regions" not in e and "firm" not in e and "license" not in e             # 활동 지역·개인 자격 항목은 없다


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


def test_rank_uses_industry_as_tiebreaker_and_has_no_region_score():
    base = ["rnd_credit"]
    c = rank_experts(load_experts(), base, want_gov_support=False, ksic="C26")
    assert c[0]["id"] == "exp-1" and c[0]["score"] == 10 + 2 and "제조업 경험" in c[0]["reasons"]      # 같은 분야 중 제조업 경험 + 명단 순서
    j = rank_experts(load_experts(), base, want_gov_support=False, ksic="J62")
    assert j[0]["id"] in ("exp-1", "exp-5") and j[0]["score"] == 12
    none = rank_experts(load_experts(), [], want_gov_support=False)
    assert all(e["score"] == 0 and e["reason_line"] == "" for e in none)
    assert not [r for e in c for r in e["reasons"] if "상담 가능" in r]                                 # 지역 가점·이유 없음


def test_db_register_approve_and_requests_are_session_local():
    from src.experts.db import add_request, approve_expert, list_experts, list_requests, new_db, register_expert
    import pytest
    a, b = new_db(), new_db()
    assert len(list_experts(a)) == 6
    new_id = register_expert(a, "가온세무법인", "세무법인", 2021, 7, "소개", ["rnd_credit"], ["화상"])
    assert len(list_experts(a)) == 6 and len(list_experts(a, "pending")) == 1       # 승인 전에는 추천 명단에 없음
    approve_expert(a, new_id)
    assert len(list_experts(a)) == 7 and len(list_experts(b)) == 6                  # 다른 접속(b)에는 영향 없음
    with pytest.raises(ValueError):
        approve_expert(a, new_id)                                                   # 이미 승인됨
    with pytest.raises(ValueError):
        register_expert(a, "", "세무법인", 2021, 7, "소개", ["rnd_credit"], ["화상"])
    with pytest.raises(ValueError):
        register_expert(a, "가", "세무법인", 2021, 7, "소개", [], ["화상"])
    with pytest.raises(ValueError):
        register_expert(a, "가", "세무법인", 1900, 7, "소개", ["rnd_credit"], ["화상"])          # 설립 연도 범위
    with pytest.raises(ValueError):
        register_expert(a, "가", "세무법인", 2021, 0, "소개", ["rnd_credit"], ["화상"])           # 인력 수 범위
    add_request(a, "DEMO-AAAAAA", new_id, "둘 다", "화상", "메모", "본문", b"%PDF")
    assert list_requests(a, new_id)[0]["receipt"] == "DEMO-AAAAAA" and list_requests(b, new_id) == []


def test_auth_by_name_hides_other_accounts_and_hashes_password():
    from src.auth import DEMO_PASSWORD, find_account, hash_pw, login
    from src.experts.db import new_db, register_expert
    db = new_db()
    assert login(db, "기업", "가상전자(주)", DEMO_PASSWORD) == {"role": "기업", "id": "corp-1", "name": "가상전자(주)"}
    assert login(db, "기업", " 가상전자 (주) ", DEMO_PASSWORD)["id"] == "corp-1"            # 띄어쓰기·대소문자는 무시
    assert login(db, "기업", "가상전자(주)", "") is None and login(db, "기업", "없는기업", DEMO_PASSWORD) is None
    assert login(db, "운영자", "운영자", DEMO_PASSWORD)["id"] == "admin-1"
    assert login(db, "회계법인/세무법인", "새빛세무법인", DEMO_PASSWORD)["id"] == "exp-1"
    assert login(db, "기업", "새빛세무법인", DEMO_PASSWORD) is None and login(db, "회계법인/세무법인", "가상전자(주)", DEMO_PASSWORD) is None
    assert find_account(db, "기업", "") is None and find_account(db, "기업", "가상") is None      # 목록 조회·부분 일치 불가
    assert hash_pw(DEMO_PASSWORD) != DEMO_PASSWORD
    register_expert(db, "가온세무법인", "세무법인", 2021, 7, "소개", ["rnd_credit"], ["화상"])
    assert login(db, "회계법인/세무법인", "가온세무법인", DEMO_PASSWORD) is None          # 승인 전에는 로그인 불가


def test_company_signup_profile_edit_and_virtual_contact_rules():
    import pytest
    from src.experts.db import get_company, new_db, register_company, register_expert, update_company, virtual_contact
    db = new_db()
    assert get_company(db, "corp-1")["email"].endswith("@example.com") and get_company(db, "corp-1")["phone"].startswith("010-0000-")
    email, phone = virtual_contact(db)
    cid = register_company(db, "해든푸드(주)", email, phone)
    assert get_company(db, cid)["name"] == "해든푸드(주)" and cid == "corp-3"
    with pytest.raises(ValueError):
        register_company(db, "해든푸드 (주)", "a@example.com", "010-0000-0009")        # 같은 이름(띄어쓰기만 다름)
    for bad_email, bad_phone in [("real@gmail.com", "010-0000-0009"), ("a@example.com", "010-1234-5678"), ("", "010-0000-0009")]:
        with pytest.raises(ValueError):
            register_company(db, "다른기업", bad_email, bad_phone)                       # 실제 이메일·연락처 형식 거부
    with pytest.raises(ValueError):
        register_company(db, " ", "a@example.com", "010-0000-0009")
    with pytest.raises(ValueError):
        register_expert(db, "새빛세무법인", "세무법인", 2021, 7, "소개", ["rnd_credit"], ["화상"])   # 법인명 중복
    update_company(db, "corp-1", "가상전자(수정)", "new1@example.com", "010-0000-0101")
    assert get_company(db, "corp-1") == dict(id="corp-1", name="가상전자(수정)", email="new1@example.com", phone="010-0000-0101")
    with pytest.raises(ValueError):
        update_company(db, "corp-1", "새싹소프트(주)", "new1@example.com", "010-0000-0101")      # 다른 기업 이름과 겹침
    assert get_company(new_db(), "corp-1")["name"] == "가상전자(주)"                           # 다른 접속에는 영향 없음


def test_brief_and_pdf_carry_company_contact():
    from src.report.pdf import build_brief_pdf
    co = {**CO, "name": "가상전자(주)", "email": "contact1@example.com", "phone": "010-0000-0001"}
    b = build_brief("가상 기업 기준 예시", co, RES, [], [])
    assert "가상전자(주)" in b and "contact1@example.com" in b and "010-0000-0001" in b
    pdf = build_brief_pdf("가상 기업 기준 예시", co, RES, [], [], expert=load_experts()[0], topic="둘 다", channel="화상")
    assert pdf.startswith(b"%PDF") and pdf.count(b"/Type /Page\n") + pdf.count(b"/Type /Page ") >= 1


def test_requests_are_isolated_by_expert_and_by_client():
    from src.experts.db import add_request, list_requests, list_requests_by_client, new_db
    db = new_db()
    add_request(db, "DEMO-000001", "exp-1", "둘 다", "화상", "", "본문1", b"1", "corp-1", "가상전자(주)")
    add_request(db, "DEMO-000002", "exp-2", "둘 다", "화상", "", "본문2", b"2", "corp-2", "새싹소프트(주)")
    assert [r["receipt"] for r in list_requests(db, "exp-1")] == ["DEMO-000001"]
    assert [r["receipt"] for r in list_requests(db, "exp-3")] == []
    assert [r["receipt"] for r in list_requests_by_client(db, "corp-2")] == ["DEMO-000002"]
    assert list_requests_by_client(db, "corp-3") == []


def test_update_expert_changes_profile_but_keeps_requests_and_rejects_bad_input():
    import pytest
    from src.experts.db import add_request, list_requests, new_db, register_expert, update_expert
    db = new_db()
    add_request(db, "DEMO-000001", "exp-1", "주제", "화상", "", "요약", False, "corp-1", "가상전자(주)")
    update_expert(db, "exp-1", "새빛세무법인(수정)", "회계법인", 2010, 30, "새 소개", ["disaster_loss"], ["전화"], ["C"])
    me = next(e for e in load_experts(db) if e["id"] == "exp-1")
    assert me["name"] == "새빛세무법인(수정)" and me["kind"] == "회계법인" and me["staff"] == 30 and me["founded"] == 2010
    assert me["specialties"] == ["disaster_loss"] and me["channels"] == ["전화"] and me["industries"] == ["C"]
    assert len(list_requests(db, "exp-1")) == 1                                   # 받은 요청은 그대로
    assert load_experts(db)[0]["id"] == "exp-1" and len(load_experts(db)) == 6     # 순서·인원 그대로
    with pytest.raises(ValueError):
        update_expert(db, "exp-1", "새빛세무법인", "세무법인", 2012, 14, "소개", [], ["화상"])   # 전문 분야 비움
    assert next(e for e in load_experts(db) if e["id"] == "exp-1")["name"] == "새빛세무법인(수정)"
    pid = register_expert(db, "대기세무법인", "세무법인", 2021, 7, "소개", ["rnd_credit"], ["화상"])
    with pytest.raises(ValueError):
        update_expert(db, pid, "대기세무법인2", "세무법인", 2021, 7, "소개", ["rnd_credit"], ["화상"])  # 미승인은 못 고침
    other = new_db()                                                               # 다른 접속(세션)에는 영향 없음
    assert next(e for e in load_experts(other) if e["id"] == "exp-1")["name"] == "새빛세무법인"


def test_etc_helpers_roundtrip():
    from src.experts import ETC, join_etc, show_etc, split_etc
    assert join_etc(["화상", ETC], "") == ["화상", "기타"] and join_etc(["화상"], " 우편 ") == ["화상", "기타: 우편"]
    assert split_etc(["화상", "기타: 우편"], ["화상", "전화"]) == (["화상"], "우편") and show_etc(["기타: 우편", "화상"]) == ["기타(우편)", "화상"]
