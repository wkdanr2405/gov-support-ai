"""창업감면의 지역 구분(과밀억제권역·인구감소지역)을 시·군·구로 판정한다. 목록은 data/tax_params/regions.yaml."""
from functools import lru_cache
import yaml
from .params import PARAMS_DIR


@lru_cache(maxsize=None)
def _r() -> dict:
    return yaml.safe_load((PARAMS_DIR / "regions.yaml").read_text(encoding="utf-8"))


def sigungu_options(sido: str) -> list[str]:
    """수도권 시·도의 시·군·구 선택지. 서울과 수도권 밖은 비어 있다."""
    r = _r()
    if sido == "인천":
        return list(r["incheon_sigungu"])
    if sido == "경기":
        return (r["overcrowded"]["gyeonggi_whole"] + list(r["overcrowded"]["gyeonggi_partial"])
                + r["pop_decline"]["gyeonggi"] + r["gyeonggi_other"])
    return []


def classify(sido: str, sigungu: str | None = None, in_overcrowded_part: bool | None = None) -> dict:
    """반환: {'area': 'overcrowded'|'capital_other'|'pop_decline'|'non_capital', 'needs_check': 안내문 또는 None}
    일부만 과밀억제권역인 시·군·구는 in_overcrowded_part(사업장이 과밀억제권역 부분에 있는지)로 정한다."""
    r = _r()
    if sido not in ("서울", "인천", "경기"):
        return {"area": "non_capital", "needs_check": None}
    if sido == "서울":
        return {"area": "overcrowded", "needs_check": None}
    if sido == "인천":
        kind = r["incheon_sigungu"].get(sigungu)
        if kind == "mixed":
            note = r["overcrowded"]["incheon_note"]
            area = "overcrowded" if in_overcrowded_part is not False else "capital_other"
            return {"area": area, "needs_check": note}
        return {"area": kind or "overcrowded", "needs_check": None}
    # 경기
    o = r["overcrowded"]
    if sigungu in o["gyeonggi_whole"]:
        return {"area": "overcrowded", "needs_check": None}
    if sigungu in o["gyeonggi_partial"]:
        area = "overcrowded" if in_overcrowded_part is not False else "capital_other"
        return {"area": area, "needs_check": o["gyeonggi_partial"][sigungu]}
    if sigungu in r["pop_decline"]["gyeonggi"]:
        return {"area": "pop_decline", "needs_check": None}
    return {"area": "capital_other", "needs_check": None}
