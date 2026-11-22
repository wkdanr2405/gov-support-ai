"""전문가 연결 시연: 가상 전문가 후보 정렬과 '상담 전달 자료' 만들기.

실제 전송·저장은 하지 않는다. 후보는 data/sample/experts.yaml의 가상 데이터다.
정렬은 규칙(합계에 들어간 공제·감면 id와 전문 분야가 겹치는 수)만 쓰고, 금액은 규칙 엔진 결과를 그대로 옮긴다.
"""
import hashlib
from functools import lru_cache
from pathlib import Path

import yaml

from src.money import won_text

DISCLAIMER = "참고용 예상치이며 최종 판단은 세무 전문가가 합니다."
STEPS = ["요청 접수", "전문가 검토", "상담 일정 안내", "상담 진행", "신청 준비 (전문가와 상의해 진행)"]
ETC = "기타"                       # 모든 선택 항목의 마지막 선택지. 고르면 '기타: 내용' 형태로 저장한다.
_REGION_FILE = Path(__file__).resolve().parents[2] / "data" / "regions_admin.yaml"


@lru_cache(maxsize=None)
def region_tree() -> dict[str, list[str]]:
    """시·도 → 시·군·구 목록 (광역시는 구·군, 도는 시·군)."""
    return yaml.safe_load(_REGION_FILE.read_text(encoding="utf-8"))


ALL_SUB = "전체"
MERGED = {"광주": "전남광주", "전남": "전남광주"}      # 기업 화면의 이전 시·도 이름 → 통합특별시 이름 (2026-07-01 전남광주통합특별시 출범)
SUB_KIND = {"서울": "구", "부산": "구·군", "대구": "구·군", "인천": "구·군", "전남광주": "구·시·군", "대전": "구", "울산": "구·군", "세종": "시"}


def sido_options() -> list[str]:
    """활동 지역 1단계 선택지: 전국 + 시·도(통합특별시 반영). '기타'는 화면에서 따로 붙인다."""
    return ["전국"] + list(region_tree())


def sub_options(sido: str) -> list[str]:
    """2단계 선택지: '전체' + 구·군(광역시) 또는 시·군(도)."""
    return [ALL_SUB] + region_tree()[sido]


def sub_kind(sido: str) -> str:
    return SUB_KIND.get(sido, "시·군")


def region_values(sido: str, subs: list[str]) -> list[str]:
    """고른 시·도와 하위 지역 → 저장 값. 비우거나 '전체'를 고르면 '서울 전체'."""
    if not subs or ALL_SUB in subs:
        return [f"{sido} {ALL_SUB}"]
    return [f"{sido} {x}" for x in subs]


def split_etc(values: list[str], options) -> tuple[list[str], str]:
    """저장된 값 목록 → (고른 선택지들, 기타 내용). '기타' 또는 '기타: 내용'은 기타로 모은다."""
    picked = [v for v in values if v in options and v != ETC]
    etc = next((v for v in values if v == ETC or v.startswith(ETC + ":")), None)
    text = etc.split(":", 1)[1].strip() if etc and ":" in etc else ""
    return picked, text


def join_etc(picked: list[str], etc_text: str) -> list[str]:
    """고른 선택지 + 기타 내용 → 저장할 값 목록. 기타를 고르거나 내용을 적으면 '기타[: 내용]'을 하나 붙인다."""
    base = [v for v in picked if v != ETC]
    text = (etc_text or "").strip()
    if text:
        return base + [f"{ETC}: {text}"]
    return base + ([ETC] if ETC in picked else [])


def show_etc(values: list[str]) -> list[str]:
    """화면 표시용: '기타: 내용' → '기타(내용)'."""
    return [f"{ETC}({v.split(':', 1)[1].strip()})" if v.startswith(ETC + ":") else v for v in values]


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
    """점수 순(분야 10점/개 + 소재지 시·도에서 활동하면 3점(전국 상담은 2점) + 경험 업종 2점). 같으면 명단 순서. score·reasons·reason_line을 붙여 돌려준다."""
    ranked = []
    for i, e in enumerate(experts):
        hit = [s for s in e["specialties"] if s in credit_ids or (want_gov_support and s == "gov_support")]
        reasons = [CREDIT_NAMES.get(s, s) for s in hit]
        score = W_SPECIALTY * len(hit)
        everywhere = "전국" in e["regions"]
        sido = MERGED.get(sido or "", sido)
        local = bool(sido) and any(r.split(" ", 1)[0] == sido for r in e["regions"])      # '경기 전체'·'경기 수원시' 모두 해당 시·도 활동
        region_ok = bool(sido) and (everywhere or local)
        if region_ok:
            score += W_REGION_LOCAL if local else W_REGION_ALL
            reasons.append(f"{sido} 상담 가능" if local else "전국 상담 가능")
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
