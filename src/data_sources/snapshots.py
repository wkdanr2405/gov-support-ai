"""API 응답 저장본(스냅샷). 시연 중 API가 실패해도 이 파일로 동작하게 한다."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAP_DIR = ROOT / "data" / "snapshots"
SAMPLE_PATH = ROOT / "data" / "sample" / "announcements_sample.json"


def save_snapshot(source: str, raw_items: list[dict], directory: Path = SNAP_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{source}.json"
    payload = {"source": source, "fetched_at": datetime.now(timezone.utc).isoformat(), "count": len(raw_items), "items": raw_items}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def load_snapshot(source: str, directory: Path = SNAP_DIR) -> dict | None:
    path = directory / f"{source}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
