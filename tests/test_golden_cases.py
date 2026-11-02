"""정답 사례 검증. 2주차에 src/tax_engine.calculate가 만들어지면 자동으로 실행된다.

엔진이 지켜야 할 약속(계약):
  calculate(input: dict) -> dict  with keys
    employment_by_year: [1차, 2차, 3차 연도 통합고용 공제액(만원)]
    rnd_credit: 연구·인력개발비 공제액(만원)
    rnd_method: "current" | "increase" | "none"
"""
from pathlib import Path

import pytest
import yaml

CASES = yaml.safe_load(
    (Path(__file__).resolve().parent / "golden_cases.yaml").read_text(encoding="utf-8")
)["cases"]

try:
    from src.tax_engine import calculate
except ImportError:  # 아직 엔진 미구현
    calculate = None


@pytest.mark.skipif(calculate is None, reason="규칙 엔진 미구현 (2주차 작업)")
@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_case(case):
    result = calculate(case["input"])
    exp = case["expect"]
    assert result["employment_by_year"] == exp["employment_by_year"]
    assert result["rnd_credit"] == exp["rnd_credit"]
    assert result["rnd_method"] == exp["rnd_method"]


def test_case_file_is_wellformed():
    assert len(CASES) >= 15
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids))
    for c in CASES:
        assert len(c["expect"]["employment_by_year"]) == 3
