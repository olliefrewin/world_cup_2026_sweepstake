# API-Football (api-sports.io) client with SQLite-backed caching.
# Free tier: 100 requests/day. We cache aggressively and never auto-poll.

from __future__ import annotations

import logging
from datetime import date, datetime, timezone, timedelta

import requests

from sweepstake.data.team_names import canonicalise
from sweepstake.constants import (
    GROUP_LETTERS,
    QF_ALL_SLOTS,
    R16_ALL_SLOTS,
    R32_ALL_SLOTS,
    SF_SLOTS,
    TOURNAMENT_END,
    TOURNAMENT_START,
)

log = logging.getLogger(__name__)

_BASE_URL = "https://v3.football.api-sports.io"
_LEAGUE_ID = 1       # FIFA World Cup
_SEASON    = 2026

# Cache TTL: 30 min on match days, 24h otherwise (in seconds)
_TTL_MATCH_DAY_S  = 30 * 60
_TTL_DEFAULT_S    = 24 * 60 * 60


class APIFootballError(RuntimeError):
    pass


class APIFootballClient:
    def __init__(self, api_key: str, repository) -> None:
        # repository: a connected Repository instance (for caching + call logging)
        self._api_key = api_key
        self._repo = repository
        self._session = requests.Session()
        self._session.headers.update({"x-apisports-key": api_key})

    def _cache_ttl(self) -> int:
        today = date.today().isoformat()
        if TOURNAMENT_START <= today <= TOURNAMENT_END:
            return _TTL_MATCH_DAY_S
        return _TTL_DEFAULT_S

    def _is_fresh(self, fetched_at_iso: str | None) -> bool:
        if not fetched_at_iso:
            return False
        try:
            fetched = datetime.fromisoformat(fetched_at_iso)
            age = datetime.now(timezone.utc) - fetched.replace(tzinfo=timezone.utc)
            return age.total_seconds() < self._cache_ttl()
        except ValueError:
            return False

    def _get(self, endpoint: str, params: dict) -> dict:
        # Checks the actuals_api cache key "{endpoint}?{params}" before hitting the network.
        cache_key = f"_cache.{endpoint}.{sorted(params.items())}"
        cached_row = self._repo.get_all_effective_actuals().get(cache_key)
        # We don't use the effective actuals cache for raw API responses --
        # raw responses are stored in actuals_api with fetched_at, so check directly.
        conn = self._repo._conn_or_raise()
        row = conn.execute(
            "SELECT value, fetched_at FROM actuals_api WHERE key=?", (cache_key,)
        ).fetchone()
        if row and self._is_fresh(row["fetched_at"]):
            log.debug("Cache hit for %s", endpoint)
            self._repo.log_api_call(endpoint, 200, cached=True)
            import json
            return json.loads(row["value"])

        # Live fetch
        url = f"{_BASE_URL}/{endpoint.lstrip('/')}"
        log.info("API fetch: %s %s", url, params)
        resp = self._session.get(url, params=params, timeout=15)

        self._repo.log_api_call(endpoint, resp.status_code, cached=False)

        if resp.status_code == 429:
            raise APIFootballError(
                "API rate limit reached for today. Scores will update tomorrow, "
                "or you can enter results manually."
            )
        if not resp.ok:
            raise APIFootballError(
                f"API request failed: {resp.status_code} {resp.text[:200]}"
            )

        data = resp.json()
        import json as _json
        self._repo.upsert_actual_api(cache_key, _json.dumps(data))
        return data

    # ------------------------------------------------------------------
    # High-level fetchers -- each writes canonical actuals into the DB
    # ------------------------------------------------------------------

    def refresh_all(self) -> None:
        # Fetch standings (group winners/runners-up) and fixture results.
        log.info("Refreshing all actuals from API-Football")
        self._fetch_standings()
        self._fetch_knockout_results()
        self._fetch_top_scorer()
        self._repo.set_setting("last_refresh_at", datetime.now(timezone.utc).isoformat())

    def _fetch_standings(self) -> None:
        data = self._get("standings", {"league": _LEAGUE_ID, "season": _SEASON})
        standings_list = data.get("response", [])
        if not standings_list:
            log.warning("No standings data returned from API")
            return

        # The API returns a list; standings are nested under league.standings
        for entry in standings_list:
            league = entry.get("league", {})
            for group_standings in league.get("standings", []):
                if not group_standings:
                    continue
                # Determine group letter from the first team's group field
                group_str = group_standings[0].get("group", "")
                # API format: "Group A", "Group B", etc.
                letter = group_str.replace("Group", "").strip()
                if letter not in GROUP_LETTERS:
                    continue

                # Sort by rank to get winner (rank 1) and runner-up (rank 2)
                sorted_group = sorted(group_standings, key=lambda x: x.get("rank", 99))
                if len(sorted_group) >= 1:
                    winner_name = canonicalise(
                        sorted_group[0].get("team", {}).get("name", "")
                    )
                    self._repo.upsert_actual_api(f"group_winner.{letter}", winner_name)
                if len(sorted_group) >= 2:
                    runner_name = canonicalise(
                        sorted_group[1].get("team", {}).get("name", "")
                    )
                    self._repo.upsert_actual_api(f"group_runner_up.{letter}", runner_name)

    def _fetch_knockout_results(self) -> None:
        # Fetch all fixtures and filter by round to populate knockout actuals.
        data = self._get("fixtures", {"league": _LEAGUE_ID, "season": _SEASON, "status": "FT"})
        fixtures = data.get("response", [])

        for fixture in fixtures:
            league_info = fixture.get("league", {})
            round_str: str = league_info.get("round", "")
            home = canonicalise(fixture["teams"]["home"]["name"])
            away = canonicalise(fixture["teams"]["away"]["name"])
            home_goals = fixture["goals"]["home"]
            away_goals = fixture["goals"]["away"]

            # Determine winner (penalties/ET all count as a win)
            if home_goals is None or away_goals is None:
                continue
            winner = home if home_goals > away_goals else away

            # Map API round strings to our slot system
            # We use fixture order within the round to assign slot IDs.
            # This is a best-effort mapping -- manual override handles any mismatches.
            self._store_knockout_result(round_str, winner, home, away, home_goals + away_goals)

    def _store_knockout_result(
        self,
        round_str: str,
        winner: str,
        home: str,
        away: str,
        total_goals: int,
    ) -> None:
        r = round_str.lower()
        # We store results by team name pair lookup rather than positional slot
        # because we can't reliably map API fixture order to our L1..R8 scheme.
        # The leaderboard engine matches by slot; we populate slots by searching
        # for which r32_pairs entry contains these two teams.
        if "round of 32" in r:
            self._store_by_pair(R32_ALL_SLOTS, "r32_winner", winner, home, away)
        elif "round of 16" in r:
            self._store_by_pair(R16_ALL_SLOTS, "r16_winner", winner, home, away)
        elif "quarter-final" in r or "quarterfinal" in r:
            self._store_by_pair(QF_ALL_SLOTS, "qf_winner", winner, home, away)
        elif "semi-final" in r or "semifinal" in r:
            self._store_by_pair(SF_SLOTS, "sf_winner", winner, home, away)
        elif "final" in r and "semi" not in r and "quarter" not in r:
            self._repo.upsert_actual_api("champion", winner)
            self._repo.upsert_actual_api("finalist_1", home)
            self._repo.upsert_actual_api("finalist_2", away)
            self._repo.upsert_actual_api("final_total_goals", str(total_goals))

    def _store_by_pair(
        self,
        slots: list[str],
        key_prefix: str,
        winner: str,
        home: str,
        away: str,
    ) -> None:
        # Find the slot whose r32_pairs contains these two teams (order-independent).
        # For higher rounds we don't have pair data in the DB, so we store sequentially.
        conn = self._repo._conn_or_raise()
        pair_json_col = {
            "r32_winner": "r32_pairs_json",
            "r16_winner": "r16_winners_json",
            "qf_winner":  "qf_winners_json",
            "sf_winner":  "sf_winners_json",
        }.get(key_prefix)

        if key_prefix == "r32_winner" and pair_json_col:
            import json
            rows = conn.execute("SELECT r32_pairs_json FROM part2_submissions LIMIT 1").fetchone()
            if rows:
                pairs = json.loads(rows["r32_pairs_json"])
                for slot, (t_a, t_b) in pairs.items():
                    if {t_a, t_b} == {home, away}:
                        self._repo.upsert_actual_api(f"{key_prefix}.{slot}", winner)
                        return

        # Fallback: find the first unpopulated slot and fill it in order
        existing = self._repo.get_all_effective_actuals()
        for slot in slots:
            key = f"{key_prefix}.{slot}"
            if key not in existing:
                self._repo.upsert_actual_api(key, winner)
                return

    def _fetch_top_scorer(self) -> None:
        data = self._get("players/topscorers", {"league": _LEAGUE_ID, "season": _SEASON})
        players = data.get("response", [])
        if not players:
            return
        top = players[0]
        name = top.get("player", {}).get("name", "")
        if name:
            self._repo.upsert_actual_api("golden_boot_api_name", name)
            log.info("Top scorer from API: %s", name)
