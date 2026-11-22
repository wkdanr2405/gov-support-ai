"""시연용 가상 로그인. 실제 개인정보·실제 비밀번호를 받지 않는다 (CLAUDE.md 절대 규칙 5).

- 계정은 코드에 적힌 가상 계정(기업 2·운영자 1)과, 전문가 명단 DB에서 승인된 전문가 전원이다.
- 비밀번호는 화면에 안내하는 공통 시연용 값이며, 비교는 해시로 한다 (실제 서비스 구조를 보여 주기 위함).
- 로그인 결과(역할·아이디·이름)는 접속(세션) 안에서만 보관한다.
"""
import hashlib
import hmac

from src.experts.db import list_experts

DEMO_PASSWORD = "demo1234"
_SALT = "gov-support-demo"
ROLE_CORP, ROLE_EXPERT, ROLE_ADMIN = "기업", "회계법인/세무법인", "운영자"
ROLES = [ROLE_CORP, ROLE_EXPERT, ROLE_ADMIN]
CORP_ACCOUNTS = [("corp-1", "가상전자(주) 대표"), ("corp-2", "새싹소프트(주) 대표")]
ADMIN_ACCOUNTS = [("admin-1", "운영자")]


def hash_pw(pw: str) -> str:
    return hashlib.sha256((_SALT + pw).encode("utf-8")).hexdigest()


_HASH = hash_pw(DEMO_PASSWORD)


def accounts(conn, role: str) -> list[dict]:
    """로그인할 수 있는 계정 목록. 전문가는 승인된 사람만(승인 대기는 로그인 불가)."""
    if role == ROLE_CORP:
        return [dict(id=i, name=n, role=role) for i, n in CORP_ACCOUNTS]
    if role == ROLE_ADMIN:
        return [dict(id=i, name=n, role=role) for i, n in ADMIN_ACCOUNTS]
    if role == ROLE_EXPERT:
        return [dict(id=e["id"], name=e["name"], role=role, kind=e["kind"]) for e in list_experts(conn, "approved")]
    return []


def login(conn, role: str, account_id: str, password: str) -> dict | None:
    """성공하면 {'role','id','name'}, 실패하면 None. 역할과 계정이 맞지 않아도 None."""
    ok = hmac.compare_digest(hash_pw(password or ""), _HASH)
    acc = next((a for a in accounts(conn, role) if a["id"] == account_id), None)
    if not (ok and acc):
        return None
    return {"role": role, "id": acc["id"], "name": acc["name"]}
