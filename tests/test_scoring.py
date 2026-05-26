# Tests for the scoring engine. This is the most important test file.
# Every edge case from the spec s11.1 is covered here.

from __future__ import annotations

import pytest

from sweepstake.scoring.engine import (
    combine_scores,
    leaderboard_sort_key,
    score_part1,
    score_part2,
    tiebreaker_distance,
)
from sweepstake.scoring.models import Actuals, Part1Prediction, Part2Prediction, ScoreBreakdown
from sweepstake.constants import (
    GROUP_LETTERS,
    POINTS_CHAMPION,
    POINTS_FINALIST,
    POINTS_GOLDEN_BOOT,
    POINTS_GROUP_RUNNER_UP,
    POINTS_GROUP_WINNER,
    POINTS_QF_WINNER,
    POINTS_R16_WINNER,
    POINTS_R32_WINNER,
    POINTS_SF_WINNER,
    POINTS_WINNER,
    QF_ALL_SLOTS,
    R16_ALL_SLOTS,
    R32_ALL_SLOTS,
    SF_SLOTS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_actuals(
    group_winners: dict | None = None,
    group_runners_up: dict | None = None,
    r32_winners: dict | None = None,
    r16_winners: dict | None = None,
    qf_winners: dict | None = None,
    sf_winners: dict | None = None,
    champion: str | None = None,
    golden_boot_canonical: str | None = None,
    finalists_set: frozenset | None = None,
    final_total_goals: int | None = None,
) -> Actuals:
    return Actuals(
        group_winners=group_winners or {},
        group_runners_up=group_runners_up or {},
        r32_winners=r32_winners or {s: None for s in R32_ALL_SLOTS},
        r16_winners=r16_winners or {s: None for s in R16_ALL_SLOTS},
        qf_winners=qf_winners or {s: None for s in QF_ALL_SLOTS},
        sf_winners=sf_winners or {s: None for s in SF_SLOTS},
        champion=champion,
        golden_boot_canonical=golden_boot_canonical,
        finalists_set=finalists_set or frozenset(),
        final_total_goals=final_total_goals,
    )


def _all_correct_group_picks() -> dict[str, tuple[str, str]]:
    # Each group: first team wins, second is runner-up
    from sweepstake.constants import GROUPS
    return {g: (GROUPS[g][0], GROUPS[g][1]) for g in GROUP_LETTERS}


def _all_correct_group_actuals() -> tuple[dict, dict]:
    from sweepstake.constants import GROUPS
    winners = {g: GROUPS[g][0] for g in GROUP_LETTERS}
    runners = {g: GROUPS[g][1] for g in GROUP_LETTERS}
    return winners, runners


def _make_part1(
    group_picks: dict | None = None,
    finalist_1: str | None = None,
    finalist_2: str | None = None,
    winner: str | None = None,
    golden_boot_raw: str = "",
) -> Part1Prediction:
    return Part1Prediction(
        participant_name="Test",
        submitted_on=None,
        group_picks=group_picks or {},
        finalists=(finalist_1, finalist_2),
        winner=winner,
        golden_boot_raw=golden_boot_raw,
    )


def _make_part2(
    r32_winners: dict | None = None,
    r16_winners: dict | None = None,
    qf_winners: dict | None = None,
    sf_winners: dict | None = None,
    champion: str | None = None,
    tiebreaker: int | None = None,
) -> Part2Prediction:
    return Part2Prediction(
        participant_name="Test",
        r32_pairs={s: ("", "") for s in R32_ALL_SLOTS},
        r32_winners=r32_winners or {s: None for s in R32_ALL_SLOTS},
        r16_winners=r16_winners or {s: None for s in R16_ALL_SLOTS},
        qf_winners=qf_winners or {s: None for s in QF_ALL_SLOTS},
        sf_winners=sf_winners or {s: None for s in SF_SLOTS},
        champion=champion,
        tiebreaker_final_goals=tiebreaker,
    )


# ---------------------------------------------------------------------------
# Part 1 -- group stage
# ---------------------------------------------------------------------------

def test_all_group_winners_and_runners_correct():
    winners, runners = _all_correct_group_actuals()
    pred = _make_part1(group_picks=_all_correct_group_picks())
    actuals = _make_actuals(group_winners=winners, group_runners_up=runners)
    bd = score_part1(pred, actuals)
    assert bd.part1_group_winners == POINTS_GROUP_WINNER * 12   # 120
    assert bd.part1_group_runners_up == POINTS_GROUP_RUNNER_UP * 12  # 60
    assert bd.part1_total == 180


def test_all_group_winners_correct_runners_all_wrong():
    winners, runners = _all_correct_group_actuals()
    # Swap runner to team[2] (wrong)
    from sweepstake.constants import GROUPS
    wrong_picks = {g: (GROUPS[g][0], GROUPS[g][2]) for g in GROUP_LETTERS}
    pred = _make_part1(group_picks=wrong_picks)
    actuals = _make_actuals(group_winners=winners, group_runners_up=runners)
    bd = score_part1(pred, actuals)
    assert bd.part1_group_winners == POINTS_GROUP_WINNER * 12   # 120
    assert bd.part1_group_runners_up == 0
    assert bd.part1_total == 120


def test_mixed_six_winners_six_runners():
    from sweepstake.constants import GROUPS
    winners, runners = _all_correct_group_actuals()
    mixed_picks = {}
    for i, g in enumerate(GROUP_LETTERS):
        if i < 6:
            # correct winner, wrong runner
            mixed_picks[g] = (GROUPS[g][0], GROUPS[g][2])
        else:
            # wrong winner (team[2]), correct runner
            mixed_picks[g] = (GROUPS[g][2], GROUPS[g][1])
    pred = _make_part1(group_picks=mixed_picks)
    actuals = _make_actuals(group_winners=winners, group_runners_up=runners)
    bd = score_part1(pred, actuals)
    assert bd.part1_group_winners == POINTS_GROUP_WINNER * 6    # 60
    assert bd.part1_group_runners_up == POINTS_GROUP_RUNNER_UP * 6  # 30
    assert bd.part1_total == 90


# ---------------------------------------------------------------------------
# Part 1 -- finalists (edge cases)
# ---------------------------------------------------------------------------

def test_duplicate_finalist_in_actual_final_scores_once():
    # Participant picks team X for BOTH finalist slots; X is in the final.
    # Should score 15 pts (not 30).
    actuals = _make_actuals(finalists_set=frozenset({"Brazil", "England"}))
    pred = _make_part1(finalist_1="Brazil", finalist_2="Brazil")
    bd = score_part1(pred, actuals)
    assert bd.part1_finalists == POINTS_FINALIST  # 15, not 30


def test_duplicate_finalist_not_in_final_scores_zero():
    actuals = _make_actuals(finalists_set=frozenset({"France", "Germany"}))
    pred = _make_part1(finalist_1="Brazil", finalist_2="Brazil")
    bd = score_part1(pred, actuals)
    assert bd.part1_finalists == 0


def test_both_finalists_correct_different_teams():
    actuals = _make_actuals(finalists_set=frozenset({"Brazil", "England"}))
    pred = _make_part1(finalist_1="Brazil", finalist_2="England")
    bd = score_part1(pred, actuals)
    assert bd.part1_finalists == POINTS_FINALIST * 2  # 30


def test_finalist_plus_winner_stacks():
    # Participant picks Brazil as finalist #1 AND Brazil as winner; Brazil wins.
    # Should score 15 (finalist) + 25 (winner) = 40.
    actuals = _make_actuals(
        finalists_set=frozenset({"Brazil", "England"}),
        champion="Brazil",
    )
    pred = _make_part1(finalist_1="Brazil", finalist_2=None, winner="Brazil")
    bd = score_part1(pred, actuals)
    assert bd.part1_finalists == POINTS_FINALIST   # 15
    assert bd.part1_winner == POINTS_WINNER        # 25
    assert bd.part1_total == 40


def test_both_finalists_and_winner_stacks_to_55():
    # Picks Brazil + Argentina as finalists, Brazil as winner.
    # Final is Brazil vs Argentina, Brazil wins.
    # Should score 15 + 15 + 25 = 55.
    actuals = _make_actuals(
        finalists_set=frozenset({"Brazil", "Argentina"}),
        champion="Brazil",
    )
    pred = _make_part1(finalist_1="Brazil", finalist_2="Argentina", winner="Brazil")
    bd = score_part1(pred, actuals)
    assert bd.part1_finalists == POINTS_FINALIST * 2  # 30
    assert bd.part1_winner == POINTS_WINNER            # 25
    assert bd.part1_total == 55


def test_wrong_finalist_no_points():
    actuals = _make_actuals(finalists_set=frozenset({"France", "Germany"}))
    pred = _make_part1(finalist_1="Brazil", finalist_2="England")
    bd = score_part1(pred, actuals)
    assert bd.part1_finalists == 0


# ---------------------------------------------------------------------------
# Part 1 -- winner
# ---------------------------------------------------------------------------

def test_correct_winner():
    actuals = _make_actuals(champion="Brazil")
    pred = _make_part1(winner="Brazil")
    bd = score_part1(pred, actuals)
    assert bd.part1_winner == POINTS_WINNER


def test_wrong_winner():
    actuals = _make_actuals(champion="Brazil")
    pred = _make_part1(winner="England")
    bd = score_part1(pred, actuals)
    assert bd.part1_winner == 0


def test_winner_unknown_scores_zero():
    actuals = _make_actuals(champion=None)
    pred = _make_part1(winner="Brazil")
    bd = score_part1(pred, actuals)
    assert bd.part1_winner == 0


# ---------------------------------------------------------------------------
# Part 1 -- Golden Boot
# ---------------------------------------------------------------------------

def test_golden_boot_matched():
    actuals = _make_actuals(golden_boot_canonical="Kylian Mbappe")
    pred = _make_part1(golden_boot_raw="Mbappe")
    bd = score_part1(pred, actuals, golden_boot_matched=True)
    assert bd.part1_golden_boot == POINTS_GOLDEN_BOOT


def test_golden_boot_not_matched():
    actuals = _make_actuals(golden_boot_canonical="Kylian Mbappe")
    pred = _make_part1(golden_boot_raw="Ronaldo")
    bd = score_part1(pred, actuals, golden_boot_matched=False)
    assert bd.part1_golden_boot == 0


def test_golden_boot_canonical_not_set():
    actuals = _make_actuals(golden_boot_canonical=None)
    pred = _make_part1(golden_boot_raw="Mbappe")
    # Even if matched=True, canonical must be set to award points
    bd = score_part1(pred, actuals, golden_boot_matched=True)
    assert bd.part1_golden_boot == 0


# ---------------------------------------------------------------------------
# Partial scoring (only group stage known)
# ---------------------------------------------------------------------------

def test_partial_scoring_group_stage_only():
    winners, runners = _all_correct_group_actuals()
    pred_part1 = _make_part1(group_picks=_all_correct_group_picks())
    pred_part2 = _make_part2()
    actuals = _make_actuals(group_winners=winners, group_runners_up=runners)
    bd1 = score_part1(pred_part1, actuals)
    bd2 = score_part2(pred_part2, actuals)
    combined = combine_scores(bd1, bd2)
    assert combined.part2_r32 == 0
    assert combined.part2_r16 == 0
    assert combined.grand_total == bd1.part1_total


# ---------------------------------------------------------------------------
# Part 2 -- knockout rounds
# ---------------------------------------------------------------------------

def _all_correct_r32() -> tuple[dict, dict]:
    actual = {s: f"Team_{s}" for s in R32_ALL_SLOTS}
    pred = {s: f"Team_{s}" for s in R32_ALL_SLOTS}
    return actual, pred


def test_all_r32_correct():
    actual_r32, pred_r32 = _all_correct_r32()
    actuals = _make_actuals(r32_winners=actual_r32)
    pred = _make_part2(r32_winners=pred_r32)
    bd = score_part2(pred, actuals)
    assert bd.part2_r32 == POINTS_R32_WINNER * 16  # 48


def test_all_r16_correct():
    actual_r16 = {s: f"Team_{s}" for s in R16_ALL_SLOTS}
    actuals = _make_actuals(r16_winners=actual_r16)
    pred = _make_part2(r16_winners={s: f"Team_{s}" for s in R16_ALL_SLOTS})
    bd = score_part2(pred, actuals)
    assert bd.part2_r16 == POINTS_R16_WINNER * 8   # 40


def test_all_qf_correct():
    actual_qf = {s: f"Team_{s}" for s in QF_ALL_SLOTS}
    actuals = _make_actuals(qf_winners=actual_qf)
    pred = _make_part2(qf_winners={s: f"Team_{s}" for s in QF_ALL_SLOTS})
    bd = score_part2(pred, actuals)
    assert bd.part2_qf == POINTS_QF_WINNER * 4     # 32


def test_all_sf_correct():
    actual_sf = {s: f"Team_{s}" for s in SF_SLOTS}
    actuals = _make_actuals(sf_winners=actual_sf)
    pred = _make_part2(sf_winners={s: f"Team_{s}" for s in SF_SLOTS})
    bd = score_part2(pred, actuals)
    assert bd.part2_sf == POINTS_SF_WINNER * 2     # 24


def test_champion_correct():
    actuals = _make_actuals(champion="Brazil")
    pred = _make_part2(champion="Brazil")
    bd = score_part2(pred, actuals)
    assert bd.part2_champion == POINTS_CHAMPION    # 20


def test_unknown_actual_scores_zero():
    # If the actual for a slot is None, that slot is skipped (no points).
    actuals = _make_actuals(r32_winners={s: None for s in R32_ALL_SLOTS})
    pred = _make_part2(r32_winners={s: "Brazil" for s in R32_ALL_SLOTS})
    bd = score_part2(pred, actuals)
    assert bd.part2_r32 == 0


# ---------------------------------------------------------------------------
# Blank / empty predictions
# ---------------------------------------------------------------------------

def test_blank_part1_does_not_crash():
    actuals = _make_actuals(
        group_winners={"A": "Mexico"},
        group_runners_up={"A": "South Korea"},
        champion="Brazil",
        finalists_set=frozenset({"Brazil", "England"}),
    )
    pred = _make_part1()
    bd = score_part1(pred, actuals)
    assert bd.grand_total == 0


def test_blank_part2_does_not_crash():
    actuals = _make_actuals(
        r32_winners={"L1": "Brazil"},
        champion="Brazil",
    )
    pred = _make_part2()
    bd = score_part2(pred, actuals)
    assert bd.grand_total == 0


# ---------------------------------------------------------------------------
# Tiebreaker
# ---------------------------------------------------------------------------

def test_tiebreaker_closer_wins():
    actuals_3goals = _make_actuals(final_total_goals=4)
    pred_3 = _make_part2(tiebreaker=3)
    pred_1 = _make_part2(tiebreaker=1)
    d3 = tiebreaker_distance(pred_3, actuals_3goals)  # abs(3-4) = 1
    d1 = tiebreaker_distance(pred_1, actuals_3goals)  # abs(1-4) = 3
    assert d3 < d1


def test_tiebreaker_equal_distance():
    actuals = _make_actuals(final_total_goals=4)
    pred_6 = _make_part2(tiebreaker=6)  # distance 2
    pred_2 = _make_part2(tiebreaker=2)  # distance 2
    assert tiebreaker_distance(pred_6, actuals) == tiebreaker_distance(pred_2, actuals)


def test_tiebreaker_final_not_played_returns_large_sentinel():
    actuals = _make_actuals(final_total_goals=None)
    pred = _make_part2(tiebreaker=3)
    assert tiebreaker_distance(pred, actuals) == 999_999


def test_tiebreaker_pred_blank_returns_large_sentinel():
    actuals = _make_actuals(final_total_goals=4)
    pred = _make_part2(tiebreaker=None)
    assert tiebreaker_distance(pred, actuals) == 999_999


# ---------------------------------------------------------------------------
# Leaderboard sort key
# ---------------------------------------------------------------------------

def test_leaderboard_sort_descending_total():
    a = leaderboard_sort_key("Alice", 100, 1)
    b = leaderboard_sort_key("Bob", 90, 1)
    assert a < b  # Alice ranks higher (lower sort key)


def test_leaderboard_sort_tiebreaker():
    # Same total, Alice is closer to actual goals
    a = leaderboard_sort_key("Alice", 100, 1)
    b = leaderboard_sort_key("Bob", 100, 3)
    assert a < b


def test_leaderboard_sort_alphabetical_on_full_tie():
    a = leaderboard_sort_key("Alice", 100, 999_999)
    b = leaderboard_sort_key("Bob", 100, 999_999)
    assert a < b  # Alice before Bob


def test_leaderboard_sort_case_insensitive():
    a = leaderboard_sort_key("alice", 100, 999_999)
    b = leaderboard_sort_key("Bob", 100, 999_999)
    assert a < b


# ---------------------------------------------------------------------------
# Maximum possible scores (sanity check against spec totals)
# ---------------------------------------------------------------------------

def test_max_part1_constant():
    from sweepstake.constants import MAX_PART1
    assert MAX_PART1 == 250


def test_max_part2_constant():
    from sweepstake.constants import MAX_PART2
    assert MAX_PART2 == 164


def test_max_total_constant():
    from sweepstake.constants import MAX_TOTAL
    assert MAX_TOTAL == 414
