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
    assert any("6,800만 원" in m.value for m in at.metric) or any("6,800" in str(m.value) for m in at.metric)


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
