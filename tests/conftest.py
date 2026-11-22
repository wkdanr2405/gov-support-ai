"""테스트마다 공유 데이터베이스(서버 메모리)를 처음 상태로 비운다."""
import pytest
import streamlit as st


@pytest.fixture(autouse=True)
def _fresh_shared_db():
    st.cache_resource.clear()
    yield
    st.cache_resource.clear()
