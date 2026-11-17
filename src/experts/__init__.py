"""전문가 연결 시연: 가상 전문가 후보 정렬과 '상담 전달 자료' 만들기.

실제 전송·저장은 하지 않는다. 후보는 data/sample/experts.yaml의 가상 데이터다.
정렬은 규칙(합계에 들어간 공제·감면 id와 전문 분야가 겹치는 수)만 쓰고, 금액은 규칙 엔진 결과를 그대로 옮긴다.
"""
import hashlib

from src.money import won_text

DISCLAIMER = "참고용 예상치이며 최종 판단은 세무 전문가가 합니다."
STEPS = ["요청 접수", "전문가 검토", "상담 일정 안내", "상담 진행", "신청 준비 (전문가와 상의해 진행)"]
# 시·도 → 상담 지역권 (전문가의 활동 지역은 지역권 이름으로 적는다)
REGION_GROUP = {"서울": "수도권", "인천": "수도권", "경기": "수도권", "대전": "충청권", "세종": "충청권", "충북": "충청권", "충남": "충청권",
                "부산": "영남권", "대구": "영남권", "울산": "영남권", "경북": "영남권", "경남": "영남권",
                "광주": "호남권", "전북": "호남권", "전남": "호남권", "강원": "강원권", "제주": "제주권"}
CREDIT_NAMES = {"rnd_credit": "연구·인력개발비 공제", "integrated_employment": "통합고용 공제", "disaster_loss": "재해손실 공제",
                "startup_sme_exemption": "창업 감면", "sme_special_reduction": "중소기업 특별감면", "gov_support": "정부지원사업"}
INDUSTRY_NAMES = {"C": "제조업", "J": "정보통신업", "F": "건설업", "G": "도소매업", "M": "전문·과학·기술 서비스업"}
# 점수: 분야 일치가 가장 중요하고, 지역·업종은 보조. 금액과 무관한 단순 규칙이다.
W_SPECIALTY, W_REGION_LOCAL, W_REGION_ALL, W_INDUSTRY = 10, 3, 2, 2   # 소재지 지역권을 직접 적은 전문가가 '전국'보다 1점 높다


def load_experts(conn=None) -> list[dict]:
    """승인된 전문가 명단. conn이 없으면 가상 기본 명단(공용)."""
    from .db import list_experts, shared_db
    return list_experts(conn or shared_db(), "approved")


def rank_experts(experts: list[dict], credit_ids: list[str], want_gov_support: bool = True,
                 sido: str | None = None, ksic: str | None = None) -> list[dict]:
    """점수 순(분야 10점/개 + 소재지 지역권 3점(전국 상담은 2점) + 경험 업종 2점). 같으면 명단 순서. score·reasons·reason_line을 붙여 돌려준다."""
    group = REGION_GROUP.get(sido or "")
    ranked = []
    for i, e in enumerate(experts):
        hit = [s for s in e["specialties"] if s in credit_ids or (want_gov_support and s == "gov_support")]
        reasons = [CREDIT_NAMES.get(s, s) for s in hit]
        score = W_SPECIALTY * len(hit)
        region_ok = bool(group) and ("전국" in e["regions"] or group in e["regions"])
        if region_ok:
            score += W_REGION_ALL if "전국" in e["regions"] else W_REGION_LOCAL
            reasons.append(f"{group} 상담 가능" if "전국" not in e["regions"] else "전국 상담 가능")
        ind_ok = bool(ksic) and any(ksic.startswith(p) for p in e.get("industries", []))
        if ind_ok:
            score += W_INDUSTRY
            reasons.append(f"{INDUSTRY_NAMES.get(ksic[0], '해당 업종')} 경험")
        ranked.append({**e, "score": score, "reasons": reasons, "region_ok": region_ok, "_i": i})
    ranked.sort(key=lambda e: (-e["score"], e["_i"]))
    for e in ranked:
        e.pop("_i")
        e["reason_line"] = " · ".join(e["reasons"])
    return ranked


def build_brief(basis: str, company: dict, res: dict, docs: list[dict], matches: list[dict],
                topic: str | None = None, memo: str = "") -> str:
    """전문가에게 건넬 요약 글. 금액은 엔진 결과(만원)를 원 단위로만 바꿔 옮긴다."""
    lines = [f"[상담 전달 자료] {basis}", "",
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
