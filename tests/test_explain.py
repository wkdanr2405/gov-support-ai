from types import SimpleNamespace

from src.report.explain import build_facts, explain, template_text, validate

RES = {"increases": {"youth": 2, "other": 1}, "total_first_year": 6800, "employment_by_year": [1800, 4100, 4400],
       "total_employment_3y": 10300, "rnd_credit": 5000}
INP = {"region": "capital"}
MATCH = [{"title": "기술개발 지원사업", "d_day": 18, "matched_keywords": ["기술개발"]}]
FACTS = build_facts("전자부품 제조업", INP, RES, MATCH, "서울")


class FakeClient:
    def __init__(self, text):
        self.messages = SimpleNamespace(create=lambda **kw: SimpleNamespace(content=[SimpleNamespace(type="text", text=text)]))


def test_template_uses_engine_numbers():
    t = template_text(FACTS)
    assert "68,000,000원" in t and "18,000,000원" in t and "50,000,000원" in t


def test_good_llm_text_passes():
    ok = "첫해 예상 공제액은 68,000,000원입니다. 기술개발 지원사업(D-18)을 확인해 보세요."
    r = explain(FACTS, client=FakeClient(ok))
    assert r["source"] == "llm" and r["text"] == ok


def test_invented_number_falls_back():
    r = explain(FACTS, client=FakeClient("첫해 예상 공제액은 99,990,000원입니다."))
    assert r["source"] == "template" and "근거 없는 숫자" in r["note"]


def test_forbidden_phrase_falls_back():
    assert validate("세무 자문을 대신해 드립니다. 68000000원", FACTS)


def test_no_key_uses_template(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = explain(FACTS)
    assert r["source"] == "template"


def test_api_error_falls_back():
    class Boom:
        class messages:
            @staticmethod
            def create(**kw):
                raise RuntimeError("down")
    assert explain(FACTS, client=Boom())["source"] == "template"


def test_long_titles_are_not_cut_inside_parentheses():
    facts = build_facts("제조업", INP, RES, [{"title": "2026년 기술컨설팅 지원사업(서울 스타트업 Tech trade-on 프로그램) 참여기업 모집", "d_day": 59, "matched_keywords": []}], "서울")
    text = template_text(facts)
    assert "(서울 스타트업 Tech (D" not in text and "2026년 기술컨설팅 지원사업 (D-59)" in text
