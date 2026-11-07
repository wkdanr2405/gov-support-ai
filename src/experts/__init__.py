"""전문가 연결 시연: 가상 전문가 후보 정렬과 '상담 전달 자료' 만들기.

실제 전송·저장은 하지 않는다. 후보는 data/sample/experts.yaml의 가상 데이터다.
정렬은 규칙(합계에 들어간 공제·감면 id와 전문 분야가 겹치는 수)만 쓰고, 금액은 규칙 엔진 결과를 그대로 옮긴다.
"""
import hashlib
from pathlib import Path

import yaml

from src.money import won_text

PATH = Path(__file__).resolve().parents[2] / "data" / "sample" / "experts.yaml"
DISCLAIMER = "참고용 예상치이며 최종 판단은 세무 전문가가 합니다."
STEPS = ["요청 접수", "전문가 검토", "상담 일정 안내", "상담 진행", "신청 준비 (전문가와 상의해 진행)"]


def load_experts() -> list[dict]:
    return yaml.safe_load(PATH.read_text(encoding="utf-8"))["experts"]


def rank_experts(experts: list[dict], credit_ids: list[str], want_gov_support: bool = True) -> list[dict]:
    """합계에 들어간 공제·감면 id와 겹치는 분야가 많은 순. 같으면 원래 순서. 각 항목에 score·reasons를 붙여 돌려준다."""
    names = {"rnd_credit": "연구·인력개발비 공제", "integrated_employment": "통합고용 공제", "disaster_loss": "재해손실 공제",
             "startup_sme_exemption": "창업 감면", "sme_special_reduction": "중소기업 특별감면", "gov_support": "정부지원사업"}
    ranked = []
    for i, e in enumerate(experts):
        hit = [s for s in e["specialties"] if s in credit_ids or (want_gov_support and s == "gov_support")]
        ranked.append({**e, "score": len(hit), "reasons": [names.get(s, s) for s in hit], "_i": i})
    ranked.sort(key=lambda e: (-e["score"], e["_i"]))
    for e in ranked:
        e.pop("_i")
    return ranked


def build_brief(basis: str, company: dict, res: dict, docs: list[dict], matches: list[dict],
                topic: str | None = None, memo: str = "") -> str:
    """전문가에게 건넬 요약 글. 금액은 엔진 결과(만원)를 원 단위로만 바꿔 옮긴다."""
    lines = [f"[상담 전달 자료 · 시연] {basis}", "",
             "■ 기업 (입력값)",
             f"- 업종: {company['industry']} / 소재지: {company['sido']} / 설립: {company['founded']}",
             f"- 중소기업 판정: {'해당' if company['is_sme'] else '확인 필요'}",
             f"- 상시근로자: 전년 {company['ep']}명 → 당해 {company['ec']}명 (청년 등 {company['yp']}명 → {company['yc']}명)", "",
             "■ 계산 결과 (규칙 엔진, 참고용)"]
    shown = [c for c in res.get("credits", []) if c["status"] == "computed" and c.get("in_total")]
    lines += [f"- {c['name']}: {won_text(c['amount_first_year'])}" for c in shown] or ["- 금액이 계산된 공제·감면 없음"]
    lines.append(f"- 첫해 예상 감면액 합계: {won_text(res['total_first_year'])}")
    if res.get("overlap_note"):
        lines.append(f"- {res['overlap_note']}")
    if docs:
        lines += ["", "■ 신청 때 준비할 서류 (일반 안내, 확인 전)"]
        for d in docs:
            lines.append(f"- {d['name']}: " + "; ".join(d["documents"]))
    if matches:
        lines += ["", "■ 추천 정부지원사업 (상위 3건)"] + [f"- {m['title']}" for m in matches[:3]]
    if topic:
        lines += ["", f"■ 상담 희망 분야: {topic}"]
    if memo.strip():
        lines += ["", f"■ 추가로 전할 말: {memo.strip()}"]
    lines += ["", f"※ {DISCLAIMER} 실제 신청 서류와 요건은 전문가와 확인하세요."]
    return "\n".join(lines)


def receipt_no(brief: str) -> str:
    """시연용 접수번호. 저장하지 않고 내용에서 계산만 한다."""
    return "DEMO-" + hashlib.sha1(brief.encode("utf-8")).hexdigest()[:6].upper()
