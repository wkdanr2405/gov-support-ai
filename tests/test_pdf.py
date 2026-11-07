import re

from src.report.explain import build_facts, template_text
from src.report.pdf import build_pdf

RES = {"increases": {"youth": 2, "other": 1}, "total_first_year": 6800, "employment_by_year": [1800, 4100, 4400],
       "total_employment_3y": 10300, "rnd_credit": 5000}
M = [{"title": "기술개발 지원사업", "d_day": 18, "period_end": "2026-11-20", "matched_keywords": ["기술개발", "R&D"]},
     {"title": "상시 접수 사업 <테스트> & 특수문자", "d_day": None, "period_end": None, "matched_keywords": []}]


def test_pdf_is_single_page_and_has_text():
    facts = build_facts("전자부품 제조업", {"region": "capital"}, RES, M, "서울")
    pdf = build_pdf(facts, template_text(facts) * 2, M, ["가정 1", "가정 2"])
    assert pdf[:4] == b"%PDF"
    assert len(re.findall(rb"/Type\s*/Page[^s]", pdf)) == 1
    assert len(pdf) > 5000


def test_pdf_with_all_documents_still_single_page():
    from src.report.docs import required_documents
    res = {**RES, "credits": [{"id": i, "status": "computed", "in_total": True} for i in
           ("integrated_employment", "rnd_credit", "disaster_loss", "startup_sme_exemption", "sme_special_reduction")]}
    docs = required_documents(res)
    assert len(docs) == 5
    facts = build_facts("전자부품 제조업", {"region": "capital"}, RES, M, "서울")
    pdf = build_pdf(facts, template_text(facts), M, ["가정 1", "가정 2"], docs=docs)
    assert len(re.findall(rb"/Type\s*/Page[^s]", pdf)) == 1
