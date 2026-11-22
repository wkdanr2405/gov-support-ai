"""로그인 화면과 전문가·운영자 화면 (Streamlit). 기업 화면은 app.py에 있다.

역할별 접근은 app.py가 로그인 결과로 어느 함수를 실행할지 정하는 방식이라, 기업 계정으로는 이 파일의 전문가·운영자 화면 코드가 아예 실행되지 않는다.
"""
import streamlit as st

from src.auth import DEMO_PASSWORD, ROLE_ADMIN, ROLE_CORP, ROLE_EXPERT, ROLES, accounts, login
from src.experts import CREDIT_NAMES, ETC, INDUSTRY_NAMES, join_etc, region_options, show_etc, split_etc
from src.experts.db import approve_expert, list_experts, list_requests, register_expert, update_expert

VIRTUAL_NOTICE = "모든 인물과 법인은 시연을 위해 지어낸 가상의 정보이며, 입력한 내용은 이 접속 동안만 메모리에 있다가 사라집니다. 실제 이름·연락처는 입력하지 마세요."


LICENSES = ["공인회계사", "세무사", ETC]
CHANNELS = ["화상", "전화", "대면", ETC]


def _etc_multiselect(col, label: str, options: list[str], values: list[str], fmt=None, placeholder="선택하세요", help_=None):
    """'기타'가 마지막 선택지로 붙은 다중 선택 + 기타 내용 입력칸. 저장할 값 목록을 돌려준다."""
    picked, text = split_etc(values, options)
    sel = col.multiselect(label, options + [ETC], default=picked + ([ETC] if (text or ETC in values) else []),
                          format_func=fmt or str, placeholder=placeholder, help=help_)
    etc = col.text_input(f"{label} · 기타 내용 (직접 입력)", value=text, placeholder="목록에 없으면 여기에 적어 주세요")
    return join_etc(sel, etc)


def _profile_form(form_key: str, d: dict, submit_label: str) -> dict | None:
    """가입 신청과 프로필 수정이 함께 쓰는 입력 화면. 제출하면 입력값 묶음을, 아니면 None을 돌려준다."""
    with st.form(form_key):
        r1, r2 = st.columns(2)
        pn = r1.text_input("이름 (가명)", value=d["name"], placeholder="예: 최가온 공인회계사")
        pf = r2.text_input("소속 (가상 법인명)", value=d["firm"], placeholder="예: 세무회계 다온 · 대구")
        r3, r4 = st.columns(2)
        lic_pick = d["license"] if d["license"] in LICENSES else ETC
        lic_text = d["license"].split(":", 1)[1].strip() if d["license"].startswith(ETC + ":") else ""
        plic = r3.radio("자격", LICENSES, index=LICENSES.index(lic_pick), horizontal=True)
        plic_etc = r3.text_input("자격 · 기타 내용 (직접 입력)", value=lic_text, placeholder="기타를 고른 경우 적어 주세요")
        pyears = r4.number_input("경력 (년)", min_value=0, max_value=60, value=int(d["years"]), step=1)
        pspec = _etc_multiselect(st, "전문 분야", list(CREDIT_NAMES), d["specialties"], fmt=lambda x: CREDIT_NAMES.get(x, x))
        st.caption("활동 지역: 광역시는 구·군, 도는 시·군까지 고를 수 있습니다. '서울 전체'처럼 시·도 전체를 고르면 그 안의 모든 지역이 해당됩니다.")
        c1, c2 = st.columns(2)
        preg = _etc_multiselect(c1, "활동 지역", region_options()[:-1], d["regions"])
        pch = _etc_multiselect(c2, "상담 방식", CHANNELS[:-1], d["channels"])
        pind = _etc_multiselect(st, "경험 업종 (비우면 전 업종)", list(INDUSTRY_NAMES), d["industries"], fmt=lambda x: INDUSTRY_NAMES.get(x, x))
        pintro = st.text_area("소개", value=d["intro"], height=80, placeholder="주로 맡는 업무를 한두 문장으로 적어 주세요")
        sent = st.form_submit_button(submit_label)
    if not sent:
        return None
    license_ = f"{ETC}: {plic_etc.strip()}" if plic == ETC and plic_etc.strip() else plic
    return dict(name=pn, firm=pf, license=license_, years=int(pyears), intro=pintro, specialties=pspec, regions=preg, channels=pch, industries=pind)


BLANK_PROFILE = dict(name="", firm="", license="공인회계사", years=5, intro="", specialties=[], regions=[], channels=[], industries=[])


def render_register_form(edb) -> None:
    """전문가 가입 신청 (로그인 전에 누구나 낼 수 있고, 운영자가 승인해야 로그인할 수 있다)."""
    st.write("실제 서비스에서는 자격번호를 한국세무사회·한국공인회계사회 공개 조회로 확인한 뒤 승인합니다. 여기서는 운영자 승인 절차만 보여 줍니다.")
    got = _profile_form("pro_register", BLANK_PROFILE, "가입 신청하기")
    if got:
        try:
            new_id = register_expert(edb, **got)
            st.success(f"가입 신청이 접수되었습니다 ({new_id}). 운영자가 승인하면 '공인회계사/세무사'로 로그인할 수 있습니다.")
        except ValueError as err:
            st.error(str(err))


def render_login(edb) -> None:
    """로그인 화면. 성공하면 st.session_state['auth']에 역할·아이디·이름을 넣고 다시 그린다."""
    st.markdown("##### 로그인")
    st.caption("로그인해야 서비스를 이용할 수 있습니다. 기업과 공인회계사/세무사는 서로의 화면과 정보를 볼 수 없고, 기업이 보낸 상담 요청만 전문가에게 전달됩니다.")
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
    with st.expander("공인회계사/세무사이신가요? 가입 신청"):
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
        st.write("가입 신청 때와 같은 항목입니다. 고친 뒤 '프로필 저장'을 누르면 기업 화면의 전문가 추천에 바로 반영됩니다.")
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


def render_admin_home(edb) -> None:
    """운영자 화면: 전문가 가입 신청 승인."""
    pending = list_experts(edb, "pending")
    if not pending:
        st.info("승인을 기다리는 가입 신청이 없습니다. 로그아웃 후 로그인 화면의 '가입 신청'에서 신청해 볼 수 있습니다.")
    for pe in pending:
        with st.container(border=True):
            st.markdown(f"**{pe['name']}** ({pe['license']}) · {pe['firm']} · 경력 {pe['years']}년")
            st.caption("분야: " + ", ".join(CREDIT_NAMES.get(x, x) for x in show_etc(pe["specialties"])) + " / 지역: " + ", ".join(show_etc(pe["regions"])) +
                       " / 방식: " + ", ".join(show_etc(pe["channels"])))
            st.write(pe["intro"])
            if st.button("자격 확인 완료 · 승인", key=f"ap_{pe['id']}"):
                approve_expert(edb, pe["id"])
                st.rerun()
    st.caption(f"승인된 전문가: {len(list_experts(edb, 'approved'))}명")
