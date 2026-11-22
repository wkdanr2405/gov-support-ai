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
from src.tax_engine.regions import classify, sigungu_options
from src.matching import Embedder, build_profile, match
from src.money import fmt_won, kor_unit, man_to_won, parse_won, won_text, won_to_eok, won_to_man
from src.auth import ROLE_CORP, ROLE_EXPERT
from src.ui_pro import VIRTUAL_NOTICE, render_admin_home, render_company_profile, render_expert_home, render_login
from src.experts import STEPS, build_brief, load_experts, rank_experts, receipt_no, show_etc
from src.experts.db import add_request, get_company, list_requests_by_client, new_db
from src.report.docs import NOTICE as DOCS_NOTICE, required_documents
from src.report.explain import build_facts, explain
from src.report.pdf import build_brief_pdf, build_pdf

from src.tax_engine import calculate, industry_list, judge_sme, scenario

DISCLAIMER = "참고용 예상치이며 최종 판단은 세무 전문가가 합니다."


st.set_page_config(page_title="AI 정부지원금 & 세액공제 추천", page_icon="📊", layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Do+Hyeon&family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
/* 디자인 규칙 (docs/09-design-system.md, Shopifi 참고): 두 바탕을 섞지 않는다 -
   맨 위 띠만 검정(시네마틱), 작업 화면은 크림색 바탕 + 흰 카드(거래 화면). 버튼은 알약 모양만 쓴다. 연두(aloe)는 면 색으로만 쓴다 */
:root {--night:#000000; --cream:#fbfbf5; --white:#ffffff; --ink:#000000; --hair:#e4e4e7; --edge:#8a8a90; --shade30:#d4d4d8; --shade40:#a1a1aa; --shade50:#71717a; --shade70:#3f3f46;
       --aloe:#c1fbd4; --pistachio:#d4f9e0; --sale:#d30005;}
.stApp {background: var(--cream);}
.stApp, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp p, .stApp label, .stApp li,
.stApp button, .stApp input, .stApp textarea, .stApp [data-baseweb="select"] {
  font-family: Inter, "Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", Helvetica, Arial, sans-serif; font-feature-settings: "ss03";}
.block-container {padding-top: 1.5rem; max-width: 1120px;}
/* 맨 위 띠: 순수 검정, 얇은(300) 큰 제목, 흰 글자 */
.hero {background: var(--night); color: #fff; padding: 56px 40px 44px; margin-bottom: 24px; border-radius: 12px;}
.hero .kicker {font-size: 0.75rem; font-weight: 400; letter-spacing: 0.06em; color: var(--shade40); margin-bottom: 16px;}
.hero h1 {color:#fff !important; font-family: "Do Hyeon", "Noto Sans KR", sans-serif !important; font-size: clamp(1.5rem, 5.6vw, 3.4rem) !important; font-weight: 400 !important;
  line-height: 1.1 !important; letter-spacing: 0; margin: 0 0 20px 0; padding: 0; white-space: nowrap;}
.hero .sub {font-size: 1rem; font-weight: 400; color: var(--shade40); line-height: 1.6; text-wrap: balance; word-break: keep-all;}
@media (max-width: 640px) {.hero {padding: 32px 22px 26px;} .hero h1 {font-size: 1.5rem !important;}}
h5 {font-size: 1.5rem !important; font-weight: 500 !important; letter-spacing: 0.01em; margin-top: 40px !important;}
/* 카드: 흰색 면, 모서리 12px, 연한 선, 작은 그림자를 겹친 은은한 테두리 효과 */
[data-testid="stVerticalBlockBorderWrapper"] {background: var(--white); border: 1px solid var(--edge) !important; border-radius: 12px !important;
  box-shadow: 0 8px 8px rgba(0,0,0,0.04), 0 4px 4px rgba(0,0,0,0.04), 0 2px 2px rgba(0,0,0,0.04);}
[data-testid="stMetricValue"] {font-size: 1.9rem; font-weight: 500;}
[data-testid="stMetricLabel"] {color: var(--shade50);}
/* 탭: 선택된 탭은 검정 밑줄 */
[data-testid="stTabs"] button[role="tab"] {font-size: 1rem; font-weight: 500; color: var(--shade50);}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {color: var(--ink);}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {background-color: var(--ink) !important; height: 2px;}
[data-testid="stTabs"] [data-baseweb="tab-border"] {background-color: var(--edge);}
/* 버튼: 알약만. 기본은 검정 알약(눌리면 shade-70), 내려받기·요청 보내기는 연두 알약 */
[data-testid^="stBaseButton-"][data-testid*="econdary"], [data-testid="stBaseButton-primary"] {
  background: var(--ink) !important; color: #fff !important; border: 0 !important; border-radius: 9999px !important;
  min-height: 48px; padding: 12px 28px; font-weight: 500; box-shadow: none !important;}
[data-testid^="stBaseButton-"][data-testid*="econdary"]:hover, [data-testid="stBaseButton-primary"]:hover, [data-testid^="stBaseButton-"][data-testid*="econdary"]:active {background: var(--shade70) !important;}
[data-testid^="stBaseButton-"][data-testid*="econdary"] p, [data-testid="stBaseButton-primary"] p {color:#fff !important;}
[data-testid="stDownloadButton"] button, [data-testid="stFormSubmitButton"] button {
  background: var(--aloe) !important; border: 0 !important; border-radius: 9999px !important; min-height: 48px; padding: 12px 28px; box-shadow: none !important;}
[data-testid="stDownloadButton"] button p, [data-testid="stFormSubmitButton"] button p {color: var(--ink) !important; font-weight: 500;}
[data-testid="stDownloadButton"] button:hover, [data-testid="stFormSubmitButton"] button:hover {background: #a8f5c2 !important;}
/* 입력칸: 흰 바탕, 1px 연한 선, 모서리 8px, 선택하면 검정 선 */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"], [data-testid="stDateInput"] [data-baseweb="input"] {
  background: var(--white) !important; border: 1px solid var(--edge) !important; border-radius: 8px !important; box-shadow: none !important;}
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within, [data-baseweb="select"] > div:focus-within {border-color: var(--ink) !important; box-shadow: 0 0 0 1px var(--ink) !important;}
/* 안내 상자: 흰 면 + 연한 선, 성공은 연두 면, 오류는 빨간 줄 */
[data-testid="stAlertContainer"] {background: var(--white) !important; color: var(--ink) !important; border: 1px solid var(--edge) !important; border-radius: 12px !important;}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) {background: var(--pistachio) !important; border-color: var(--pistachio) !important;}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) {border-left: 4px solid var(--sale) !important;}
[data-testid="stAlert"] p, [data-testid="stAlertContainer"] p {color: var(--ink) !important;}
/* 펼침 상자와 입력 양식 */
[data-testid="stExpander"], [data-testid="stExpander"] details {background: var(--white) !important; border: 1px solid var(--edge) !important; border-radius: 12px !important;}
[data-testid="stForm"] {background: var(--white) !important; border: 1px solid var(--edge) !important; border-radius: 12px !important;}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {color: var(--shade50) !important; opacity: 1 !important;}
/* 작은 알약 표시: 해당/계산됨은 연두, 나머지는 회색 */
.ok, .na {display: inline-block; font-size: 0.75rem; font-weight: 500; letter-spacing: 0.04em; padding: 4px 12px; border-radius: 9999px; color: var(--ink);}
.ok {background: var(--aloe);} .na {background: var(--shade30);}
/* 현재 Streamlit 구조에 맞춘 진한 테두리: 카드(테두리 있는 묶음)·입력칸·날짜칸 */
[data-testid="stVerticalBlock"][style*="border"], [data-testid="stColumn"] [data-testid="stVerticalBlock"] {border-color: var(--edge) !important;}
[data-testid="stTextInputRootElement"], [data-testid="stDateInputField"], [data-testid="stSelectbox"] [role="group"], [data-testid="stNumberInput"] [role="group"],
[data-testid="stTextAreaRootElement"] {background: var(--white) !important; border: 1px solid var(--edge) !important; border-radius: 8px !important; box-shadow: none !important;}
[data-testid="stTextInputRootElement"]:focus-within, [data-testid="stDateInputField"]:focus-within, [data-testid="stSelectbox"] [role="group"]:focus-within,
[data-testid="stTextAreaRootElement"]:focus-within {border-color: var(--ink) !important; box-shadow: 0 0 0 1px var(--ink) !important;}
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
                                                        ct=0, ip=100, fy=2023, ceo=True),
    "② 부산 기계장비 제조 (설립 7년, 소폭 증원)": dict(ind="C29", sido="부산", founded=date(2019, 5, 2), rev=80, assets=120, big=False,
                                                    ep=25, ec=27, yp=3, yc=4, rc=8000, rp=7000, known=True, avg4=6500,
                                                    ct=3000, ip=100, fy=2019, ceo=False),
    "③ 경기 소프트웨어 (설립 2년, 급성장)": dict(ind="J", sido="경기", founded=date(2024, 6, 10), rev=5, assets=8, big=False,
                                              ep=4, ec=8, yp=1, yc=5, rc=6000, rp=0, known=False, avg4=0,
                                              ct=800, ip=100, fy=2024, ceo=True, sg="용인시"),
}
NO_DIS = dict(dl=0, dt=0, du=0, dcur=0, dred=0)      # 재해손실 입력 기본값 (재해 없음)
for _p in PRESETS.values():
    _p.update(NO_DIS)
PRESETS["④ 서울 전자부품 제조 (공장 화재 · 재해손실세액공제 시연)"] = dict(
    PRESETS[list(PRESETS)[0]], dl=16000, dt=40000, du=3000, dcur=2000, dred=500)
PRESETS["⑤ 대구 전자부품 제조 (2026년 창업 · 청년창업 감면 vs 통합고용 중복 배제 시연)"] = dict(
    PRESETS[list(PRESETS)[0]], sido="대구", founded=date(2026, 3, 1), yp=0, yc=2,
    ct=4000, ip=100, fy=2026, ceo=True)
# 직접 입력이 기본: 빈 칸에서 시작한다 (금액·인원 0). '가상 기업 시연'을 고르면 예시 기업 5곳 중에서 골라 채울 수 있다
MODE_MANUAL, MODE_DEMO = "직접 입력", "가상 기업 시연"
BLANK = dict(ind=industries[0]["code"], sido="서울", founded=date.today(), rev=0, assets=0, big=False, ep=0, ec=0, yp=0, yc=0,
             rc=0, rp=0, known=False, avg4=0, ct=0, ip=100, fy=date.today().year, ceo=False, **NO_DIS)
KEYS = ["ind", "sido", "founded", "rev", "assets", "big", "ep", "ec", "yp", "yc", "rc", "rp", "known", "avg4",
        "dl", "dt", "du", "dcur", "dred", "ct", "ip", "fy", "ceo"]


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
    st.session_state.pop("ip2", None)
    if p.get("sg"):
        st.session_state["sg"] = p["sg"]      # 시·군·구 선택칸 (수도권 안 예시만)
    else:
        st.session_state.pop("sg", None)


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

edb = st.session_state.setdefault("expert_db", new_db())   # 전문가 명단 데이터베이스 (이 접속 동안만 메모리에 있음)
# ---------- 로그인 (시연용 가상 로그인) ----------
# 로그인하지 않으면 아래 어떤 화면도 실행되지 않는다. 역할마다 실행되는 화면 코드가 달라서 기업과 전문가는 서로의 화면·정보를 볼 수 없다.
auth = st.session_state.get("auth")
if not auth:
    render_login(edb)
    st.stop()


def do_logout():
    """로그아웃: 기업 입력·결과·화면 상태를 모두 지운다. 전문가 명단·상담 요청 보관함(expert_db)만 접속 동안 남긴다."""
    for k in list(st.session_state.keys()):
        if k != "expert_db":
            del st.session_state[k]


bar1, bar2 = st.columns([5, 1])
bar1.markdown(f"**{auth['name']}** · {auth['role']} 계정으로 로그인됨")
bar2.button("로그아웃", key="logout", on_click=do_logout)
if auth["role"] != ROLE_CORP:           # 전문가·운영자는 기업 입력·결과 화면 코드가 실행되기 전에 여기서 끝난다
    st.caption(VIRTUAL_NOTICE)
    if auth["role"] == ROLE_EXPERT:
        render_expert_home(edb, auth)
    else:
        render_admin_home(edb)
    st.stop()
render_company_profile(edb, auth)       # 기업 본인 프로필 (기업명·이메일·연락처)
top_cust = st.container()

with top_cust:
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
        t1, t2, t3 = st.columns(3)
        with t1:
            corp_tax_w = money_input("법인세 산출세액 (원)", "ct")
            income_pct = st.number_input("감면 대상 소득 비율 (%)", min_value=0, max_value=100, step=10, key="ip")
        first_year = t2.number_input("최초 소득 발생 연도 (창업감면)", min_value=1980, max_value=2030, step=1, key="fy")
        youth_ceo = t2.checkbox("대표자가 창업 당시 만 34세 이하 (청년창업)", key="ceo")
        sigungu, in_part = None, None
        with t3:
            opts = sigungu_options(sido)
            if opts:
                sigungu = st.selectbox("사업장 시·군·구 (창업감면 지역 구분)", opts, key="sg",
                                       help="수도권정비계획법 시행령 별표 1과 행정안전부 고시(제2026-61호)로 과밀억제권역·인구감소지역을 자동 구분합니다.")
                _c = classify(sido, sigungu)
                if _c["needs_check"]:
                    in_part = st.radio("사업장이 과밀억제권역에 해당하는 곳인가요?", ["예", "아니오"], key="ip2", horizontal=True,
                                       help=_c["needs_check"]) == "예"
            else:
                st.caption("수도권 밖이거나 서울이라 시·군·구 선택이 필요 없습니다.")
    _cls = classify(sido, sigungu, in_part)

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

    sme_blank = revenue_w == 0 and assets_w == 0   # 매출액·자산총액을 아직 넣지 않은 빈 화면
    sme = judge_sme({"ksic": labels[label], "avg_revenue_eok": revenue, "assets_eok": assets, "owned_by_large_corp": big_owner})
    inp = {"region": "capital" if sido in CAPITAL_AREA else "non_capital",
           "employees_prev": int(ep), "employees_curr": int(ec), "youth_prev": int(yp), "youth_curr": int(yc),
           "rnd_curr": rnd_curr, "rnd_prev": rnd_prev,
           "ksic": labels[label], "avg_revenue_eok": revenue, "is_sme": sme["is_sme"], "founded": founded.isoformat(),
           "first_income_year": int(first_year), "youth_ceo": youth_ceo, "corp_tax": corp_tax, "eligible_income_pct": income_pct,
           "startup_area": _cls["area"],
           "disaster_lost_assets": dis_lost, "disaster_total_assets": dis_total, "disaster_unpaid_tax": dis_unpaid,
           "disaster_current_tax": dis_cur, "disaster_other_reductions": dis_red}
    if known:
        inp["rnd_prev4_avg"] = avg4
    res = calculate(inp)

    st.markdown("##### 결과")
    r_tax, r_match, r_report, r_expert = st.tabs(["세액공제 · 감면", "지원사업 추천", "해설 · PDF 리포트", "전문가 연결"])

    # ---------- 세액공제·감면 ----------
    with r_tax:
        if sme_blank:
            st.info("매출액과 자산총액을 입력하면 중소기업 해당 여부를 판정합니다. 지금은 확인할 수 없습니다.")
        elif sme["is_sme"]:
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
    TOP_N, PAGE_SIZE = 10, 4      # 추천 10건을 한 화면에 4건씩 쪽을 넘겨 보여 준다
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
            out = match(profile, anns, get_embedder() if use_ai else None, top_n=TOP_N)
        except Exception as e:  # 모델 내려받기 실패 등
            st.warning(f"의미 기반 점수를 쓸 수 없어 키워드 점수만 사용합니다. ({type(e).__name__})")
            out = match(profile, anns, None, top_n=TOP_N)
        items = out["items"]
        n_pages = max(1, -(-len(items) // PAGE_SIZE))
        page = st.session_state.get("match_page", 1)
        if page > n_pages:                       # 입력이 바뀌어 공고 수가 줄었으면 첫 쪽으로
            page = st.session_state["match_page"] = 1
        st.caption(f"조건에 맞는 공고 중 점수가 높은 {len(items)}건 · {page}/{n_pages}쪽 ({PAGE_SIZE}건씩)")
        for r in items[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]:
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
        if n_pages > 1:
            st.radio("쪽 이동", list(range(1, n_pages + 1)), key="match_page", horizontal=True, label_visibility="collapsed",
                     format_func=lambda n: f"{n}")
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
        st.caption("표시된 전문가·법인명과 접수 결과는 모두 시연을 위해 지어낸 가상의 정보이며, 입력한 내용은 전송·저장되지 않습니다.")
        with st.expander("개인정보 안내"):
            st.write("· 실제 서비스라면 상담 연결을 위해 이름·연락처 같은 개인정보를 받게 됩니다. 이때 수집 목적, 항목, 보관 기간을 알리고 동의를 받아야 합니다.\n"
                     "· 이 화면은 어떤 정보도 서버에 보내거나 저장하지 않습니다. 실제 이름·이메일·전화번호는 입력하지 마세요.\n"
                     "· 상담은 세무 전문가가 하며, 이 서비스는 신고 대행·세액 확정·세무 자문을 하지 않습니다.")

        # 1) 전문가 고르기: 합계에 들어간 공제·감면과 분야가 겹치는 순서로 보여 준다
        st.markdown("**1. 법인 고르기**")
        in_total_ids = [c["id"] for c in res["credits"] if c["status"] == "computed" and c.get("in_total")]
        experts = rank_experts(load_experts(edb), in_total_ids, ksic=labels[label])
        st.caption(f"회계·세무법인 {len(experts)}곳 중 이번 결과의 분야·업종에 잘 맞는 순서입니다 (분야 10점 · 업종 2점, 같으면 명단 순서).")
        for e_, col in zip(experts[:3], st.columns(3)):
            with col, st.container(border=True):
                st.markdown(f"**{e_['name']}**")
                st.caption(f"{e_['kind']} · 전문 인력 {e_['staff']}명 · 업력 {e_['years']}년")
                st.write(e_["intro"])
                st.caption("상담 방식: " + " · ".join(show_etc(e_["channels"])))
                st.markdown(f'<span class="{"ok" if e_["reasons"] else "na"}">' +
                            ("● 추천 이유: " + e_["reason_line"] if e_["reasons"] else "○ 이번 결과와 겹치는 항목 없음") + "</span>",
                            unsafe_allow_html=True)
        if len(experts) > 3:
            with st.expander(f"나머지 법인 {len(experts) - 3}곳 보기"):
                for e_ in experts[3:]:
                    st.markdown(f"**{e_['name']}** · {e_['kind']} · 전문 인력 {e_['staff']}명 · 업력 {e_['years']}년  \n"
                                f"{e_['intro']}  \n"
                                f"<span class=\"{'ok' if e_['reasons'] else 'na'}\">" +
                                ("● 추천 이유: " + e_["reason_line"] if e_["reasons"] else "○ 이번 결과와 겹치는 항목 없음") + "</span>",
                                unsafe_allow_html=True)
        pick = st.radio("상담받을 법인", [x["name"] for x in experts], key="expert_pick", horizontal=True)
        chosen = next(x for x in experts if x["name"] == pick)

        # 2) 상담 전달 자료: 계산 결과·준비 서류·추천 공고를 자동으로 묶는다 (1페이지 PDF)
        me_corp = get_company(edb, auth["id"])
        company = dict(name=me_corp["name"], email=me_corp["email"], phone=me_corp["phone"], industry=label.split(" ", 1)[1], sido=sido, founded=founded.isoformat(), is_sme=sme["is_sme"] and not sme_blank,
                       ep=int(ep), ec=int(ec), yp=int(yp), yc=int(yc))
        st.markdown("**2. 상담 전달 자료**")
        preview = build_brief(BASIS, company, res, docs, out["items"])
        with st.expander("전달될 내용 미리보기", expanded=False):
            st.text(preview)
        st.download_button("상담 전달 자료 PDF 내려받기", build_brief_pdf(BASIS, company, res, docs, out["items"], expert=chosen),
                           file_name="상담_전달_자료.pdf", mime="application/pdf")

        # 3) 상담 요청
        st.markdown("**3. 상담 요청**")
        with st.form("expert_form"):
            st.caption(f"법인에 전달되는 연락처: {me_corp['email']} · {me_corp['phone']} (위쪽 '내 기업 프로필'에서 고칠 수 있습니다)")
            g1, g2 = st.columns(2)
            topic = g1.selectbox("상담 희망 분야", ["세액공제 예상액 검토", "정부지원사업 신청 준비", "둘 다", "기타 (추가로 전할 말에 적어 주세요)"])
            channel = g2.selectbox("희망 상담 방식", chosen["channels"], format_func=lambda x: show_etc([x])[0])
            memo = st.text_area("추가로 전할 말", placeholder="궁금한 점이나 원하는 일정을 적어 주세요", height=80)
            agree = st.checkbox("개인정보 안내를 읽고 이해했습니다")
            sent = st.form_submit_button("상담 요청 보내기")
        if sent:
            if not agree:
                st.error("개인정보 안내 확인에 체크해 주세요.")
            else:
                brief = build_brief(BASIS, company, res, docs, out["items"], topic=topic, memo=memo)
                no = receipt_no(brief)
                st.success("상담 요청이 접수되었습니다.")
                st.write(f"**접수번호:** {no}  \n**상담 법인:** {chosen['name']} ({chosen['kind']})  \n"
                         f"**상담 분야:** {topic} · **방식:** {channel}")
                st.markdown("**앞으로의 진행**")
                st.markdown("\n".join(f"{i}. {s_}" for i, s_ in enumerate(STEPS, 1)))
                sent_pdf = build_brief_pdf(BASIS, company, res, docs, out["items"], expert=chosen, topic=topic, channel=channel,
                                           memo=memo, receipt=no)
                add_request(edb, no, chosen["id"], topic, channel, memo, brief, sent_pdf, auth["id"], auth["name"])    # 그 전문가 계정의 '고객 상담 요청'에 나타남
                st.download_button("접수한 상담 전달 자료 PDF 내려받기", sent_pdf,
                                   file_name=f"상담_전달_자료_{no}.pdf", mime="application/pdf")
                st.caption("이 요청은 선택한 전문가 계정의 '고객 상담 요청'에만 전달됩니다 (로그아웃 후 그 전문가로 로그인하면 볼 수 있습니다).")
                st.caption("신청·신고는 전문가와 상의해 진행하세요.")

        # 4) 내가 보낸 상담 요청 (이 기업 계정이 보낸 것만 보인다)
        st.markdown("**4. 내가 보낸 상담 요청**")
        mine = list_requests_by_client(edb, auth["id"])
        if not mine:
            st.caption("아직 보낸 상담 요청이 없습니다.")
        for rq in mine:
            st.write(f"· {rq['receipt']} · {rq['topic']} · {rq['channel']} · 요청 전달 법인: {next((e['name'] for e in load_experts(edb) if e['id'] == rq['expert_id']), rq['expert_id'])}")

    # ---------- 맨 위 결과 요약 (위에서 만들어 둔 자리에 채운다) ----------
    with summary:
        n_done = sum(1 for c in res["credits"] if c["status"] == "computed")
        with st.container(border=True):
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("첫해 예상 감면액", won(res["total_first_year"]), help="계산된 공제·감면 중 중복 배제에서 제외되지 않은 항목의 합 · " + "= " + kor_unit(man_to_won(res["total_first_year"])))
            s2.metric("금액이 계산된 항목", f"{n_done}개 / {len(res['credits'])}개", help="통합고용·연구개발비·재해손실·창업감면·특별감면")
            s3.metric("중소기업 판정", "해당" if sme["is_sme"] and not sme_blank else "확인 필요")
            s4.metric("추천 공고", f"{len(out['items'])}건", help="조건에 맞는 공고 중 점수가 높은 순서")
            st.caption(f"{BASIS} · {DISCLAIMER} 아래 탭에서 자세한 내용을 확인하세요.")
