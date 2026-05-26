# Tests for the SQLite storage layer.

from __future__ import annotations

import pytest
from pathlib import Path

from sweepstake.storage.repository import Repository
from sweepstake.parsers.part1 import Part1ParseResult
from sweepstake.parsers.part2 import Part2ParseResult
from sweepstake.constants import GROUPS, R32_ALL_SLOTS, R16_ALL_SLOTS, QF_ALL_SLOTS, SF_SLOTS


@pytest.fixture
def repo(tmp_path) -> Repository:
    r = Repository(db_path=tmp_path / "test.db")
    r.connect()
    yield r
    r.close()


def _dummy_part1_result(name="Alice") -> Part1ParseResult:
    picks = {g: (GROUPS[g][0], GROUPS[g][1]) for g in GROUPS}
    return Part1ParseResult(
        participant_name=name,
        submitted_on="2026-06-01",
        group_picks=picks,
        finalist_1="Brazil",
        finalist_2="England",
        winner="Brazil",
        golden_boot_raw="Lionel Messi",
    )


def _dummy_part2_result(name="Alice") -> Part2ParseResult:
    return Part2ParseResult(
        participant_name=name,
        r32_pairs={s: ("Mexico", "South Africa") for s in R32_ALL_SLOTS},
        r32_winners={s: "Mexico" for s in R32_ALL_SLOTS},
        r16_winners={s: "Mexico" for s in R16_ALL_SLOTS},
        qf_winners={s: "Mexico" for s in QF_ALL_SLOTS},
        sf_winners={s: "Mexico" for s in SF_SLOTS},
        champion="Brazil",
        tiebreaker_final_goals=3,
    )


# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------

def test_set_and_get_setting(repo):
    repo.set_setting("api_key", "test123")
    assert repo.get_setting("api_key") == "test123"


def test_get_missing_setting_returns_none(repo):
    assert repo.get_setting("nonexistent") is None


def test_setting_upserts(repo):
    repo.set_setting("api_key", "first")
    repo.set_setting("api_key", "second")
    assert repo.get_setting("api_key") == "second"


# ------------------------------------------------------------------
# Participants
# ------------------------------------------------------------------

def test_get_or_create_participant(repo):
    pid = repo.get_or_create_participant("Alice")
    assert isinstance(pid, int)
    # Second call returns same id
    assert repo.get_or_create_participant("Alice") == pid


def test_list_participants(repo):
    repo.get_or_create_participant("Alice")
    repo.get_or_create_participant("Bob")
    names = [p["name"] for p in repo.list_participants()]
    assert "Alice" in names
    assert "Bob" in names


# ------------------------------------------------------------------
# Part 1 submissions
# ------------------------------------------------------------------

def test_save_and_retrieve_part1(repo):
    pid = repo.get_or_create_participant("Alice")
    repo.save_part1(pid, _dummy_part1_result(), "part1.xlsx")
    row = repo.get_part1(pid)
    assert row is not None
    assert row["finalist_1"] == "Brazil"
    assert row["golden_boot_raw"] == "Lionel Messi"


def test_duplicate_part1_raises(repo):
    pid = repo.get_or_create_participant("Alice")
    repo.save_part1(pid, _dummy_part1_result(), "part1.xlsx")
    with pytest.raises(Exception):  # UNIQUE constraint
        repo.save_part1(pid, _dummy_part1_result(), "part1_again.xlsx")


def test_delete_part1(repo):
    pid = repo.get_or_create_participant("Alice")
    repo.save_part1(pid, _dummy_part1_result(), "part1.xlsx")
    repo.delete_part1(pid)
    assert repo.get_part1(pid) is None


def test_build_part1_prediction(repo):
    pid = repo.get_or_create_participant("Alice")
    repo.save_part1(pid, _dummy_part1_result(), "part1.xlsx")
    pred = repo.build_part1_prediction(pid)
    assert pred is not None
    assert pred.winner == "Brazil"
    assert pred.finalists == ("Brazil", "England")
    assert pred.group_picks["A"] == (GROUPS["A"][0], GROUPS["A"][1])


# ------------------------------------------------------------------
# Part 2 submissions
# ------------------------------------------------------------------

def test_save_and_retrieve_part2(repo):
    pid = repo.get_or_create_participant("Alice")
    repo.save_part2(pid, _dummy_part2_result(), "part2.xlsx")
    row = repo.get_part2(pid)
    assert row is not None
    assert row["champion"] == "Brazil"
    assert row["tiebreaker_final_goals"] == 3


def test_build_part2_prediction(repo):
    pid = repo.get_or_create_participant("Alice")
    repo.save_part2(pid, _dummy_part2_result(), "part2.xlsx")
    pred = repo.build_part2_prediction(pid)
    assert pred is not None
    assert pred.champion == "Brazil"
    assert pred.tiebreaker_final_goals == 3


def test_delete_part2(repo):
    pid = repo.get_or_create_participant("Alice")
    repo.save_part2(pid, _dummy_part2_result(), "part2.xlsx")
    repo.delete_part2(pid)
    assert repo.get_part2(pid) is None


# ------------------------------------------------------------------
# Actuals
# ------------------------------------------------------------------

def test_upsert_and_read_actual_api(repo):
    repo.upsert_actual_api("champion", "Brazil")
    actuals = repo.build_actuals()
    assert actuals.champion == "Brazil"


def test_override_wins_over_api(repo):
    repo.upsert_actual_api("champion", "England")
    repo.upsert_actual_override("champion", "Brazil", note="API was wrong")
    actuals = repo.build_actuals()
    assert actuals.champion == "Brazil"


def test_override_without_api_entry(repo):
    repo.upsert_actual_override("champion", "France")
    actuals = repo.build_actuals()
    assert actuals.champion == "France"


def test_delete_override_reverts_to_api(repo):
    repo.upsert_actual_api("champion", "England")
    repo.upsert_actual_override("champion", "Brazil")
    repo.delete_actual_override("champion")
    actuals = repo.build_actuals()
    assert actuals.champion == "England"


def test_finalists_set_built_correctly(repo):
    repo.upsert_actual_api("finalist_1", "Brazil")
    repo.upsert_actual_api("finalist_2", "Argentina")
    actuals = repo.build_actuals()
    assert actuals.finalists_set == frozenset({"Brazil", "Argentina"})


def test_final_goals_parsed(repo):
    repo.upsert_actual_api("final_total_goals", "4")
    actuals = repo.build_actuals()
    assert actuals.final_total_goals == 4


# ------------------------------------------------------------------
# Golden Boot
# ------------------------------------------------------------------

def test_golden_boot_matched(repo):
    pid = repo.get_or_create_participant("Alice")
    repo.upsert_golden_boot_resolution(pid, "Messi", "matched", "Lionel Messi")
    assert repo.is_golden_boot_matched(pid) is True


def test_golden_boot_rejected_not_matched(repo):
    pid = repo.get_or_create_participant("Alice")
    repo.upsert_golden_boot_resolution(pid, "Ronaldo", "rejected")
    assert repo.is_golden_boot_matched(pid) is False


def test_golden_boot_pending_not_matched(repo):
    pid = repo.get_or_create_participant("Alice")
    repo.upsert_golden_boot_resolution(pid, "Mbappe", "pending")
    assert repo.is_golden_boot_matched(pid) is False


# ------------------------------------------------------------------
# API call tracking
# ------------------------------------------------------------------

def test_api_calls_today(repo):
    repo.log_api_call("/fixtures", 200, cached=False)
    repo.log_api_call("/standings", 200, cached=False)
    repo.log_api_call("/fixtures", 200, cached=True)  # cached -- not counted
    assert repo.api_calls_today() == 2
