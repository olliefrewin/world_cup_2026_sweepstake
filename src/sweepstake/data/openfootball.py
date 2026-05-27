from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone

import requests

from sweepstake.data.team_names import canonicalise
from sweepstake.constants import (
    GROUP_LETTERS,
    QF_ALL_SLOTS,
    R16_ALL_SLOTS,
    R32_ALL_SLOTS,
    SF_SLOTS,
)

log = logging.getLogger(__name__)

_DATA_URL = (
    "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
)
_CACHE_TTL_S = 30 * 60


class OpenFootballError(RuntimeError):
    pass


class OpenFootballClient:
    def __init__(self, repository) -> None:
        self._repo = repository
        self._session = requests.Session()

    def _is_fresh(self, fetched_at_iso: str | None) -> bool:
        if not fetched_at_iso:
            return False
        try:
            fetched = datetime.fromisoformat(fetched_at_iso)
            age = datetime.now(timezone.utc) - fetched.replace(tzinfo=timezone.utc)
            return age.total_seconds() < _CACHE_TTL_S
        except ValueError:
            return False

    def _fetch_schedule(self) -> list[dict]:
        cache_key = "_cache.openfootball.schedule"
        conn = self._repo._conn_or_raise()
        row = conn.execute(
            "SELECT value, fetched_at FROM actuals_api WHERE key=?", (cache_key,)
        ).fetchone()
        if row and self._is_fresh(row["fetched_at"]):
            log.debug("Cache hit for openfootball schedule")
            return json.loads(row["value"])

        log.info("Fetching schedule from %s", _DATA_URL)
        resp = self._session.get(_DATA_URL, timeout=15)
        if resp.status_code == 404:
            raise OpenFootballError(
                "2026 World Cup data not yet available. "
                "Check back once the tournament has started, or enter results manually."
            )
        if not resp.ok:
            raise OpenFootballError(
                f"Failed to fetch data: HTTP {resp.status_code}"
            )

        matches = resp.json().get("matches", [])
        self._repo.upsert_actual_api(cache_key, json.dumps(matches))
        return matches

    def refresh_all(self) -> None:
        log.info("Refreshing all actuals from openfootball")
        matches = self._fetch_schedule()
        group_matches = [m for m in matches if m.get("group") and m.get("score")]
        knockout_matches = [m for m in matches if not m.get("group") and m.get("score")]
        self._compute_group_standings(group_matches)
        self._process_knockout(knockout_matches)
        self._compute_top_scorer(matches)
        self._repo.set_setting("last_refresh_at", datetime.now(timezone.utc).isoformat())

    # ------------------------------------------------------------------

    def _compute_group_standings(self, matches: list[dict]) -> None:
        groups: dict[str, dict[str, dict]] = defaultdict(
            lambda: defaultdict(lambda: {"pts": 0, "gf": 0, "ga": 0})
        )
        for m in matches:
            ft = m["score"]["ft"]
            g1, g2 = ft[0], ft[1]
            t1 = canonicalise(m["team1"])
            t2 = canonicalise(m["team2"])
            letter = m["group"].replace("Group", "").strip()
            if letter not in GROUP_LETTERS:
                continue
            g = groups[letter]
            g[t1]["gf"] += g1
            g[t1]["ga"] += g2
            g[t2]["gf"] += g2
            g[t2]["ga"] += g1
            if g1 > g2:
                g[t1]["pts"] += 3
            elif g2 > g1:
                g[t2]["pts"] += 3
            else:
                g[t1]["pts"] += 1
                g[t2]["pts"] += 1

        for letter, teams in groups.items():
            ranked = sorted(
                teams.items(),
                key=lambda kv: (
                    -kv[1]["pts"],
                    -(kv[1]["gf"] - kv[1]["ga"]),
                    -kv[1]["gf"],
                    kv[0],
                ),
            )
            if len(ranked) >= 1:
                self._repo.upsert_actual_api(f"group_winner.{letter}", ranked[0][0])
            if len(ranked) >= 2:
                self._repo.upsert_actual_api(f"group_runner_up.{letter}", ranked[1][0])

    def _winner(self, team1: str, team2: str, score: dict) -> str:
        if score.get("p"):
            p = score["p"]
            return team1 if p[0] > p[1] else team2
        ft = score["ft"]
        et = score.get("et", [0, 0])
        t1_goals = ft[0] + et[0]
        t2_goals = ft[1] + et[1]
        return team1 if t1_goals >= t2_goals else team2

    def _process_knockout(self, matches: list[dict]) -> None:
        counters: dict[str, int] = {"r32": 0, "r16": 0, "qf": 0, "sf": 0}
        for m in sorted(matches, key=lambda x: (x.get("date", ""), x.get("num", 0))):
            score = m["score"]
            t1 = canonicalise(m["team1"])
            t2 = canonicalise(m["team2"])
            winner = self._winner(t1, t2, score)
            rnd = m["round"]

            if rnd == "Round of 32":
                idx = counters["r32"]
                if idx < len(R32_ALL_SLOTS):
                    self._repo.upsert_actual_api(f"r32_winner.{R32_ALL_SLOTS[idx]}", winner)
                counters["r32"] += 1
            elif rnd == "Round of 16":
                idx = counters["r16"]
                if idx < len(R16_ALL_SLOTS):
                    self._repo.upsert_actual_api(f"r16_winner.{R16_ALL_SLOTS[idx]}", winner)
                counters["r16"] += 1
            elif rnd == "Quarter-final":
                idx = counters["qf"]
                if idx < len(QF_ALL_SLOTS):
                    self._repo.upsert_actual_api(f"qf_winner.{QF_ALL_SLOTS[idx]}", winner)
                counters["qf"] += 1
            elif rnd == "Semi-final":
                idx = counters["sf"]
                if idx < len(SF_SLOTS):
                    self._repo.upsert_actual_api(f"sf_winner.{SF_SLOTS[idx]}", winner)
                counters["sf"] += 1
            elif rnd == "Final":
                ft = score["ft"]
                et = score.get("et", [0, 0])
                total_goals = ft[0] + ft[1] + et[0] + et[1]
                self._repo.upsert_actual_api("champion", winner)
                self._repo.upsert_actual_api("finalist_1", t1)
                self._repo.upsert_actual_api("finalist_2", t2)
                self._repo.upsert_actual_api("final_total_goals", str(total_goals))

    def _compute_top_scorer(self, matches: list[dict]) -> None:
        tally: dict[str, int] = defaultdict(int)
        for m in matches:
            for goal_list in (m.get("goals1", []), m.get("goals2", [])):
                for g in goal_list:
                    if g.get("owngoal"):
                        continue
                    name = g.get("name", "").strip()
                    if name:
                        tally[name] += 1
        if not tally:
            return
        top = max(tally, key=lambda n: tally[n])
        self._repo.upsert_actual_api("golden_boot_api_name", top)
        log.info("Top scorer: %s (%d goals)", top, tally[top])
