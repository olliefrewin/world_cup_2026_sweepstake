# JS bridge -- all methods on this class are callable from the frontend via
# window.pywebview.api.<method>(...) which returns a Promise.

from __future__ import annotations

import csv
import io
import json
import logging
import os
from pathlib import Path

import webview

from sweepstake.parsers.classifier import classify, ClassifierError
from sweepstake.parsers.part1 import parse as parse_part1
from sweepstake.parsers.part2 import parse as parse_part2
from sweepstake.scoring.engine import (
    combine_scores,
    leaderboard_sort_key,
    score_part1,
    score_part2,
    tiebreaker_distance,
)
from sweepstake.data.manual import seed_golden_boot_resolutions
from sweepstake.constants import GROUP_LETTERS

log = logging.getLogger(__name__)

_VERSION = "1.0.0"


def _ok(data=None) -> dict:
    return {"ok": True, "data": data}


def _err(message: str) -> dict:
    return {"ok": False, "error": message}


class SweepstakeAPI:
    def __init__(self, repository) -> None:
        self._repo = repository
        self._pending_upload: dict | None = None  # staged parse result awaiting confirmation

    # ------------------------------------------------------------------
    # Leaderboard
    # ------------------------------------------------------------------

    def get_leaderboard(self) -> dict:
        try:
            actuals = self._repo.build_actuals()
            participants = self._repo.list_participants()
            rows = []
            for p in participants:
                pid = p["id"]
                name = p["name"]
                p1_pred = self._repo.build_part1_prediction(pid)
                p2_pred = self._repo.build_part2_prediction(pid)

                if p1_pred:
                    gb_matched = self._repo.is_golden_boot_matched(pid)
                    bd1 = score_part1(p1_pred, actuals, golden_boot_matched=gb_matched)
                else:
                    bd1 = None

                if p2_pred:
                    bd2 = score_part2(p2_pred, actuals)
                else:
                    bd2 = None

                if bd1 and bd2:
                    combined = combine_scores(bd1, bd2)
                    grand_total = combined.grand_total
                    tb = tiebreaker_distance(p2_pred, actuals)
                    part1_total = combined.part1_total
                    part2_total = combined.part2_total
                    tb_pred = p2_pred.tiebreaker_final_goals
                elif bd1:
                    grand_total = bd1.part1_total
                    tb = 999_999
                    part1_total = bd1.part1_total
                    part2_total = None
                    tb_pred = None
                else:
                    grand_total = 0
                    tb = 999_999
                    part1_total = None
                    part2_total = None
                    tb_pred = None

                rows.append({
                    "participant_id": pid,
                    "name": name,
                    "part1_total": part1_total,
                    "part2_total": part2_total,
                    "grand_total": grand_total,
                    "tiebreaker_pred": tb_pred,
                    "_sort_key": leaderboard_sort_key(name, grand_total, tb),
                })

            rows.sort(key=lambda r: r["_sort_key"])
            for i, row in enumerate(rows):
                row["rank"] = i + 1
                del row["_sort_key"]

            return _ok(rows)
        except Exception as exc:
            log.exception("get_leaderboard failed")
            return _err(str(exc))

    def get_score_breakdown(self, participant_id: int) -> dict:
        try:
            actuals = self._repo.build_actuals()
            p1_pred = self._repo.build_part1_prediction(participant_id)
            p2_pred = self._repo.build_part2_prediction(participant_id)

            breakdown = {}
            if p1_pred:
                gb_matched = self._repo.is_golden_boot_matched(participant_id)
                bd1 = score_part1(p1_pred, actuals, golden_boot_matched=gb_matched)
                breakdown["part1"] = {
                    "group_winners":  bd1.part1_group_winners,
                    "group_runners_up": bd1.part1_group_runners_up,
                    "finalists":      bd1.part1_finalists,
                    "winner":         bd1.part1_winner,
                    "golden_boot":    bd1.part1_golden_boot,
                    "total":          bd1.part1_total,
                }
            if p2_pred:
                bd2 = score_part2(p2_pred, actuals)
                breakdown["part2"] = {
                    "r32":      bd2.part2_r32,
                    "r16":      bd2.part2_r16,
                    "qf":       bd2.part2_qf,
                    "sf":       bd2.part2_sf,
                    "champion": bd2.part2_champion,
                    "total":    bd2.part2_total,
                }
            return _ok(breakdown)
        except Exception as exc:
            log.exception("get_score_breakdown failed")
            return _err(str(exc))

    # ------------------------------------------------------------------
    # Submissions
    # ------------------------------------------------------------------

    def open_file_dialog(self) -> dict:
        # Opens the native file picker and returns the chosen path (or None).
        try:
            window = webview.windows[0]
            result = window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=("Excel files (*.xlsx)",),
            )
            if result and len(result) > 0:
                return _ok(result[0])
            return _ok(None)
        except Exception as exc:
            log.exception("open_file_dialog failed")
            return _err(str(exc))

    def stage_upload(self, file_path: str) -> dict:
        # Parse the file and hold the result in memory for confirmation -- does not write to DB.
        try:
            kind = classify(file_path)
        except ClassifierError as exc:
            return _err(str(exc))

        try:
            if kind == "part1":
                result = parse_part1(file_path)
            else:
                result = parse_part2(file_path)
        except Exception as exc:
            return _err(f"Failed to parse file: {exc}")

        if not result.is_valid:
            return _err("Validation errors:\n" + "\n".join(result.errors))

        # Check for duplicate submission
        name = result.participant_name
        participants = {p["name"]: p["id"] for p in self._repo.list_participants()}
        if name in participants:
            pid = participants[name]
            existing = self._repo.get_part1(pid) if kind == "part1" else self._repo.get_part2(pid)
            if existing:
                uploaded_at = existing.get("uploaded_at", "unknown date")[:16].replace("T", " ")
                return _err(
                    f"Participant '{name}' has already submitted Part "
                    f"{'1' if kind == 'part1' else '2'} (uploaded {uploaded_at} UTC). "
                    f"To replace it, remove the existing submission first using the Submissions tab."
                )

        # Stage it
        self._pending_upload = {
            "kind": kind,
            "file_path": file_path,
            "filename": Path(file_path).name,
            "result": result,
        }

        # Build a preview to show the user before they confirm
        preview = self._build_preview(kind, result)
        return _ok({"kind": kind, "preview": preview, "warnings": result.warnings})

    def confirm_upload(self) -> dict:
        # Write the staged upload to the DB.
        if not self._pending_upload:
            return _err("No staged upload to confirm.")
        try:
            kind = self._pending_upload["kind"]
            result = self._pending_upload["result"]
            filename = self._pending_upload["filename"]
            name = result.participant_name
            pid = self._repo.get_or_create_participant(name)
            if kind == "part1":
                self._repo.save_part1(pid, result, filename)
                # If a golden boot canonical is already set, seed resolutions
                canonical = self._repo.get_setting("golden_boot_canonical")
                if canonical:
                    seed_golden_boot_resolutions(self._repo, canonical)
            else:
                self._repo.save_part2(pid, result, filename)
            self._pending_upload = None
            return _ok(f"Submission for '{name}' saved successfully.")
        except Exception as exc:
            log.exception("confirm_upload failed")
            return _err(str(exc))

    def cancel_upload(self) -> dict:
        self._pending_upload = None
        return _ok()

    def list_submissions(self) -> dict:
        try:
            part1_rows = self._repo.list_all_part1()
            part2_rows = self._repo.list_all_part2()
            # Index part2 by participant_id for quick lookup
            part2_by_pid = {r["participant_id"]: r for r in part2_rows}
            combined = []
            # Build a unified list keyed by participant
            all_pids = {r["participant_id"] for r in part1_rows} | {r["participant_id"] for r in part2_rows}
            by_pid: dict[int, dict] = {}
            for r in part1_rows:
                pid = r["participant_id"]
                by_pid.setdefault(pid, {"participant_id": pid, "name": r["participant_name"]})
                by_pid[pid]["part1"] = {
                    "uploaded_at": r["uploaded_at"][:16].replace("T", " "),
                    "filename": r["filename"],
                    "submitted_on": r.get("submitted_on", ""),
                }
            for r in part2_rows:
                pid = r["participant_id"]
                by_pid.setdefault(pid, {"participant_id": pid, "name": r["participant_name"]})
                by_pid[pid]["part2"] = {
                    "uploaded_at": r["uploaded_at"][:16].replace("T", " "),
                    "filename": r["filename"],
                }
            return _ok(sorted(by_pid.values(), key=lambda x: x["name"].lower()))
        except Exception as exc:
            log.exception("list_submissions failed")
            return _err(str(exc))

    def remove_submission(self, participant_id: int, part: str) -> dict:
        try:
            if part == "part1":
                self._repo.delete_part1(participant_id)
            elif part == "part2":
                self._repo.delete_part2(participant_id)
            else:
                return _err(f"Unknown part: {part}")
            return _ok()
        except Exception as exc:
            log.exception("remove_submission failed")
            return _err(str(exc))

    # ------------------------------------------------------------------
    # Actuals
    # ------------------------------------------------------------------

    def get_api_status(self) -> dict:
        try:
            calls_today = self._repo.api_calls_today()
            last_refresh = self._repo.get_setting("last_refresh_at") or "Never"
            if last_refresh != "Never":
                last_refresh = last_refresh[:16].replace("T", " ") + " UTC"
            api_key_set = bool(self._repo.get_setting("api_key"))
            return _ok({
                "calls_today": calls_today,
                "quota": 100,
                "last_refresh": last_refresh,
                "api_key_set": api_key_set,
            })
        except Exception as exc:
            return _err(str(exc))

    def refresh_now(self) -> dict:
        try:
            api_key = self._repo.get_setting("api_key")
            if not api_key:
                return _err("No API key configured. Enter your key in the Settings tab first.")
            from sweepstake.data.apifootball import APIFootballClient, APIFootballError
            client = APIFootballClient(api_key, self._repo)
            client.refresh_all()
            return _ok("Results refreshed successfully.")
        except Exception as exc:
            log.exception("refresh_now failed")
            return _err(str(exc))

    def get_actuals_grid(self) -> dict:
        try:
            import sqlite3
            conn = self._repo._conn_or_raise()
            api_rows = {r[0]: r[1] for r in conn.execute("SELECT key, value FROM actuals_api WHERE key NOT LIKE '_cache.%'")}
            override_rows = {r[0]: r[1] for r in conn.execute("SELECT key, value FROM actuals_override")}
            all_keys = sorted(set(api_rows) | set(override_rows))
            grid = []
            for key in all_keys:
                grid.append({
                    "key": key,
                    "api_value": api_rows.get(key),
                    "override_value": override_rows.get(key),
                    "effective": override_rows.get(key) if key in override_rows else api_rows.get(key),
                })
            return _ok(grid)
        except Exception as exc:
            log.exception("get_actuals_grid failed")
            return _err(str(exc))

    def set_override(self, key: str, value: str, note: str = "") -> dict:
        try:
            self._repo.upsert_actual_override(key, value or None, note)
            return _ok()
        except Exception as exc:
            return _err(str(exc))

    def delete_override(self, key: str) -> dict:
        try:
            self._repo.delete_actual_override(key)
            return _ok()
        except Exception as exc:
            return _err(str(exc))

    def add_manual_actual(self, key: str, value: str, note: str = "") -> dict:
        try:
            self._repo.upsert_actual_override(key, value or None, note)
            return _ok()
        except Exception as exc:
            return _err(str(exc))

    # ------------------------------------------------------------------
    # Golden Boot
    # ------------------------------------------------------------------

    def get_golden_boot_pending(self) -> dict:
        try:
            rows = self._repo.list_golden_boot_resolutions(status="pending")
            return _ok(rows)
        except Exception as exc:
            return _err(str(exc))

    def resolve_golden_boot(self, participant_id: int, matched: bool) -> dict:
        try:
            rows = self._repo.list_golden_boot_resolutions()
            row = next((r for r in rows if r["participant_id"] == participant_id), None)
            if not row:
                return _err(f"No resolution record found for participant {participant_id}")
            canonical = self._repo.get_setting("golden_boot_canonical")
            self._repo.upsert_golden_boot_resolution(
                participant_id,
                row["raw_text"],
                "matched" if matched else "rejected",
                canonical if matched else None,
            )
            return _ok()
        except Exception as exc:
            return _err(str(exc))

    def set_golden_boot_canonical(self, canonical: str) -> dict:
        try:
            self._repo.set_setting("golden_boot_canonical", canonical)
            self._repo.upsert_actual_api("golden_boot_canonical", canonical)
            counts = seed_golden_boot_resolutions(self._repo, canonical)
            return _ok(counts)
        except Exception as exc:
            return _err(str(exc))

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def get_settings(self) -> dict:
        try:
            return _ok({
                "api_key": self._repo.get_setting("api_key") or "",
                "db_path": str(self._repo._path),
            })
        except Exception as exc:
            return _err(str(exc))

    def save_api_key(self, api_key: str) -> dict:
        try:
            self._repo.set_setting("api_key", api_key.strip())
            return _ok("API key saved.")
        except Exception as exc:
            return _err(str(exc))

    def test_api_connection(self, api_key: str = "") -> dict:
        # api_key is passed directly from the input field so the user can test before saving.
        try:
            key = api_key.strip() or self._repo.get_setting("api_key") or ""
            if not key:
                return _err("No API key configured. Enter a key and click Save (or Test Connection).")
            import requests as _requests
            resp = _requests.get(
                "https://v3.football.api-sports.io/status",
                headers={"x-apisports-key": key},
                timeout=10,
            )
            if resp.ok:
                data = resp.json()
                # api-sports returns requests.current and requests.limit_day (not "remaining")
                req = data.get("response", {}).get("requests", {})
                current   = req.get("current", 0)
                limit_day = req.get("limit_day", 100)
                remaining = limit_day - current
                return _ok(f"Connected. Requests used today: {current} / {limit_day} ({remaining} remaining)")
            return _err(f"Connection failed: HTTP {resp.status_code}")
        except Exception as exc:
            return _err(str(exc))

    def export_csv(self) -> dict:
        try:
            window = webview.windows[0]
            save_path = window.create_file_dialog(
                webview.SAVE_DIALOG,
                save_filename="sweepstake_results.csv",
                file_types=("CSV files (*.csv)",),
            )
            if not save_path:
                return _ok(None)
            if isinstance(save_path, (list, tuple)):
                save_path = save_path[0]

            actuals = self._repo.build_actuals()
            participants = self._repo.list_participants()

            with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Rank", "Name",
                    "Part 1 Total", "Part 2 Total", "Grand Total",
                    "Tiebreaker Prediction",
                    "P1 Group Winners", "P1 Group Runners-Up",
                    "P1 Finalists", "P1 Winner", "P1 Golden Boot",
                    "P2 R32", "P2 R16", "P2 QF", "P2 SF", "P2 Champion",
                ])

                rows = []
                from sweepstake.scoring.engine import tiebreaker_distance, leaderboard_sort_key
                for p in participants:
                    pid = p["id"]
                    p1 = self._repo.build_part1_prediction(pid)
                    p2 = self._repo.build_part2_prediction(pid)
                    gb = self._repo.is_golden_boot_matched(pid)
                    bd1 = score_part1(p1, actuals, golden_boot_matched=gb) if p1 else None
                    bd2 = score_part2(p2, actuals) if p2 else None
                    total = (bd1.part1_total if bd1 else 0) + (bd2.part2_total if bd2 else 0)
                    tb = tiebreaker_distance(p2, actuals) if p2 else 999_999
                    rows.append((leaderboard_sort_key(p["name"], total, tb), p, bd1, bd2, total, p2))

                rows.sort(key=lambda x: x[0])
                for rank, (_, p, bd1, bd2, total, p2) in enumerate(rows, 1):
                    tb_pred = p2.tiebreaker_final_goals if p2 else ""
                    writer.writerow([
                        rank, p["name"],
                        bd1.part1_total if bd1 else "",
                        bd2.part2_total if bd2 else "",
                        total,
                        tb_pred if tb_pred is not None else "",
                        bd1.part1_group_winners if bd1 else "",
                        bd1.part1_group_runners_up if bd1 else "",
                        bd1.part1_finalists if bd1 else "",
                        bd1.part1_winner if bd1 else "",
                        bd1.part1_golden_boot if bd1 else "",
                        bd2.part2_r32 if bd2 else "",
                        bd2.part2_r16 if bd2 else "",
                        bd2.part2_qf if bd2 else "",
                        bd2.part2_sf if bd2 else "",
                        bd2.part2_champion if bd2 else "",
                    ])

            return _ok(f"Exported to {save_path}")
        except Exception as exc:
            log.exception("export_csv failed")
            return _err(str(exc))

    def get_version(self) -> dict:
        return _ok(_VERSION)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_preview(self, kind: str, result) -> dict:
        if kind == "part1":
            return {
                "name": result.participant_name,
                "submitted_on": result.submitted_on,
                "group_picks": {g: {"winner": w, "runner_up": r} for g, (w, r) in result.group_picks.items()},
                "finalist_1": result.finalist_1,
                "finalist_2": result.finalist_2,
                "winner": result.winner,
                "golden_boot": result.golden_boot_raw,
            }
        else:
            return {
                "name": result.participant_name,
                "champion": result.champion,
                "tiebreaker": result.tiebreaker_final_goals,
                "r32_winners": result.r32_winners,
                "r16_winners": result.r16_winners,
                "qf_winners": result.qf_winners,
                "sf_winners": result.sf_winners,
            }
