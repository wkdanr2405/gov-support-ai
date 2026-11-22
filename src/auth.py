"""시연용 가상 로그인. 실제 개인정보·실제 비밀번호를 받지 않는다 (CLAUDE.md 절대 규칙 5).

- 계정은 기업명·법인명으로 구분한다. 가상 기업 2곳·가상 법인 6곳·운영자 1과, 회원가입으로 만든 계정이 있다(메모리 DB, 접속 동안만).
- 로그인 화면에는 계정 목록을 보여 주지 않고, 입력한 이름 하나만 조회한다 (다른 기업·법인이 보이지 않게).
- 비밀번호는 화면에 안내하는 공통 시연용 값이며, 비교는 해시로 한다 (실제 서비스 구조를 보여 주기 위함).
- 로그인 결과(역할·아이디·이름)는 접속(세션) 안에서만 보관한다.
"""
import hashlib
import hmac

from src.experts.db import find_company_by_name, list_experts

DEMO_PASSWORD = "demo1234"
_SALT = "gov-support-demo"
ROLE_CORP, ROLE_EXPERT, ROLE_ADMIN = "기업", "회계법인/세무법인", "운영자"
ROLES = [ROLE_CORP, ROLE_EXPERT, ROLE_ADMIN]
ADMIN_NAME = "운영자"
DEMO_HINT = "시연용 가상 계정 예시: 기업 '가상전자(주)' · 회계법인/세무법인 '새빛세무법인' · 운영자 '운영자'"


def hash_pw(pw: str) -> str:
    return hashlib.sha256((_SALT + pw).encode("utf-8")).hexdigest()


_HASH = hash_pw(DEMO_PASSWORD)


def _norm(name: str) -> str:
    return (name or "").replace(" ", "").lower()


def find_account(conn, role: str, name: str) -> dict | None:
    """계정은 기업명·법인명으로 구분한다. 화면에 전체 목록을 보여 주지 않고, 입력한 이름 하나만 찾는다.
    법인은 운영자가 승인한 곳만 로그인할 수 있다."""
    if role == ROLE_CORP:
        c = find_company_by_name(conn, name)
        return dict(id=c["id"], name=c["name"], role=role) if c else None
    if role == ROLE_ADMIN:
        return dict(id="admin-1", name=ADMIN_NAME, role=role) if _norm(name) == _norm(ADMIN_NAME) else None
    if role == ROLE_EXPERT:
        e = next((e for e in list_experts(conn, "approved") if _norm(e["name"]) == _norm(name)), None)
        return dict(id=e["id"], name=e["name"], role=role) if e else None
    return None


def login(conn, role: str, account_name: str, password: str) -> dict | None:
    """성공하면 {'role','id','name'}, 실패하면 None. 계정이 없는지 비밀번호가 틀린지는 알려 주지 않는다."""
    ok = hmac.compare_digest(hash_pw(password or ""), _HASH)
    acc = find_account(conn, role, account_name)
    if not (ok and acc):
        return None
    return {"role": role, "id": acc["id"], "name": acc["name"]}
