"""공고 데이터 상태 안내 띠."""
import streamlit as st

from src.data_sources.status import banner


def show_banner(statuses: list[dict]) -> None:
    b = banner(statuses)
    box, icon = {"success": (st.success, "✅"), "info": (st.info, "ℹ️"), "warning": (st.warning, "⚠️"), "error": (st.error, "⛔")}[b["level"]]
    box(f"**{b['title']}**\n\n" + "\n".join("- " + x for x in b["lines"]), icon=icon)
