"""결과 해설. 숫자는 규칙 엔진이 계산한 값만 쓴다 (LLM은 문장만 쓴다).

흐름: facts(엔진·매칭 결과) → Claude에게 해설 요청 → 검증(facts에 없는 숫자·금지 표현 차단) → 통과 못 하면 템플릿 문장 사용.
API 키가 없거나 호출이 실패해도 템플릿으로 항상 결과가 나온다. 면책 문구는 코드가 붙인다.
모델명은 환경변수 ANTHROPIC_MODEL (기본값 아래).
"""
import json
import os
import re

DISCLAIMER = "참고용 예상치이며 최종 판단은 세무 전문가가 합니다."
DEFAULT_MODEL = "claude-sonnet-5-5"
FORBIDDEN = ["신고 대행", "세액 확정", "세무 자문", "확정됩니다", "반드시 받", "보장"]

SYSTEM = (
    "당신은 중소기업 대표에게 세액공제 예상치와 정부지원사업 추천 결과를 쉬운 말로 설명하는 도우미입니다.\n"
    "규칙: 1) 제공된 JSON의 숫자만 사용하고 새 숫자를 만들거나 계산하지 마세요. 2) '신고 대행', '세액 확정', '세무 자문' 같은 표현과 "
    "'받을 수 있습니다'처럼 확정하는 표현을 쓰지 마세요('예상', '가능성'으로 쓰세요). 3) 공고 신청 자격은 원문 확인이 필요하다고 안내하세요. "
    "4) 4~6문장, 문단 2개 이내, 마크다운 기호 없이 쓰세요."
)


def build_facts(profile_name: str, inputs: dict, res: dict, matches: list[dict], sido: str) -> dict:
    return {
        "기업": {"업종": profile_name, "소재지": sido, "수도권": "예" if inputs["region"] == "capital" else "아니오"},
        "인원": {"증가 청년": res["increases"]["youth"], "증가 청년외": res["increases"]["other"]},
        "세액공제(만원)": {"첫해 합계": res["total_first_year"], "통합고용 연차별": res["employment_by_year"],
                      "통합고용 3년 합계": res["total_employment_3y"], "연구인력개발비": res["rnd_credit"]},
        "추천공고": [{"제목": m["title"], "마감": "상시/확인 필요" if m["d_day"] is None else f"D-{m['d_day']}",
                    "근거": m["matched_keywords"][:4]} for m in matches[:3]],
    }


def _numbers(text: str) -> set[str]:
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def validate(text: str, facts: dict) -> list[str]:
    """문제 목록(빈 리스트면 통과)."""
    problems = []
    allowed = _numbers(json.dumps(facts, ensure_ascii=False)) | {"1", "2", "3", "4", "5", "6"}   # 서수·목록 번호 정도는 허용
    extra = _numbers(text) - allowed
    if extra:
        problems.append("근거 없는 숫자: " + ", ".join(sorted(extra)))
    for w in FORBIDDEN:
        if w in text:
            problems.append("금지 표현: " + w)
    if not text.strip():
        problems.append("빈 응답")
    return problems


def _short(title: str, n: int = 30) -> str:
    """제목이 길면 괄호 앞에서 끊거나 말줄임표로 줄인다 (괄호가 열린 채 잘리지 않게)."""
    t = title.split("(")[0].strip() if len(title) > n and "(" in title[:n + 10] else title
    return t if len(t) <= n else t[:n].rstrip() + "…"


def template_text(facts: dict) -> str:
    c = facts["세액공제(만원)"]
    lines = [f"입력하신 조건 기준으로 첫해 세액공제 예상액은 약 {c['첫해 합계']:,}만 원입니다. "
             f"이 중 통합고용세액공제는 연차별로 {', '.join(f'{v:,}만 원' for v in c['통합고용 연차별'])}이고, "
             f"연구·인력개발비 세액공제는 {c['연구인력개발비']:,}만 원으로 계산되었습니다."]
    recs = facts["추천공고"]
    if recs:
        names = " / ".join(f"{_short(r['제목'])} ({r['마감']})" for r in recs)
        lines.append(f"조건에 맞는 지원사업 후보는 {names} 입니다. 신청 자격과 마감은 공고 원문에서 꼭 확인하세요.")
    else:
        lines.append("현재 조건에 맞는 지원사업 후보가 없습니다. 입력 조건을 바꿔 보세요.")
    return "\n".join(lines)


def explain(facts: dict, client=None, model: str | None = None) -> dict:
    """반환: {text, source('llm'|'template'), note}. 면책 문구는 포함하지 않는다(화면·PDF에서 코드가 붙인다)."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if client is None and not key:
        return {"text": template_text(facts), "source": "template", "note": "API 키 없음 → 기본 문장 사용"}
    try:
        if client is None:
            import anthropic
            client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model=model or os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL), max_tokens=600, system=SYSTEM,
            messages=[{"role": "user", "content": "다음 결과를 설명해 주세요.\n" + json.dumps(facts, ensure_ascii=False)}])
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    except Exception as e:   # 네트워크·키 오류 등. 키 값은 오류 문구에 남기지 않는다.
        return {"text": template_text(facts), "source": "template", "note": f"LLM 호출 실패({type(e).__name__}) → 기본 문장 사용"}
    problems = validate(text, facts)
    if problems:
        return {"text": template_text(facts), "source": "template", "note": "검증 실패 → 기본 문장 사용: " + "; ".join(problems)}
    return {"text": text, "source": "llm", "note": ""}
