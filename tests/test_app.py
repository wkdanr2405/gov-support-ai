"""화면(app.py)을 실제로 돌려 보는 점검. 임베딩은 끄고(키워드 점수만) 빠르게 확인한다."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


CORP = dict(role="기업", id="corp-1", name="가상전자(주)")


def run(auth=CORP):
    """기업 계정으로 이미 로그인한 상태에서 시작한다 (로그인 화면 자체는 아래 로그인 테스트에서 확인)."""
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["auth"] = dict(auth)
    at.run()
    at.toggle[0].set_value(False).run()
    return at


def fresh():
    return AppTest.from_file(APP, default_timeout=120).run()


NAMES = {"corp-1": "가상전자(주)", "corp-2": "새싹소프트(주)", "exp-1": "새빛세무법인", "exp-2": "다온세무법인", "exp-7": "가온세무법인", "admin-1": "운영자"}


def login_ui(at, role, acc, pw="demo1234"):
    """계정은 목록에서 고르지 않고 기업명·법인명을 직접 입력한다 (acc에 id를 주면 이름으로 바꿔 입력)."""
    at.radio(key="login_role").set_value(role).run()
    at.text_input(key="login_acc").set_value(NAMES.get(acc, acc))
    at.text_input(key="login_pw").set_value(pw)
    next(b for b in at.button if b.label == "로그인").click().run()
    return at


def md(at):
    return " ".join(str(m.value) for m in at.markdown)


def demo(at=None, name=None):
    """입력 방식을 '가상 기업 시연'으로 바꾸고(처음엔 ① 예시), 원하면 다른 예시를 고른다."""
    at = at or run()
    at.radio(key="mode").set_value("가상 기업 시연").run()
    if name:
        at.selectbox(key="preset").select(name).run()
    return at


def test_app_runs_without_error():
    at = demo()
    assert not at.exception
    assert any("68,000,000원" in m.value for m in at.metric) or any("6,800" in str(m.value) for m in at.metric)


def test_preset_changes_inputs_and_region_rules():
    at = demo()
    at.selectbox(key="preset").select("② 부산 기계장비 제조 (설립 7년, 소폭 증원)").run()
    assert not at.exception
    assert at.selectbox(key="sido").value == "부산"
    assert at.number_input(key="ec").value == 27
    at.selectbox(key="preset").select("③ 경기 소프트웨어 (설립 2년, 급성장)").run()
    assert not at.exception and at.checkbox(key="known").value is False


def btn(at, label):
    return next(b for b in at.button if b.label == label)


def consent(at):
    return next(c for c in at.checkbox if "개인정보 안내를 읽고" in c.label)


def test_expert_form_requires_consent_and_stores_nothing():
    at = run()
    btn(at, "상담 요청 보내기").click().run()          # 동의 없이 제출
    assert any("체크" in e.value for e in at.error)
    consent(at).check()                                # 폼 안의 값은 제출할 때 함께 전달된다
    btn(at, "상담 요청 보내기").click().run()
    assert any("접수되었습니다" in s.value for s in at.success)


def test_disaster_preset_shows_credit_and_total():
    at = demo()
    assert at.text_input(key="dl").value == "0"           # ① 예시는 재해 없음
    at.selectbox(key="preset").select("④ 서울 전자부품 제조 (공장 화재 · 재해손실세액공제 시연)").run()
    assert not at.exception
    assert at.text_input(key="dl").value == "160,000,000"
    # (미납 3,000만 + 올해 2,000만-감면 500만) × 40% = 1,800만 원(18,000,000원) → 첫해 합계 6,800만 + 1,800만 원
    assert any("86,000,000원" in str(m.value) for m in at.metric)
    assert any("18,000,000원" in str(m.value) for m in at.metric)


def test_disaster_input_error_when_lost_exceeds_total():
    at = demo()
    at.text_input(key="dl").set_value("5,000,000").run()
    assert any("총자산가액보다 클 수 없습니다" in e.value for e in at.error)


def test_overlap_presets_pick_the_better_combination():
    at = demo()
    at.selectbox(key="preset").select("③ 경기 소프트웨어 (설립 2년, 급성장)").run()
    assert not at.exception
    # ③: 통합고용 2,800 + 특별감면 160(소기업 수도권 20% × 800) > 창업감면 800 → 합계 2,800 + 160 + R&D 1,500
    assert any("44,600,000원" in str(m.value) for m in at.metric)
    assert any("합계에서 제외" in w.value for w in at.warning)
    at.selectbox(key="preset").select("⑤ 대구 전자부품 제조 (2026년 창업 · 청년창업 감면 vs 통합고용 중복 배제 시연)").run()
    assert not at.exception
    # ⑤: 창업감면 4,000(비수도권 청년 100%) > 통합고용 2,700 + 특별감면 1,200 → 합계 4,000 + R&D 5,000
    assert any("90,000,000원" in str(m.value) for m in at.metric)
    assert at.text_input(key="ct").value == "40,000,000"


def test_manual_entry_is_default_and_starts_blank():
    at = run()
    assert at.radio(key="mode").value == "직접 입력"
    assert not at.exception
    assert at.text_input(key="rc").value == "0" and at.text_input(key="rev").value == "0"
    assert at.number_input(key="ec").value == 0
    assert not [s for s in at.selectbox if s.key == "preset"]          # 가상 기업 목록은 시연 방식에서만 보인다
    at.text_input(key="rc").set_value("100,000,000").run()
    assert not at.exception
    at.radio(key="mode").set_value("가상 기업 시연").run()              # 시연으로 바꾸면 ①이 채워진다
    assert at.selectbox(key="preset").value.startswith("①") and at.text_input(key="rc").value == "200,000,000"
    at.radio(key="mode").set_value("직접 입력").run()                   # 다시 직접 입력 → 빈 칸
    assert at.text_input(key="rc").value == "0"


def test_recommendations_are_ten_and_paged_by_four():
    at = demo()
    assert any(m.value == "10건" for m in at.metric)
    page = lambda: [c for c in at.get("caption") if "쪽" in str(c.value) and "건씩" in str(c.value)]
    assert "1/3쪽" in str(page()[0].value)
    assert len(at.radio(key="match_page").options) == 3
    at.radio(key="match_page").set_value(3).run()
    assert not at.exception and "3/3쪽" in str(page()[0].value)


def test_expert_tab_ranks_picks_and_shows_receipt():
    at = demo()
    assert at.radio(key="expert_pick").options[0] == "새빛세무법인"      # ① 예시는 R&D·고용 공제 → 새빛세무법인가 맨 앞
    at.radio(key="expert_pick").set_value("푸른회계법인").run()
    consent(at).check()
    btn(at, "상담 요청 보내기").click().run()
    assert not at.exception
    text = " ".join(str(m.value) for m in at.markdown)
    assert "DEMO-" in text and "푸른회계법인" in text and "요청 접수" in text


def test_blank_manual_screen_says_sme_needs_confirmation():
    at = run()                                                           # 직접 입력, 매출·자산 0
    assert [m.value for m in at.metric if m.label == "중소기업 판정"] == ["확인 필요"]
    assert any("판정합니다" in i.value for i in at.info)
    at.text_input(key="rev").set_value("3,000,000,000").run()
    at.text_input(key="assets").set_value("5,000,000,000").run()
    assert [m.value for m in at.metric if m.label == "중소기업 판정"] == ["해당"]


def test_sigungu_selector_appears_only_for_capital_area_and_classifies():
    at = demo()                                   # ① 서울: 시·군·구 선택 없음
    assert not at.exception and not [s for s in at.selectbox if s.key == "sg"]
    at = demo(at, "③ 경기 소프트웨어 (설립 2년, 급성장)")
    assert not at.exception
    sg = [s for s in at.selectbox if s.key == "sg"]
    assert sg and sg[0].value == "용인시"
    sg[0].select("남양주시").run()                # 일부 동만 과밀억제권역 → 추가 확인 질문
    assert not at.exception and [r for r in at.radio if r.key == "ip2"]
    at.selectbox(key="sido").select("부산").run()  # 수도권 밖으로 바꿔도 오류가 없어야 함
    assert not at.exception


def test_login_is_required_and_blocks_everything_else():
    at = fresh()
    assert not at.exception
    assert [t.label for t in at.tabs][:2] == ["로그인", "회원가입"] and "기업 정보 입력" not in md(at)
    assert not at.selectbox and "가입 신청" not in md(at) + " ".join(e.label for e in at.expander)           # 계정 목록 선택칸·'가입 신청' 표현 없음
    allt = md(at) + " ".join(c.value for c in at.caption)
    assert "새싹소프트" not in allt and "다온세무법인" not in allt and "푸른회계법인" not in allt            # 다른 기업·법인 이름이 화면에 없다
    assert not at.metric and not [t for t in at.tabs if t.label == "전문가 연결"]


def test_wrong_password_is_rejected_and_role_account_mismatch_too():
    at = fresh()
    login_ui(at, "기업", "corp-1", pw="틀린비밀번호")
    assert any("맞지 않습니다" in e.value for e in at.error) and "auth" not in at.session_state
    from src.auth import login
    from src.experts.db import new_db
    assert login(new_db(), "회계법인/세무법인", "가상전자(주)", "demo1234") is None      # 기업 계정으로 법인 로그인 불가
    assert login(new_db(), "기업", "새빛세무법인", "demo1234") is None


def test_corp_sees_company_screen_only_and_expert_sees_expert_screen_only():
    at = fresh()
    login_ui(at, "기업", "corp-1")
    assert not at.exception and "기업 정보 입력" in md(at)
    assert not [t for t in at.tabs if t.label == "고객 상담 요청"]
    at = fresh()
    login_ui(at, "회계법인/세무법인", "exp-1")
    assert not at.exception and "기업 정보 입력" not in md(at) and not at.metric
    assert [t for t in at.tabs if t.label == "고객 상담 요청"]
    assert "새빛세무법인" in md(at)


def test_request_reaches_only_the_chosen_expert_and_logout_clears_company_data():
    at = demo()                                                       # 가상전자(주)로 로그인된 상태, ① 예시
    assert at.text_input(key="rev").value != "0"
    at.radio(key="expert_pick").set_value("다온세무법인").run()
    consent(at).check()
    btn(at, "상담 요청 보내기").click().run()
    receipt = next(m.value for m in at.markdown if "DEMO-" in str(m.value))
    receipt = "DEMO-" + receipt.split("DEMO-")[1][:6]
    assert any(receipt in str(m.value) for m in at.markdown) and "내가 보낸 상담 요청" in md(at)
    # 로그아웃: 기업 입력은 지워지고(빈 값), 로그인 화면으로 돌아간다. 전문가 보관함은 접속 동안 남는다.
    btn(at, "로그아웃").click().run()
    assert "auth" not in at.session_state and at.session_state["rev"] == "0" and "기업 정보 입력" not in md(at)
    # 다른 기업 계정에는 보이지 않는다
    login_ui(at, "기업", "corp-2")
    assert any("아직 보낸 상담 요청이 없습니다" in c.value for c in at.caption) and receipt not in md(at)
    btn(at, "로그아웃").click().run()
    # 요청을 받은 전문가에게는 보이고, 다른 전문가에게는 보이지 않는다
    login_ui(at, "회계법인/세무법인", "exp-2")
    assert receipt in " ".join(e.label for e in at.expander) and "가상전자" in " ".join(e.label for e in at.expander)
    btn(at, "로그아웃").click().run()
    login_ui(at, "회계법인/세무법인", "exp-1")
    assert not [e for e in at.expander if receipt in e.label] and "아직 들어온 고객 상담 요청이 없습니다" in " ".join(i.value for i in at.info)


def test_corporation_signup_admin_approval_then_login():
    at = fresh()
    at.radio(key="signup_role").set_value("회계법인/세무법인").run()
    assert not [m for m in at.multiselect if "지역" in m.label] and not [r for r in at.radio if r.label == "자격"]      # 활동 지역·개인 자격 입력 없음
    next(t for t in at.text_input if t.label.startswith("법인명")).set_value("가온세무법인")
    next(t for t in at.text_area if t.label == "소개").set_value("제조업 연구개발비 공제를 주로 맡습니다.")
    next(m for m in at.multiselect if m.label == "전문 분야").set_value(["rnd_credit"])
    next(m for m in at.multiselect if m.label == "상담 방식").set_value(["화상"])
    btn(at, "회원가입").click().run()
    assert any("접수되었습니다" in s.value for s in at.success)
    login_ui(at, "회계법인/세무법인", "가온세무법인")                              # 승인 전에는 로그인 불가
    assert "auth" not in at.session_state and any("맞지 않습니다" in e.value for e in at.error)
    login_ui(at, "운영자", "admin-1")
    assert not at.exception and "기업 정보 입력" not in md(at) and "가온세무법인" in md(at)
    btn(at, "법인 등록 확인 완료 · 승인").click().run()
    btn(at, "로그아웃").click().run()
    login_ui(at, "회계법인/세무법인", "exp-7")
    assert not at.exception and "가온세무법인" in md(at)


def test_corporation_profile_edit_has_etc_cpa_first_labels_and_persists():
    at = fresh()
    assert at.radio(key="login_role").options == ["기업", "회계법인/세무법인", "운영자"]
    login_ui(at, "회계법인/세무법인", "exp-1")
    assert [t for t in at.tabs if t.label == "내 법인 프로필"]
    kind = next(r for r in at.radio if r.label == "법인 유형")
    assert kind.options == ["회계법인", "세무법인", "기타"] and kind.value == "세무법인"
    assert next(t for t in at.text_input if t.label.startswith("법인명")).value == "새빛세무법인"
    assert not [m for m in at.multiselect if "지역" in m.label]
    for label in ("전문 분야", "상담 방식", "경험 업종 (비우면 전 업종)"):
        ms = next(m for m in at.multiselect if m.label == label)
        assert ms.options[-1] == "기타" and any(t.label == f"{label} · 기타 내용 (직접 입력)" for t in at.text_input), label
    # 전문 분야를 비우면 오류, 저장되지 않음
    next(m for m in at.multiselect if m.label == "전문 분야").set_value([])
    btn(at, "프로필 저장").click().run()
    assert any("하나 이상" in e.value for e in at.error)
    # 정상 수정
    next(t for t in at.text_input if t.label.startswith("법인명")).set_value("새빛세무법인(수정)")
    next(r for r in at.radio if r.label == "법인 유형").set_value("기타")
    next(t for t in at.text_input if t.label == "법인 유형 · 기타 내용 (직접 입력)").set_value("관세법인")
    next(t for t in at.text_area if t.label == "소개").set_value("수정한 소개입니다.")
    next(m for m in at.multiselect if m.label == "전문 분야").set_value(["rnd_credit"])
    next(t for t in at.text_input if t.label == "상담 방식 · 기타 내용 (직접 입력)").set_value("채팅")
    btn(at, "프로필 저장").click().run()
    assert not at.exception and any("프로필이 저장되었습니다" in s.value for s in at.success)
    assert "새빛세무법인(수정)" in md(at)                                              # 위쪽 표시 이름도 바뀜
    btn(at, "로그아웃").click().run()
    login_ui(at, "회계법인/세무법인", "새빛세무법인")                                    # 계정은 법인명이므로 예전 이름으로는 로그인되지 않는다
    assert "auth" not in at.session_state
    login_ui(at, "회계법인/세무법인", "새빛세무법인(수정)")
    assert next(t for t in at.text_area if t.label == "소개").value == "수정한 소개입니다."
    assert next(t for t in at.text_input if t.label == "상담 방식 · 기타 내용 (직접 입력)").value == "채팅"
    assert next(r for r in at.radio if r.label == "법인 유형").value == "기타"
    assert next(t for t in at.text_input if t.label == "법인 유형 · 기타 내용 (직접 입력)").value == "관세법인"


def test_company_expert_cards_show_corporation_facts_without_region():
    at = demo()
    text = " ".join(c.value for c in at.caption)
    assert "세무법인 · 전문 인력 14명" in text and "지역:" not in text and "소재지" not in text.split("회계·세무법인")[1][:60]
    assert at.radio(key="expert_pick").label == "상담받을 법인"


def test_company_signup_login_profile_edit_and_contact_reaches_corporation():
    at = fresh()
    assert at.radio(key="signup_role").value == "기업"
    def field(label):
        return next(t for t in at.text_input if t.label == label)
    assert field("이메일 (가상)").value.endswith("@example.com")                       # 가상 이메일·연락처가 미리 채워져 있다
    next(t for t in at.text_input if t.label.startswith("기업명")).set_value("해든푸드(주)")
    field("이메일 (가상)").set_value("real@gmail.com")
    btn(at, "회원가입").click().run()
    assert any("가상 형식" in e.value for e in at.error) and "auth" not in at.session_state       # 실제 이메일 형식은 거부
    field("이메일 (가상)").set_value("haeden@example.com")
    field("연락처 (가상)").set_value("010-0000-0003")
    btn(at, "회원가입").click().run()
    assert any("회원가입이 완료" in s.value for s in at.success)
    login_ui(at, "기업", "해든푸드(주)")
    assert at.session_state["auth"]["name"] == "해든푸드(주)" and "기업 정보 입력" in md(at)
    # 프로필 수정: 같은 입력 화면에 현재 값이 채워져 있고, 저장하면 계정 이름도 바뀐다
    assert next(t for t in at.text_input if t.label == "이메일 (가상)" and t.value == "haeden@example.com")
    prof_email = next(t for t in at.text_input if t.key == "corp_edit_corp-3_email")
    prof_email.set_value("haeden2@example.com")
    btn(at, "프로필 저장").click().run()
    assert any("프로필이 저장되었습니다" in s.value for s in at.success) and not at.exception
    # 상담 요청을 보내면 법인 쪽 전달 자료에 기업명·이메일·연락처가 담긴다
    at.radio(key="mode").set_value("가상 기업 시연").run()
    assert any("haeden2@example.com" in c.value for c in at.caption)
    consent(at).check()
    btn(at, "상담 요청 보내기").click().run()
    assert not at.exception
    pick = at.radio(key="expert_pick").value
    from src.experts import load_experts
    edb = at.session_state["expert_db"]
    from src.experts.db import list_requests
    exp_id = next(e["id"] for e in load_experts(edb) if e["name"] == pick)
    got = list_requests(edb, exp_id)[0]
    assert "해든푸드(주)" in got["brief"] and "haeden2@example.com" in got["brief"] and "010-0000-0003" in got["brief"]
    assert got["pdf"].startswith(b"%PDF") and got["client_name"] == "해든푸드(주)"


def test_admin_sees_approved_companies_and_firms_split_by_origin():
    at = fresh()
    login_ui(at, "운영자", "admin-1")
    assert not at.exception and "기업 정보 입력" not in md(at)
    corp_df, firm_df = at.dataframe[0].value, at.dataframe[1].value
    assert list(corp_df["기업명"]) == ["가상전자(주)", "새싹소프트(주)"] and set(corp_df["구분"]) == {"가상 시연 데이터"}
    assert len(firm_df) == 6 and set(firm_df["구분"]) == {"가상 시연 데이터"} and "새빛세무법인" in list(firm_df["법인명"])
    assert any("가상 시연 데이터 2곳" in c.value for c in at.caption) and any("가상 시연 데이터 6곳" in c.value for c in at.caption)
    # 회원가입한 기업, 승인된 법인은 '회원가입'으로 구분되어 나타나고, 승인 전 법인은 목록에 없다
    from src.experts.db import approve_expert, register_company, register_expert
    edb = at.session_state["expert_db"]
    register_company(edb, "해든푸드(주)", "haeden@example.com", "010-0000-0003")
    ok = register_expert(edb, "가온세무법인", "세무법인", 2021, 7, "소개", ["rnd_credit"], ["화상"])
    register_expert(edb, "대기회계법인", "회계법인", 2021, 7, "소개", ["rnd_credit"], ["화상"])
    approve_expert(edb, ok)
    at.run()
    corp_df, firm_df = at.dataframe[0].value, at.dataframe[1].value
    assert dict(zip(corp_df["기업명"], corp_df["구분"]))["해든푸드(주)"] == "회원가입"
    assert dict(zip(firm_df["법인명"], firm_df["구분"]))["가온세무법인"] == "회원가입" and "대기회계법인" not in list(firm_df["법인명"])
    assert "대기회계법인" in md(at)                                                      # 승인 대기 쪽에는 보인다


def test_data_survives_refresh_is_shared_across_sessions_and_admin_can_reset():
    # 세션 1: 기업이 푸른회계법인에 상담 요청을 보낸다
    at = demo()
    at.radio(key="expert_pick").set_value("푸른회계법인").run()
    consent(at).check()
    btn(at, "상담 요청 보내기").click().run()
    receipt = "DEMO-" + next(m.value for m in at.markdown if "DEMO-" in str(m.value)).split("DEMO-")[1][:6]
    # 새로고침 = 새 세션(로그인은 풀리지만 데이터는 서버 메모리에 남는다)
    at2 = fresh()
    assert "auth" not in at2.session_state
    login_ui(at2, "회계법인/세무법인", "푸른회계법인")
    assert receipt in " ".join(e.label for e in at2.expander)
    # 다른 사람(세션 3)이 가입한 기업은 운영자 세션에서도 보인다
    at3 = fresh()
    at3.radio(key="signup_role").set_value("기업").run()
    next(t for t in at3.text_input if t.label.startswith("기업명")).set_value("해든푸드(주)")
    btn(at3, "회원가입").click().run()
    assert any("회원가입이 완료" in s.value for s in at3.success)
    at4 = fresh()
    login_ui(at4, "운영자", "admin-1")
    assert "해든푸드(주)" in list(at4.dataframe[0].value["기업명"])
    # 운영자가 되돌리면 가입·상담 요청이 사라지고 가상 계정만 남는다
    btn(at4, "시연 데이터 처음 상태로 되돌리기").click().run()
    assert list(at4.dataframe[0].value["기업명"]) == ["가상전자(주)", "새싹소프트(주)"]
    at5 = fresh()
    login_ui(at5, "회계법인/세무법인", "푸른회계법인")
    assert receipt not in " ".join(e.label for e in at5.expander)
