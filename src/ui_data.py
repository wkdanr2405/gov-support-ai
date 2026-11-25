"""공고 데이터 상태 안내 띠. 성공은 초록, 실패는 같은 모양의 붉은 상자(❌)로 통일한다."""
import html

import streamlit as st

from src.data_sources.status import banner

_BOX = ('<div style="border-radius:0.75rem;padding:1rem 1.25rem;background:#fddcd9;color:#3b0d0a">'
        '<div style="font-weight:700;margin-bottom:0.5rem">❌ {title}</div><ul style="margin:0;padding-left:1.4rem;line-height:1.7">{lines}</ul></div>')


def show_banner(statuses: list[dict]) -> None:
    b = banner(statuses)
    if b["level"] == "error":      # st.error는 이 테마에서 흰색으로 보여 같은 모양의 붉은 상자를 직접 그린다
        st.markdown(_BOX.format(title=html.escape(b["title"]), lines="".join(f"<li>{html.escape(x)}</li>" for x in b["lines"])),
                    unsafe_allow_html=True)
        return
    box, icon = {"success": (st.success, "✅"), "info": (st.info, "ℹ️"), "warning": (st.warning, "⚠️")}[b["level"]]
    box(f"**{b['title']}**\n\n" + "\n".join("- " + x for x in b["lines"]), icon=icon)
