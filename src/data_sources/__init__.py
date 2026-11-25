"""공고 데이터 출처 (테스트·스크립트용 읽기 함수; 화면은 live.load_with_status를 쓰며 가상 샘플을 보여 주지 않는다). 실제 호출은 scripts/fetch_snapshots.py가 한다."""
import json

from . import bizinfo, kstartup
from .snapshots import SAMPLE_PATH, SNAP_DIR, load_snapshot, save_snapshot

__all__ = ["load_announcements", "load_snapshot", "save_snapshot", "kstartup", "bizinfo"]

_NORMALIZERS = {"kstartup": kstartup.normalize, "bizinfo": bizinfo.normalize}


def load_announcements(directory=SNAP_DIR) -> tuple[list[dict], str]:
    """(공고 목록, 출처 설명). 실제 저장본이 있으면 그것을, 없으면 가상 샘플을 쓴다."""
    items: list[dict] = []
    used = []
    for source, norm in _NORMALIZERS.items():
        snap = load_snapshot(source, directory)
        if snap and snap.get("items"):
            items += [norm(i) for i in snap["items"]]
            used.append(f"{source} 저장본 {snap['count']}건 ({snap['fetched_at'][:10]})")
    if items:
        return items, " · ".join(used)
    sample = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    return sample, f"가상 샘플 공고 {len(sample)}건 (실제 공고 아님)"
