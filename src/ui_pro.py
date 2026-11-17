"""로그인 화면과 전문가·운영자 화면 (Streamlit). 기업 화면은 app.py에 있다.

역할별 접근은 app.py가 로그인 결과로 어느 함수를 실행할지 정하는 방식이라, 기업 계정으로는 이 파일의 전문가·운영자 화면 코드가 아예 실행되지 않는다.
"""
import streamlit as st

from src.auth import DEMO_PASSWORD, ROLE_ADMIN, ROLE_CORP, ROLE_EXPERT, ROLES, accounts, login
from src.experts import CREDIT_NAMES, INDUSTRY_NAMES, REGION_GROUP
from src.experts.db import approve_expert, list_experts, list_requests, register_expert

VIRTUAL_NOTICE = "모든 인물과 법인은 시연을 위해 지어낸 가상의 정보이며, 입력한 내용은 이 접속 동안만 메모리에 있다가 사라집니다. 실제 이름·연락처는 입력하지 마세요."


def render_register_form(edb) -> None:
    """전문가 가입 신청 (로그인 전에 누구나 낼 수 있고, 운영자가 승인해야 로그인할 수 있다)."""
    st.write("실제 서비스에서는 자격번호를 한국세무사회·한국공인회계사회 공개 조회로 확인한 뒤 승인합니다. 여기서는 운영자 승인 절차만 보여 줍니다.")
    with st.form("pro_register"):
        r1, r2 = st.columns(2)
        pn = r1.text_input("이름 (가명)", placeholder="예: 최가온 세무사")
        pf = r2.text_input("소속 (가상 법인명)", placeholder="예: 세무회계 다온 · 대구")
        r3, r4 = st.columns(2)
        plic = r3.radio("자격", ["세무사", "공인회계사"], horizontal=True)
        pyears = r4.number_input("경력 (년)", min_value=0, max_value=60, value=5, step=1)
        pspec = st.multiselect("전문 분야", list(CREDIT_NAMES), format_func=CREDIT_NAMES.get, placeholder="선택하세요")
        c1, c2 = st.columns(2)
        preg = c1.multiselect("활동 지역", ["전국"] + sorted(set(REGION_GROUP.values())), placeholder="선택하세요")
        pch = c2.multiselect("상담 방식", ["화상", "전화", "대면"], placeholder="선택하세요")
        pind = st.multiselect("경험 업종 (비우면 전 업종)", list(INDUSTRY_NAMES), format_func=INDUSTRY_NAMES.get, placeholder="선택하세요")
        pintro = st.text_area("소개", height=80, placeholder="주로 맡는 업무를 한두 문장으로 적어 주세요")
        sent = st.form_submit_button("가입 신청하기")
    if sent:
        try:
            new_id = register_expert(edb, pn, pf, plic, int(pyears), pintro, pspec, preg, pch, pind)
            st.success(f"가입 신청이 접수되었습니다 ({new_id}). 운영자가 승인하면 '세무사/회계사'로 로그인할 수 있습니다.")
        except ValueError as err:
            st.error(str(err))


def render_login(edb) -> None:
    """로그인 화면. 성공하면 st.session_state['auth']에 역할·아이디·이름을 넣고 다시 그린다."""
    st.markdown("##### 로그인")
    st.caption("로그인해야 서비스를 이용할 수 있습니다. 기업과 세무사/회계사는 서로의 화면과 정보를 볼 수 없고, 기업이 보낸 상담 요청만 전문가에게 전달됩니다.")
    role = st.radio("로그인 유형", ROLES, key="login_role", horizontal=True)
    opts = accounts(edb, role)
    names = {a["id"]: a["name"] + (f" · {a['firm']}" if a.get("firm") else "") for a in opts}
    with st.form("login_form"):
        acc = st.selectbox("계정", list(names), format_func=names.get, key="login_acc")
        pw = st.text_input("비밀번호", type="password", key="login_pw", placeholder="시연용 비밀번호")
        go = st.form_submit_button("로그인")
    st.caption(f"시연용 가상 계정입니다. 모든 계정의 비밀번호는 {DEMO_PASSWORD} 입니다.")
    if go:
        got = login(edb, role, acc, pw)
        if got:
            st.session_state["auth"] = got
            st.rerun()
        else:
            st.error("계정 또는 비밀번호가 맞지 않습니다.")
    with st.expander("세무사/회계사이신가요? 가입 신청"):
        render_register_form(edb)


def render_expert_home(edb, auth: dict) -> None:
    """전문가 본인 화면: 자기에게 온 상담 요청만 보인다."""
    me = next((e for e in list_experts(edb, "approved") if e["id"] == auth["id"]), None)
    t1, t2 = st.tabs(["고객 상담 요청", "내 프로필"])
    with t1:
        inbox = list_requests(edb, auth["id"])
        if not inbox:
            st.info("아직 들어온 고객 상담 요청이 없습니다. 기업 계정으로 로그인해 이 전문가에게 상담을 요청하면 여기에 나타납니다.")
        for rq in inbox:
            with st.expander(f"{rq['receipt']} · {rq['client_name'] or '의뢰 기업'} · {rq['topic']} · {rq['channel']}", expanded=True):
                st.text(rq["brief"])
                st.download_button("전달 자료 PDF", rq["pdf"], file_name=f"상담_전달_자료_{rq['receipt']}.pdf", mime="application/pdf",
                                   key=f"pdf_{rq['receipt']}")
    with t2:
        if me:
            st.markdown(f"**{me['name']}** ({me['license']}) · {me['firm']} · 경력 {me['years']}년")
            st.write(me["intro"])
            st.caption("전문 분야: " + ", ".join(CREDIT_NAMES.get(x, x) for x in me["specialties"]) + " / 지역: " + ", ".join(me["regions"]) +
                       " / 상담 방식: " + ", ".join(me["channels"]))


def render_admin_home(edb) -> None:
    """운영자 화면: 전문가 가입 신청 승인."""
    pending = list_experts(edb, "pending")
    if not pending:
        st.info("승인을 기다리는 가입 신청이 없습니다. 로그아웃 후 로그인 화면의 '가입 신청'에서 신청해 볼 수 있습니다.")
    for pe in pending:
        with st.container(border=True):
            st.markdown(f"**{pe['name']}** ({pe['license']}) · {pe['firm']} · 경력 {pe['years']}년")
            st.caption("분야: " + ", ".join(CREDIT_NAMES.get(x, x) for x in pe["specialties"]) + " / 지역: " + ", ".join(pe["regions"]) +
                       " / 방식: " + ", ".join(pe["channels"]))
            st.write(pe["intro"])
            if st.button("자격 확인 완료 · 승인", key=f"ap_{pe['id']}"):
                approve_expert(edb, pe["id"])
                st.rerun()
    st.caption(f"승인된 전문가: {len(list_experts(edb, 'approved'))}명")
