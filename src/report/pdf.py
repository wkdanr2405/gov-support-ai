"""대표자용 1페이지 PDF 리포트 (reportlab, 나눔고딕 포함)."""
from datetime import date
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .explain import DISCLAIMER

FONT = Path(__file__).resolve().parents[2] / "assets" / "fonts" / "NanumGothic-Regular.ttf"
_registered = False


def _font() -> str:
    global _registered
    if not _registered:
        pdfmetrics.registerFont(TTFont("Nanum", str(FONT)))
        _registered = True
    return "Nanum"


def _esc(t: str) -> str:
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_pdf(facts: dict, explanation: str, matches: list[dict], notes: list[str], explain_source: str = "template") -> bytes:
    f = _font()
    st = lambda size, lead=None, **kw: ParagraphStyle("s", fontName=f, fontSize=size, leading=lead or size * 1.45, **kw)
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=12 * mm,
                            title="세액공제·정부지원사업 추천 리포트", author="AI 정부지원금 & 세액공제 추천 서비스")
    c = facts["세액공제(원)"]
    story = [Paragraph("세액공제·정부지원사업 추천 리포트", st(17, textColor=colors.HexColor("#14365d"))),
             Paragraph(f"가상 기업 기준 예시 · 작성일 {date.today().isoformat()} · {DISCLAIMER}", st(8, textColor=colors.grey)),
             Spacer(1, 4 * mm)]

    def table(rows, widths, head=True):
        t = Table([[Paragraph(_esc(x), st(8.5)) for x in r] for r in rows], colWidths=widths)
        style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c8d0da")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                 ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
        if head:
            style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef6")))
        t.setStyle(TableStyle(style))
        return t

    story += [Paragraph("1. 기업 조건", st(11)), Spacer(1, 1.5 * mm),
              table([["업종", facts["기업"]["업종"]], ["소재지", f"{facts['기업']['소재지']} (수도권: {facts['기업']['수도권']})"],
                     ["늘어난 상시근로자", f"청년 등 {facts['인원']['증가 청년']}명, 청년 외 {facts['인원']['증가 청년외']}명"]],
                    [38 * mm, 140 * mm], head=False), Spacer(1, 4 * mm)]
    yr = c["통합고용 연차별"]
    story += [Paragraph("2. 세액공제 예상액 (단위: 원)", st(11)), Spacer(1, 1.5 * mm),
              table([["구분", "금액"], ["첫해 합계 (금액이 계산된 공제의 합)", f"{c['첫해 합계']:,}"],
                     ["통합고용세액공제 연차별", " / ".join(f"{i+1}차 {v:,}" for i, v in enumerate(yr))],
                     ["통합고용 3년 합계", f"{c['통합고용 3년 합계']:,}"], ["연구·인력개발비 세액공제", f"{c['연구인력개발비']:,}"]]
                     + [[n, f"{c[n]:,}"] for n in ("재해손실세액공제", "창업중소기업 세액감면", "중소기업 특별세액감면") if c.get(n)],
                    [100 * mm, 78 * mm]), Spacer(1, 4 * mm)]
    rows = [["추천 정부지원사업", "마감", "근거"]]
    for m in matches[:3]:
        rows.append([m["title"][:48], "상시/확인 필요" if m["d_day"] is None else f"D-{m['d_day']} ({m['period_end']})",
                     ", ".join(m["matched_keywords"][:4]) or "-"])
    if len(rows) == 1:
        rows.append(["조건에 맞는 후보 없음", "-", "-"])
    story += [Paragraph("3. 추천 정부지원사업 Top 3", st(11)), Spacer(1, 1.5 * mm), table(rows, [100 * mm, 36 * mm, 42 * mm]),
              Spacer(1, 4 * mm), Paragraph("4. 해설", st(11)), Spacer(1, 1.5 * mm)]
    for para in explanation.split("\n"):
        if para.strip():
            story.append(Paragraph(_esc(para), st(9.5, 15)))
    story += [Spacer(1, 3 * mm), Paragraph("유의사항", st(9)),
              Paragraph("· " + "<br/>· ".join(_esc(n) for n in notes[:6]), st(7.5, 11, textColor=colors.HexColor("#444444"))),
              Spacer(1, 2 * mm),
              Paragraph(_esc(f"본 문서는 {DISCLAIMER} 공고 신청 자격과 마감은 반드시 원문 공고에서 확인하세요."), st(8, textColor=colors.HexColor("#8a1c1c")))]
    doc.build(story)
    return buf.getvalue()
