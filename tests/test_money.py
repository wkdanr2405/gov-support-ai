import pytest

from src.money import fmt_won, kor_unit, parse_won, won_to_eok, won_to_man


@pytest.mark.parametrize("text,expected", [
    ("500000000", 500000000), ("500,000,000", 500000000), (" 500,000,000 원 ", 500000000), ("0", 0), ("", 0),
    ("1,234", 1234), (500000000, 500000000),
])
def test_parse_won_accepts_plain_comma_and_won_suffix(text, expected):
    assert parse_won(text) == expected


@pytest.mark.parametrize("text", ["abc", "-1", "1.5", "5억", "1,2,x", None, True])
def test_parse_won_rejects_non_numbers(text):
    assert parse_won(text) is None


def test_fmt_won():
    assert fmt_won(500000000) == "500,000,000" and fmt_won(0) == "0"


@pytest.mark.parametrize("n,expected", [
    (0, "0원"), (5000, "5,000원"), (30000, "3만 원"), (250000000, "2억 5,000만 원"), (3000000000, "30억 원"),
    (1200000000000, "1조 2,000억 원"), (123456789, "1억 2,345만 6,789원"),
])
def test_kor_unit(n, expected):
    assert kor_unit(n) == expected


def test_conversions_keep_exact_value():
    assert won_to_man(50000000) == 5000 and isinstance(won_to_man(50000000), int)
    assert won_to_man(12345) == 1.2345
    assert won_to_eok(3000000000) == 30 and isinstance(won_to_eok(3000000000), int)
    assert won_to_eok(150000000) == 1.5


def test_result_amounts_shown_in_won():
    from src.money import man_to_won, won_text
    assert won_text(6800) == "68,000,000원"
    assert won_text(0) == "0원"
    assert man_to_won(1800) == 18_000_000
