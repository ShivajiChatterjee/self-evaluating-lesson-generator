import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from src.state import LessonState


DATABASE_PATH = Path(__file__).resolve().parent.parent / "data" / "lesson_memory.db"


def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            overall_pass INTEGER NOT NULL,
            retry_count INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            attempt INTEGER NOT NULL,
            criterion TEXT NOT NULL,
            reason TEXT NOT NULL,
            required_fix TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES runs(id)
        );

        CREATE TABLE IF NOT EXISTS learned_rules (
            topic TEXT NOT NULL,
            criterion TEXT NOT NULL,
            guidance TEXT NOT NULL,
            failure_count INTEGER NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (topic, criterion)
        );
        """
    )
    connection.commit()
    return connection


def persist_run_memory(state: LessonState) -> dict:
    timestamp = datetime.now(timezone.utc).isoformat()
    with closing(_connect()) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO runs (topic, overall_pass, retry_count, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    state["topic"],
                    int(state["evaluation"]["overall_pass"]),
                    state["retry_count"],
                    timestamp,
                ),
            )
            run_id = cursor.lastrowid

            for rejection in state["rejection_history"]:
                for check in rejection["failed_checks"]:
                    required_fix = check["required_fix"]
                    guidance = (
                        required_fix
                        if isinstance(required_fix, str) and required_fix.strip()
                        else check["reason"]
                    )
                    connection.execute(
                        """
                        INSERT INTO failures (
                            run_id, topic, attempt, criterion, reason,
                            required_fix, created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            run_id,
                            state["topic"],
                            rejection["attempt"],
                            check["criterion"],
                            check["reason"],
                            required_fix,
                            timestamp,
                        ),
                    )
                    connection.execute(
                        """
                        INSERT INTO learned_rules (
                            topic, criterion, guidance, failure_count, updated_at
                        )
                        VALUES (?, ?, ?, 1, ?)
                        ON CONFLICT(topic, criterion) DO UPDATE SET
                            guidance = excluded.guidance,
                            failure_count = learned_rules.failure_count + 1,
                            updated_at = excluded.updated_at
                        """,
                        (
                            state["topic"],
                            check["criterion"],
                            guidance,
                            timestamp,
                        ),
                    )

    return {}


def load_memory_guidance(state: LessonState) -> dict:
    with closing(_connect()) as connection:
        rows = connection.execute(
            """
            SELECT criterion, guidance, failure_count
            FROM learned_rules
            WHERE topic = ?
            ORDER BY failure_count DESC, updated_at DESC
            LIMIT 4
            """,
            (state["topic"],),
        ).fetchall()

    guidance = [
        f"{criterion} (seen {failure_count} "
        f"{'time' if failure_count == 1 else 'times'}): {rule}"
        for criterion, rule, failure_count in rows
    ]
    return {"memory_guidance": guidance}
