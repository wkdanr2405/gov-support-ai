"""조건 필터: 마감, 지역, 업력. 틀린 공고를 먼저 걸러 낸다. 판단이 불확실하면 남기고(unknown) 표시한다."""
import re
from datetime import date


def parse_biz_age(text: str, company_age_years: int) -> bool | None:
    """공고의 '창업 기간' 문구와 우리 회사 업력(만 나이)을 비교. True 해당, False 비해당, None 알 수 없음.

    예: '3년미만,5년미만,7년미만' → 7년 미만이면 해당(여러 항목은 합집합). '예비창업자'만 있으면 이미 창업한 회사는 비해당.
    """
    t = re.sub(r"\s+", "", text or "")
    if not t:
        return None
    rules = re.findall(r"(\d+)년(미만|이내|이하)", t)
    if rules:
        return any(company_age_years < int(n) if kind == "미만" else company_age_years <= int(n) for n, kind in rules)
    if "예비창업" in t:
        return False
    return None


def d_day(a: dict, today: date) -> int | None:
    return (date.fromisoformat(a["end"]) - today).days if a.get("end") else None


# 지원금·사업화 자금이 아니라 교육·행사 참가 모집인 공고. 제목에 이 단어가 있으면 추천에서 뺀다.
EVENT_WORDS = ["특강", "세미나", "설명회", "강연", "인턴십", "경진대회", "해커톤", "공모전", "아카데미", "교육생", "캠프",
               "포럼", "네트워킹", "멘토링", "참관객"]


def is_event(a: dict) -> bool:
    return any(w in a["title"] for w in EVENT_WORDS)


def check(a: dict, profile: dict, today: date) -> tuple[bool, str, list[str]]:
    """(통과 여부, 탈락 사유, 주의 표시)"""
    flags: list[str] = []
    dd = d_day(a, today)
    if a.get("ongoing_flag") == "N" or (dd is not None and dd < 0):
        return False, "마감", flags
    if is_event(a):
        return False, "교육·행사", flags
    if "전국" not in a["regions"] and profile["sido"] not in a["regions"]:
        return False, "지역", flags
    age_ok = parse_biz_age(a.get("biz_age", ""), profile["age_years"])
    if age_ok is False:
        return False, "업력", flags
    if age_ok is None and not a.get("biz_age"):
        flags.append("업력 조건 확인 필요")
    if dd is None:
        flags.append("상시 접수 (마감일 상세 확인)")
    return True, "", flags
