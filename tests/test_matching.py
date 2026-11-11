from datetime import date

import numpy as np

from src.data_sources import load_announcements
from src.data_sources.snapshots import SAMPLE_PATH
from src.data_sources.common import normalize_regions, parse_period
from src.matching import build_profile, match
from src.matching.filters import parse_biz_age

TODAY = date(2026, 11, 2)
SAMPLE_ONLY = SAMPLE_PATH.parent / "_no_snapshots"   # 저장본이 없는 폴더 → 항상 가상 샘플 사용


class FakeEmbedder:
    """모델 없이 글자 겹침으로 만든 가짜 임베딩 (테스트 속도·재현성용)."""
    model_name = "fake"

    def embed(self, texts):
        out = []
        for t in texts:
            v = np.zeros(64, dtype=np.float32)
            for ch in t:
                v[ord(ch) % 64] += 1
            out.append(v / (np.linalg.norm(v) or 1))
        return np.array(out)


def profile(**kw):
    base = dict(industry_name="전자부품, 컴퓨터, 영상, 음향 및 통신장비 제조업", sido="서울", founded=date(2023, 3, 15),
                employees_prev=10, employees_curr=13, youth_prev=0, youth_curr=2, rnd_curr=20000, today=TODAY)
    base.update(kw)
    return build_profile(**base)


def test_biz_age():
    assert parse_biz_age("3년미만,5년미만,7년미만", 3) is True
    assert parse_biz_age("3년미만", 5) is False
    assert parse_biz_age("예비창업자", 3) is False
    assert parse_biz_age("", 3) is None


def test_filters_remove_expired_wrong_region_and_age():
    ann, _ = load_announcements(directory=SAMPLE_ONLY)
    out = match(profile(), ann, None, top_n=50, today=TODAY)
    ids = {r["id"] for r in out["items"]}
    assert "S11" not in ids          # 마감
    assert "S05" not in ids and "S08" not in ids and "S18" not in ids   # 다른 지역
    assert "S04" not in ids          # 예비창업자 대상
    assert out["excluded"]["마감"] == 1


def test_region_change_changes_result():
    ann, _ = load_announcements(directory=SAMPLE_ONLY)
    ids = {r["id"] for r in match(profile(sido="부산"), ann, None, top_n=50, today=TODAY)["items"]}
    assert "S05" in ids and "S03" not in ids


def test_manufacturing_rnd_ranks_first_keyword_only():
    ann, _ = load_announcements(directory=SAMPLE_ONLY)
    top = match(profile(), ann, None, top_n=3, today=TODAY)["items"]
    assert top[0]["id"] in ("S02", "S16")
    assert all(r["is_sample"] for r in top)


def test_hybrid_runs_with_fake_embedder(tmp_path):
    ann, _ = load_announcements(directory=SAMPLE_ONLY)
    out = match(profile(), ann, FakeEmbedder(), top_n=5, today=TODAY, index_path=tmp_path / "e.npz")
    assert out["semantic_used"] and len(out["items"]) == 5
    assert all(0 <= r["semantic"] <= 1 for r in out["items"])
    # 두 번째 호출은 저장된 벡터를 재사용해도 같은 결과
    again = match(profile(), ann, FakeEmbedder(), top_n=5, today=TODAY, index_path=tmp_path / "e.npz")
    assert [r["id"] for r in out["items"]] == [r["id"] for r in again["items"]]


def test_region_and_period_parsing():
    assert set(normalize_regions("서울특별시")) == {"서울"}
    assert str(parse_period("20261101 ~ 20261130")[1]) == "2026-11-30"


def test_real_kstartup_snapshot_normalizes():
    """실제 저장본이 있을 때만: 모든 공고가 같은 형식으로 정제되고 마감일·링크가 있다."""
    import pytest
    from src.data_sources import kstartup
    from src.data_sources.snapshots import SNAP_DIR, load_snapshot
    snap = load_snapshot("kstartup", SNAP_DIR)
    if not snap:
        pytest.skip("저장본 없음")
    items = [kstartup.normalize(i) for i in snap["items"]]
    assert len(items) == snap["count"] > 0
    assert all(a["title"] and a["end"] and a["url"] for a in items)


def test_bizinfo_regions_from_agency_and_title():
    from src.data_sources import bizinfo
    base = {"pblancId": "x", "pblancNm": "", "jrsdInsttNm": "중소벤처기업부", "reqstBeginEndDe": "2026-11-02 ~ 2026-11-26"}
    assert bizinfo.normalize({**base, "pblancNm": "[대구] 모빌리티 지원"})["regions"] == ["대구"]
    assert bizinfo.normalize({**base, "pblancNm": "수출 물류비 지원"})["regions"] == ["전국"]
    assert bizinfo.normalize({**base, "jrsdInsttNm": "경상북도"})["regions"] == ["경북"]
    n = bizinfo.normalize({**base, "reqstBeginEndDe": "예산 소진시까지", "bsnsSumryCn": "<p>안내 &amp; 문의</p>"})
    assert n["end"] is None and n["summary"] == "안내 & 문의"
    assert bizinfo.normalize(base)["end"] == "2026-11-26"


def test_event_announcements_are_excluded():
    from src.matching.filters import check, is_event
    a = {"title": "스타트업을 위한 정부 R&D 특강", "regions": ["전국"], "end": "2026-12-01", "ongoing_flag": "Y", "biz_age": ""}
    assert is_event(a)
    ok, reason, _ = check(a, {"sido": "서울", "age_years": 3}, TODAY)
    assert not ok and reason == "교육·행사"
    assert not is_event({"title": "중소기업 기술개발 지원사업"})


def test_announcement_text_drops_broken_glyphs():
    from src.data_sources.common import make_announcement
    a = make_announcement(title="모집​공고", target=" 모집대상 : 창업 후 10년", summary="가\xa0나�다")
    assert a["title"] == "모집공고" and a["target"] == "· 모집대상 : 창업 후 10년" and a["summary"] == "가 나다"
