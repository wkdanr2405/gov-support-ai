"""로그인 화면과 전문가·운영자 화면 (Streamlit). 기업 화면은 app.py에 있다.

역할별 접근은 app.py가 로그인 결과로 어느 함수를 실행할지 정하는 방식이라, 기업 계정으로는 이 파일의 전문가·운영자 화면 코드가 아예 실행되지 않는다.
"""
import streamlit as st

from src.auth import DEMO_HINT, DEMO_PASSWORD, ROLE_ADMIN, ROLE_CORP, ROLE_EXPERT, ROLES, login
from datetime import date

from src.experts import CREDIT_NAMES, ETC, INDUSTRY_NAMES, join_etc, show_etc, split_etc
from src.experts.db import (KINDS, approve_expert, get_company, list_companies, list_experts, list_requests, register_company, register_expert,
                            update_company, update_expert, virtual_contact)

VIRTUAL_NOTICE = "모든 인물과 법인은 시연을 위해 지어낸 가상의 정보이며, 회원가입과 상담 요청 내용은 서버 메모리에 담겨 접속한 모든 사람이 함께 쓰며, 서버가 다시 시작되면 사라집니다. 실제 이름·연락처는 입력하지 마세요."


CHANNELS = ["화상", "전화", "대면", ETC]


def _etc_multiselect(col, fk: str, label: str, options: list[str], values: list[str], fmt=None, placeholder="선택하세요"):
    """'기타'가 마지막 선택지로 붙은 다중 선택 + 기타 내용 입력칸. 저장할 값 목록을 돌려준다."""
    picked, text = split_etc(values, options)
    sel = col.multiselect(label, options + [ETC], default=picked + ([ETC] if (text or ETC in values) else []),
                          format_func=fmt or str, placeholder=placeholder, key=f"{fk}_{label}")
    etc = col.text_input(f"{label} · 기타 내용 (직접 입력)", value=text, placeholder="목록에 없으면 여기에 적어 주세요", key=f"{fk}_{label}_etc")
    return join_etc(sel, etc)


def _profile_form(form_key: str, d: dict, submit_label: str) -> dict | None:
    """가입 신청과 프로필 수정이 함께 쓰는 입력 화면(법인 단위). 제출하면 입력값 묶음을, 아니면 None을 돌려준다."""
    fk = form_key
    pn = st.text_input("법인명 (가상)", value=d["name"], placeholder="예: 새빛세무법인", key=f"{fk}_name")
    r1, r2, r3 = st.columns(3)
    kind_pick = d["kind"] if d["kind"] in KINDS else ETC
    kind_text = d["kind"].split(":", 1)[1].strip() if d["kind"].startswith(ETC + ":") else ""
    pkind = r1.radio("법인 유형", KINDS, index=KINDS.index(kind_pick), horizontal=True, key=f"{fk}_kind")
    pkind_etc = r1.text_input("법인 유형 · 기타 내용 (직접 입력)", value=kind_text, placeholder="기타를 고른 경우 적어 주세요", key=f"{fk}_kind_etc")
    pfounded = r2.number_input("설립 연도", min_value=1950, max_value=date.today().year, value=int(d["founded"]), step=1, key=f"{fk}_founded")
    pstaff = r3.number_input("소속 전문 인력 수 (공인회계사·세무사 합계, 명)", min_value=1, max_value=5000, value=int(d["staff"]), step=1, key=f"{fk}_staff")
    pspec = _etc_multiselect(st, fk, "전문 분야", list(CREDIT_NAMES), d["specialties"], fmt=lambda x: CREDIT_NAMES.get(x, x))
    pch = _etc_multiselect(st, fk, "상담 방식", CHANNELS[:-1], d["channels"])
    pind = _etc_multiselect(st, fk, "경험 업종 (비우면 전 업종)", list(INDUSTRY_NAMES), d["industries"], fmt=lambda x: INDUSTRY_NAMES.get(x, x))
    pintro = st.text_area("소개", value=d["intro"], height=80, placeholder="주로 맡는 업무를 한두 문장으로 적어 주세요", key=f"{fk}_intro")
    if not st.button(submit_label, key=f"{fk}_submit"):
        return None
    kind = f"{ETC}: {pkind_etc.strip()}" if pkind == ETC and pkind_etc.strip() else pkind
    return dict(name=pn, kind=kind, founded=int(pfounded), staff=int(pstaff), intro=pintro, specialties=pspec, channels=pch, industries=pind)


BLANK_PROFILE = dict(name="", kind="회계법인", founded=2020, staff=5, intro="", specialties=[], channels=[], industries=[])


def _company_form(fk: str, d: dict, submit_label: str) -> dict | None:
    """기업 회원가입과 기업 프로필 수정이 함께 쓰는 입력 화면. 이메일·연락처는 가상 형식만 받는다."""
    pn = st.text_input("기업명 (가상)", value=d["name"], placeholder="예: 가상전자(주)", key=f"{fk}_name")
    c1, c2 = st.columns(2)
    pe = c1.text_input("이메일 (가상)", value=d["email"], placeholder="corp3@example.com", key=f"{fk}_email",
                       help="시연용이라 example.com 형식의 가상 이메일만 입력할 수 있습니다.")
    pp = c2.text_input("연락처 (가상)", value=d["phone"], placeholder="010-0000-0003", key=f"{fk}_phone",
                       help="시연용이라 010-0000-XXXX 형식의 가상 번호만 입력할 수 있습니다.")
    st.caption("회계법인/세무법인에 상담 요청을 보내면 이 이메일·연락처가 전달 자료(PDF)에 담겨 법인이 연락할 수 있습니다. 실제 이메일·연락처는 입력하지 마세요.")
    if not st.button(submit_label, key=f"{fk}_submit"):
        return None
    return dict(name=pn, email=pe, phone=pp)


def render_company_profile(edb, auth: dict) -> None:
    """기업 본인 프로필: 회계법인/세무법인 프로필과 같은 방식(현재 값이 채워진 입력 화면 → 저장)."""
    me = get_company(edb, auth["id"])
    with st.expander("내 기업 프로필 (기업명 · 이메일 · 연락처 수정)"):
        if st.session_state.pop("profile_saved", False):
            st.success("프로필이 저장되었습니다.")
        if me:
            got = _company_form(f"corp_edit_{me['id']}", me, "프로필 저장")
            if got:
                try:
                    update_company(edb, me["id"], **got)
                    st.session_state["auth"] = {**auth, "name": got["name"].strip()}
                    st.session_state["profile_saved"] = True
                    st.rerun()
                except ValueError as err:
                    st.error(str(err))


def render_register_form(edb) -> None:
    """회원가입: 기업은 바로 계정이 만들어지고, 회계법인/세무법인은 운영자가 승인해야 로그인할 수 있다."""
    role = st.radio("가입 유형", [ROLE_CORP, ROLE_EXPERT], key="signup_role", horizontal=True)
    if role == ROLE_CORP:
        em, ph = virtual_contact(edb)
        got = _company_form("corp_signup", dict(name="", email=em, phone=ph), "회원가입")
        if got:
            try:
                register_company(edb, **got)
                st.success(f"회원가입이 완료되었습니다. '로그인' 탭에서 기업명 '{got['name'].strip()}'과 비밀번호 {DEMO_PASSWORD}로 로그인하세요.")
            except ValueError as err:
                st.error(str(err))
        return
    st.write("실제 서비스에서는 법인 등록 여부를 공개 자료로 확인한 뒤 승인합니다. 여기서는 운영자 승인 절차만 보여 줍니다.")
    got = _profile_form("pro_register", BLANK_PROFILE, "회원가입")
    if got:
        try:
            register_expert(edb, **got)
            st.success("회원가입이 접수되었습니다. 운영자가 승인하면 '로그인' 탭에서 법인명으로 로그인할 수 있습니다.")
        except ValueError as err:
            st.error(str(err))


def render_login(edb) -> None:
    """로그인·회원가입 화면. 성공하면 st.session_state['auth']에 역할·아이디·이름을 넣고 다시 그린다.
    계정 목록은 보여 주지 않는다: 기업명·법인명을 직접 입력해야 한다."""
    tab_in, tab_up = st.tabs(["로그인", "회원가입"])
    with tab_in:
        st.caption("로그인해야 서비스를 이용할 수 있습니다. 기업과 회계법인/세무법인은 서로의 화면과 정보를 볼 수 없고, 기업이 보낸 상담 요청만 법인에 전달됩니다.")
        role = st.radio("로그인 유형", ROLES, key="login_role", horizontal=True)
        with st.form("login_form"):
            acc = st.text_input("계정 (기업명 · 법인명)", key="login_acc", placeholder={ROLE_CORP: "기업명을 입력하세요", ROLE_EXPERT: "법인명을 입력하세요"}.get(role, "운영자"))
            pw = st.text_input("비밀번호", type="password", key="login_pw", placeholder="시연용 비밀번호")
            go = st.form_submit_button("로그인")
        st.caption(f"{DEMO_HINT}. 모든 계정의 비밀번호는 {DEMO_PASSWORD} 입니다.")
        if go:
            got = login(edb, role, acc, pw)
            if got:
                st.session_state["auth"] = got
                st.rerun()
            else:
                st.error("계정 또는 비밀번호가 맞지 않습니다.")
    with tab_up:
        render_register_form(edb)


def render_expert_home(edb, auth: dict) -> None:
    """법인 본인 화면: 자기에게 온 상담 요청만 보인다."""
    me = next((e for e in list_experts(edb, "approved") if e["id"] == auth["id"]), None)
    t1, t2 = st.tabs(["고객 상담 요청", "내 법인 프로필"])
    with t1:
        inbox = list_requests(edb, auth["id"])
        if not inbox:
            st.info("아직 들어온 고객 상담 요청이 없습니다. 기업 계정으로 로그인해 이 법인에 상담을 요청하면 여기에 나타납니다.")
        for rq in inbox:
            with st.expander(f"{rq['receipt']} · {rq['client_name'] or '의뢰 기업'} · {rq['topic']} · {rq['channel']}", expanded=True):
                st.text(rq["brief"])
                st.download_button("전달 자료 PDF", rq["pdf"], file_name=f"상담_전달_자료_{rq['receipt']}.pdf", mime="application/pdf",
                                   key=f"pdf_{rq['receipt']}")
    with t2:
        st.write("가입 신청 때와 같은 항목입니다. 고친 뒤 '프로필 저장'을 누르면 기업 화면의 법인 추천에 바로 반영됩니다.")
        if st.session_state.pop("profile_saved", False):
            st.success("프로필이 저장되었습니다.")
        if me:
            got = _profile_form(f"pro_edit_{me['id']}", me, "프로필 저장")
            if got:
                try:
                    update_expert(edb, me["id"], **got)
                    st.session_state["auth"] = {**auth, "name": got["name"].strip()}     # 위쪽 로그인 표시 이름도 바뀐다
                    st.session_state["profile_saved"] = True
                    st.rerun()
                except ValueError as err:
                    st.error(str(err))


ORIGIN_LABEL = {"seed": "가상 시연 데이터", "signup": "회원가입"}


def render_admin_home(edb) -> None:
    """운영자 화면: 법인 회원가입 승인, 그리고 승인된 기업·법인 현황 (가상 시연 데이터와 회원가입 계정을 구분해 표시)."""
    pending = list_experts(edb, "pending")
    st.caption("회원가입·상담 요청 데이터는 서버 메모리에 하나만 있어 접속한 모든 사람에게 공유되고, 새로고침해도 남습니다 (서버 재시작 시 초기화).")
    if st.button("시연 데이터 처음 상태로 되돌리기", key="reset_demo", help="회원가입·상담 요청을 모두 지우고 가상 기업 2곳·법인 6곳만 남깁니다."):
        st.cache_resource.clear()
        st.rerun()
    from src.data_sources.live import OUTAGE_MODES
    from src.flags import shared_flags
    flags = shared_flags()
    st.markdown("##### 외부 API 장애 시연")
    flags["api_outage"] = st.selectbox("기업 화면에서 '최신 공고 확인'을 누르면", list(OUTAGE_MODES), index=list(OUTAGE_MODES).index(flags["api_outage"]),
                                        format_func=OUTAGE_MODES.get, key="outage_mode",
                                        help="발표 때 외부 공고 서버가 실패한 상황을 보여 주는 스위치입니다. 실제 장애가 아니며 서버가 재시작되면 꺼집니다.")
    st.markdown("##### 승인 대기 (회계법인/세무법인 회원가입)")
    if not pending:
        st.info("승인을 기다리는 회원가입이 없습니다. 로그아웃 후 '회원가입' 탭에서 회계법인/세무법인으로 가입해 볼 수 있습니다.")
    for pe in pending:
        with st.container(border=True):
            st.markdown(f"**{pe['name']}** ({pe['kind']}) · 전문 인력 {pe['staff']}명 · 업력 {pe['years']}년")
            st.caption("분야: " + ", ".join(CREDIT_NAMES.get(x, x) for x in show_etc(pe["specialties"])) + " / 방식: " + ", ".join(show_etc(pe["channels"])))
            st.write(pe["intro"])
            if st.button("법인 등록 확인 완료 · 승인", key=f"ap_{pe['id']}"):
                approve_expert(edb, pe["id"])
                st.rerun()

    corps, firms = list_companies(edb), list_experts(edb, "approved")
    n_seed = lambda rows: sum(1 for r in rows if r["origin"] == "seed")
    st.markdown("##### 승인된 기업")
    st.caption(f"{len(corps)}곳 · 가상 시연 데이터 {n_seed(corps)}곳 (Claude가 시연용으로 만든 계정) · 회원가입 {len(corps) - n_seed(corps)}곳. 기업은 회원가입 즉시 승인됩니다.")
    st.dataframe([{"구분": ORIGIN_LABEL[c["origin"]], "기업명": c["name"], "이메일 (가상)": c["email"], "연락처 (가상)": c["phone"]} for c in corps],
                 hide_index=True, use_container_width=True)
    st.markdown("##### 승인된 회계법인/세무법인")
    st.caption(f"{len(firms)}곳 · 가상 시연 데이터 {n_seed(firms)}곳 (Claude가 시연용으로 만든 법인) · 회원가입 후 승인 {len(firms) - n_seed(firms)}곳")
    st.dataframe([{"구분": ORIGIN_LABEL[f["origin"]], "법인명": f["name"], "유형": f["kind"], "설립 연도": f["founded"], "전문 인력(명)": f["staff"],
                   "전문 분야": ", ".join(CREDIT_NAMES.get(x, x) for x in show_etc(f["specialties"]))} for f in firms],
                 hide_index=True, use_container_width=True)
