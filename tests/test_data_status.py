"""외부 공고 API 실패 안내 (피드백 11/25 ②): 상태 모델, 실패 이유, 저장본·샘플 대체, 장애 시연 모드."""
import json
from datetime import date

import pytest

from src.data_sources import live
from src.data_sources.snapshots import save_snapshot
from src.data_sources.status import banner, describe

KS_RAW = [{"pbanc_sn": 900001, "biz_pbanc_nm": "실시간 창업 지원사업", "pbanc_rcpt_end_dt": "20271231", "detl_pg_url": "https://example.com/k"}]
BZ_RAW = [{"pblancId": "PBLN_LIVE", "pblancNm": "실시간 기업마당 사업", "reqstBeginEndDe": "20260101 ~ 20271231", "jrsdInsttNm": "중소벤처기업부"}]


@pytest.fixture
def snaps(tmp_path):
    save_snapshot("kstartup", [{"pbanc_sn": 1, "biz_pbanc_nm": "저장본 사업 K"}], tmp_path)
    save_snapshot("bizinfo", [{"pblancId": "OLD", "pblancNm": "저장본 사업 B", "jrsdInsttNm": "중소벤처기업부"}], tmp_path)
    return tmp_path


def ok_k(timeout=8):
    return KS_RAW


def ok_b(timeout=8):
    return BZ_RAW


def boom(msg):
    def f(timeout=8):
        raise RuntimeError(msg)
    return f


def run(snaps, k=ok_k, b=ok_b, **kw):
    return live.load_with_status({"kstartup": k, "bizinfo": b}, directory=snaps, **kw)


def by(statuses):
    return {s["source"]: s for s in statuses}


def test_not_tried_uses_snapshot_and_warns_when_old(snaps):
    items, st = live.load_with_status(None, directory=snaps, today=date(2099, 1, 1))
    assert {s["mode"] for s in st} == {"snapshot"} and len(items) == 2
    b = banner(st)
    assert b["level"] == "warning" and "일이 지나" in " ".join(b["lines"])          # 오래된 저장본은 숨기지 않고 알린다


def test_all_live_ok(snaps):
    items, st = run(snaps)
    assert {s["mode"] for s in st} == {"live"} and {i["title"] for i in items} == {"실시간 창업 지원사업", "실시간 기업마당 사업"}
    assert banner(st)["level"] == "success"


def test_one_source_fails_falls_back_to_its_snapshot_and_says_why(snaps):
    items, st = run(snaps, k=boom("K-Startup API 연결 실패: timeout"))
    s = by(st)
    assert s["kstartup"]["mode"] == "fallback" and "연결" in s["kstartup"]["reason"] and s["kstartup"]["count"] == 1 and s["kstartup"]["date"]
    assert s["bizinfo"]["mode"] == "live"
    assert {i["title"] for i in items} == {"저장본 사업 K", "실시간 기업마당 사업"}
    b = banner(st)
    assert b["level"] == "error" and "저장본" in b["title"] and any("K-Startup" in x and "연결" in x for x in b["lines"])
    assert "원문" in " ".join(b["lines"])


def test_reason_texts_are_plain_and_never_leak_keys(snaps):
    for msg, word in (("DATA_GO_KR_API_KEY가 없습니다. .env", "키"), ("K-Startup API 응답 오류 403: forbidden", "403"),
                      ("기업마당 API 연결 실패: ReadTimeout", "연결")):
        _, st = run(snaps, k=boom(msg))
        r = by(st)["kstartup"]["reason"]
        assert word in r and ".env" not in r and "Traceback" not in r


def test_both_fail_and_no_snapshot_means_no_announcements_and_no_sample(tmp_path):
    items, st = live.load_with_status({"kstartup": boom("연결 실패"), "bizinfo": boom("연결 실패")}, directory=tmp_path)
    assert items == [] and all(s["mode"] == "missing" for s in st)
    b = banner(st)
    assert b["level"] == "error" and "추천할 수 없습니다" in b["title"] and "세액공제" in " ".join(b["lines"])
    assert "샘플" not in " ".join([b["title"], *b["lines"]])


def test_partial_failure_banner_is_red_with_per_line_marks(snaps):
    _, st = run(snaps, force="partial")
    b = banner(st)
    assert b["level"] == "error" and "일부" in b["title"]
    assert b["lines"][0].startswith("❌") and b["lines"][1].startswith("✅")


def test_all_failure_with_snapshot_is_red(snaps):
    _, st = run(snaps, force="all")
    assert banner(st)["level"] == "error" and "저장본으로 추천했습니다" in banner(st)["title"]


@pytest.mark.parametrize("force,expect", [("partial", {"kstartup": "fallback", "bizinfo": "live"}),
                                          ("all", {"kstartup": "fallback", "bizinfo": "fallback"})])
def test_outage_demo_modes(snaps, force, expect):
    _, st = run(snaps, force=force)
    assert {k: v["mode"] for k, v in by(st).items()} == expect
    assert "장애 시연" in by(st)["kstartup"]["reason"]


def test_outage_demo_nosnap_shows_no_announcements(snaps):
    items, st = run(snaps, force="nosnap")
    assert items == [] and all(s["mode"] == "missing" for s in st)


def test_describe_lines(snaps):
    _, st = run(snaps, k=boom("연결 실패"))
    s = by(st)
    assert "실시간" in describe(s["bizinfo"]) and "저장본" in describe(s["kstartup"]) and "실패" in describe(s["kstartup"])
