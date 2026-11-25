"""PDF 부록과 화면에 쓰는 '계산·추천 근거' (피드백 11/25 ②)."""
import re

import pytest

from src.data_sources.status import source_status
from src.report.evidence import build_evidence
from src.report.explain import build_facts, template_text
from src.report.pdf import build_pdf
from src.tax_engine import calculate, judge_sme
from src.tax_engine.params import load_params

INP = {"region": "capital", "employees_prev": 10, "employees_curr": 15, "youth_prev": 2, "youth_curr": 5, "rnd_curr": 8000,
       "rnd_prev": 6000, "ksic": "C26", "avg_revenue_eok": 50, "is_sme": True, "founded": "2023-03-15", "first_income_year": 2024,
       "youth_ceo": False, "corp_tax": 3000, "eligible_income_pct": 100, "startup_area": "capital_other",
       "disaster_lost_assets": 0, "disaster_total_assets": 0, "disaster_unpaid_tax": 0, "disaster_current_tax": 0,
       "disaster_other_reductions": 0}
M = [{"id": "179674", "source": "kstartup", "title": "기술개발 지원사업", "agency": "가상기관", "d_day": 18, "period_end": "2026-12-20",
      "url": "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=179674", "score": 62.0, "keyword": 0.6,
      "semantic": 0.71, "matched_keywords": ["기술개발", "R&D"], "flags": ["시·군·구 확인 필요"], "is_sample": False},
     {"id": "s-1", "source": "sample", "title": "샘플 사업", "agency": "가상", "d_day": None, "period_end": None, "url": "", "score": 40.0,
      "keyword": 0.4, "semantic": None, "matched_keywords": [], "flags": [], "is_sample": True}]


def _ev(matches=M):
    res = calculate(INP)
    sme = judge_sme({"ksic": "C26", "avg_revenue_eok": 50, "assets_eok": 40, "owned_by_large_corp": False})
    return res, build_evidence(res, sme, load_params(2026), matches, source_status(), {"마감": 3, "지역": 2}, 120,
                               [["소재지", "서울 (수도권)"]])


def test_cards_carry_check_date_and_evidence():
    for c in calculate(INP)["credits"]:
        assert c["checked_at"] and c["evidence"] and c["law_ref"]


def test_source_status_reports_snapshot_counts_and_date():
    st = {s["source"]: s for s in source_status()}
    assert st["kstartup"]["mode"] == "snapshot" and st["kstartup"]["count"] > 0 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", st["kstartup"]["date"])
    assert st["kstartup"]["label"].startswith("K-Startup")


def test_tax_rows_cite_law_and_mark_unverified():
    _, ev = _ev()
    rows = {r["name"]: r for r in ev["tax_rows"]}
    assert "조세특례제한법 제29조의8" in rows["통합고용세액공제"]["law_ref"]
    assert "미확인" in rows["창업중소기업 세액감면"]["status"]          # verified: false 는 확정처럼 보이지 않는다
    assert "조문 확인" in rows["통합고용세액공제"]["status"] and "2026-11-01" in rows["통합고용세액공제"]["status"]
    assert "중소기업 해당 여부" in rows and "중소기업기본법" in rows["중소기업 해당 여부"]["law_ref"]
    assert "중복 적용 배제" in rows and "제127조" in rows["중복 적용 배제"]["law_ref"]


def test_match_rows_have_source_id_link_and_score_parts():
    _, ev = _ev()
    a, b = ev["match_rows"]
    assert a["source_label"].startswith("K-Startup") and a["id"] == "179674" and a["url"].startswith("https://")
    assert "키워드 0.6" in a["why"] and "의미 0.71" in a["why"] and "기술개발" in a["why"]
    assert "실제 공고 아님" in b["source_label"]


def test_pdf_has_appendix_page_with_basis_and_sources():
    pypdf = pytest.importorskip("pypdf")
    from io import BytesIO
    res, ev = _ev()
    facts = build_facts("전자부품 제조업", {"region": "capital"}, res, M, "서울")
    pdf = build_pdf(facts, template_text(facts), M, ["가정 1"], evidence=ev)
    r = pypdf.PdfReader(BytesIO(pdf))
    assert len(r.pages) == 2
    p2 = r.pages[1].extract_text().replace("\n", "").replace(" ", "")
    for must in ("조세특례제한법제29조의8", "미확인", "K-Startup", "179674", "pbancSn=179674", "수집", "실제공고아님"):
        assert must in p2, must
    p1 = r.pages[0].extract_text().replace(" ", "")
    assert "부록" in p1                                                  # 1쪽에서 부록 위치를 안내한다


def test_pdf_without_evidence_still_works():
    facts = build_facts("전자부품 제조업", {"region": "capital"}, calculate(INP), M, "서울")
    assert build_pdf(facts, template_text(facts), M, [])[:4] == b"%PDF"


def test_appendix_stays_one_page_with_real_snapshots_and_many_notes():
    """실제 저장본 공고(긴 제목·확인 필요 표시)와 안내문이 많아도 본문 1쪽 + 부록 1쪽을 넘지 않는다."""
    pypdf = pytest.importorskip("pypdf")
    from datetime import date
    from io import BytesIO

    from src.data_sources import load_announcements
    from src.matching import build_profile, match
    from src.report.docs import required_documents
    res = calculate(INP)
    anns, _ = load_announcements()
    prof = build_profile("전자부품, 컴퓨터, 영상, 음향 및 통신장비 제조업", "서울", date(2023, 3, 15), 10, 15, 2, 5, 8000)
    out = match(prof, anns, None, top_n=10)
    sme = judge_sme({"ksic": "C26", "avg_revenue_eok": 50, "assets_eok": 40, "owned_by_large_corp": False})
    ev = build_evidence(res, sme, load_params(2026), out["items"], source_status(), out["excluded"], out["scored"],
                        [["입력 방식", "입력하신 값 기준 예시"], ["업종 · 소재지", "전자부품 제조업 · 서울"], ["설립일", "2023-03-15"],
                         ["평균 매출액 · 자산총액", "5,000,000,000원 · 4,000,000,000원"]])
    facts = build_facts("전자부품 제조업", INP, res, out["items"], "서울")
    pdf = build_pdf(facts, template_text(facts), out["items"], res["notes"], docs=required_documents(res), evidence=ev)
    assert len(pypdf.PdfReader(BytesIO(pdf)).pages) == 2
