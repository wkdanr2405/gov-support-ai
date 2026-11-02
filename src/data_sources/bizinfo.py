"""기업마당 지원사업정보 API 클라이언트. 응답 필드는 2026-11-02 실제 응답(300건)으로 확인했다: {"jsonArray":[...]}.
이 개발 환경에서는 bizinfo.go.kr 접속이 막혀 있어, 내 PC나 배포 환경에서 받아 저장본으로 쓴다.
지역은 관할기관(jrsdInsttNm)으로 정한다: 시·도 기관이면 그 지역, 중앙부처는 전국. 접수기간이 날짜가 아닌 공고(예산 소진시까지 등)는 종료일 없음."""
import os
import re

import requests

from .common import make_announcement, normalize_regions, parse_period, strip_html

URL = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"


def _regions(item: dict) -> list[str]:
    """관할기관이 시·도면 그 지역. 중앙부처 소관이어도 제목이 '[대구] …'처럼 지역 표기로 시작하면 그 지역."""
    regs = normalize_regions(item.get("jrsdInsttNm"))
    if "전국" in regs:
        m = re.match(r"\s*\[([^\]]+)\]", item.get("pblancNm", ""))
        tagged = normalize_regions(m.group(1)) if m else {"전국"}
        if "전국" not in tagged:
            regs = tagged
    return sorted(regs)


def normalize(item: dict) -> dict:
    start, end = parse_period(item.get("reqstBeginEndDe"))
    return make_announcement(
        id=str(item.get("pblancId", "")),
        source="bizinfo",
        title=item.get("pblancNm", ""),
        agency=item.get("excInsttNm") or item.get("jrsdInsttNm", ""),
        summary=strip_html(item.get("bsnsSumryCn", "")),
        target=item.get("trgetNm", ""),
        field=item.get("pldirSportRealmLclasCodeNm", ""),
        regions=_regions(item),
        start=start, end=end,
        url=item.get("pblancUrl") or item.get("rceptEngnHmpgUrl", ""),
        contact=item.get("refrncNm", ""),
    )


def fetch_raw(api_key: str | None = None, count: int = 200, timeout: int = 20) -> list[dict]:
    key = api_key or os.environ.get("BIZINFO_API_KEY", "")
    if not key:
        raise RuntimeError("BIZINFO_API_KEY가 없습니다. .env 또는 secrets에 넣어 주세요.")
    try:
        resp = requests.get(URL, params={"crtfcKey": key, "dataType": "json", "searchCnt": count}, timeout=timeout)
    except requests.RequestException as e:
        raise RuntimeError("기업마당 API 연결 실패: " + str(e).replace(key, "***")) from None
    if resp.status_code != 200:
        raise RuntimeError(f"기업마당 API 응답 오류 {resp.status_code}")
    arr = resp.json().get("jsonArray", [])
    return arr.get("item", []) if isinstance(arr, dict) else arr
