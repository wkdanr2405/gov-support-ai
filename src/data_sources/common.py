"""공고 수집 공통 도구: 날짜·지역 정규화와 공통 공고 형식(Announcement)."""
import re
from datetime import date, datetime

SIDO = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
_LONG = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
         "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기", "강원특별자치도": "강원", "강원도": "강원", "충청북도": "충북",
         "충청남도": "충남", "전북특별자치도": "전북", "전라북도": "전북", "전라남도": "전남", "경상북도": "경북", "경상남도": "경남",
         "제주특별자치도": "제주"}
CAPITAL_AREA = {"서울", "인천", "경기"}


def normalize_regions(text: str | None) -> set[str]:
    """지역 문구 → 시도 집합. 전국/지역 언급 없음은 {'전국'}. '전남광주'는 광주·전남 둘 다."""
    if not text or not str(text).strip():
        return {"전국"}
    s = str(text)
    found = set()
    if "전남광주" in s:
        found |= {"광주", "전남"}
        s = s.replace("전남광주", " ")
    for long, short in _LONG.items():
        if long in s:
            found.add(short)
            s = s.replace(long, " ")
    for short in SIDO:
        if short in s:
            found.add(short)
    if "전국" in str(text) or not found:
        return {"전국"} | found if "전국" in str(text) else {"전국"}
    return found


def parse_date(value) -> date | None:
    """'20261130', '2026-11-30', '20261130235959' 등 → date. 해석할 수 없으면 None."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    digits = re.sub(r"\D", "", str(value))[:8]
    if len(digits) != 8:
        return None
    try:
        return datetime.strptime(digits, "%Y%m%d").date()
    except ValueError:
        return None


def strip_html(text: str | None) -> str:
    """공고 요약에 섞인 HTML 태그·엔티티를 걷어 낸다."""
    import html
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def parse_period(text: str | None) -> tuple[date | None, date | None]:
    """'20220727 ~ 20220930' → (시작, 종료). '상시', '예산 소진 시까지' 등 종료일 없음 → (None 또는 시작, None)."""
    if not text:
        return None, None
    parts = re.findall(r"\d{8}", re.sub(r"(?<=\d)-(?=\d)", "", str(text)))
    if len(parts) >= 2:
        return parse_date(parts[0]), parse_date(parts[1])
    if len(parts) == 1:
        return parse_date(parts[0]), None
    return None, None


def make_announcement(**kw) -> dict:
    """모든 출처가 같은 형식을 쓰도록 맞춘다."""
    base = {"id": "", "source": "", "title": "", "agency": "", "summary": "", "target": "", "field": "",
            "regions": ["전국"], "start": None, "end": None, "ongoing_flag": None, "biz_age": "", "age_limit": "",
            "url": "", "contact": "", "is_sample": False}
    base.update(kw)
    for k in ("start", "end"):
        if isinstance(base[k], date):
            base[k] = base[k].isoformat()
    base["regions"] = sorted(base["regions"]) if not isinstance(base["regions"], list) else base["regions"]
    return base
