"""K-Startup 조회서비스(창업진흥원, 공공데이터포털 15125364) 클라이언트.

확인된 것(2026-11-02 실제 호출): 경로 getAnnouncementInformation01, 응답 {currentCount, matchCount, page, perPage, totalCount, data[]},
cond[rcrt_prgs_yn::EQ]=Y 로 모집 중인 공고만 받을 수 있다(당시 196건 / 전체 30,483건). 건수 판단은 totalCount가 아니라 matchCount를 쓴다.
프록시 연결이 간헐적으로 끊겨 재시도를 넣었다.
"""
import os
import time

import requests

from .common import make_announcement, normalize_regions, parse_date

BASE_URL = "https://apis.data.go.kr/B552735/kisedKstartupService01"
ANNOUNCEMENT_PATH = "getAnnouncementInformation01"


def _first(item: dict, *keys, default=""):
    for k in keys:
        v = item.get(k)
        if v not in (None, ""):
            return v
    return default


def normalize(item: dict) -> dict:
    return make_announcement(
        id=str(_first(item, "pbanc_sn", "id", "biz_pbanc_nm")),
        source="kstartup",
        title=_first(item, "biz_pbanc_nm", "intg_pbanc_biz_nm"),
        agency=_first(item, "pbanc_ntrp_nm", "sprv_inst", "biz_prch_dprt_nm"),
        summary=_first(item, "pbanc_ctnt", "supt_biz_intrd_info"),
        target=_first(item, "aply_trgt_ctnt", "aply_trgt"),
        field=_first(item, "supt_biz_clsfc"),
        regions=sorted(normalize_regions(_first(item, "supt_regin"))),
        start=parse_date(_first(item, "pbanc_rcpt_bgng_dt", default=None)),
        end=parse_date(_first(item, "pbanc_rcpt_end_dt", default=None)),
        ongoing_flag=_first(item, "rcrt_prgs_yn", default=None),
        biz_age=_first(item, "biz_enyy"),
        age_limit=_first(item, "biz_trgt_age"),
        url=_first(item, "detl_pg_url", "biz_gdnc_url"),
        contact=_first(item, "prch_cnpl_no"),
    )


def fetch_raw(api_key: str | None = None, max_items: int = 300, per_page: int = 100, recruiting_only: bool = True, timeout: int = 20, retries: int = 4) -> list[dict]:
    """공고 원본을 페이지 단위로 받아온다. 키는 환경변수 DATA_GO_KR_API_KEY(.env)에서 읽고, 오류 메시지에 키를 남기지 않는다."""
    key = api_key or os.environ.get("DATA_GO_KR_API_KEY", "")
    if not key:
        raise RuntimeError("DATA_GO_KR_API_KEY가 없습니다. .env 또는 secrets에 넣어 주세요.")
    items: list[dict] = []
    page = 1
    while len(items) < max_items:
        params = {"serviceKey": key, "page": page, "perPage": per_page, "returnType": "json"}
        if recruiting_only:
            params["cond[rcrt_prgs_yn::EQ]"] = "Y"
        resp = None
        for attempt in range(retries):
            try:
                resp = requests.get(f"{BASE_URL}/{ANNOUNCEMENT_PATH}", params=params, timeout=timeout)
                break
            except requests.RequestException as e:
                if attempt == retries - 1:
                    raise RuntimeError("K-Startup API 연결 실패: " + str(e).replace(key, "***")) from None
                time.sleep(2 * (attempt + 1))
        if resp.status_code != 200:
            raise RuntimeError(f"K-Startup API 응답 오류 {resp.status_code}: {resp.text[:200].replace(key, '***')}")
        body = resp.json()
        data = body.get("data", [])
        items += data
        if not data or len(items) >= int(body.get("matchCount", body.get("totalCount", 0)) or 0):
            break
        page += 1
    return items[:max_items]
