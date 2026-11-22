"""회계·세무법인 명단 데이터베이스(SQLite). 시연용이라 메모리에만 만들고, 가상 법인(data/sample/experts.yaml)으로 채운다.

- 세션(접속 1회)마다 따로 만들어지며 파일로 저장하지 않는다 (사용자 입력 저장 금지 규칙).
- 전문가 등록 → 승인 대기 → 운영자 승인 → 추천 명단에 포함, 상담 요청 → 전문가의 '고객 상담 요청'이라는 흐름을 그대로 보여 주기 위한 것이다.
"""
import re
import sqlite3
import threading
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml

SEED = Path(__file__).resolve().parents[2] / "data" / "sample" / "experts.yaml"
LISTS = ("specialties", "channels", "industries")
KINDS = ["회계법인", "세무법인", "기타"]
SCHEMA = """
CREATE TABLE experts (id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL, founded INTEGER NOT NULL, staff INTEGER NOT NULL,
                      intro TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', seq INTEGER NOT NULL, origin TEXT NOT NULL DEFAULT 'signup');
CREATE TABLE corporations (id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL, seq INTEGER NOT NULL, origin TEXT NOT NULL DEFAULT 'signup');
CREATE TABLE expert_items (expert_id TEXT NOT NULL REFERENCES experts(id), kind TEXT NOT NULL, value TEXT NOT NULL);
CREATE TABLE requests (receipt TEXT PRIMARY KEY, expert_id TEXT NOT NULL REFERENCES experts(id), topic TEXT, channel TEXT,
                       memo TEXT, brief TEXT, pdf BLOB, client_id TEXT NOT NULL DEFAULT '', client_name TEXT NOT NULL DEFAULT '', seq INTEGER NOT NULL);
"""


def _insert(conn: sqlite3.Connection, e: dict, status: str, origin: str = "signup") -> None:
    seq = conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM experts").fetchone()[0]
    conn.execute("INSERT INTO experts VALUES (?,?,?,?,?,?,?,?,?)",
                 (e["id"], e["name"], e["kind"], int(e["founded"]), int(e["staff"]), e["intro"], status, seq, origin))
    conn.executemany("INSERT INTO expert_items VALUES (?,?,?)",
                     [(e["id"], k, v) for k in LISTS for v in e.get(k, [])])


class _LockedConn:
    """여러 접속(스레드)이 하나의 메모리 DB를 함께 쓸 때 쿼리가 섞이지 않도록 잠금을 걸어 주는 얇은 껍데기."""

    def __init__(self, conn: sqlite3.Connection):
        self._c, self._lock = conn, threading.RLock()

    def execute(self, *a):
        with self._lock:
            return self._c.execute(*a)

    def executemany(self, *a):
        with self._lock:
            return self._c.executemany(*a)

    def executescript(self, *a):
        with self._lock:
            return self._c.executescript(*a)

    def commit(self):
        with self._lock:
            self._c.commit()


def new_db(shared: bool = False):
    """가상 전문가로 채운 새 메모리 데이터베이스. shared=True이면 여러 접속이 함께 쓰도록 잠금을 건다."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    if shared:
        conn = _LockedConn(conn)
    conn.executescript(SCHEMA)
    seed = yaml.safe_load(SEED.read_text(encoding="utf-8"))
    for e in seed["experts"]:
        _insert(conn, e, "approved", "seed")
    for c in seed["companies"]:
        conn.execute("INSERT INTO corporations VALUES (?,?,?,?,?,?)", (c["id"], c["name"], c["email"], c["phone"],
                                                                     conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM corporations").fetchone()[0], "seed"))
    conn.commit()
    return conn


@lru_cache(maxsize=1)
def shared_db() -> sqlite3.Connection:
    """읽기 전용으로만 쓰는 공용 명단 (화면 밖 코드·테스트용)."""
    return new_db()


def list_experts(conn: sqlite3.Connection, status: str | None = "approved") -> list[dict]:
    q = "SELECT id, name, kind, founded, staff, intro, status, origin FROM experts" + (" WHERE status = ?" if status else "") + " ORDER BY seq"
    rows = conn.execute(q, (status,) if status else ()).fetchall()
    out = []
    for id_, name, kind, founded, staff, intro, st_, origin in rows:
        e = dict(id=id_, name=name, kind=kind, founded=founded, staff=staff, years=max(0, date.today().year - founded), intro=intro, status=st_, origin=origin)
        for k in LISTS:
            e[k] = [r[0] for r in conn.execute("SELECT value FROM expert_items WHERE expert_id = ? AND kind = ? ORDER BY rowid", (id_, k))]
        out.append(e)
    return out


def _name_taken(conn: sqlite3.Connection, table: str, name: str, except_id: str | None = None) -> bool:
    rows = conn.execute(f"SELECT id FROM {table} WHERE REPLACE(LOWER(name), ' ', '') = ?", (name.replace(" ", "").lower(),)).fetchall()
    return any(r[0] != except_id for r in rows)


def _validate(name: str, founded: int, staff: int, intro: str, specialties: list, channels: list) -> None:
    if not (name.strip() and intro.strip()):
        raise ValueError("법인명과 소개를 입력해 주세요.")
    if not (specialties and channels):
        raise ValueError("전문 분야와 상담 방식을 하나 이상 골라 주세요.")
    if not 1950 <= int(founded) <= date.today().year:
        raise ValueError(f"설립 연도는 1950~{date.today().year} 사이로 입력해 주세요.")
    if not 1 <= int(staff) <= 5000:
        raise ValueError("소속 전문 인력 수는 1~5000명 사이로 입력해 주세요.")


def register_expert(conn: sqlite3.Connection, name: str, kind: str, founded: int, staff: int, intro: str,
                    specialties: list[str], channels: list[str], industries: list[str] | None = None) -> str:
    """법인 등록 신청(승인 대기). 필수 항목이 비어 있으면 ValueError."""
    _validate(name, founded, staff, intro, specialties, channels)
    if _name_taken(conn, "experts", name):
        raise ValueError("이미 쓰고 있는 법인명입니다. 계정은 법인명으로 구분하므로 다른 이름을 입력해 주세요.")
    n = conn.execute("SELECT COUNT(*) FROM experts").fetchone()[0] + 1
    id_ = f"exp-{n}"
    _insert(conn, dict(id=id_, name=name.strip(), kind=kind, founded=founded, staff=staff, intro=intro.strip(),
                       specialties=specialties, channels=channels, industries=industries or []), "pending")
    conn.commit()
    return id_


def update_expert(conn: sqlite3.Connection, expert_id: str, name: str, kind: str, founded: int, staff: int, intro: str,
                  specialties: list[str], channels: list[str], industries: list[str] | None = None) -> None:
    """승인된 법인이 자기 프로필을 고친다. 같은 검증을 하고, 승인 상태와 받은 상담 요청은 그대로 둔다."""
    _validate(name, founded, staff, intro, specialties, channels)
    if _name_taken(conn, "experts", name, expert_id):
        raise ValueError("이미 쓰고 있는 법인명입니다. 계정은 법인명으로 구분하므로 다른 이름을 입력해 주세요.")
    cur = conn.execute("UPDATE experts SET name = ?, kind = ?, founded = ?, staff = ?, intro = ? WHERE id = ? AND status = 'approved'",
                       (name.strip(), kind, int(founded), int(staff), intro.strip(), expert_id))
    if cur.rowcount != 1:
        raise ValueError("프로필을 고칠 수 있는 법인 계정이 아닙니다.")
    conn.execute("DELETE FROM expert_items WHERE expert_id = ?", (expert_id,))
    items = dict(specialties=specialties, channels=channels, industries=industries or [])
    conn.executemany("INSERT INTO expert_items VALUES (?,?,?)", [(expert_id, k, v) for k in LISTS for v in items[k]])
    conn.commit()


def approve_expert(conn: sqlite3.Connection, expert_id: str) -> None:
    cur = conn.execute("UPDATE experts SET status = 'approved' WHERE id = ? AND status = 'pending'", (expert_id,))
    if cur.rowcount != 1:
        raise ValueError("승인 대기 중인 법인이 아닙니다.")
    conn.commit()


def add_request(conn: sqlite3.Connection, receipt: str, expert_id: str, topic: str, channel: str, memo: str, brief: str, pdf: bytes,
                client_id: str = "", client_name: str = "") -> None:
    seq = conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM requests").fetchone()[0]
    conn.execute("INSERT OR REPLACE INTO requests VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (receipt, expert_id, topic, channel, memo, brief, pdf, client_id, client_name, seq))
    conn.commit()


def _req(r) -> dict:
    return dict(receipt=r[0], topic=r[1], channel=r[2], memo=r[3], brief=r[4], pdf=r[5], expert_id=r[6], client_name=r[7])


_COLS = "receipt, topic, channel, memo, brief, pdf, expert_id, client_name"


def list_requests(conn: sqlite3.Connection, expert_id: str) -> list[dict]:
    """전문가 한 명에게 들어온 요청 (그 전문가 본인 화면에서만 사용)."""
    return [_req(r) for r in conn.execute(f"SELECT {_COLS} FROM requests WHERE expert_id = ? ORDER BY seq DESC", (expert_id,))]


def list_requests_by_client(conn: sqlite3.Connection, client_id: str) -> list[dict]:
    """기업 한 곳이 보낸 요청 (그 기업 본인 화면에서만 사용)."""
    return [_req(r) for r in conn.execute(f"SELECT {_COLS} FROM requests WHERE client_id = ? ORDER BY seq DESC", (client_id,))]


# ---------- 기업 계정 (시연용 가상 정보만) ----------
EMAIL_RE = re.compile(r"^[a-z0-9._-]+@example\.com$")
PHONE_RE = re.compile(r"^010-0000-\d{4}$")


def virtual_contact(conn: sqlite3.Connection) -> tuple[str, str]:
    """새 기업에 기본으로 부여하는 가상 이메일·연락처 (example.com과 010-0000-XXXX는 실제로 쓰이지 않는 시연용 형식)."""
    n = conn.execute("SELECT COUNT(*) FROM corporations").fetchone()[0] + 1
    return f"corp{n}@example.com", f"010-0000-{n:04d}"


def _validate_company(conn: sqlite3.Connection, name: str, email: str, phone: str, except_id: str | None = None) -> None:
    if not name.strip():
        raise ValueError("기업명을 입력해 주세요.")
    if _name_taken(conn, "corporations", name.strip(), except_id):
        raise ValueError("이미 쓰고 있는 기업명입니다. 계정은 기업명으로 구분하므로 다른 이름을 입력해 주세요.")
    if not EMAIL_RE.match(email.strip().lower()):
        raise ValueError("시연용이므로 이메일은 가상 형식(예: corp3@example.com)만 입력할 수 있습니다. 실제 이메일은 입력하지 마세요.")
    if not PHONE_RE.match(phone.strip()):
        raise ValueError("시연용이므로 연락처는 가상 형식(예: 010-0000-0003)만 입력할 수 있습니다. 실제 연락처는 입력하지 마세요.")


def register_company(conn: sqlite3.Connection, name: str, email: str, phone: str) -> str:
    """기업 회원가입. 승인 없이 바로 계정이 만들어진다 (시연용). 실패하면 ValueError."""
    _validate_company(conn, name, email, phone)
    n = conn.execute("SELECT COUNT(*) FROM corporations").fetchone()[0] + 1
    id_ = f"corp-{n}"
    seq = conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM corporations").fetchone()[0]
    conn.execute("INSERT INTO corporations VALUES (?,?,?,?,?,?)", (id_, name.strip(), email.strip().lower(), phone.strip(), seq, "signup"))
    conn.commit()
    return id_


def update_company(conn: sqlite3.Connection, company_id: str, name: str, email: str, phone: str) -> None:
    """기업이 자기 프로필을 고친다. 보낸 상담 요청은 그대로 둔다."""
    _validate_company(conn, name, email, phone, company_id)
    cur = conn.execute("UPDATE corporations SET name = ?, email = ?, phone = ? WHERE id = ?",
                       (name.strip(), email.strip().lower(), phone.strip(), company_id))
    if cur.rowcount != 1:
        raise ValueError("프로필을 고칠 수 있는 기업 계정이 아닙니다.")
    conn.commit()


def get_company(conn: sqlite3.Connection, company_id: str) -> dict | None:
    r = conn.execute("SELECT id, name, email, phone FROM corporations WHERE id = ?", (company_id,)).fetchone()
    return dict(id=r[0], name=r[1], email=r[2], phone=r[3]) if r else None


def find_company_by_name(conn: sqlite3.Connection, name: str) -> dict | None:
    r = conn.execute("SELECT id FROM corporations WHERE REPLACE(LOWER(name), ' ', '') = ?", (name.replace(" ", "").lower(),)).fetchone()
    return get_company(conn, r[0]) if r else None


def list_companies(conn: sqlite3.Connection) -> list[dict]:
    """가입된 기업 전체 (운영자 화면 전용). origin: 'seed'(Claude가 만든 가상 기업) / 'signup'(회원가입으로 만든 계정)."""
    return [dict(id=r[0], name=r[1], email=r[2], phone=r[3], origin=r[4])
            for r in conn.execute("SELECT id, name, email, phone, origin FROM corporations ORDER BY seq")]
