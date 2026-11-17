"""화면(app.py)을 실제로 돌려 보는 점검. 임베딩은 끄고(키워드 점수만) 빠르게 확인한다."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def run():
    at = AppTest.from_file(APP, default_timeout=120).run()
    at.toggle[0].set_value(False).run()
    return at


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
    assert at.radio(key="expert_pick").options[0] == "박서윤 세무사"      # ① 예시는 R&D·고용 공제 → 박서윤 세무사가 맨 앞
    at.radio(key="expert_pick").set_value("이하린 공인회계사").run()
    consent(at).check()
    btn(at, "상담 요청 보내기").click().run()
    assert not at.exception
    text = " ".join(str(m.value) for m in at.markdown)
    assert "DEMO-" in text and "이하린 공인회계사" in text and "요청 접수" in text


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


def test_expert_flow_register_approve_and_inbox():
    """전문가 등록 신청 → 운영자 승인 → 추천 명단에 포함, 상담 요청 → 전문가의 받은 요청에 나타남."""
    at = demo()
    assert len(at.radio(key="expert_pick").options) == 6
    # 필수 항목 없이 등록하면 안내
    btn(at, "등록 신청하기").click().run()
    assert any("입력해 주세요" in e.value or "골라 주세요" in e.value for e in at.error)
    # 정상 등록 → 승인 대기이므로 아직 명단에 없다
    next(t for t in at.text_input if t.label.startswith("이름")).set_value("최가온 세무사")
    next(t for t in at.text_input if t.label.startswith("소속")).set_value("세무회계 다온 · 대구")
    next(t for t in at.text_area if t.label == "소개").set_value("제조업 연구개발비 공제를 주로 맡습니다.")
    next(m for m in at.multiselect if m.label == "전문 분야").set_value(["rnd_credit"])
    next(m for m in at.multiselect if m.label == "활동 지역").set_value(["영남권"])
    next(m for m in at.multiselect if m.label == "상담 방식").set_value(["화상"])
    btn(at, "등록 신청하기").click().run()
    assert any("접수되었습니다" in s.value for s in at.success)
    assert len(at.radio(key="expert_pick").options) == 6
    # 운영자 승인 → 7명
    btn(at, "자격 확인 완료 · 승인").click().run()
    assert not at.exception and len(at.radio(key="expert_pick").options) == 7
    # 상담 요청 → 받은 요청에 나타남
    at.radio(key="expert_pick").set_value("최가온 세무사").run()
    consent(at).check()
    btn(at, "상담 요청 보내기").click().run()
    assert not at.exception
    at.selectbox(key="pro_who").select("최가온 세무사").run()
    assert any("DEMO-" in e.label for e in at.expander)
