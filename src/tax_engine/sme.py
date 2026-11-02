"""중소기업 판정 (중소기업기본법 시행령 제3조·별표 1). 단순화: 입력으로 받은 값을 기준표와 비교한다."""
from .params import load_params


def industry_list(params: dict | None = None) -> list[dict]:
    params = params or load_params()
    return params["sme_test"]["industries"]


def judge_sme(profile: dict, params: dict | None = None) -> dict:
    """profile: ksic(업종 코드), avg_revenue_eok(평균매출액등, 억원), assets_eok(자산총액, 억원),
    owned_by_large_corp(자산 5천억 이상 법인이 30% 이상 지분을 가진 최다출자자인지, 선택),
    in_large_group(상호출자제한기업집단 소속, 선택·미확인 기준), consumer_service(소비성 서비스업, 선택·미확인 기준)

    반환: {is_sme, checks:[{name, passed, detail, verified}], unverified:[...]}
    """
    sme = (params or load_params())["sme_test"]
    by_code = {i["code"]: i for i in sme["industries"]}
    code = profile.get("ksic")
    if code not in by_code:
        raise ValueError(f"알 수 없는 업종 코드입니다: {code!r}")
    for k in ("avg_revenue_eok", "assets_eok"):
        v = profile.get(k)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
            raise ValueError(f"{k}은(는) 0 이상의 숫자여야 합니다: {v!r}")
    ind = by_code[code]
    asset_limit = sme["assets_total_limit_eok"]

    checks = [
        {"name": "평균매출액등 기준", "passed": profile["avg_revenue_eok"] <= ind["limit_eok"], "verified": True,
         "detail": f"{ind['name']}: 평균매출액 {profile['avg_revenue_eok']:,}억 원 (기준 {ind['limit_eok']:,}억 원 이하)"},
        {"name": "자산총액 기준", "passed": profile["assets_eok"] < asset_limit, "verified": True,
         "detail": f"자산총액 {profile['assets_eok']:,}억 원 (기준 {asset_limit:,}억 원 미만)"},
        {"name": "독립성(대기업 지배 여부)", "passed": not profile.get("owned_by_large_corp", False), "verified": True,
         "detail": "자산 5천억 원 이상 법인이 30% 이상 지분을 가진 최다출자자이면 중소기업이 아님"},
    ]
    unverified = []
    if profile.get("in_large_group"):
        checks.append({"name": "상호출자제한기업집단 소속", "passed": False, "verified": False,
                       "detail": "소속이면 중소기업이 아닌 것으로 안내 (원문 확인 전)"})
    else:
        unverified.append("상호출자제한기업집단 소속 여부는 입력값만 반영 (원문 확인 전)")
    if profile.get("consumer_service"):
        checks.append({"name": "소비성 서비스업", "passed": False, "verified": False,
                       "detail": "주된 사업이 소비성 서비스업이면 중소기업이 아닌 것으로 안내 (원문 확인 전)"})
    unverified += [u["item"] for u in sme["unverified_parts"] if u["item"] not in " ".join(unverified)]
    return {"is_sme": all(c["passed"] for c in checks), "checks": checks, "unverified": unverified,
            "industry": ind["name"], "limit_eok": ind["limit_eok"]}
