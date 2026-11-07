"""화면(app.py)을 실제로 돌려 보는 점검. 임베딩은 끄고(키워드 점수만) 빠르게 확인한다."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def run():
    at = AppTest.from_file(APP, default_timeout=120).run()
    at.toggle[0].set_value(False).run()
    return at


def test_app_runs_without_error():
    at = run()
    assert not at.exception
    assert any("68,000,000원" in m.value for m in at.metric) or any("6,800" in str(m.value) for m in at.metric)


def test_preset_changes_inputs_and_region_rules():
    at = run()
    at.selectbox(key="preset").select("② 부산 기계장비 제조 (설립 7년, 소폭 증원)").run()
    assert not at.exception
    assert at.selectbox(key="sido").value == "부산"
    assert at.number_input(key="ec").value == 27
    at.selectbox(key="preset").select("③ 경기 소프트웨어 (설립 2년, 급성장)").run()
    assert not at.exception and at.checkbox(key="known").value is False


def test_expert_form_requires_consent_and_stores_nothing():
    at = run()
    at.button[-1].click().run()          # 동의 없이 제출
    assert any("체크" in e.value for e in at.error)
    at.checkbox[-1].check()              # 폼 안의 값은 제출할 때 함께 전달된다
    at.button[-1].click().run()
    assert any("전송·저장되지 않았습니다" in s.value for s in at.success)


def test_disaster_preset_shows_credit_and_total():
    at = run()
    assert at.text_input(key="dl").value == "0"           # 기본 시나리오는 재해 없음
    at.selectbox(key="preset").select("④ 서울 전자부품 제조 (공장 화재 · 재해손실세액공제 시연)").run()
    assert not at.exception
    assert at.text_input(key="dl").value == "160,000,000"
    # (미납 3,000만 + 올해 2,000만-감면 500만) × 40% = 1,800만 원(18,000,000원) → 첫해 합계 6,800만 + 1,800만 원
    assert any("86,000,000원" in str(m.value) for m in at.metric)
    assert any("18,000,000원" in str(m.value) for m in at.metric)


def test_disaster_input_error_when_lost_exceeds_total():
    at = run()
    at.text_input(key="dl").set_value("5,000,000").run()
    assert any("총자산가액보다 클 수 없습니다" in e.value for e in at.error)


def test_overlap_presets_pick_the_better_combination():
    at = run()
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
