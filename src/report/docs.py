"""공제·감면별 신청·신고 준비 서류 안내. data/required_docs.yaml에서 읽는다 (참고용 일반 안내).

합계에 들어간 항목(금액이 계산되었고 중복 배제에서 제외되지 않은 항목)만 보여 준다.
"""
from pathlib import Path

import yaml

PATH = Path(__file__).resolve().parents[2] / "data" / "required_docs.yaml"
NOTICE = "서류 목록은 일반적인 안내입니다. 실제 서식과 첨부서류는 홈택스·관할 세무서·세무 전문가에게 확인하세요."


def load_docs() -> dict:
    return yaml.safe_load(PATH.read_text(encoding="utf-8"))


def required_documents(res: dict) -> list[dict]:
    """계산 결과(res)에서 합계에 들어간 항목별 [{id, name, timing, documents, verified}]."""
    data = load_docs()
    out = []
    for c in res.get("credits", []):
        if c.get("status") == "computed" and c.get("in_total") and c["id"] in data:
            d = data[c["id"]]
            out.append({"id": c["id"], "name": d["name"], "timing": d["timing"], "documents": list(d["documents"]),
                        "verified": d["verified"]})
    return out
