"""공고 실시간 조회 시도 + 실패 시 저장본·샘플로 대체. 실패 이유는 쉬운 말로 바꾸고 API 키는 어디에도 남기지 않는다.
force는 발표용 '장애 시연' 모드: partial=K-Startup만 실패, all=둘 다 실패(저장본 사용), nosnap=둘 다 실패하고 저장본도 없음(공고 없음 → 추천 불가). 가상 샘플 공고는 쓰지 않는다."""
import re
from datetime import date

from . import bizinfo, kstartup
from .snapshots import SNAP_DIR, load_snapshot
from .status import snapshot_info, source_label, source_status

NORMALIZERS = {"kstartup": kstartup.normalize, "bizinfo": bizinfo.normalize}
DEFAULT_FETCHERS = {"kstartup": lambda timeout=8: kstartup.fetch_raw(timeout=timeout, retries=1),
                    "bizinfo": lambda timeout=8: bizinfo.fetch_raw(timeout=timeout)}
OUTAGE_MODES = {"off": "끔 (실제 조회 결과대로 표시)", "partial": "일부 실패 (K-Startup만)", "all": "모두 실패 (저장본으로 대체)", "nosnap": "공고 없음 (모두 실패 + 저장본 없음)"}


def explain_error(e: Exception) -> str:
    s = str(e)
    if "장애 시연" in s:
        return "장애 시연 모드입니다 (실제 장애가 아님)"
    if "API_KEY" in s or "키가 없" in s:
        return "접속 키(API 키)가 설정되어 있지 않습니다"
    m = re.search(r"응답 오류 (\d{3})", s)
    if m:
        return f"공고 서버가 오류({m.group(1)})를 돌려보냈습니다"
    if "연결" in s or "Timeout" in type(e).__name__ or "Connection" in type(e).__name__:
        return "공고 서버에 연결하지 못했습니다 (서버 점검이나 네트워크 차단 가능성)"
    if "0건" in s:
        return "응답은 왔지만 공고가 한 건도 없었습니다"
    if isinstance(e, ValueError):
        return "응답 형식을 읽지 못했습니다"
    return "알 수 없는 오류로 조회하지 못했습니다"


def _forced_fail(code: str, force: str | None):
    if force == "partial" and code == "kstartup" or force in ("all", "nosnap"):
        def f(timeout=8):
            raise RuntimeError("장애 시연 모드: 외부 공고 서버가 응답하지 않는 상황을 재현합니다")
        return f
    return None


def load_with_status(fetchers: dict | None, directory=SNAP_DIR, force: str | None = None, today: date | None = None) -> tuple[list[dict], list[dict]]:
    """(공고 목록, 출처별 상태). fetchers가 None이면 조회를 시도하지 않고 저장본을 쓴다."""
    today = today or date.today()
    items: list[dict] = []
    if fetchers is None:
        statuses = source_status(directory, today)
        for s in statuses:
            if s["mode"] == "snapshot":
                items += [NORMALIZERS[s["source"]](i) for i in load_snapshot(s["source"], directory)["items"]]
    else:
        statuses = []
        for code, norm in NORMALIZERS.items():
            base = {"source": code, "label": source_label(code), "reason": ""}
            try:
                fetch = _forced_fail(code, force) or fetchers[code]
                raw = fetch()
                if not raw:
                    raise RuntimeError("응답 0건")
                items += [norm(i) for i in raw]
                statuses.append({**base, "mode": "live", "count": len(raw), "date": today.isoformat(), "age_days": 0})
            except Exception as e:                       # 어떤 실패든 화면이 멈추지 않게 저장본으로 대체한다
                base["reason"] = explain_error(e)
                info = None if force == "nosnap" else snapshot_info(code, directory, today)
                if info:
                    items += [norm(i) for i in load_snapshot(code, directory)["items"]]
                    statuses.append({**base, "mode": "fallback", **info})
                else:
                    statuses.append({**base, "mode": "missing", "count": 0, "date": "", "age_days": None})
    return items, statuses
