"""법령 수치 파일(YAML)을 읽는다. 수치는 코드에 쓰지 않고 data/tax_params/*.yaml에만 둔다."""
from functools import lru_cache
from pathlib import Path

import yaml

PARAMS_DIR = Path(__file__).resolve().parents[2] / "data" / "tax_params"


@lru_cache(maxsize=None)
def load_params(year: int = 2026) -> dict:
    path = PARAMS_DIR / f"{year}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"{year}년 수치 파일이 없습니다: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))
