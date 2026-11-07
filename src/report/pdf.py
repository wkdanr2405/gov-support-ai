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

from .docs import NOTICE
from .explain import DISCLAIMER

FONTS = Path(__file__).resolve().parents[2] / "assets" / "fonts"
FONT = FONTS / "NanumGothic-Regular.ttf"          # 한글 본문
DISPLAY_FONT = FONTS / "DoHyeon-Regular.ttf"      # 제목·큰 숫자 (Do Hyeon, SIL Open Font License). 화면 맨 위 제목과 같은 글꼴
INK, CLOUD, HAIR, MUTE = "#111111", "#f5f5f5", "#cacacb", "#707072"   # docs/09-design-system.md
_registered = False


def _font() -> str:
    global _registered
    if not _registered:
        pdfmetrics.registerFont(TTFont("Nanum", str(FONT)))
        pdfmetrics.registerFont(TTFont("Display", str(DISPLAY_FONT)))
        _registered = True
    return "Nanum"


def _esc(t: str) -> str:
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_pdf(facts: dict, explanation: str, matches: list[dict], notes: list[str], explain_source: str = "template",
              docs: list[dict] | None = None) -> bytes:
    f = _font()
    st = lambda size, lead=None, **kw: ParagraphStyle("s", fontName=f, fontSize=size, leading=lead or size * 1.45, **kw)
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=10 * mm, bottomMargin=9 * mm,
                            title="세액공제·정부지원사업 추천 리포트", author="AI 정부지원금 & 세액공제 추천 서비스")
    c = facts["세액공제(원)"]
    W = A4[0] - 32 * mm
    # 도현 글꼴에는 가운뎃점(·)이 없어 그 글자만 나눔고딕으로 그린다
    head = Table([[Paragraph("세액공제 · 정부지원사업", st(8, textColor=colors.HexColor("#9e9ea0")))],
                  [Paragraph('<font name="Display">세액공제</font><font name="Nanum">·</font><font name="Display">정부지원사업 추천 리포트</font>', st(21, 26, textColor=colors.white))],
                  [Paragraph(f"가상 기업 기준 예시 · 작성일 {date.today().isoformat()} · {DISCLAIMER}", st(7.5, textColor=colors.HexColor("#e5e5e5")))]],
                 colWidths=[W])
    head.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(INK)), ("LEFTPADDING", (0, 0), (-1, -1), 10),
                              ("TOPPADDING", (0, 0), (0, 0), 9), ("BOTTOMPADDING", (0, -1), (-1, -1), 9),
                              ("TOPPADDING", (0, 1), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -2), 2)]))
    big = Table([[Paragraph("첫해 예상 감면액", st(8, textColor=colors.HexColor(MUTE))),
                  Paragraph(f'<font name="Display" size="30">{c["첫해 합계"]:,}</font><font size="12"> 원</font>', st(12, 34, textColor=colors.HexColor(INK)))]],
                colWidths=[38 * mm, W - 38 * mm])
    big.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(HAIR)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                             ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story = [head, Spacer(1, 2 * mm), big, Spacer(1, 3 * mm)]

    def table(rows, widths, head=True, size=8.5, pad=3):
        t = Table([[Paragraph(_esc(x), st(size)) for x in r] for r in rows], colWidths=widths)
        style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(HAIR)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                 ("TOPPADDING", (0, 0), (-1, -1), pad), ("BOTTOMPADDING", (0, 0), (-1, -1), pad)]
        if head:
            style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(CLOUD)))
        t.setStyle(TableStyle(style))
        return t

    story += [Paragraph("1. 기업 조건", st(11)), Spacer(1, 1.5 * mm),
              table([["업종", facts["기업"]["업종"]], ["소재지", f"{facts['기업']['소재지']} (수도권: {facts['기업']['수도권']})"],
                     ["늘어난 상시근로자", f"청년 등 {facts['인원']['증가 청년']}명, 청년 외 {facts['인원']['증가 청년외']}명"]],
                    [38 * mm, 140 * mm], head=False), Spacer(1, 3 * mm)]
    yr = c["통합고용 연차별"]
    story += [Paragraph("2. 세액공제 예상액 (단위: 원)", st(11)), Spacer(1, 1.5 * mm),
              table([["구분", "금액"],
                     ["통합고용세액공제 연차별", " / ".join(f"{i+1}차 {v:,}" for i, v in enumerate(yr))],
                     ["통합고용 3년 합계", f"{c['통합고용 3년 합계']:,}"], ["연구·인력개발비 세액공제", f"{c['연구인력개발비']:,}"]]
                     + [[n, f"{c[n]:,}"] for n in ("재해손실세액공제", "창업중소기업 세액감면", "중소기업 특별세액감면") if c.get(n)],
                    [100 * mm, 78 * mm]), Spacer(1, 3 * mm)]
    rows = [["추천 정부지원사업", "마감", "근거"]]
    for m in matches[:3]:
        rows.append([m["title"][:48], "상시/확인 필요" if m["d_day"] is None else f"D-{m['d_day']} ({m['period_end']})",
                     ", ".join(m["matched_keywords"][:4]) or "-"])
    if len(rows) == 1:
        rows.append(["조건에 맞는 후보 없음", "-", "-"])
    story += [Paragraph("3. 추천 정부지원사업 Top 3", st(11)), Spacer(1, 1.5 * mm), table(rows, [100 * mm, 36 * mm, 42 * mm]),
              Spacer(1, 3 * mm)]
    if docs:
        story += [Paragraph("4. 신청·신고 때 준비할 서류 (참고)", st(11)), Spacer(1, 1.5 * mm),
                  table([["공제·감면", "준비 서류", "시기"]] + [[d["name"], "; ".join(d["documents"]), d["timing"]] for d in docs],
                        [27 * mm, 108 * mm, 43 * mm], size=7, pad=1.5),
                  Paragraph(_esc(NOTICE), st(7.5, 11, textColor=colors.HexColor(MUTE))), Spacer(1, 3 * mm)]
    story += [Paragraph("5. 해설" if docs else "4. 해설", st(11)), Spacer(1, 1.5 * mm)]
    for para in explanation.split("\n"):
        if para.strip():
            story.append(Paragraph(_esc(para), st(9, 13.5)))
    story += [Spacer(1, 3 * mm), Paragraph("유의사항", st(9)),
              Paragraph("· " + "<br/>· ".join(_esc(n) for n in notes[:6]), st(7.5, 11, textColor=colors.HexColor(MUTE))),
              Spacer(1, 2 * mm)]
    foot = Table([[Paragraph(_esc(f"본 문서는 {DISCLAIMER} 공고 신청 자격과 마감은 반드시 원문 공고에서 확인하세요."), st(8, textColor=colors.HexColor(INK)))]], colWidths=[W])
    foot.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(CLOUD)), ("LINEBEFORE", (0, 0), (0, -1), 2.5, colors.HexColor(INK)),
                              ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.append(foot)
    doc.build(story)
    return buf.getvalue()
