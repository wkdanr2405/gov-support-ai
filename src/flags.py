"""서버 메모리에 하나만 있는 시연용 스위치. 운영자 화면에서 바꾸면 접속한 모든 사람에게 적용된다 (서버가 재시작되면 꺼진 상태로 돌아간다)."""
import streamlit as st


@st.cache_resource
def shared_flags() -> dict:
    return {"api_outage": "off"}      # off / partial / all / nosnap (src/data_sources/live.py OUTAGE_MODES)
