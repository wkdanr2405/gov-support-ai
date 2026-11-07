import os
from datetime import date

import pandas as pd
import streamlit as st

# 키 읽기: 내 PC에서는 .env, 배포 서버에서는 Streamlit Secrets (코드나 저장소에는 키를 두지 않는다)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass
try:
    for _k in ("DATA_GO_KR_API_KEY", "BIZINFO_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "EMBED_MODEL"):
        if _k in st.secrets and not os.environ.get(_k):
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass  # secrets 파일이 없으면 건너뜀 (키 없이도 기본 문장·저장본으로 동작)

from src.data_sources import load_announcements
from src.data_sources.common import CAPITAL_AREA, SIDO
from src.matching import Embedder, build_profile, match
from src.report.explain import build_facts, explain
from src.report.pdf import build_pdf

from src.tax_engine import calculate, industry_list, judge_sme, scenario

DISCLAIMER = "참고용 예상치이며 최종 판단은 세무 전문가가 합니다."

st.set_page_config(page_title="AI 정부지원금 & 세액공제 추천", layout="wide")
st.title("AI 정부지원금 & 세액공제 맞춤형 추천 서비스")
st.caption(f"시연용 프로토타입 · 가상 기업 데이터 기준 예시 · {DISCLAIMER}")

won = lambda v: f"{v:,}만 원"

st.info("사용 방법: ① 아래에서 시연 시나리오를 고르거나 직접 입력 → ② 세액공제 예상액과 추천 공고 확인 → ③ 해설을 만들고 PDF로 내려받기. 가상 기업 데이터만 입력하세요.")

st.header("1. 기업 정보")
industries = industry_list()
labels = {f"{i['code']} {i['name']}": i["code"] for i in industries}
label_of = {code: lab for lab, code in labels.items()}

# 시연 시나리오: 고르면 아래 입력칸이 한 번에 채워진다 (가상 기업)
PRESETS = {
    "① 서울 전자부품 제조 (설립 3년, 청년 2명 채용)": dict(ind="C26", sido="서울", founded=date(2023, 3, 15), rev=30, assets=50, big=False,
                                                        ep=10, ec=13, yp=0, yc=2, rc=20000, rp=15000, known=True, avg4=14000,
                                                        ct=0, ip=100, fy=2023, ceo=True, sa="수도권 과밀억제권역"),
    "② 부산 기계장비 제조 (설립 7년, 소폭 증원)": dict(ind="C29", sido="부산", founded=date(2019, 5, 2), rev=80, assets=120, big=False,
                                                    ep=25, ec=27, yp=3, yc=4, rc=8000, rp=7000, known=True, avg4=6500,
                                                    ct=3000, ip=100, fy=2019, ceo=False, sa="비수도권"),
    "③ 경기 소프트웨어 (설립 2년, 급성장)": dict(ind="J", sido="경기", founded=date(2024, 6, 10), rev=5, assets=8, big=False,
                                              ep=4, ec=8, yp=1, yc=5, rc=6000, rp=0, known=False, avg4=0,
                                              ct=800, ip=100, fy=2024, ceo=True, sa="수도권 (과밀억제권역 제외)"),
}
NO_DIS = dict(dl=0, dt=0, du=0, dcur=0, dred=0)      # 재해손실 입력 기본값 (재해 없음)
for _p in PRESETS.values():
    _p.update(NO_DIS)
PRESETS["④ 서울 전자부품 제조 (공장 화재 · 재해손실세액공제 시연)"] = dict(
    PRESETS[list(PRESETS)[0]], dl=16000, dt=40000, du=3000, dcur=2000, dred=500)
PRESETS["⑤ 대구 전자부품 제조 (2026년 창업 · 청년창업 감면 vs 통합고용 중복 배제 시연)"] = dict(
    PRESETS[list(PRESETS)[0]], sido="대구", founded=date(2026, 3, 1), yp=0, yc=2,
    ct=4000, ip=100, fy=2026, ceo=True, sa="비수도권")
KEYS = ["ind", "sido", "founded", "rev", "assets", "big", "ep", "ec", "yp", "yc", "rc", "rp", "known", "avg4",
        "dl", "dt", "du", "dcur", "dred", "ct", "ip", "fy", "ceo", "sa"]


def apply_preset():
    p = PRESETS[st.session_state["preset"]]
    for k in KEYS:
        st.session_state[k] = label_of[p[k]] if k == "ind" else p[k]


first = PRESETS[list(PRESETS)[0]]
for k in KEYS:
    st.session_state.setdefault(k, label_of[first[k]] if k == "ind" else first[k])
st.selectbox("시연 시나리오 (선택하면 입력칸이 채워집니다)", list(PRESETS), key="preset", on_change=apply_preset)

c1, c2, c3 = st.columns(3)
with c1:
    label = st.selectbox("업종", list(labels), key="ind")
    sido = st.selectbox("소재지 (시·도)", SIDO, key="sido")
    founded = st.date_input("설립일", min_value=date(1980, 1, 1), max_value=date.today(), key="founded")
with c2:
    revenue = st.number_input("최근 3년 평균 매출액 (억 원)", min_value=0, step=1, key="rev")
    assets = st.number_input("자산총액 (억 원)", min_value=0, step=1, key="assets")
    big_owner = st.checkbox("자산 5천억 원 이상 법인이 지분 30% 이상을 가진 최다출자자", key="big")
with c3:
    ep = st.number_input("전년 상시근로자 수", min_value=0, step=1, key="ep")
    ec = st.number_input("당해 상시근로자 수", min_value=0, step=1, key="ec")
    yp = st.number_input("전년 청년 등 근로자 수", min_value=0, step=1, key="yp")
    yc = st.number_input("당해 청년 등 근로자 수", min_value=0, step=1, key="yc")

st.subheader("연구·인력개발비 (만 원)")
r1, r2, r3 = st.columns(3)
rnd_curr = r1.number_input("당해 지출액", min_value=0, step=100, key="rc")
rnd_prev = r2.number_input("직전 과세연도 지출액", min_value=0, step=100, key="rp")
known = r3.checkbox("직전 4년 연평균을 알고 있음", key="known")
avg4 = r3.number_input("직전 4년 연평균 (만 원)", min_value=0, step=100, disabled=not known, key="avg4")

st.subheader("재해손실 (선택, 만 원)")
st.caption("화재·풍수해 등으로 사업용 자산을 잃은 경우에만 입력하세요. 토지는 제외한 장부가액 기준입니다. 입력하지 않으면(0) 해당 없음으로 봅니다.")
d1, d2, d3 = st.columns(3)
dis_lost = d1.number_input("재해로 상실한 자산가액", min_value=0, step=100, key="dl")
dis_total = d1.number_input("상실 전 총자산가액 (토지 제외)", min_value=0, step=100, key="dt")
dis_unpaid = d2.number_input("재해일 현재 미부과·미납 법인세", min_value=0, step=100, key="du")
dis_cur = d2.number_input("재해일이 속한 사업연도 법인세", min_value=0, step=100, key="dcur")
dis_red = d3.number_input("그 법인세에서 다른 법률로 받는 공제·감면세액", min_value=0, step=100, key="dred")

st.subheader("법인세 감면 (창업중소기업 · 중소기업 특별세액감면, 만 원)")
st.caption("두 감면은 법인세 산출세액에 감면율을 곱해 계산합니다. 산출세액은 직접 입력하세요. 감면 대상이 아닌 사업의 소득이 섞여 있으면 아래 비율을 낮추세요.")
AREAS = {"수도권 과밀억제권역": "overcrowded", "수도권 (과밀억제권역 제외)": "capital_other",
         "수도권 인구감소지역": "pop_decline", "비수도권": "non_capital"}
t1, t2, t3 = st.columns(3)
corp_tax = t1.number_input("법인세 산출세액", min_value=0, step=100, key="ct")
income_pct = t1.number_input("감면 대상 소득 비율 (%)", min_value=0, max_value=100, step=10, key="ip")
first_year = t2.number_input("최초 소득 발생 연도 (창업감면)", min_value=1980, max_value=2030, step=1, key="fy")
youth_ceo = t2.checkbox("대표자가 창업 당시 만 34세 이하 (청년창업)", key="ceo")
area_label = t3.selectbox("창업 지역 구분 (창업감면)", list(AREAS), key="sa",
                          help="과밀억제권역·인구감소지역 해당 여부는 직접 선택합니다. 소재지가 수도권 밖이면 '비수도권'이 적용됩니다.")

with st.expander("청년 등 근로자는 누구인가요?"):
    st.write("만 15~34세(병역 이행 시 최대 6년을 뺀 나이), 장애인, 계약일 현재 60세 이상, 경력단절근로자, "
             "북한이탈주민입니다. 근로계약 체결 당시 34세 이하면 이후 일정 기간 청년으로 봅니다. "
             "(시행령 제26조의8 제4항)")

if dis_lost > dis_total:
    st.error("상실한 자산가액이 상실 전 총자산가액보다 클 수 없습니다.")
    st.stop()
if yp > ep or yc > ec:
    st.error("청년 등 근로자 수는 전체 상시근로자 수보다 많을 수 없습니다.")
    st.stop()

st.header("2. 중소기업 판정")
sme = judge_sme({"ksic": labels[label], "avg_revenue_eok": revenue, "assets_eok": assets, "owned_by_large_corp": big_owner})
if sme["is_sme"]:
    st.success(f"중소기업 기준에 해당합니다. ({sme['industry']}: 평균매출액 {sme['limit_eok']:,}억 원 이하, 자산총액 5천억 원 미만)")
else:
    st.warning("중소기업 기준에 해당하지 않을 수 있습니다. 아래 계산은 중소기업 기준이라 참고용으로만 보세요.")
st.table(pd.DataFrame([{"항목": c["name"], "결과": "충족" if c["passed"] else "불충족", "설명": c["detail"]} for c in sme["checks"]]))
with st.expander("아직 원문 확인 전인 판정 기준"):
    for u in sme["unverified"]:
        st.write("· " + u)

st.header("3. 세액공제 예상액")
inp = {"region": "capital" if sido in CAPITAL_AREA else "non_capital",
       "employees_prev": int(ep), "employees_curr": int(ec), "youth_prev": int(yp), "youth_curr": int(yc),
       "rnd_curr": rnd_curr, "rnd_prev": rnd_prev,
       "ksic": labels[label], "avg_revenue_eok": revenue, "is_sme": sme["is_sme"], "founded": founded.isoformat(),
       "first_income_year": int(first_year), "youth_ceo": youth_ceo, "corp_tax": corp_tax, "eligible_income_pct": income_pct,
       "startup_area": ("non_capital" if sido not in CAPITAL_AREA else
                        (AREAS[area_label] if AREAS[area_label] != "non_capital" else "capital_other")),
       "disaster_lost_assets": dis_lost, "disaster_total_assets": dis_total, "disaster_unpaid_tax": dis_unpaid,
       "disaster_current_tax": dis_cur, "disaster_other_reductions": dis_red}
if known:
    inp["rnd_prev4_avg"] = avg4
res = calculate(inp)

st.subheader("세액공제 항목별 판정")
STATUS_LABEL = {"computed": "🟢 금액 계산됨", "not_applicable": "⚪ 해당 없음 (입력 기준)"}
ORDER = {"computed": 0, "not_applicable": 1, "planned": 2}   # 계산된 공제를 먼저 보여준다
cards = sorted(res["credits"], key=lambda c: ORDER[c["status"]])
for i in range(0, len(cards), 3):
    for card, col in zip(cards[i:i + 3], st.columns(3)):
        with col, st.container(border=True):
            st.markdown(f"**{card['name']}**")
            st.caption(STATUS_LABEL[card["status"]])
            if card["status"] == "computed":
                st.metric("첫해 예상액", won(card["amount_first_year"]))
            st.write(card["basis"])
            if card["status"] == "computed" and not card["in_total"]:
                st.warning("합계에서 제외: " + card["excluded_reason"])
            st.caption(card["law_ref"] + ("" if card["verified"] else " · 일부 조문 확인 전"))
if res["overlap_note"]:
    st.info(res["overlap_note"])
st.caption("아래 '첫해 예상 감면액'은 금액이 계산되고 중복 적용 배제에서 제외되지 않은 항목만 더한 값입니다. 최저한세는 반영하지 않았습니다.")

m1, m2, m3 = st.columns(3)
m1.metric("첫해 예상 감면액", won(res["total_first_year"]), help="계산된 공제·감면 중 중복 배제에서 제외되지 않은 항목의 합")
m2.metric("통합고용 3년 합계", won(res["total_employment_3y"]))
m3.metric("연구·인력개발비 (당해)", won(res["rnd_credit"]),
          help={"current": "당기분 방식(25%)", "increase": "증가분 방식(50%)", "none": "지출 없음"}[res["rnd_method"]])
inc = res["increases"]
st.write(f"늘어난 인원: 청년 등 **{inc['youth']}명**, 청년 외 **{inc['other']}명**")
st.dataframe(pd.DataFrame({"구분": ["통합고용세액공제"], **{f"{i+1}차연도": [won(v)] for i, v in enumerate(res["employment_by_year"])}}),
             hide_index=True, width="stretch")

st.subheader("청년을 더 채용하면? (통합고용세액공제)")
sc = scenario(inp)
df = pd.DataFrame({f"{r['extra_youth']}명 추가": r["employment_by_year"] for r in sc}, index=["1차연도", "2차연도", "3차연도"]).T
st.bar_chart(df)
st.caption("단위: 만 원. 막대는 연차별 공제액입니다.")

for n in res["notes"]:
    st.caption("· " + n)
st.info(f"가상 기업 기준 예시입니다. {DISCLAIMER}")


st.header("4. 맞춤 정부지원사업 추천")
use_ai = st.toggle("의미 기반(임베딩) 점수 사용", value=True, help="글의 뜻이 비슷한지를 숫자로 비교합니다. 끄면 키워드 점수만 씁니다.")


@st.cache_resource(show_spinner="임베딩 모델을 준비하는 중입니다 (처음 한 번)")
def get_embedder():
    return Embedder()


@st.cache_data
def get_announcements():
    return load_announcements()


anns, src_desc = get_announcements()
profile = build_profile(label.split(" ", 1)[1], sido, founded, int(ep), int(ec), int(yp), int(yc), float(rnd_curr))
try:
    out = match(profile, anns, get_embedder() if use_ai else None, top_n=5)
except Exception as e:  # 모델 내려받기 실패 등
    st.warning(f"의미 기반 점수를 쓸 수 없어 키워드 점수만 사용합니다. ({type(e).__name__})")
    out = match(profile, anns, None, top_n=5)
st.caption(f"데이터: {src_desc} · 조건 탈락 {sum(out['excluded'].values())}건 {out['excluded']} · 점수 계산 {out['scored']}건")
for r in out["items"]:
    dd = "상시" if r["d_day"] is None else f"D-{r['d_day']}"
    with st.container(border=True):
        st.markdown(f"**{r['title']}** · {dd} · 점수 {r['score']}")
        st.caption(f"{r['agency']} · {r['region']} · 대상: {r['target']}")
        st.write("근거 키워드: " + (", ".join(r["matched_keywords"]) or "없음") +
                 ("" if r["semantic"] is None else f" · 의미 유사도 {r['semantic']}"))
        for f in r["flags"]:
            st.caption("⚠ " + f)
        if r["url"]:
            st.link_button("공고 보기", r["url"])
st.info("공고 신청 자격은 원문 공고로 반드시 확인하세요. 점수는 추천 순서를 위한 상대값입니다.")


st.header("5. 해설과 1페이지 리포트")
st.caption("숫자는 규칙 엔진이 계산한 값만 쓰고, 해설 문장은 AI(Claude)가 씁니다. API 키가 없거나 검증에 실패하면 기본 문장을 씁니다.")
facts = build_facts(label.split(" ", 1)[1], inp, res, out["items"], sido)
if st.button("해설 만들기"):
    with st.spinner("해설을 만드는 중입니다"):
        st.session_state["explain"] = {"facts": facts, **explain(facts)}
ex = st.session_state.get("explain")
if ex and ex["facts"] == facts:
    st.write(ex["text"])
    st.caption(("AI 작성" if ex["source"] == "llm" else "기본 문장") + (f" · {ex['note']}" if ex["note"] else ""))
    pdf = build_pdf(facts, ex["text"], out["items"], res["notes"], ex["source"])
    st.download_button("1페이지 PDF 내려받기", pdf, file_name="세액공제_지원사업_추천_리포트.pdf", mime="application/pdf")
elif ex:
    st.info("입력이 바뀌었습니다. '해설 만들기'를 다시 눌러 주세요.")
st.warning(f"{DISCLAIMER} 신고 대행·세액 확정·세무 자문이 아닙니다.")


st.header("6. 전문가 연결 (시뮬레이션)")
st.caption("실제로 전문가에게 전달되지 않는 시연 화면입니다. 입력한 내용은 전송하거나 저장하지 않습니다.")
with st.expander("개인정보 안내"):
    st.write("· 실제 서비스라면 상담 연결을 위해 이름·연락처 같은 개인정보를 받게 됩니다. 이때 수집 목적, 항목, 보관 기간을 알리고 동의를 받아야 합니다.\n"
             "· 이 시연 화면은 어떤 정보도 서버에 보내거나 저장하지 않습니다. 실제 이름·이메일·전화번호는 입력하지 마세요.\n"
             "· 상담은 세무 전문가가 하며, 이 서비스는 신고 대행·세액 확정·세무 자문을 하지 않습니다.")
with st.form("expert_form"):
    f1, f2 = st.columns(2)
    nick = f1.text_input("회사 별칭 (가상)", placeholder="예: 가상전자")
    mail = f2.text_input("연락받을 이메일 (가상)", placeholder="demo@example.com")
    topic = st.selectbox("상담 희망 분야", ["세액공제 예상액 검토", "정부지원사업 신청 준비", "둘 다"])
    memo = st.text_area("전문가에게 전달할 내용", value=f"{label.split(' ', 1)[1]} / {sido} / 첫해 예상 감면액 {res['total_first_year']:,}만 원 (참고용)", height=80)
    agree = st.checkbox("개인정보 안내를 읽었고 시연용임을 이해했습니다")
    sent = st.form_submit_button("상담 요청 보내기 (시연)")
if sent:
    if not agree:
        st.error("개인정보 안내 확인에 체크해 주세요.")
    else:
        st.success("시연용 요청이 접수된 것으로 표시합니다. 실제로는 아무 곳에도 전송·저장되지 않았습니다.")
        st.write(f"**상담 분야:** {topic}  \n**전달될 내용(예시):** {memo}")
        st.caption("실제 서비스에서는 이 화면 뒤에 세무 전문가 매칭과 일정 안내가 이어집니다.")
