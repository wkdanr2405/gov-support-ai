"""공고 데이터 출처 상태. PDF 부록과 화면이 '어느 출처를, 언제 받은 저장본으로, 몇 건 썼는지', 그리고 실시간 조회가 실패했는지를 알릴 때 쓴다.

상태(mode): live 실시간 조회 성공 / fallback 실시간 조회 실패 → 저장본 사용 / snapshot 조회를 시도하지 않고 저장본 사용 /
missing 조회 실패에 저장본도 없음 / empty 조회도 안 했고 저장본도 없음. 가상 샘플 공고는 화면에 쓰지 않는다."""
from datetime import date

from .snapshots import SNAP_DIR, load_snapshot

LABELS = {"kstartup": "K-Startup (창업진흥원)", "bizinfo": "기업마당 (중소벤처기업부)"}
OLD_DAYS = 7      # 저장본이 이 날수보다 오래되면 '오래됨'으로 알린다


def source_label(code: str) -> str:
    return LABELS.get(code, code or "출처 미상")


def snapshot_info(code: str, directory=SNAP_DIR, today: date | None = None) -> dict | None:
    snap = load_snapshot(code, directory)
    if not (snap and snap.get("items")):
        return None
    d = snap["fetched_at"][:10]
    return {"count": snap["count"], "date": d, "age_days": ((today or date.today()) - date.fromisoformat(d)).days}


def source_status(directory=SNAP_DIR, today: date | None = None) -> list[dict]:
    """조회를 시도하지 않고 저장본을 쓸 때의 출처별 상태."""
    out = []
    for code in ("kstartup", "bizinfo"):
        info = snapshot_info(code, directory, today)
        if info:
            out.append({"source": code, "label": source_label(code), "mode": "snapshot", "reason": "", **info})
        else:
            out.append({"source": code, "label": source_label(code), "mode": "empty", "reason": "", "count": 0, "date": "", "age_days": None})
    return out


def describe(s: dict, with_label: bool = True) -> str:
    """상태 한 줄 설명 (화면 캡션과 PDF 부록에서 같이 쓴다)."""
    m, lab = s["mode"], (s["label"] + ": " if with_label else "")
    snap = f"저장본 {s['count']:,}건 ({s['date']} 수집, {s['age_days']}일 경과)"
    if m == "live":
        return f"{lab}실시간 조회 {s['count']:,}건 ({s['date']})"
    if m == "fallback":
        return f"{lab}실시간 조회 실패({s['reason']}) → {snap} 사용"
    if m == "snapshot":
        return f"{lab}{snap}"
    if m == "empty":
        return f"{lab}저장본 없음"
    if m == "missing":
        return f"{lab}실시간 조회 실패({s['reason']}), 저장본도 없음"
    return f"{lab}{s['count']:,}건"


def banner(statuses: list[dict]) -> dict:
    """사용자에게 보여 줄 안내 띠. level은 success/info/warning/error. 실패 화면은 모두 error(붉은색, ❌)로 통일한다."""
    note = "최신 공고와 다를 수 있습니다. 마감과 신청 자격은 반드시 원문 링크에서 확인하세요."
    usable = [s for s in statuses if s["mode"] in ("live", "fallback", "snapshot")]
    if not usable:
        return {"level": "error", "title": "공고를 불러오지 못해 지원사업을 추천할 수 없습니다",
                "lines": [describe(s) for s in statuses] +
                         ["세액공제·감면 예상액 계산은 공고와 관계없이 계속 사용할 수 있습니다. 잠시 뒤 '최신 공고 확인'으로 다시 시도해 주세요."]}
    failed = [s for s in statuses if s["mode"] in ("fallback", "missing")]
    if failed:
        if len(failed) == len(statuses):
            return {"level": "error", "title": "최신 공고를 불러오지 못해 저장본으로 추천했습니다",
                    "lines": [describe(s) for s in statuses] + [note + " '최신 공고 확인'으로 다시 시도할 수 있습니다."]}
        return {"level": "error", "title": "일부 공고를 불러오지 못해 저장본을 섞어 추천했습니다",
                "lines": [("❌ " if s in failed else "✅ ") + describe(s) for s in statuses] + [note + " '최신 공고 확인'으로 다시 시도할 수 있습니다."]}
    if all(s["mode"] == "live" for s in statuses):
        return {"level": "success", "title": "실시간 공고를 불러왔습니다", "lines": [describe(s) for s in statuses]}
    lines = [describe(s) for s in statuses]
    old = max((s["age_days"] or 0) for s in statuses)
    if old > OLD_DAYS:
        return {"level": "warning", "title": "저장본 공고를 기준으로 추천했습니다 (오래된 자료)",
                "lines": lines + [f"수집한 지 {old}일이 지나 그사이 마감·변경된 공고가 있을 수 있습니다. '최신 공고 확인'을 눌러 보세요. " + note]}
    return {"level": "info", "title": "저장본 공고를 기준으로 추천했습니다", "lines": lines + [note]}


def item_source_line(item: dict, statuses: list[dict]) -> str:
    """공고 카드 한 줄: 출처 · 공고번호 · 어느 시점 자료인지."""
    st = next((s for s in statuses if s["source"] == item.get("source")), None)
    when = ""
    if st:
        when = {"live": f" · 실시간 조회 {st['date']}", "fallback": f" · 저장본 {st['date']} 수집 (실시간 조회 실패)",
                "snapshot": f" · 저장본 {st['date']} 수집"}.get(st["mode"], "")
    return f"출처: {source_label(item.get('source', ''))} · 공고번호 {item.get('id', '-')}{when}"
