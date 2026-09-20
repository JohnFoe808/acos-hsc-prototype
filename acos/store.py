from __future__ import annotations

import json
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    """Small SQLite persistence layer for prototype memory, skills, state and audit logs."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance REAL NOT NULL DEFAULT 0.5,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL DEFAULT '',
                    trigger_text TEXT NOT NULL DEFAULT 'manual',
                    steps_json TEXT NOT NULL,
                    successes INTEGER NOT NULL DEFAULT 0,
                    failures INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'candidate',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS kv_state (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT NOT NULL,
                    detail_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    outcome_json TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    context_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    archived INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS attention_queue (
                    event_id INTEGER PRIMARY KEY,
                    priority REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    processed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS reflections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    summary_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS compute_jobs (
                    id TEXT PRIMARY KEY,
                    backend TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS hybrid_jobs (
                    id TEXT PRIMARY KEY,
                    graph_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS hybrid_stages (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    node_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS world_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    tick INTEGER NOT NULL DEFAULT 0,
                    clock TEXT NOT NULL DEFAULT 'Day 1, 00:00',
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS world_entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    kind TEXT NOT NULL DEFAULT 'object',
                    description TEXT NOT NULL DEFAULT '',
                    location TEXT NOT NULL DEFAULT 'Origin',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS world_locations (
                    name TEXT PRIMARY KEY,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS world_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tick INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute("INSERT OR IGNORE INTO schema_meta(key, value) VALUES('version', '4')")
            # Backfill conversations for databases created before chat metadata existed.
            conn.execute(
                "INSERT OR IGNORE INTO conversations(id, title, created_at, updated_at) "
                "SELECT conversation_id, 'Conversation', MIN(created_at), MAX(created_at) "
                "FROM chat_messages GROUP BY conversation_id"
            )
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(skills)")}
            if "version" not in columns:
                conn.execute("ALTER TABLE skills ADD COLUMN version INTEGER NOT NULL DEFAULT 1")
            if "review_required" not in columns:
                conn.execute(
                    "ALTER TABLE skills ADD COLUMN review_required INTEGER NOT NULL DEFAULT 0"
                )
            conn.execute(
                "INSERT OR IGNORE INTO world_state"
                "(id, tick, clock, updated_at) VALUES(1, 0, 'Day 1, 00:00', ?)",
                (utc_now(),),
            )

    def world_status(self) -> dict[str, Any]:
        with self._connect() as conn:
            state = conn.execute("SELECT * FROM world_state WHERE id=1").fetchone()
            entities = conn.execute("SELECT * FROM world_entities ORDER BY id").fetchall()
            locations = conn.execute("SELECT * FROM world_locations ORDER BY name").fetchall()
            events = conn.execute("SELECT * FROM world_events ORDER BY id DESC LIMIT 20").fetchall()
        return {
            "name": "The World",
            "simulation_only": True,
            "tick": state["tick"],
            "clock": state["clock"],
            "entities": [dict(row) for row in entities],
            "locations": [dict(row) for row in locations],
            "events": [
                {**dict(row), "payload": json.loads(row["payload_json"])}
                for row in reversed(events)
            ],
        }

    def world_add_entity(
        self, name: str, kind: str = "object", description: str = "", location: str = "Origin"
    ) -> dict[str, Any]:
        name, kind, location = name.strip(), kind.strip(), location.strip()
        if not name or len(name) > 120 or not kind or len(kind) > 80 or not location:
            raise ValueError("world entity fields are invalid")
        with self._lock, self._connect() as conn:
            try:
                cur = conn.execute(
                    "INSERT INTO world_entities"
                    "(name, kind, description, location, created_at) VALUES(?,?,?,?,?)",
                    (name, kind, description[:2000], location, utc_now()),
                )
            except sqlite3.IntegrityError:
                raise ValueError(f"Entity already exists: {name}") from None
            row = conn.execute(
                "SELECT * FROM world_entities WHERE id=?", (cur.lastrowid,)
            ).fetchone()
            conn.execute(
                "INSERT OR IGNORE INTO world_locations"
                "(name, description, created_at) VALUES(?,?,?)",
                (location, "A bounded location in The World.", utc_now()),
            )
            self._world_event(conn, "entity.created", {"entity": dict(row)})
        return dict(row)

    def world_advance(self, steps: int = 1) -> dict[str, Any]:
        if steps < 1 or steps > 1000:
            raise ValueError("steps must be between 1 and 1000")
        with self._lock, self._connect() as conn:
            state = conn.execute("SELECT * FROM world_state WHERE id=1").fetchone()
            tick = state["tick"] + steps
            clock = f"Day {tick // 24 + 1}, {(tick % 24):02d}:00"
            conn.execute(
                "UPDATE world_state SET tick=?, clock=?, updated_at=? WHERE id=1",
                (tick, clock, utc_now()),
            )
            self._world_event(conn, "time.advanced", {"steps": steps, "tick": tick})
        return self.world_status()

    @staticmethod
    def _world_event(conn: sqlite3.Connection, event_type: str, payload: dict[str, Any]) -> None:
        state = conn.execute("SELECT tick FROM world_state WHERE id=1").fetchone()
        conn.execute(
            "INSERT INTO world_events(tick, type, payload_json, created_at) VALUES(?,?,?,?)",
            (state["tick"], event_type, json.dumps(payload), utc_now()),
        )

    def add_chat_message(
        self, conversation_id: str, role: str, content: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if role not in {"user", "assistant"}:
            raise ValueError("chat role must be user or assistant")
        with self._lock, self._connect() as conn:
            now = utc_now()
            conn.execute(
                "INSERT OR IGNORE INTO conversations(id, title, created_at, updated_at) "
                "VALUES(?, 'New chat', ?, ?)",
                (conversation_id, now, now),
            )
            conversation = conn.execute(
                "SELECT title FROM conversations WHERE id=?", (conversation_id,)
            ).fetchone()
            if (
                role == "user"
                and conversation
                and conversation["title"] in {"New chat", "Conversation"}
            ):
                title = " ".join(content.strip().split())[:60] or "New chat"
                conn.execute(
                    "UPDATE conversations SET title=?, updated_at=? WHERE id=?",
                    (title, now, conversation_id),
                )
            cur = conn.execute(
                "INSERT INTO chat_messages("
                "conversation_id, role, content, context_json, created_at) "
                "VALUES(?,?,?,?,?)",
                (conversation_id, role, content[:20_000], json.dumps(context or {}), now),
            )
            row = conn.execute(
                "SELECT * FROM chat_messages WHERE id=?", (cur.lastrowid,)
            ).fetchone()
        return self._chat_row(row)

    def create_conversation(self, title: str = "New chat") -> dict[str, Any]:
        conversation_id = uuid.uuid4().hex
        now = utc_now()
        title = " ".join(title.strip().split())[:120] or "New chat"
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO conversations(id, title, created_at, updated_at) VALUES(?,?,?,?)",
                (conversation_id, title, now, now),
            )
        return self.get_conversation(conversation_id)

    def list_conversations(self, include_archived: bool = False) -> list[dict[str, Any]]:
        where = "" if include_archived else "WHERE archived=0"
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT c.*, COUNT(m.id) AS message_count FROM conversations c "
                f"LEFT JOIN chat_messages m ON m.conversation_id=c.id {where} "
                "GROUP BY c.id ORDER BY c.updated_at DESC"
            ).fetchall()
        return [self._conversation_row(row) for row in rows]

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT c.*, COUNT(m.id) AS message_count FROM conversations c "
                "LEFT JOIN chat_messages m ON m.conversation_id=c.id WHERE c.id=? GROUP BY c.id",
                (conversation_id,),
            ).fetchone()
        if not row:
            raise KeyError(conversation_id)
        return self._conversation_row(row)

    def update_conversation(self, conversation_id: str, title: str) -> dict[str, Any]:
        title = " ".join(title.strip().split())[:120]
        if not title:
            raise ValueError("title must not be blank")
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "UPDATE conversations SET title=?, updated_at=? WHERE id=? AND archived=0",
                (title, utc_now(), conversation_id),
            )
            if not cur.rowcount:
                raise KeyError(conversation_id)
        return self.get_conversation(conversation_id)

    @staticmethod
    def _conversation_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "archived": bool(row["archived"]),
            "message_count": row["message_count"],
        }

    def list_chat_messages(self, conversation_id: str, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 100))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM chat_messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()
        return [self._chat_row(row) for row in reversed(rows)]

    @staticmethod
    def _chat_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "conversation_id": row["conversation_id"],
            "role": row["role"],
            "content": row["content"],
            "context": json.loads(row["context_json"]),
            "created_at": row["created_at"],
        }

    def add_memory(
        self,
        kind: str,
        content: str,
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = metadata or {}
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO memories(kind, content, importance, metadata_json, created_at) "
                "VALUES(?,?,?,?,?)",
                (kind, content, importance, json.dumps(metadata), utc_now()),
            )
            memory_id = cur.lastrowid
        return self.get_memory(memory_id)

    def get_memory(self, memory_id: int) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        if row is None:
            raise KeyError(memory_id)
        return self._memory_row(row)

    def list_memories(self, kind: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 200))
        with self._connect() as conn:
            if kind:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE kind=? ORDER BY id DESC LIMIT ?", (kind, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memories ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
        return [self._memory_row(r) for r in rows]

    def search_memories(
        self, query: str, limit: int = 10, kind: str | None = None
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 50))
        terms = list(dict.fromkeys(re.findall(r"[a-z0-9][a-z0-9_-]{2,}", query.lower())))[:8]
        if not terms:
            return self.list_memories(kind=kind, limit=limit)
        where = " OR ".join(["LOWER(content) LIKE ?" for _ in terms])
        params: list[Any] = [f"%{term}%" for term in terms]
        kind_clause = ""
        if kind:
            kind_clause = " AND kind=?"
            params.append(kind)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM memories WHERE ({where}){kind_clause} "
                "ORDER BY importance DESC, id DESC LIMIT ?",
                [*params, max(limit * 5, 50)],
            ).fetchall()
        query_terms = set(terms)
        ranked: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            memory = self._memory_row(row)
            words = set(re.findall(r"[a-z0-9][a-z0-9_-]{2,}", memory["content"].lower()))
            overlap = len(query_terms & words) / len(query_terms)
            phrase_bonus = 0.2 if query.strip().lower() in memory["content"].lower() else 0.0
            source_bonus = 0.05 if memory["metadata"].get("source") else 0.0
            score = overlap + phrase_bonus + (memory["importance"] * 0.1) + source_bonus
            ranked.append((score, memory))
        ranked.sort(key=lambda item: (item[0], item[1]["id"]), reverse=True)
        return [memory for _, memory in ranked[:limit]]

    def memory_observability(self, limit: int = 100) -> dict[str, Any]:
        memories = self.list_memories(limit=limit)
        by_kind: dict[str, int] = {}
        for memory in memories:
            by_kind[memory["kind"]] = by_kind.get(memory["kind"], 0) + 1
        return {"count": len(memories), "by_kind": by_kind, "recent": memories[:10]}

    def consolidate_memories(self, limit: int = 200) -> dict[str, Any]:
        memories = self.list_memories(limit=limit)
        seen: dict[str, dict[str, Any]] = {}
        duplicates = 0
        for memory in memories:
            key = " ".join(memory["content"].lower().split())
            if key in seen:
                duplicates += 1
                with self._lock, self._connect() as conn:
                    conn.execute("DELETE FROM memories WHERE id=?", (memory["id"],))
            else:
                seen[key] = memory
        return {"examined": len(memories), "duplicates_removed": duplicates}

    @staticmethod
    def _memory_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "kind": row["kind"],
            "content": row["content"],
            "importance": row["importance"],
            "metadata": json.loads(row["metadata_json"]),
            "created_at": row["created_at"],
        }

    def upsert_skill(
        self, name: str, description: str, trigger: str, steps: list[str]
    ) -> dict[str, Any]:
        now = utc_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO skills(
                    name, description, trigger_text, steps_json, created_at, updated_at
                )
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(name) DO UPDATE SET
                  description=excluded.description,
                  trigger_text=excluded.trigger_text,
                  steps_json=excluded.steps_json,
                  version=skills.version + 1,
                  review_required=0,
                  updated_at=excluded.updated_at
                """,
                (name, description, trigger, json.dumps(steps), now, now),
            )
        return self.get_skill(name)

    def get_skill(self, name: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM skills WHERE name=?", (name,)).fetchone()
        if row is None:
            raise KeyError(name)
        return self._skill_row(row)

    def list_skills(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM skills ORDER BY updated_at DESC").fetchall()
        return [self._skill_row(r) for r in rows]

    def record_skill_execution(self, name: str, success: bool, threshold: int) -> dict[str, Any]:
        field = "successes" if success else "failures"
        with self._lock, self._connect() as conn:
            conn.execute(
                f"UPDATE skills SET {field}={field}+1, updated_at=? WHERE name=?",
                (utc_now(), name),
            )
            row = conn.execute("SELECT * FROM skills WHERE name=?", (name,)).fetchone()
            if row is None:
                raise KeyError(name)
            status = (
                "integrated"
                if row["successes"] >= threshold and row["failures"] == 0
                else "candidate"
            )
            conn.execute(
                "UPDATE skills SET status=?, updated_at=? WHERE name=?",
                (status, utc_now(), name),
            )
            if not success:
                conn.execute(
                    "UPDATE skills SET review_required=1, updated_at=? WHERE name=?",
                    (utc_now(), name),
                )
        return self.get_skill(name)

    @staticmethod
    def _skill_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "trigger": row["trigger_text"],
            "steps": json.loads(row["steps_json"]),
            "successes": row["successes"],
            "failures": row["failures"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "version": row["version"],
            "review_required": bool(row["review_required"]),
        }

    def get_state(self, key: str, default: Any = None) -> Any:
        with self._connect() as conn:
            row = conn.execute("SELECT value_json FROM kv_state WHERE key=?", (key,)).fetchone()
        return default if row is None else json.loads(row["value_json"])

    def set_state(self, key: str, value: Any) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO kv_state(key, value_json, updated_at) VALUES(?,?,?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json=excluded.value_json, updated_at=excluded.updated_at
                """,
                (key, json.dumps(value), utc_now()),
            )

    def audit(self, event: str, detail: dict[str, Any] | None = None) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO audit_log(event, detail_json, created_at) VALUES(?,?,?)",
                (event, json.dumps(detail or {}), utc_now()),
            )

    def list_audit(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (max(1, min(limit, 200)),)
            ).fetchall()
        return [
            {
                "id": r["id"],
                "event": r["event"],
                "detail": json.loads(r["detail_json"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def record_event(
        self, event_type: str, payload: dict[str, Any] | None = None, source: str = "system"
    ) -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO events(event_type, source, payload_json, created_at) VALUES(?,?,?,?)",
                (event_type, source, json.dumps(payload or {}), utc_now()),
            )
            event_id = cur.lastrowid
            base_priority = {
                "user": 1.0,
                "compute": 0.85,
                "model-core": 0.75,
                "memory": 0.65,
                "system": 0.5,
            }.get(source, 0.5)
            conn.execute(
                "INSERT OR IGNORE INTO attention_queue"
                "(event_id, priority, created_at) VALUES(?,?,?)",
                (event_id, base_priority, utc_now()),
            )
        return self.get_event(event_id)

    def enqueue_attention(self, event_id: int, priority: float) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO attention_queue(event_id, priority, created_at)
                VALUES(?,?,?)
                ON CONFLICT(event_id) DO UPDATE SET priority=MAX(priority, excluded.priority)
                """,
                (event_id, priority, utc_now()),
            )

    def next_attention(self, limit: int = 10) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT e.*, q.priority FROM attention_queue q
                JOIN events e ON e.id=q.event_id
                WHERE q.status='pending' ORDER BY q.priority DESC, q.event_id ASC LIMIT ?
                """,
                (max(1, min(limit, 100)),),
            ).fetchall()
        return [{**self._event_row(row), "priority": row["priority"]} for row in rows]

    def mark_attention_processed(self, event_id: int) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE attention_queue SET status='processed', processed_at=? WHERE event_id=?",
                (utc_now(), event_id),
            )

    def record_reflection(self, summary: dict[str, Any]) -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO reflections(summary_json, created_at) VALUES(?,?)",
                (json.dumps(summary), utc_now()),
            )
            reflection_id = cur.lastrowid
        return {"id": reflection_id, "summary": summary}

    def list_reflections(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM reflections ORDER BY id DESC LIMIT ?", (max(1, min(limit, 100)),)
            ).fetchall()
        return [
            {
                "id": row["id"],
                "summary": json.loads(row["summary_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def create_compute_job(
        self, backend: str, operation: str, payload: dict[str, Any], plan: dict[str, Any]
    ) -> str:
        import uuid

        job_id = str(uuid.uuid4())
        now = utc_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO compute_jobs VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    job_id,
                    backend,
                    operation,
                    json.dumps(payload),
                    json.dumps(plan),
                    "queued",
                    None,
                    now,
                    now,
                ),
            )
        return job_id

    def update_compute_job(
        self, job_id: str, status: str, result: dict[str, Any] | None = None
    ) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE compute_jobs SET status=?, result_json=?, updated_at=? WHERE id=?",
                (status, json.dumps(result) if result is not None else None, utc_now(), job_id),
            )

    def get_compute_job(self, job_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM compute_jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return {
            "id": row["id"],
            "backend": row["backend"],
            "operation": row["operation"],
            "payload": json.loads(row["payload_json"]),
            "plan": json.loads(row["plan_json"]),
            "status": row["status"],
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_compute_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id FROM compute_jobs ORDER BY created_at DESC LIMIT ?",
                (max(1, min(limit, 200)),),
            ).fetchall()
        return [self.get_compute_job(row["id"]) for row in rows]

    def create_hybrid_job(self, graph: dict[str, Any]) -> str:
        import uuid

        job_id = str(uuid.uuid4())
        now = utc_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO hybrid_jobs VALUES(?,?,?,?,?,?)",
                (job_id, json.dumps(graph), "running", None, now, now),
            )
        return job_id

    def update_hybrid_job(self, job_id: str, status: str, result: dict[str, Any]) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE hybrid_jobs SET status=?, result_json=?, updated_at=? WHERE id=?",
                (status, json.dumps(result), utc_now(), job_id),
            )

    def get_hybrid_job(self, job_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM hybrid_jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        with self._connect() as conn:
            stages = conn.execute(
                "SELECT * FROM hybrid_stages WHERE job_id=? ORDER BY created_at", (job_id,)
            ).fetchall()
        return {
            "id": row["id"],
            "graph": json.loads(row["graph_json"]),
            "status": row["status"],
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "stages": [
                {
                    "id": stage["id"],
                    "node": json.loads(stage["node_json"]),
                    "status": stage["status"],
                    "result": json.loads(stage["result_json"]) if stage["result_json"] else None,
                }
                for stage in stages
            ],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_hybrid_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id FROM hybrid_jobs ORDER BY created_at DESC LIMIT ?",
                (max(1, min(limit, 200)),),
            ).fetchall()
        return [self.get_hybrid_job(row["id"]) for row in rows]

    def create_hybrid_stage(self, job_id: str, node: dict[str, Any]) -> str:
        import uuid

        stage_id = str(uuid.uuid4())
        now = utc_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO hybrid_stages VALUES(?,?,?,?,?,?,?)",
                (stage_id, job_id, json.dumps(node), "running", None, now, now),
            )
        return stage_id

    def update_hybrid_stage(self, stage_id: str, status: str, result: dict[str, Any]) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE hybrid_stages SET status=?, result_json=?, updated_at=? WHERE id=?",
                (status, json.dumps(result), utc_now(), stage_id),
            )

    def get_event(self, event_id: int) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        if row is None:
            raise KeyError(event_id)
        return self._event_row(row)

    def list_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (max(1, min(limit, 200)),)
            ).fetchall()
        return [self._event_row(row) for row in rows]

    def update_event_outcome(self, event_id: int, outcome: dict[str, Any]) -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE events SET outcome_json=? WHERE id=?",
                (json.dumps(outcome), event_id),
            )
        return self.get_event(event_id)

    @staticmethod
    def _event_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "type": row["event_type"],
            "source": row["source"],
            "payload": json.loads(row["payload_json"]),
            "outcome": json.loads(row["outcome_json"]) if row["outcome_json"] else None,
            "created_at": row["created_at"],
        }
