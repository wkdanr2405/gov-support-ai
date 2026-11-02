"""수치 파일(YAML) 점검: 모든 법령 수치 블록에 출처·확인일·verified 표시가 있는지."""
from pathlib import Path

import yaml

PARAMS = Path(__file__).resolve().parent.parent / "data" / "tax_params" / "2026.yaml"


def load():
    return yaml.safe_load(PARAMS.read_text(encoding="utf-8"))


def test_blocks_have_verified_and_date():
    p = load()
    for key in ("integrated_employment", "rnd_credit", "sme_test"):
        block = p[key]
        assert isinstance(block.get("verified"), bool), f"{key}: verified 표시 없음"
        assert block.get("checked_at"), f"{key}: 확인일 없음"


def _value_blocks(node, path=""):
    if isinstance(node, dict):
        if "value" in node:
            yield path, node
        for k, v in node.items():
            yield from _value_blocks(v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _value_blocks(v, f"{path}[{i}]")


def test_every_value_block_declares_verified():
    for path, block in _value_blocks(load()):
        assert isinstance(block.get("verified"), bool), f"{path}: verified 표시 없음"


def test_sme_industry_table():
    ind = {i["code"]: i["limit_eok"] for i in load()["sme_test"]["industries"]}
    assert ind["C26"] == 1000
    assert set(ind.values()) <= {400, 600, 800, 1000, 1200, 1500, 1800}


def test_employment_table_shape():
    sme = load()["integrated_employment"]["sme"]
    for region in ("capital_area", "non_capital_area"):
        for kind in ("youth_etc", "other"):
            row = sme[region][kind]
            assert len(row) == 3 and all(isinstance(v, int) and v > 0 for v in row)
            assert row == sorted(row), "연차가 올라갈수록 금액이 같거나 커야 함"
    # 수도권 밖이 수도권보다 같거나 큼
    for kind in ("youth_etc", "other"):
        assert all(a >= b for a, b in zip(sme["non_capital_area"][kind], sme["capital_area"][kind]))
