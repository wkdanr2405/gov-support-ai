"""전문가 명단 데이터베이스(SQLite). 시연용이라 메모리에만 만들고, 가상 전문가(data/sample/experts.yaml)로 채운다.

- 세션(접속 1회)마다 따로 만들어지며 파일로 저장하지 않는다 (사용자 입력 저장 금지 규칙).
- 전문가 등록 → 승인 대기 → 운영자 승인 → 추천 명단에 포함, 상담 요청 → 전문가의 '고객 상담 요청'이라는 흐름을 그대로 보여 주기 위한 것이다.
"""
import sqlite3
from functools import lru_cache
from pathlib import Path

import yaml

SEED = Path(__file__).resolve().parents[2] / "data" / "sample" / "experts.yaml"
LISTS = ("specialties", "regions", "channels", "industries")
SCHEMA = """
CREATE TABLE experts (id TEXT PRIMARY KEY, name TEXT NOT NULL, firm TEXT NOT NULL, license TEXT NOT NULL,
                      years INTEGER NOT NULL, intro TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', seq INTEGER NOT NULL);
CREATE TABLE expert_items (expert_id TEXT NOT NULL REFERENCES experts(id), kind TEXT NOT NULL, value TEXT NOT NULL);
CREATE TABLE requests (receipt TEXT PRIMARY KEY, expert_id TEXT NOT NULL REFERENCES experts(id), topic TEXT, channel TEXT,
                       memo TEXT, brief TEXT, pdf BLOB, client_id TEXT NOT NULL DEFAULT '', client_name TEXT NOT NULL DEFAULT '', seq INTEGER NOT NULL);
"""


def _insert(conn: sqlite3.Connection, e: dict, status: str) -> None:
    seq = conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM experts").fetchone()[0]
    conn.execute("INSERT INTO experts VALUES (?,?,?,?,?,?,?,?)",
                 (e["id"], e["name"], e["firm"], e["license"], int(e["years"]), e["intro"], status, seq))
    conn.executemany("INSERT INTO expert_items VALUES (?,?,?)",
                     [(e["id"], k, v) for k in LISTS for v in e.get(k, [])])


def new_db() -> sqlite3.Connection:
    """가상 전문가로 채운 새 메모리 데이터베이스."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.executescript(SCHEMA)
    for e in yaml.safe_load(SEED.read_text(encoding="utf-8"))["experts"]:
        _insert(conn, e, "approved")
    conn.commit()
    return conn


@lru_cache(maxsize=1)
def shared_db() -> sqlite3.Connection:
    """읽기 전용으로만 쓰는 공용 명단 (화면 밖 코드·테스트용)."""
    return new_db()


def list_experts(conn: sqlite3.Connection, status: str | None = "approved") -> list[dict]:
    q = "SELECT id, name, firm, license, years, intro, status FROM experts" + (" WHERE status = ?" if status else "") + " ORDER BY seq"
    rows = conn.execute(q, (status,) if status else ()).fetchall()
    out = []
    for id_, name, firm, lic, years, intro, st_ in rows:
        e = dict(id=id_, name=name, firm=firm, license=lic, years=years, intro=intro, status=st_)
        for k in LISTS:
            e[k] = [r[0] for r in conn.execute("SELECT value FROM expert_items WHERE expert_id = ? AND kind = ? ORDER BY rowid", (id_, k))]
        out.append(e)
    return out


def register_expert(conn: sqlite3.Connection, name: str, firm: str, license: str, years: int, intro: str,
                    specialties: list[str], regions: list[str], channels: list[str], industries: list[str] | None = None) -> str:
    """전문가 등록 신청(승인 대기). 필수 항목이 비어 있으면 ValueError."""
    if not (name.strip() and firm.strip() and intro.strip()):
        raise ValueError("이름·소속·소개를 모두 입력해 주세요.")
    if not (specialties and regions and channels):
        raise ValueError("전문 분야·활동 지역·상담 방식을 하나 이상 골라 주세요.")
    if not 0 <= int(years) <= 60:
        raise ValueError("경력은 0~60년 사이로 입력해 주세요.")
    n = conn.execute("SELECT COUNT(*) FROM experts").fetchone()[0] + 1
    id_ = f"exp-{n}"
    _insert(conn, dict(id=id_, name=name.strip(), firm=firm.strip(), license=license, years=years, intro=intro.strip(),
                       specialties=specialties, regions=regions, channels=channels, industries=industries or []), "pending")
    conn.commit()
    return id_


def approve_expert(conn: sqlite3.Connection, expert_id: str) -> None:
    cur = conn.execute("UPDATE experts SET status = 'approved' WHERE id = ? AND status = 'pending'", (expert_id,))
    if cur.rowcount != 1:
        raise ValueError("승인 대기 중인 전문가가 아닙니다.")
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
