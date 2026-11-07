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
from src.money import fmt_won, kor_unit, man_to_won, parse_won, won_text, won_to_eok, won_to_man
from src.report.docs import NOTICE as DOCS_NOTICE, required_documents
from src.report.explain import build_facts, explain
from src.report.pdf import build_pdf

from src.tax_engine import calculate, industry_list, judge_sme, scenario

DISCLAIMER = "참고용 예상치이며 최종 판단은 세무 전문가가 합니다."


st.set_page_config(page_title="AI 정부지원금 & 세액공제 추천", page_icon="📊", layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&family=Do+Hyeon&display=swap');
/* 디자인 규칙 (docs/09-design-system.md): 검정·흰색·옅은 회색만 쓰고, 버튼은 알약 모양, 카드는 평평하게(그림자 없음) */
:root {--ink:#111111; --cloud:#f5f5f5; --hair:#cacacb; --mute:#707072; --success:#007d48; --sale:#d30005;}
.stApp, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp p, .stApp label, .stApp li,
.stApp button, .stApp input, .stApp textarea, .stApp [data-baseweb="select"] {
  font-family: Inter, "Helvetica Neue", Helvetica, "Apple SD Gothic Neo", "Noto Sans KR", "Malgun Gothic", Arial, sans-serif;}
.block-container {padding-top: 1.5rem; max-width: 1120px;}
/* 맨 위 안내 띠: 사진 없이 큰 글자만 (검정 바탕에 흰 글자) */
.hero {background: var(--ink); color: #fff; padding: 40px 32px 32px; margin-bottom: 16px;}
.hero .kicker {font-size: 0.8rem; font-weight: 500; letter-spacing: 0.04em; color: #9e9ea0; margin-bottom: 12px;}
/* 큰 글자 단계: 원본의 전용 글꼴(Futura ND) 대신 Do Hyeon(도현)을 쓴다. 한 줄로 보이도록 화면 폭에 맞춰 크기를 줄인다 */
.hero h1 {color:#fff !important; font-family: "Do Hyeon", "Noto Sans KR", sans-serif !important; font-size: clamp(1.5rem, 5.6vw, 3.4rem) !important; font-weight: 400 !important;
  line-height: 1.1 !important; letter-spacing: 0; margin: 0 0 16px 0; padding: 0; white-space: nowrap;}
.hero .sub {font-size: 1rem; color: #e5e5e5; line-height: 1.6; text-wrap: balance; word-break: keep-all;}   /* 한 줄로 두고, 좁은 화면에서 줄이 바뀌어도 '니다.'만 남지 않게 고르게 나눈다 */
@media (max-width: 640px) {.hero {padding: 28px 20px 22px;} .hero h1 {font-size: 1.5rem !important;}}
h5 {font-size: 1.5rem !important; font-weight: 500 !important; letter-spacing: -0.01em; margin-top: 32px !important;}
/* 평평한 카드: 모서리 직각, 그림자 없음, 머리카락 두께 선 */
[data-testid="stVerticalBlock"] {border-radius: 0 !important; border-color: var(--hair) !important; box-shadow: none !important;}
[data-testid="stMetricValue"] {font-size: 1.9rem; font-weight: 700; letter-spacing: -0.01em;}
[data-testid="stMetricLabel"] {color: var(--mute);}
/* 탭: 선택된 탭은 검정 밑줄 */
[data-testid="stTabs"] button[role="tab"] {font-size: 1rem; font-weight: 500; color: var(--mute);}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {color: var(--ink);}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {background-color: var(--ink) !important; height: 2px;}
[data-testid="stTabs"] [data-baseweb="tab-border"] {background-color: var(--hair);}
/* 버튼: 검정 알약(주 버튼) */
[data-testid^="stBaseButton-"][data-testid*="econdary"], [data-testid="stBaseButton-primary"], [data-testid="stDownloadButton"] button {
  background: var(--ink) !important; color: #fff !important; border: 0 !important; border-radius: 30px !important;
  min-height: 48px; padding: 0 32px; font-weight: 500; box-shadow: none !important;}
[data-testid^="stBaseButton-"][data-testid*="econdary"] p, [data-testid="stBaseButton-primary"] p, [data-testid="stDownloadButton"] button p {color:#fff !important;}
/* 입력칸: 옅은 회색 바탕, 선택하면 검정 2px 테두리 */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"], [data-testid="stDateInput"] [data-baseweb="input"] {
  background: var(--cloud) !important; border-color: transparent !important; border-radius: 24px !important;}
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within, [data-baseweb="select"] > div:focus-within {
  background: #fff !important; border: 2px solid var(--ink) !important; box-shadow: 0 0 0 6px var(--cloud) !important;}
[data-baseweb="textarea"] {border-radius: 16px !important;}
/* 안내 상자: 평평한 옅은 회색, 왼쪽에 색 줄 (색은 의미가 있을 때만) */
[data-testid="stAlert"], [data-testid="stAlertContainer"] {background: var(--cloud) !important; color: var(--ink) !important; border-radius: 0 !important;}
[data-testid="stAlertContainer"] {border: 0 !important; border-left: 3px solid var(--ink) !important;}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) {border-left-color: var(--success) !important;}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) {border-left-color: var(--sale) !important;}
[data-testid="stAlert"] p {color: var(--ink) !important;}
/* 펼침 상자와 표 */
[data-testid="stExpander"] {border-radius: 0 !important; border-color: var(--hair) !important;}
[data-testid="stExpander"] details {border-radius: 0 !important;}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {color: var(--mute) !important; opacity: 1 !important;}
.ok {color: var(--success); font-weight: 500;} .na {color: var(--mute);}
</style>""", unsafe_allow_html=True)
st.markdown(
    '<div class="hero"><div class="kicker">세액공제 · 정부지원사업</div>'
    '<h1>AI 정부지원금 &amp; 세액공제</h1>'
    '<div class="sub">기업 정보를 넣으면 ① 세액공제·감면 예상액 ② 맞는 정부지원사업 ③ 1페이지 리포트를 만들어 줍니다.</div></div>',
    unsafe_allow_html=True)

won = won_text   # 엔진 결과(만원)를 화면에는 원 단위로 보여 준다

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
# 직접 입력이 기본: 빈 칸에서 시작한다 (금액·인원 0). '가상 기업 시연'을 고르면 예시 기업 5곳 중에서 골라 채울 수 있다
MODE_MANUAL, MODE_DEMO = "직접 입력", "가상 기업 시연"
BLANK = dict(ind=industries[0]["code"], sido="서울", founded=date.today(), rev=0, assets=0, big=False, ep=0, ec=0, yp=0, yc=0,
             rc=0, rp=0, known=False, avg4=0, ct=0, ip=100, fy=date.today().year, ceo=False, sa="수도권 과밀억제권역", **NO_DIS)
KEYS = ["ind", "sido", "founded", "rev", "assets", "big", "ep", "ec", "yp", "yc", "rc", "rp", "known", "avg4",
        "dl", "dt", "du", "dcur", "dred", "ct", "ip", "fy", "ceo", "sa"]


# 금액 칸: 프리셋에 적은 값(억 원·만 원)을 원 단위로 바꿔 쉼표 문자열로 넣는다
MONEY = {"rev": 10 ** 8, "assets": 10 ** 8, "rc": 10 ** 4, "rp": 10 ** 4, "avg4": 10 ** 4,
         "dl": 10 ** 4, "dt": 10 ** 4, "du": 10 ** 4, "dcur": 10 ** 4, "dred": 10 ** 4, "ct": 10 ** 4}


def state_value(p, k):
    if k == "ind":
        return label_of[p[k]]
    return fmt_won(int(p[k] * MONEY[k])) if k in MONEY else p[k]


def _fill(p):
    for k in KEYS:
        st.session_state[k] = state_value(p, k)


def apply_preset():
    _fill(PRESETS[st.session_state["preset"]])


def apply_mode():
    """입력 방식을 바꾸면 입력칸을 새로 채운다: 직접 입력 → 빈 칸, 가상 기업 시연 → 첫 번째 예시."""
    if st.session_state["mode"] == MODE_MANUAL:
        _fill(BLANK)
    else:
        st.session_state["preset"] = list(PRESETS)[0]
        apply_preset()


def normalize_money(key):
    """입력이 끝나면 숫자를 쉼표 형태로 정리한다 (숫자가 아니면 그대로 두고 아래에서 안내)."""
    v = parse_won(st.session_state.get(key))
    if v is not None:
        st.session_state[key] = fmt_won(v)


BAD_MONEY = []


def money_input(label, key, help=None, disabled=False):
    """원 단위 금액 입력. 쉼표를 넣어도 되고 안 넣어도 되며, 칸 아래에 '억·만' 단위로 읽어 준다."""
    st.text_input(label, key=key, on_change=normalize_money, args=(key,), help=help, disabled=disabled, placeholder="예: 500,000,000")
    v = parse_won(st.session_state.get(key))
    if v is None:
        BAD_MONEY.append(label)
        st.caption("⚠ 숫자만 입력해 주세요")
        return 0
    st.caption("= " + kor_unit(v))
    return v


for k in KEYS:
    st.session_state.setdefault(k, state_value(BLANK, k))

summary = st.container()     # 계산이 끝난 뒤 맨 위에 결과 요약을 채운다

st.markdown("##### 기업 정보 입력")
st.radio("입력 방식", [MODE_MANUAL, MODE_DEMO], key="mode", horizontal=True, on_change=apply_mode)
BASIS = "가상 기업 기준 예시" if st.session_state["mode"] == MODE_DEMO else "입력하신 값 기준 예시"
if st.session_state["mode"] == MODE_MANUAL:
    st.caption("입력한 내용은 저장하지 않고 이 화면에서만 계산합니다. 공개 주소이므로 실제 기업의 민감한 정보는 넣지 마세요.")
if st.session_state["mode"] == MODE_DEMO:
    st.caption("가상 기업 5곳 중에서 고르면 아래 입력칸이 한 번에 채워집니다. 직접 값을 고쳐도 됩니다.")
    st.selectbox("가상 기업", list(PRESETS), key="preset", on_change=apply_preset)
tab_a, tab_b, tab_c, tab_d = st.tabs(["기업 정보", "인력 · 연구개발비", "재해손실 (선택)", "법인세 감면 (선택)"])
with tab_a:
    c1, c2 = st.columns(2)
    with c1:
        label = st.selectbox("업종", list(labels), key="ind")
        sido = st.selectbox("소재지 (시·도)", SIDO, key="sido")
        founded = st.date_input("설립일", min_value=date(1980, 1, 1), max_value=date.today(), key="founded")
    with c2:
        revenue_w = money_input("최근 3년 평균 매출액 (원)", "rev")
        assets_w = money_input("자산총액 (원)", "assets")
        big_owner = st.checkbox("자산 5천억 원 이상 법인이 지분 30% 이상을 가진 최다출자자", key="big")
with tab_b:
    st.caption("통합고용세액공제와 연구·인력개발비 세액공제에 쓰입니다.")
    b1, b2, b3 = st.columns(3)
    ep = b1.number_input("전년 상시근로자 수", min_value=0, step=1, key="ep")
    ec = b1.number_input("당해 상시근로자 수", min_value=0, step=1, key="ec")
    yp = b2.number_input("전년 청년 등 근로자 수", min_value=0, step=1, key="yp")
    yc = b2.number_input("당해 청년 등 근로자 수", min_value=0, step=1, key="yc")
    with b3:
        rnd_curr_w = money_input("연구·인력개발비 당해 지출액 (원)", "rc")
        rnd_prev_w = money_input("직전 과세연도 지출액 (원)", "rp")
        known = st.checkbox("직전 4년 연평균을 알고 있음", key="known")
        avg4_w = money_input("직전 4년 연평균 (원)", "avg4", disabled=not known)
    with st.expander("청년 등 근로자는 누구인가요?"):
        st.write("만 15~34세(병역 이행 시 최대 6년을 뺀 나이), 장애인, 계약일 현재 60세 이상, 경력단절근로자, "
                 "북한이탈주민입니다. 근로계약 체결 당시 34세 이하면 이후 일정 기간 청년으로 봅니다. "
                 "(시행령 제26조의8 제4항)")
with tab_c:
    st.caption("화재·풍수해 등으로 사업용 자산을 잃은 경우에만 입력하세요 (원 단위, 토지는 제외한 장부가액). 입력하지 않으면(0) 해당 없음으로 봅니다.")
    d1, d2, d3 = st.columns(3)
    with d1:
        dis_lost_w = money_input("재해로 상실한 자산가액 (원)", "dl")
        dis_total_w = money_input("상실 전 총자산가액, 토지 제외 (원)", "dt")
    with d2:
        dis_unpaid_w = money_input("재해일 현재 미부과·미납 법인세 (원)", "du")
        dis_cur_w = money_input("재해일이 속한 사업연도 법인세 (원)", "dcur")
    with d3:
        dis_red_w = money_input("그 법인세에서 다른 법률로 받는 공제·감면세액 (원)", "dred")
with tab_d:
    st.caption("창업중소기업 세액감면과 중소기업 특별세액감면은 법인세 산출세액에 감면율을 곱해 계산합니다 (원 단위). "
               "산출세액을 비워 두면(0) 계산하지 않습니다. 감면 대상이 아닌 사업의 소득이 섞여 있으면 비율을 낮추세요.")
    AREAS = {"수도권 과밀억제권역": "overcrowded", "수도권 (과밀억제권역 제외)": "capital_other",
             "수도권 인구감소지역": "pop_decline", "비수도권": "non_capital"}
    t1, t2, t3 = st.columns(3)
    with t1:
        corp_tax_w = money_input("법인세 산출세액 (원)", "ct")
        income_pct = st.number_input("감면 대상 소득 비율 (%)", min_value=0, max_value=100, step=10, key="ip")
    first_year = t2.number_input("최초 소득 발생 연도 (창업감면)", min_value=1980, max_value=2030, step=1, key="fy")
    youth_ceo = t2.checkbox("대표자가 창업 당시 만 34세 이하 (청년창업)", key="ceo")
    area_label = t3.selectbox("창업 지역 구분 (창업감면)", list(AREAS), key="sa",
                              help="과밀억제권역·인구감소지역 해당 여부는 직접 선택합니다. 소재지가 수도권 밖이면 '비수도권'이 적용됩니다.")

if BAD_MONEY:
    st.error("금액은 숫자만 입력해 주세요 (쉼표는 자동으로 붙습니다): " + ", ".join(BAD_MONEY))
    st.stop()
# 화면은 원 단위로 받고, 계산 엔진에는 만원(억원)으로 환산해 넘긴다
revenue, assets = won_to_eok(revenue_w), won_to_eok(assets_w)
rnd_curr, rnd_prev, avg4 = won_to_man(rnd_curr_w), won_to_man(rnd_prev_w), won_to_man(avg4_w)
dis_lost, dis_total, dis_unpaid, dis_cur, dis_red = (won_to_man(v) for v in (dis_lost_w, dis_total_w, dis_unpaid_w, dis_cur_w, dis_red_w))
corp_tax = won_to_man(corp_tax_w)
if dis_lost > dis_total:
    st.error("상실한 자산가액이 상실 전 총자산가액보다 클 수 없습니다. ('재해손실' 탭을 확인하세요)")
    st.stop()
if yp > ep or yc > ec:
    st.error("청년 등 근로자 수는 전체 상시근로자 수보다 많을 수 없습니다. ('인력 · 연구개발비' 탭을 확인하세요)")
    st.stop()

sme = judge_sme({"ksic": labels[label], "avg_revenue_eok": revenue, "assets_eok": assets, "owned_by_large_corp": big_owner})
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

st.markdown("##### 결과")
r_tax, r_match, r_report, r_expert = st.tabs(["세액공제 · 감면", "지원사업 추천", "해설 · PDF 리포트", "전문가 연결 (시연)"])

# ---------- 세액공제·감면 ----------
with r_tax:
    if sme["is_sme"]:
        st.success(f"중소기업 기준에 해당합니다. ({sme['industry']}: 평균매출액 {sme['limit_eok']:,}억 원 이하, 자산총액 5천억 원 미만)")
    else:
        st.warning("중소기업 기준에 해당하지 않을 수 있습니다. 아래 계산은 중소기업 기준이라 참고용으로만 보세요.")
    with st.expander("중소기업 판정 세부 내용"):
        st.table(pd.DataFrame([{"항목": c["name"], "결과": "충족" if c["passed"] else "불충족", "설명": c["detail"]} for c in sme["checks"]]))
        st.caption("아직 원문 확인 전인 판정 기준")
        for u in sme["unverified"]:
            st.write("· " + u)

    STATUS_LABEL = {"computed": "● 금액 계산됨", "not_applicable": "○ 해당 없음 (입력 기준)"}
    ORDER = {"computed": 0, "not_applicable": 1, "planned": 2}   # 계산된 공제를 먼저 보여준다
    cards = sorted(res["credits"], key=lambda c: ORDER[c["status"]])
    for i in range(0, len(cards), 3):
        for card, col in zip(cards[i:i + 3], st.columns(3)):
            with col, st.container(border=True):
                st.markdown(f"**{card['name']}**")
                st.markdown(f'<span class="{"ok" if card["status"] == "computed" else "na"}">{STATUS_LABEL[card["status"]]}</span>', unsafe_allow_html=True)
                if card["status"] == "computed":
                    st.metric("첫해 예상액", won(card["amount_first_year"]))
                    st.caption("= " + kor_unit(man_to_won(card["amount_first_year"])))
                st.write(card["basis"])
                if card["status"] == "computed" and not card["in_total"]:
                    st.warning("합계에서 제외: " + card["excluded_reason"])
                st.caption(card["law_ref"] + ("" if card["verified"] else " · 일부 조문 확인 전"))
    if res["overlap_note"]:
        st.info(res["overlap_note"])

    with st.expander("통합고용세액공제 연차별 금액 · 청년을 더 채용하면?"):
        inc = res["increases"]
        st.write(f"늘어난 인원: 청년 등 **{inc['youth']}명**, 청년 외 **{inc['other']}명**")
        st.dataframe(pd.DataFrame({"구분": ["통합고용세액공제"], **{f"{i+1}차연도": [won(v)] for i, v in enumerate(res["employment_by_year"])}}),
                     hide_index=True, width="stretch")
        sc = scenario(inp)
        df = pd.DataFrame({f"{r['extra_youth']}명 추가": r["employment_by_year"] for r in sc}, index=["1차연도", "2차연도", "3차연도"]).T * 10 ** 4
        st.bar_chart(df)
        st.caption("단위: 원. 막대는 청년을 더 채용했을 때 연차별 공제액입니다.")
    with st.expander("계산 가정과 한계"):
        for n in res["notes"]:
            st.write("· " + n)
    st.caption(f"{BASIS}입니다. '첫해 예상 감면액'은 금액이 계산되고 중복 적용 배제에서 제외되지 않은 항목의 합이며, 최저한세는 반영하지 않았습니다. {DISCLAIMER}")

# ---------- 지원사업 추천 ----------
with r_match:
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
    for r in out["items"]:
        dd = "상시" if r["d_day"] is None else f"D-{r['d_day']}"
        with st.container(border=True):
            st.markdown(f"**{r['title']}**")
            st.caption(f"{dd} · 추천 점수 {r['score']} · {r['agency']} · {r['region']}")
            st.caption(f"대상: {r['target']}")
            st.write("근거 키워드: " + (", ".join(r["matched_keywords"]) or "없음") +
                     ("" if r["semantic"] is None else f" · 의미 유사도 {r['semantic']}"))
            for f in r["flags"]:
                st.caption("⚠ " + f)
            if r["url"]:
                st.link_button("공고 보기", r["url"])
    st.info("공고 신청 자격은 원문 공고로 반드시 확인하세요. 추천 점수는 키워드와 의미 유사도를 섞은 상대값으로, 추천 순서를 정하는 데만 씁니다.")
    ex_ = out["excluded"]
    with st.expander("데이터 출처와 제외된 공고"):
        st.write(f"공고 데이터: {src_desc}")
        st.write(f"조건에 맞지 않아 제외한 공고 {sum(ex_.values()):,}건 "
                 f"(마감 {ex_.get('마감', 0):,}, 교육·행사 {ex_.get('교육·행사', 0):,}, 지역 {ex_.get('지역', 0):,}, 업력 {ex_.get('업력', 0):,}) · "
                 f"점수를 계산한 공고 {out['scored']:,}건")

# ---------- 해설·PDF ----------
with r_report:
    st.caption("숫자는 규칙 엔진이 계산한 값만 쓰고, 해설 문장은 AI(Claude)가 씁니다. API 키가 없거나 검증에 실패하면 기본 문장을 씁니다.")
    facts = build_facts(label.split(" ", 1)[1], inp, res, out["items"], sido)
    docs = required_documents(res)
    with st.expander("신청·신고 때 준비할 서류 (참고)", expanded=True):
        st.caption(DOCS_NOTICE)
        for d in docs:
            st.markdown(f"**{d['name']}** · {d['timing']}")
            st.markdown("\n".join("- " + x for x in d["documents"]))
        if not docs:
            st.write("금액이 계산된 공제·감면이 없어 안내할 서류가 없습니다.")
    if st.button("해설 만들기"):
        with st.spinner("해설을 만드는 중입니다"):
            st.session_state["explain"] = {"facts": facts, **explain(facts)}
    ex = st.session_state.get("explain")
    if ex and ex["facts"] == facts:
        st.write(ex["text"])
        st.caption(("AI 작성" if ex["source"] == "llm" else "기본 문장") + (f" · {ex['note']}" if ex["note"] else ""))
        pdf = build_pdf(facts, ex["text"], out["items"], res["notes"], ex["source"], docs=docs, basis=BASIS)
        st.download_button("1페이지 PDF 내려받기", pdf, file_name="세액공제_지원사업_추천_리포트.pdf", mime="application/pdf")
    elif ex:
        st.info("입력이 바뀌었습니다. '해설 만들기'를 다시 눌러 주세요.")
    st.warning(f"{DISCLAIMER} 신고 대행·세액 확정·세무 자문이 아닙니다.")

# ---------- 전문가 연결 ----------
with r_expert:
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
        memo = st.text_area("전문가에게 전달할 내용", value=f"{label.split(' ', 1)[1]} / {sido} / 첫해 예상 감면액 {won(res['total_first_year'])} (참고용)", height=80)
        agree = st.checkbox("개인정보 안내를 읽었고 시연용임을 이해했습니다")
        sent = st.form_submit_button("상담 요청 보내기 (시연)")
    if sent:
        if not agree:
            st.error("개인정보 안내 확인에 체크해 주세요.")
        else:
            st.success("시연용 요청이 접수된 것으로 표시합니다. 실제로는 아무 곳에도 전송·저장되지 않았습니다.")
            st.write(f"**상담 분야:** {topic}  \n**전달될 내용(예시):** {memo}")
            st.caption("실제 서비스에서는 이 화면 뒤에 세무 전문가 매칭과 일정 안내가 이어집니다.")

# ---------- 맨 위 결과 요약 (위에서 만들어 둔 자리에 채운다) ----------
with summary:
    n_done = sum(1 for c in res["credits"] if c["status"] == "computed")
    with st.container(border=True):
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("첫해 예상 감면액", won(res["total_first_year"]), help="계산된 공제·감면 중 중복 배제에서 제외되지 않은 항목의 합 · " + "= " + kor_unit(man_to_won(res["total_first_year"])))
        s2.metric("금액이 계산된 항목", f"{n_done}개 / {len(res['credits'])}개", help="통합고용·연구개발비·재해손실·창업감면·특별감면")
        s3.metric("중소기업 판정", "해당" if sme["is_sme"] else "확인 필요")
        s4.metric("추천 공고", f"{len(out['items'])}건", help="조건에 맞는 공고 중 점수가 높은 순서")
        st.caption(f"{BASIS} · {DISCLAIMER} 아래 탭에서 자세한 내용을 확인하세요.")
