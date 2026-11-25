"""공고 데이터 출처 상태. PDF 부록과 화면이 '어느 출처를, 언제 받은 저장본으로, 몇 건 썼는지'를 알려 줄 때 쓴다."""
from datetime import date

from .snapshots import SAMPLE_PATH, SNAP_DIR, load_snapshot

LABELS = {"kstartup": "K-Startup (창업진흥원)", "bizinfo": "기업마당 (중소벤처기업부)", "sample": "가상 샘플 공고 (실제 공고 아님)"}


def source_label(code: str) -> str:
    return LABELS.get(code, code or "출처 미상")


def source_status(directory=SNAP_DIR, today: date | None = None) -> list[dict]:
    """출처별 상태 목록. mode: 'snapshot'(저장본 사용) / 'sample'(저장본이 없어 가상 샘플 사용).
    date는 저장본을 받은 날(YYYY-MM-DD), age_days는 오늘까지 지난 날수."""
    today = today or date.today()
    out = []
    for code in ("kstartup", "bizinfo"):
        snap = load_snapshot(code, directory)
        if snap and snap.get("items"):
            d = snap["fetched_at"][:10]
            out.append({"source": code, "label": source_label(code), "mode": "snapshot", "count": snap["count"], "date": d,
                        "age_days": (today - date.fromisoformat(d)).days})
    if not out:
        import json
        n = len(json.loads(SAMPLE_PATH.read_text(encoding="utf-8")))
        out.append({"source": "sample", "label": source_label("sample"), "mode": "sample", "count": n, "date": "", "age_days": None})
    return out
