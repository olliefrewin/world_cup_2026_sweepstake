# All database access for the sweepstake app.
# One module, one connection, plain sqlite3 -- no ORM.

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path

from sweepstake.scoring.models import (
    Actuals,
    Part1Prediction,
    Part2Prediction,
)
from sweepstake.constants import (
    QF_ALL_SLOTS,
    R16_ALL_SLOTS,
    R32_ALL_SLOTS,
    SF_SLOTS,
)

log = logging.getLogger(__name__)

_DB_NAME = "sweepstake.db"


def _db_path() -> Path:
    # Store the DB in %LOCALAPPDATA%\WorldCupSweepstake\ so it survives next to the .exe
    # and is writable even when the app is installed in Program Files.
    local_app_data = os.environ.get("LOCALAPPDATA", str(Path.home()))
    folder = Path(local_app_data) / "WorldCupSweepstake"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / _DB_NAME


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Repository:
    def __init__(self, db_path: Path | None = None) -> None:
        self._path = db_path or _db_path()
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._apply_schema()
        log.info("Database opened at %s", self._path)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "Repository":
        self.connect()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def _conn_or_raise(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Repository is not connected. Call connect() first.")
        return self._conn

    def _apply_schema(self) -> None:
        try:
            # Works both from source tree and inside a PyInstaller bundle
            schema_text = (
                resources.files("sweepstake.storage")
                .joinpath("schema.sql")
                .read_text(encoding="utf-8")
            )
        except Exception:
            schema_path = Path(__file__).parent / "schema.sql"
            schema_text = schema_path.read_text(encoding="utf-8")

        conn = self._conn_or_raise()
        conn.executescript(schema_text)
        conn.commit()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def get_setting(self, key: str) -> str | None:
        conn = self._conn_or_raise()
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def set_setting(self, key: str, value: str) -> None:
        conn = self._conn_or_raise()
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        conn.commit()

    # ------------------------------------------------------------------
    # Participants
    # ------------------------------------------------------------------

    def get_or_create_participant(self, name: str) -> int:
        conn = self._conn_or_raise()
        row = conn.execute("SELECT id FROM participants WHERE name=?", (name,)).fetchone()
        if row:
            return row["id"]
        cur = conn.execute("INSERT INTO participants(name) VALUES(?)", (name,))
        conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def list_participants(self) -> list[dict]:
        conn = self._conn_or_raise()
        return [dict(r) for r in conn.execute("SELECT id, name FROM participants ORDER BY name")]

    # ------------------------------------------------------------------
    # Part 1 submissions
    # ------------------------------------------------------------------

    def save_part1(self, participant_id: int, result, filename: str) -> None:
        # result is a Part1ParseResult from the parser
        conn = self._conn_or_raise()
        group_picks_json = json.dumps(
            {g: list(pair) for g, pair in result.group_picks.items()}
        )
        conn.execute(
            """
            INSERT INTO part1_submissions
                (participant_id, submitted_on, uploaded_at, filename,
                 group_picks_json, finalist_1, finalist_2, winner, golden_boot_raw)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                participant_id,
                result.submitted_on,
                _now(),
                filename,
                group_picks_json,
                result.finalist_1,
                result.finalist_2,
                result.winner,
                result.golden_boot_raw,
            ),
        )
        conn.commit()

    def get_part1(self, participant_id: int) -> dict | None:
        conn = self._conn_or_raise()
        row = conn.execute(
            "SELECT * FROM part1_submissions WHERE participant_id=?", (participant_id,)
        ).fetchone()
        return dict(row) if row else None

    def delete_part1(self, participant_id: int) -> None:
        conn = self._conn_or_raise()
        conn.execute(
            "DELETE FROM part1_submissions WHERE participant_id=?", (participant_id,)
        )
        conn.commit()

    def list_all_part1(self) -> list[dict]:
        conn = self._conn_or_raise()
        rows = conn.execute(
            """
            SELECT s.*, p.name AS participant_name
            FROM part1_submissions s
            JOIN participants p ON s.participant_id = p.id
            ORDER BY p.name
            """
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Part 2 submissions
    # ------------------------------------------------------------------

    def save_part2(self, participant_id: int, result, filename: str) -> None:
        conn = self._conn_or_raise()
        conn.execute(
            """
            INSERT INTO part2_submissions
                (participant_id, uploaded_at, filename,
                 r32_pairs_json, r32_winners_json, r16_winners_json,
                 qf_winners_json, sf_winners_json, champion, tiebreaker_final_goals)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                participant_id,
                _now(),
                filename,
                json.dumps({k: list(v) for k, v in result.r32_pairs.items()}),
                json.dumps(result.r32_winners),
                json.dumps(result.r16_winners),
                json.dumps(result.qf_winners),
                json.dumps(result.sf_winners),
                result.champion,
                result.tiebreaker_final_goals,
            ),
        )
        conn.commit()

    def get_part2(self, participant_id: int) -> dict | None:
        conn = self._conn_or_raise()
        row = conn.execute(
            "SELECT * FROM part2_submissions WHERE participant_id=?", (participant_id,)
        ).fetchone()
        return dict(row) if row else None

    def delete_part2(self, participant_id: int) -> None:
        conn = self._conn_or_raise()
        conn.execute(
            "DELETE FROM part2_submissions WHERE participant_id=?", (participant_id,)
        )
        conn.commit()

    def list_all_part2(self) -> list[dict]:
        conn = self._conn_or_raise()
        rows = conn.execute(
            """
            SELECT s.*, p.name AS participant_name
            FROM part2_submissions s
            JOIN participants p ON s.participant_id = p.id
            ORDER BY p.name
            """
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Actuals
    # ------------------------------------------------------------------

    def upsert_actual_api(self, key: str, value: str | None) -> None:
        conn = self._conn_or_raise()
        conn.execute(
            "INSERT INTO actuals_api(key, value, fetched_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, fetched_at=excluded.fetched_at",
            (key, value, _now()),
        )
        conn.commit()

    def upsert_actual_override(self, key: str, value: str | None, note: str = "") -> None:
        conn = self._conn_or_raise()
        conn.execute(
            "INSERT INTO actuals_override(key, value, set_at, note) VALUES(?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, set_at=excluded.set_at, note=excluded.note",
            (key, value, _now(), note),
        )
        conn.commit()

    def delete_actual_override(self, key: str) -> None:
        conn = self._conn_or_raise()
        conn.execute("DELETE FROM actuals_override WHERE key=?", (key,))
        conn.commit()

    def get_all_effective_actuals(self) -> dict[str, str | None]:
        conn = self._conn_or_raise()
        rows = conn.execute("SELECT key, value FROM actuals_effective").fetchall()
        return {r["key"]: r["value"] for r in rows}

    def build_actuals(self) -> Actuals:
        # Reads the effective actuals view and constructs the Actuals dataclass.
        raw = self.get_all_effective_actuals()

        def _get(key: str) -> str | None:
            return raw.get(key)

        group_winners: dict[str, str] = {}
        group_runners_up: dict[str, str] = {}
        for letter in "ABCDEFGHIJKL":
            w = _get(f"group_winner.{letter}")
            r = _get(f"group_runner_up.{letter}")
            if w:
                group_winners[letter] = w
            if r:
                group_runners_up[letter] = r

        r32_winners = {s: _get(f"r32_winner.{s}") for s in R32_ALL_SLOTS}
        r16_winners = {s: _get(f"r16_winner.{s}") for s in R16_ALL_SLOTS}
        qf_winners  = {s: _get(f"qf_winner.{s}")  for s in QF_ALL_SLOTS}
        sf_winners  = {s: _get(f"sf_winner.{s}")  for s in SF_SLOTS}
        champion    = _get("champion")

        finalist_1  = _get("finalist_1")
        finalist_2  = _get("finalist_2")
        finalists_set: frozenset[str] = frozenset(
            t for t in [finalist_1, finalist_2] if t
        )

        golden_boot = _get("golden_boot_canonical")

        final_goals_raw = _get("final_total_goals")
        final_total_goals: int | None = None
        if final_goals_raw is not None:
            try:
                final_total_goals = int(final_goals_raw)
            except ValueError:
                pass

        return Actuals(
            group_winners=group_winners,
            group_runners_up=group_runners_up,
            r32_winners=r32_winners,
            r16_winners=r16_winners,
            qf_winners=qf_winners,
            sf_winners=sf_winners,
            champion=champion,
            golden_boot_canonical=golden_boot,
            finalists_set=finalists_set,
            final_total_goals=final_total_goals,
        )

    # ------------------------------------------------------------------
    # Golden Boot resolutions
    # ------------------------------------------------------------------

    def upsert_golden_boot_resolution(
        self,
        participant_id: int,
        raw_text: str,
        status: str,
        resolved_canonical: str | None = None,
    ) -> None:
        conn = self._conn_or_raise()
        conn.execute(
            """
            INSERT INTO golden_boot_resolutions
                (participant_id, raw_text, resolved_canonical, status, resolved_at)
            VALUES (?,?,?,?,?)
            ON CONFLICT(participant_id) DO UPDATE SET
                raw_text=excluded.raw_text,
                resolved_canonical=excluded.resolved_canonical,
                status=excluded.status,
                resolved_at=excluded.resolved_at
            """,
            (
                participant_id,
                raw_text,
                resolved_canonical,
                status,
                _now() if status in ("matched", "rejected") else None,
            ),
        )
        conn.commit()

    def list_golden_boot_resolutions(self, status: str | None = None) -> list[dict]:
        conn = self._conn_or_raise()
        if status:
            rows = conn.execute(
                """
                SELECT r.*, p.name AS participant_name
                FROM golden_boot_resolutions r
                JOIN participants p ON r.participant_id = p.id
                WHERE r.status=?
                ORDER BY p.name
                """,
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT r.*, p.name AS participant_name
                FROM golden_boot_resolutions r
                JOIN participants p ON r.participant_id = p.id
                ORDER BY p.name
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def is_golden_boot_matched(self, participant_id: int) -> bool:
        conn = self._conn_or_raise()
        row = conn.execute(
            "SELECT status FROM golden_boot_resolutions WHERE participant_id=?",
            (participant_id,),
        ).fetchone()
        return bool(row and row["status"] == "matched")

    # ------------------------------------------------------------------
    # API call tracking
    # ------------------------------------------------------------------

    def log_api_call(self, endpoint: str, status_code: int, cached: bool = False) -> None:
        conn = self._conn_or_raise()
        conn.execute(
            "INSERT INTO api_calls(endpoint, called_at, status_code, cached) VALUES(?,?,?,?)",
            (endpoint, _now(), status_code, 1 if cached else 0),
        )
        conn.commit()

    def api_calls_today(self) -> int:
        conn = self._conn_or_raise()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM api_calls WHERE called_at LIKE ? AND cached=0",
            (f"{today}%",),
        ).fetchone()
        return row["n"] if row else 0

    # ------------------------------------------------------------------
    # Prediction retrieval (converts DB rows to scoring model objects)
    # ------------------------------------------------------------------

    def build_part1_prediction(self, participant_id: int) -> Part1Prediction | None:
        row = self.get_part1(participant_id)
        if not row:
            return None
        group_picks_raw = json.loads(row["group_picks_json"])
        group_picks = {g: (v[0], v[1]) for g, v in group_picks_raw.items()}
        return Part1Prediction(
            participant_name=row.get("participant_name", ""),
            submitted_on=row["submitted_on"],
            group_picks=group_picks,
            finalists=(row["finalist_1"], row["finalist_2"]),
            winner=row["winner"],
            golden_boot_raw=row["golden_boot_raw"] or "",
        )

    def build_part2_prediction(self, participant_id: int) -> Part2Prediction | None:
        row = self.get_part2(participant_id)
        if not row:
            return None
        return Part2Prediction(
            participant_name=row.get("participant_name", ""),
            r32_pairs={k: tuple(v) for k, v in json.loads(row["r32_pairs_json"]).items()},
            r32_winners=json.loads(row["r32_winners_json"]),
            r16_winners=json.loads(row["r16_winners_json"]),
            qf_winners=json.loads(row["qf_winners_json"]),
            sf_winners=json.loads(row["sf_winners_json"]),
            champion=row["champion"],
            tiebreaker_final_goals=row["tiebreaker_final_goals"],
        )
