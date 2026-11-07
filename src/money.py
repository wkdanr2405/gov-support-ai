"""금액 입력 도우미. 화면에서는 원 단위(쉼표 표기)로 받고, 계산 엔진에는 만원·억원으로 환산해 넘긴다."""
import re


def parse_won(text) -> int | None:
    """'500,000,000' · '500000000' · '500,000,000 원' → 500000000. 숫자가 아니면 None. 빈 칸은 0."""
    if isinstance(text, bool) or text is None:
        return None
    if isinstance(text, int):
        return text if text >= 0 else None
    s = str(text).strip().replace(",", "").replace(" ", "")
    if s.endswith("원"):
        s = s[:-1]
    if s == "":
        return 0
    return int(s) if re.fullmatch(r"\d+", s) else None


def fmt_won(n: int) -> str:
    return f"{n:,}"


def kor_unit(n: int) -> str:
    """읽기 쉬운 한글 단위: 250000000 → '2억 5,000만 원'."""
    if n == 0:
        return "0원"
    parts, rest = [], n
    for unit, name in ((10 ** 12, "조"), (10 ** 8, "억"), (10 ** 4, "만")):
        q, rest = divmod(rest, unit)
        if q:
            parts.append(f"{q:,}{name}")
    if rest:
        parts.append(f"{rest:,}")
    text = " ".join(parts)
    return text + ("원" if rest else " 원")


def man_to_won(n) -> int:
    """엔진 결과(만원) → 원."""
    return int(round(n * 10 ** 4))


def won_text(man) -> str:
    """엔진 결과(만원)를 '68,000,000원' 모양으로."""
    return f"{man_to_won(man):,}원"


def won_to_man(n: int):
    """원 → 만원. 딱 떨어지면 정수, 아니면 소수(엔진이 만원 미만을 절사한다)."""
    return n // 10 ** 4 if n % 10 ** 4 == 0 else n / 10 ** 4


def won_to_eok(n: int):
    return n // 10 ** 8 if n % 10 ** 8 == 0 else n / 10 ** 8
