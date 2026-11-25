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
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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


class _Kit:
    """리포트와 상담 전달 자료가 함께 쓰는 모양(검정 띠·큰 금액·회색 표 머리·면책 상자)."""

    def __init__(self):
        self.f = _font()
        self.W = A4[0] - 32 * mm

    def st(self, size, lead=None, **kw):
        return ParagraphStyle("s", fontName=self.f, fontSize=size, leading=lead or size * 1.45, **kw)

    def doc(self, buf, title):
        return SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=10 * mm, bottomMargin=9 * mm,
                                 title=title, author="AI 정부지원금 & 세액공제 추천 서비스")

    def head(self, kicker, title_html, sub):
        h = Table([[Paragraph(kicker, self.st(8, textColor=colors.HexColor("#9e9ea0")))],
                   [Paragraph(title_html, self.st(21, 26, textColor=colors.white))],
                   [Paragraph(sub, self.st(7.5, textColor=colors.HexColor("#e5e5e5")))]], colWidths=[self.W])
        h.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(INK)), ("LEFTPADDING", (0, 0), (-1, -1), 10),
                               ("TOPPADDING", (0, 0), (0, 0), 9), ("BOTTOMPADDING", (0, -1), (-1, -1), 9),
                               ("TOPPADDING", (0, 1), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -2), 2)]))
        return h

    def big(self, label, number):
        b = Table([[Paragraph(label, self.st(8, textColor=colors.HexColor(MUTE))),
                    Paragraph(f'<font name="Display" size="30">{number:,}</font><font size="12"> 원</font>', self.st(12, 34, textColor=colors.HexColor(INK)))]],
                  colWidths=[38 * mm, self.W - 38 * mm])
        b.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(HAIR)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        return b

    def table(self, rows, widths, head=True, size=8.5, pad=3):
        t = Table([[Paragraph(_esc(x), self.st(size)) for x in r] for r in rows], colWidths=widths)
        style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(HAIR)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                 ("TOPPADDING", (0, 0), (-1, -1), pad), ("BOTTOMPADDING", (0, 0), (-1, -1), pad)]
        if head:
            style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(CLOUD)))
        t.setStyle(TableStyle(style))
        return t

    def foot(self, text):
        x = Table([[Paragraph(_esc(text), self.st(8, textColor=colors.HexColor(INK)))]], colWidths=[self.W])
        x.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(CLOUD)), ("LINEBEFORE", (0, 0), (0, -1), 2.5, colors.HexColor(INK)),
                               ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        return x


# 도현 글꼴에는 가운뎃점(·)이 없어 그 글자만 나눔고딕으로 그린다
_TITLE_REPORT = '<font name="Display">세액공제</font><font name="Nanum">·</font><font name="Display">정부지원사업 추천 리포트</font>'
_TITLE_BRIEF = '<font name="Display">상담 전달 자료</font>'


def _appendix(k: "_Kit", matches: list[dict], notes: list[str], ev: dict | None) -> list:
    """2쪽 부록: 세액공제 계산 근거(조문·확인일·미확인 표시)와 공고 추천 근거(출처·번호·원문 링크·수집일)."""
    from src.report.evidence import match_rows
    st, table = k.st, k.table
    MU = colors.HexColor(MUTE)
    ev = ev or {"tax_rows": [], "match_rows": match_rows(matches), "data_status": [], "excluded": {}, "scored": 0, "input_rows": []}
    story = [PageBreak(), k.head("부록", '<font name="Display">계산과 추천 근거, 출처</font>',
                                  f"작성일 {date.today().isoformat()} · {DISCLAIMER}"), Spacer(1, 3 * mm)]
    if ev["tax_rows"]:
        story += [Paragraph("A. 세액공제·감면 계산 근거", st(11)), Spacer(1, 1.5 * mm),
                  table([["항목", "적용 조문", "계산 방식", "이번 결과", "확인 상태"]]
                        + [[r["name"], r["law_ref"], r["formula"], r["result"], r["status"]] for r in ev["tax_rows"]],
                        [24 * mm, 40 * mm, 32 * mm, 60 * mm, 22 * mm], size=6.5, pad=1.5),
                  Paragraph("금액은 규칙 엔진(코드)이 법령 수치 파일(조문 출처·확인일 기록)로 계산했고, AI는 계산에 관여하지 않습니다. "
                            "'일부 미확인'은 조문 확인이 끝나지 않은 세부 규정이 남아 있다는 뜻입니다. 최저한세는 반영하지 않았습니다.",
                            st(7, 10.5, textColor=MU)), Spacer(1, 3 * mm)]
    if ev["input_rows"]:
        story += [Paragraph("B. 계산에 사용한 입력값", st(11)), Spacer(1, 1.5 * mm), table(ev["input_rows"], [38 * mm, 140 * mm], head=False, size=7, pad=1.5),
                  Spacer(1, 3 * mm)]
    story += [Paragraph("C. 추천 공고 근거 (상위 3건)", st(11)), Spacer(1, 1.5 * mm)]
    rows = [["공고", "출처 · 공고번호", "마감", "추천 근거"]]
    for r in ev["match_rows"]:
        num = "" if r["sample"] else (f" · 번호 {r['id']}" if r["id"] else "")
        why = r["why"] + ("".join(f" · 확인 필요: {f}" for f in r["flags"]))
        rows.append([r["title"][:60] + (f" ({r['agency']})" if r["agency"] else ""), r["source_label"] + num, r["deadline"], why])
    if len(rows) == 1:
        rows.append(["조건에 맞는 후보 없음", "-", "-", "-"])
    story.append(table(rows, [52 * mm, 34 * mm, 24 * mm, 68 * mm], size=6.5, pad=1.5))
    links = [r for r in ev["match_rows"] if r["url"]]
    if links:
        story.append(Spacer(1, 1.5 * mm))
        story.append(table([["원문 링크"]] + [[f"{i}. {r['url']}"] for i, r in enumerate(links, 1)], [178 * mm], size=6.5, pad=1.5))
    story.append(Spacer(1, 3 * mm))
    story += [Paragraph("D. 공고 데이터 기준", st(11)), Spacer(1, 1.5 * mm)]
    drows = []
    for s in ev["data_status"]:
        if s["mode"] == "snapshot":
            drows.append([s["label"], f"저장본 {s['count']:,}건 · 수집 {s['date']} ({s['age_days']}일 경과)"])
        else:
            drows.append([s["label"], f"가상 샘플 {s['count']:,}건 · 실제 공고가 아니며 외부 API 저장본이 없어 대체함"])
    if ev["data_status"]:
        ex = ev["excluded"]
        drows.append(["후보 선별", f"조건 불일치로 제외 {sum(ex.values()):,}건 (" + ", ".join(f"{a} {b:,}" for a, b in ex.items()) + f") · 점수 계산 {ev['scored']:,}건"])
    if drows:
        story.append(table(drows, [48 * mm, 130 * mm], head=False, size=7, pad=1.5))
    story += [Spacer(1, 3 * mm), Paragraph("E. 유의사항", st(11)), Spacer(1, 1.5 * mm),
              Paragraph("· " + "<br/>· ".join(_esc(x) for x in (
        "공고는 수집일 기준 저장본입니다. 수집 이후 마감·수정된 공고는 반영되지 않았을 수 있으니 신청 전 원문 링크에서 마감과 자격을 확인하세요.",
        "추천 점수는 키워드·의미 유사도를 섞은 상대값으로 추천 순서를 정하는 데만 쓰며, 신청 자격 판정이 아닙니다.",
        "법령 수치의 출처 조문과 확인일은 data/tax_params 파일에 기록되어 있습니다.") + tuple(notes[:2])), st(7, 10.5, textColor=MU))]
    return story


def build_pdf(facts: dict, explanation: str, matches: list[dict], notes: list[str], explain_source: str = "template",
              docs: list[dict] | None = None, basis: str = "가상 기업 기준 예시", evidence: dict | None = None) -> bytes:
    k = _Kit()
    st, table, W = k.st, k.table, k.W
    buf = BytesIO()
    doc = k.doc(buf, "세액공제·정부지원사업 추천 리포트")
    c = facts["세액공제(원)"]
    story = [k.head("세액공제 · 정부지원사업", _TITLE_REPORT, f"{basis} · 작성일 {date.today().isoformat()} · {DISCLAIMER} 근거·출처는 2쪽 부록"),
             Spacer(1, 2 * mm), k.big("첫해 예상 감면액", c["첫해 합계"]), Spacer(1, 3 * mm)]

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
    story += [Spacer(1, 3 * mm), k.foot(f"본 문서는 {DISCLAIMER} 공고 신청 자격과 마감은 반드시 원문 공고에서 확인하세요.")]
    story += _appendix(k, matches, notes, evidence)
    doc.build(story)
    return buf.getvalue()


def build_brief_pdf(basis: str, company: dict, res: dict, docs: list[dict], matches: list[dict], expert: dict | None = None,
                    topic: str | None = None, channel: str | None = None, memo: str = "", receipt: str | None = None) -> bytes:
    """상담 전달 자료 1페이지 PDF. 리포트와 같은 모양이고, 금액은 규칙 엔진 결과(만원)를 원 단위로만 바꿔 옮긴다."""
    from src.money import man_to_won
    k = _Kit()
    st, table = k.st, k.table
    buf = BytesIO()
    doc = k.doc(buf, "상담 전달 자료")
    sub = f"{basis} · 작성일 {date.today().isoformat()}" + (f" · 접수번호 {receipt}" if receipt else "") + f" · {DISCLAIMER}"
    story = [k.head("세액공제 · 정부지원사업", _TITLE_BRIEF, sub), Spacer(1, 2 * mm),
             k.big("첫해 예상 감면액", man_to_won(res["total_first_year"])), Spacer(1, 2 * mm)]
    if expert:
        story += [Paragraph("상담 요청", st(11)), Spacer(1, 1.5 * mm),
                  table([["상담 법인", f"{expert['name']} · {expert['kind']}"], ["상담 분야", topic or "-"], ["희망 방식", channel or "-"]]
                        + ([["추가로 전할 말", memo.strip()[:120]]] if memo.strip() else []), [38 * mm, 140 * mm], head=False, size=8, pad=2),
                  Spacer(1, 2 * mm)]
    story += [Paragraph("1. 기업 조건", st(11)), Spacer(1, 1.5 * mm),
              table(([["기업 · 연락처 (가상)", f"{company['name']} · {company.get('email', '-')} · {company.get('phone', '-')}"]] if company.get("name") else [])
                    + [["업종 · 소재지", f"{company['industry']} · {company['sido']}"], ["설립일", company["founded"]],
                     ["중소기업 판정", "해당" if company["is_sme"] else "확인 필요"],
                     ["상시근로자", f"전년 {company['ep']}명 → 당해 {company['ec']}명 (청년 등 {company['yp']}명 → {company['yc']}명)"]],
                    [38 * mm, 140 * mm], head=False, size=8, pad=2), Spacer(1, 2 * mm)]
    rows = [["구분", "첫해 예상액 (원)"]]
    rows += [[c["name"], f"{man_to_won(c['amount_first_year']):,}"] for c in res.get("credits", [])
             if c["status"] == "computed" and c.get("in_total")]
    if len(rows) == 1:
        rows.append(["금액이 계산된 공제·감면 없음", "-"])
    story += [Paragraph("2. 계산 결과 (규칙 엔진, 참고용)", st(11)), Spacer(1, 1.5 * mm), table(rows, [100 * mm, 78 * mm], size=8, pad=2)]
    if res.get("overlap_note"):
        story.append(Paragraph(_esc(res["overlap_note"]), st(7.5, 11, textColor=colors.HexColor(MUTE))))
    story.append(Spacer(1, 2 * mm))
    if docs:
        story += [Paragraph("3. 신청 때 준비할 서류 (일반 안내)", st(11)), Spacer(1, 1.5 * mm),
                  table([["공제·감면", "준비 서류", "시기"]] + [[d["name"], "; ".join(d["documents"]), d["timing"]] for d in docs],
                        [27 * mm, 108 * mm, 43 * mm], size=7, pad=1.5),
                  Paragraph(_esc(NOTICE), st(7.5, 11, textColor=colors.HexColor(MUTE))), Spacer(1, 2 * mm)]
    if matches:
        story += [Paragraph("4. 추천 정부지원사업 (상위 3건)", st(11)), Spacer(1, 1.5 * mm),
                  table([["공고"]] + [[m["title"][:70]] for m in matches[:3]], [178 * mm], size=8, pad=2), Spacer(1, 2 * mm)]
    story.append(k.foot(f"본 문서는 {DISCLAIMER} 실제 신청 서류와 요건은 전문가와 확인하세요."))
    doc.build(story)
    return buf.getvalue()
