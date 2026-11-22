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


def test_brief_pdf_is_single_page_with_all_documents():
    from src.experts import load_experts
    from src.report.docs import required_documents
    from src.report.pdf import build_brief_pdf
    ids = ("integrated_employment", "rnd_credit", "disaster_loss", "startup_sme_exemption", "sme_special_reduction")
    res = {"total_first_year": 6800, "overlap_note": "중복 적용 배제: 예시 문장입니다.",
           "credits": [{"id": i, "name": i, "status": "computed", "in_total": True, "amount_first_year": 100} for i in ids]}
    co = dict(name="가상전자(주)", email="contact1@example.com", phone="010-0000-0001", industry="전자부품 제조업", sido="서울",
              founded="2023-03-15", is_sme=True, ep=10, ec=13, yp=0, yc=2)               # 기업명·가상 연락처 행이 늘어도 1페이지
    pdf = build_brief_pdf("입력하신 값 기준 예시", co, res, required_documents(res), M, expert=load_experts()[0],
                          topic="둘 다", channel="화상", memo="일정 문의 " * 20, receipt="DEMO-ABC123")
    assert pdf[:4] == b"%PDF" and len(re.findall(rb"/Type\s*/Page[^s]", pdf)) == 1
