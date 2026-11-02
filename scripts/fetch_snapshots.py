"""공고를 API로 받아 data/snapshots에 저장한다. 키는 .env에서 읽는다.
사용: python scripts/fetch_snapshots.py [kstartup|bizinfo|all]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv

load_dotenv()
from src.data_sources import bizinfo, kstartup
from src.data_sources.snapshots import save_snapshot

which = sys.argv[1] if len(sys.argv) > 1 else "all"
for name, mod in (("kstartup", kstartup), ("bizinfo", bizinfo)):
    if which in (name, "all"):
        try:
            raw = mod.fetch_raw()
            path = save_snapshot(name, raw)
            print(f"{name}: {len(raw)}건 저장 → {path}")
        except Exception as e:
            print(f"{name}: 실패 - {e}")
