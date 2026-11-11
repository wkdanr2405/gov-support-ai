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
               "포럼", "네트워킹", "멘토링", "참관객", "포상", "시상"]
# 자금·사업 지원이 아니라 사무공간 임대·입주 공고 (창업보육센터, 인큐베이팅센터 입주 등)
LEASE_WORDS = ["입주기업", "입주자 모집", "입주자모집", "임대공급", "임대 공급", "입점기업"]
# 제목에 이 업종이 드러나면 해당 업종 기업만 대상으로 본다 (우리 업종 이름에 같은 단어가 없으면 제외)
SECTOR_WORDS = ["농업", "농촌", "농식품", "어업", "수산", "축산", "임업", "귀농"]


def is_event(a: dict) -> bool:
    return any(w in a["title"] for w in EVENT_WORDS)


def is_lease(a: dict) -> bool:
    return any(w in a["title"] for w in LEASE_WORDS)


def other_sector(a: dict, profile: dict) -> bool:
    return any(w in a["title"] and w not in profile.get("industry_name", "") for w in SECTOR_WORDS)


def region_in_title(a: dict, profile: dict) -> bool:
    """제목에 다른 시도 이름이 있으면(전국 표시 공고라도) 그 지역 기업만 대상으로 본다. 우리 지역 이름이 함께 있으면 통과."""
    from src.data_sources.common import SIDO, normalize_regions
    named = normalize_regions(a["title"]) - {"전국"}
    return bool(named) and profile["sido"] not in named


def capital_mismatch(a: dict, profile: dict) -> bool:
    """제목의 '[비수도권]'·'[수도권]' 표시가 우리 회사 소재지와 맞지 않으면 제외."""
    from src.data_sources.common import CAPITAL_AREA
    in_capital = profile["sido"] in CAPITAL_AREA
    title = a["title"]
    if "비수도권" in title:
        return in_capital
    return "수도권" in title and not in_capital


def sub_region_hint(a: dict) -> bool:
    """제목·대상 앞부분에 구·군·시 이름이 있으면 세부 지역 조건이 있을 수 있어 확인 표시를 붙인다."""
    text = a["title"] + " " + a.get("target", "")[:80]
    return bool(re.search(r"(?<![가-힣])[가-힣]{2,4}(구|군|시)(?![가-힣])", text))


def only_pre_founders(a: dict) -> bool:
    """대상이 예비창업자뿐인 공고(이미 창업한 회사는 신청할 수 없음). '창업기업·창업 후·중소기업' 같은 말이 함께 있으면 남긴다."""
    t = a["title"] + " " + a.get("target", "")
    return "예비창업" in t and not any(w in t for w in ("창업기업", "창업 후", "창업후", "년 이내", "년 미만", "중소기업", "벤처"))


def too_big_for_micro(a: dict, profile: dict) -> bool:
    """소상공인 전용 공고인데 우리 회사 상시근로자 수가 소상공인 기준(제조업 10명 미만, 그 외 5명 미만) 이상이면 제외."""
    t = a["title"] + " " + a.get("target", "")
    if "소상공인" not in a["title"] or "중소기업" in t:
        return False
    limit = 10 if profile.get("is_manufacturing") else 5
    return profile.get("employees_curr", 0) >= limit


def check(a: dict, profile: dict, today: date) -> tuple[bool, str, list[str]]:
    """(통과 여부, 탈락 사유, 주의 표시)"""
    flags: list[str] = []
    dd = d_day(a, today)
    if a.get("ongoing_flag") == "N" or (dd is not None and dd < 0):
        return False, "마감", flags
    if is_event(a):
        return False, "교육·행사", flags
    if is_lease(a):
        return False, "입주·임대", flags
    if other_sector(a, profile):
        return False, "다른 업종", flags
    if "전국" not in a["regions"] and profile["sido"] not in a["regions"]:
        return False, "지역", flags
    if region_in_title(a, profile):
        return False, "지역", flags
    if capital_mismatch(a, profile):
        return False, "지역", flags
    if only_pre_founders(a):
        return False, "예비창업자 전용", flags
    if too_big_for_micro(a, profile):
        return False, "소상공인 전용", flags
    age_ok = parse_biz_age(a.get("biz_age", ""), profile["age_years"])
    if age_ok is False:
        return False, "업력", flags
    if age_ok is None and not a.get("biz_age"):
        flags.append("업력 조건 확인 필요")
    if sub_region_hint(a):
        flags.append("세부 지역(시·군·구) 조건 확인 필요")
    if "청년" in a["title"] + a.get("target", "")[:80] and re.search(r"대표자|\d+세", a["title"] + a.get("target", "")):
        flags.append("대표자 연령 조건 확인 필요")
    if dd is None:
        flags.append("상시 접수 (마감일 상세 확인)")
    return True, "", flags
