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

st.header("1. 기업 정보")
industries = industry_list()
labels = {f"{i['code']} {i['name']}": i["code"] for i in industries}
c1, c2, c3 = st.columns(3)
with c1:
    label = st.selectbox("업종", list(labels), index=list(labels.values()).index("C26"))
    sido = st.selectbox("소재지 (시·도)", SIDO, index=SIDO.index("서울"))
    founded = st.date_input("설립일", value=date(2023, 3, 15), min_value=date(1980, 1, 1), max_value=date.today())
with c2:
    revenue = st.number_input("최근 3년 평균 매출액 (억 원)", min_value=0, value=30, step=1)
    assets = st.number_input("자산총액 (억 원)", min_value=0, value=50, step=1)
    big_owner = st.checkbox("자산 5천억 원 이상 법인이 지분 30% 이상을 가진 최다출자자")
with c3:
    ep = st.number_input("전년 상시근로자 수", min_value=0, value=10, step=1)
    ec = st.number_input("당해 상시근로자 수", min_value=0, value=13, step=1)
    yp = st.number_input("전년 청년 등 근로자 수", min_value=0, value=0, step=1)
    yc = st.number_input("당해 청년 등 근로자 수", min_value=0, value=2, step=1)

st.subheader("연구·인력개발비 (만 원)")
r1, r2, r3 = st.columns(3)
rnd_curr = r1.number_input("당해 지출액", min_value=0, value=20000, step=100)
rnd_prev = r2.number_input("직전 과세연도 지출액", min_value=0, value=15000, step=100)
known = r3.checkbox("직전 4년 연평균을 알고 있음", value=True)
avg4 = r3.number_input("직전 4년 연평균 (만 원)", min_value=0, value=14000, step=100, disabled=not known)

with st.expander("청년 등 근로자는 누구인가요?"):
    st.write("만 15~34세(병역 이행 시 최대 6년을 뺀 나이), 장애인, 계약일 현재 60세 이상, 경력단절근로자, "
             "북한이탈주민입니다. 근로계약 체결 당시 34세 이하면 이후 일정 기간 청년으로 봅니다. "
             "(시행령 제26조의8 제4항)")

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
       "rnd_curr": rnd_curr, "rnd_prev": rnd_prev}
if known:
    inp["rnd_prev4_avg"] = avg4
res = calculate(inp)

m1, m2, m3 = st.columns(3)
m1.metric("첫해 예상 감면액", won(res["total_first_year"]), help="통합고용 1차연도 + 연구·인력개발비")
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
    st.download_button("1페이지 PDF 내려받기", pdf, file_name="recommendation_report.pdf", mime="application/pdf")
elif ex:
    st.info("입력이 바뀌었습니다. '해설 만들기'를 다시 눌러 주세요.")
st.warning(f"{DISCLAIMER} 신고 대행·세액 확정·세무 자문이 아닙니다.")
